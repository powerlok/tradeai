from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from datetime import datetime, timezone

from app.db.engine import AsyncSession
from app.db.models import PaperTrade, Trade
from app.quant.paper import PaperPosition, PaperTradingEngine
from app.observability.metrics import inc_paper_trade
from app.core.config import settings
from app.quant.risk import RiskLimits, assess_portfolio_risk
from app.services.operational_state import entry_enabled, get_operational_state

router = APIRouter()


async def get_db():
    async with AsyncSession() as session:
        yield session


class PaperOpenRequest(BaseModel):
    symbol: str
    direction: str
    quantity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    opened_at: int
    decision_snapshot: dict[str, object] | None = None


class PaperCloseRequest(BaseModel):
    price: float | None = Field(default=None, gt=0)
    closed_at: int


@router.get("/paper/positions")
async def positions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PaperTrade).where(PaperTrade.status == "OPEN").order_by(PaperTrade.id.desc()))
    open_positions = result.scalars().all()
    response = []
    for position in open_positions:
        price_result = await db.execute(select(Trade).where(Trade.symbol == position.symbol).order_by(Trade.event_time.desc()).limit(1))
        latest_trade = price_result.scalars().first()
        mark_price = float(latest_trade.price) if latest_trade else None
        direction = 1.0 if position.direction in {"BUY", "LONG"} else -1.0
        unrealized_pnl = (position.quantity * (mark_price - position.entry_price) * direction) if mark_price is not None else None
        entry_value = position.quantity * position.entry_price
        response.append({
            key: value for key, value in position.__dict__.items() if not key.startswith("_")
        } | {
            "mark_price": mark_price,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": (unrealized_pnl / entry_value) if unrealized_pnl is not None and entry_value else None,
            "price_updated_at": int(latest_trade.event_time) if latest_trade else None,
        })
    start_of_day = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    realized_today = float((await db.execute(select(func.coalesce(func.sum(PaperTrade.pnl), 0.0)).where(PaperTrade.status == "CLOSED", PaperTrade.closed_at >= start_of_day))).scalar_one())
    risk = assess_portfolio_risk(
        open_positions, realized_today, 0.0, 0.0, 0.0,
        RiskLimits(settings.paper_initial_equity, settings.paper_max_trade_risk_pct, settings.paper_max_portfolio_risk_pct, settings.paper_max_exposure_pct, settings.paper_max_daily_loss_pct),
    )
    return {"positions": response, "risk": risk.as_dict()}


@router.get("/paper/history")
async def paper_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = int((await db.execute(select(func.count()).select_from(PaperTrade).where(PaperTrade.status == "CLOSED"))).scalar_one())
    result = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.status == "CLOSED")
        .order_by(PaperTrade.closed_at.desc(), PaperTrade.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    trades = result.scalars().all()
    realized_pnl = float((await db.execute(select(func.coalesce(func.sum(PaperTrade.pnl), 0.0)).where(PaperTrade.status == "CLOSED"))).scalar_one())
    winning_trades = int((await db.execute(select(func.count()).select_from(PaperTrade).where(PaperTrade.status == "CLOSED", PaperTrade.pnl > 0))).scalar_one())
    return {
        "trades": [{key: value for key, value in trade.__dict__.items() if not key.startswith("_")} for trade in trades],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
        "summary": {"realized_pnl": realized_pnl, "winning_trades": winning_trades, "losing_trades": total - winning_trades},
    }


@router.post("/paper/positions")
async def open_position(payload: PaperOpenRequest):
    operational_state = await get_operational_state()
    if not entry_enabled(operational_state):
        raise HTTPException(status_code=423, detail=f"paper entry blocked by operational state: {operational_state}")
    engine = PaperTradingEngine(initial_cash=settings.paper_initial_equity)
    position = PaperPosition(payload.symbol.upper(), payload.direction.upper(), payload.quantity, payload.entry_price, payload.stop, payload.target, payload.opened_at)
    try:
        engine.open_position(position)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    async with AsyncSession() as db:
        open_result = await db.execute(select(PaperTrade).where(PaperTrade.status == "OPEN"))
        open_positions = open_result.scalars().all()
        start_of_day = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        realized_today = float((await db.execute(select(func.coalesce(func.sum(PaperTrade.pnl), 0.0)).where(PaperTrade.status == "CLOSED", PaperTrade.closed_at >= start_of_day))).scalar_one())
        risk = assess_portfolio_risk(
            open_positions, realized_today, payload.quantity, payload.entry_price, payload.stop,
            RiskLimits(settings.paper_initial_equity, settings.paper_max_trade_risk_pct, settings.paper_max_portfolio_risk_pct, settings.paper_max_exposure_pct, settings.paper_max_daily_loss_pct),
        )
        if not risk.approved:
            raise HTTPException(status_code=409, detail=f"paper risk gate blocked entry: {', '.join(risk.reason_codes)}")
        trade = PaperTrade(
            symbol=payload.symbol.upper(), direction=payload.direction.upper(),
            quantity=payload.quantity, entry_price=payload.entry_price,
            stop=payload.stop, target=payload.target, opened_at=payload.opened_at,
            status="OPEN",
            decision_snapshot=payload.decision_snapshot or {
                "assessment_id": None,
                "status": "MANUAL_ENTRY",
                "action": "PAPER_ENTRY",
                "reason_codes": ["MANUAL_ENTRY"],
                "plan": {"entry_price": payload.entry_price, "stop": payload.stop, "target": payload.target},
                "risk": risk.as_dict(),
            },
        )
        db.add(trade)
        await db.commit()
        await db.refresh(trade)
        inc_paper_trade("open", trade.direction)
        return {"status": "OPEN", "risk": risk.as_dict(), "trade": {key: value for key, value in trade.__dict__.items() if not key.startswith("_")}}


@router.post("/paper/positions/{trade_id}/close")
async def close_position(trade_id: int, payload: PaperCloseRequest):
    async with AsyncSession() as db:
        trade = await db.get(PaperTrade, trade_id)
        if not trade or trade.status != "OPEN":
            raise HTTPException(status_code=404, detail="open paper position not found")
        exit_price = payload.price
        if exit_price is None:
            price_result = await db.execute(select(Trade).where(Trade.symbol == trade.symbol).order_by(Trade.event_time.desc()).limit(1))
            latest_trade = price_result.scalars().first()
            if latest_trade is None:
                raise HTTPException(status_code=409, detail="no current market price available")
            exit_price = float(latest_trade.price)
        direction = 1.0 if trade.direction in {"BUY", "LONG"} else -1.0
        trade.pnl = trade.quantity * (exit_price - trade.entry_price) * direction
        trade.exit_price = exit_price
        trade.closed_at = payload.closed_at
        trade.status = "CLOSED"
        await db.commit()
        inc_paper_trade("close", trade.direction)
        return {"status": "CLOSED", "trade_id": trade_id, "pnl": trade.pnl}