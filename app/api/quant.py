from fastapi import APIRouter, Depends, Query

from app.db.engine import AsyncSession
from app.ml.features import get_recent_candles
from app.quant.engines import build_multi_timeframe_view, classify_regime

router = APIRouter()


async def get_db():
    async with AsyncSession() as session:
        yield session


@router.get("/market/multi-timeframe")
async def multi_timeframe(
    symbol: str = Query("BTCUSDT"),
    db: AsyncSession = Depends(get_db),
):
    normalized_symbol = symbol.upper()
    candles_by_timeframe = {
        timeframe: await get_recent_candles(db, normalized_symbol, timeframe, limit=200)
        for timeframe in ("1d", "4h", "1h", "15m", "5m")
    }
    views = build_multi_timeframe_view(candles_by_timeframe)
    closes = [candle.close for candle in candles_by_timeframe.get("1h", [])]
    regime = classify_regime(closes)
    return {
        "symbol": normalized_symbol,
        "timeframes": [view.__dict__ for view in views],
        "regime": regime.__dict__,
    }
