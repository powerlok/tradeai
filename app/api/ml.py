from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import desc, select
from app.db.engine import AsyncSession
from app.db.models import Candle
from app.ml.features import calculate_features

router = APIRouter()


async def get_db():
    from app.db.engine import AsyncSession as AS
    async with AS() as session:
        yield session


@router.get("/features/{symbol}")
async def get_features(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe: 1h, 4h, 1d, etc"),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate and return technical indicators for a symbol.
    
    Indicators include:
    - SMA (20, 50)
    - EMA (12, 26)
    - RSI (14)
    - MACD with Signal line
    - Bollinger Bands (20)
    - ATR (14)
    - Summary signals (overbought, oversold, trends)
    """
    symbol = symbol.upper()
    features = await calculate_features(db, symbol, timeframe, limit=200)
    
    if not features:
        raise HTTPException(
            status_code=404,
            detail=f"No candle data found for {symbol} on {timeframe} timeframe"
        )
    
    return features


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    timeframe: str = Query("1h"),
    limit: int = Query(120, ge=20, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return recent OHLCV candles for charting."""
    result = await db.execute(
        select(Candle)
        .where(Candle.symbol == symbol.upper(), Candle.timeframe == timeframe)
        .order_by(desc(Candle.open_time))
        .limit(limit)
    )
    candles = list(reversed(result.scalars().all()))
    if not candles:
        raise HTTPException(status_code=404, detail="No candle data found for the requested symbol")
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "candles": [
            {
                "timestamp": candle.open_time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in candles
        ],
    }
