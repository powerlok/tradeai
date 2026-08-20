from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.db.engine import AsyncSession
from app.db.models import OrderBookSnapshot, Trade

router = APIRouter()


async def get_db():
    async with AsyncSession() as session:
        yield session


def summarize_orderbook(snapshot: dict) -> dict:
    bids = snapshot.get("bids", []) or []
    asks = snapshot.get("asks", []) or []
    best_bid = float(bids[0][0]) if bids else None
    best_ask = float(asks[0][0]) if asks else None
    spread = (best_ask - best_bid) if best_bid is not None and best_ask is not None else None
    mid_price = (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "mid_price": mid_price,
        "bid_qty": float(bids[0][1]) if bids else 0.0,
        "ask_qty": float(asks[0][1]) if asks else 0.0,
    }


@router.get("/market/price")
async def latest_market_price(
    symbol: str = Query("BTCUSDT", description="Trading symbol, e.g. BTCUSDT"),
    db: AsyncSession = Depends(get_db),
):
    normalized_symbol = symbol.upper()
    stmt = select(Trade).where(Trade.symbol == normalized_symbol).order_by(Trade.event_time.desc()).limit(1)
    result = await db.execute(stmt)
    trade = result.scalars().first()

    if not trade:
        raise HTTPException(status_code=404, detail=f"No live trade data found for {normalized_symbol}")

    return {
        "symbol": normalized_symbol,
        "price": float(trade.price),
        "qty": float(trade.qty),
        "event_time": int(trade.event_time),
        "source": "binance_ws",
        "updated_at": int(trade.event_time),
    }


@router.get("/market/prices")
async def market_prices(
    symbols: str = Query("BTCUSDT,ETHUSDT,SOLUSDT", description="Comma-separated symbols"),
    db: AsyncSession = Depends(get_db),
):
    selected = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if not selected:
        raise HTTPException(status_code=400, detail="At least one symbol is required")

    prices = []
    for symbol in selected:
        stmt = select(Trade).where(Trade.symbol == symbol).order_by(Trade.event_time.desc()).limit(1)
        result = await db.execute(stmt)
        trade = result.scalars().first()
        if trade is None:
            continue
        prices.append({
            "symbol": symbol,
            "price": float(trade.price),
            "qty": float(trade.qty),
            "event_time": int(trade.event_time),
            "source": "binance_ws",
        })

    return {"prices": prices}


@router.get("/market/orderbook")
async def market_orderbook(
    symbol: str = Query("BTCUSDT", description="Trading symbol, e.g. BTCUSDT"),
    db: AsyncSession = Depends(get_db),
):
    normalized_symbol = symbol.upper()
    stmt = select(OrderBookSnapshot).where(OrderBookSnapshot.symbol == normalized_symbol).order_by(OrderBookSnapshot.event_time.desc()).limit(1)
    result = await db.execute(stmt)
    snapshot = result.scalars().first()

    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No order book snapshot found for {normalized_symbol}")

    orderbook = {"bids": snapshot.bids, "asks": snapshot.asks}
    summary = summarize_orderbook(orderbook)
    return {
        "symbol": normalized_symbol,
        "event_time": int(snapshot.event_time),
        "summary": summary,
        "bids": snapshot.bids[:5],
        "asks": snapshot.asks[:5],
    }
