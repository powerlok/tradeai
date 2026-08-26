"""Periodic synchronization of public Binance klines into PostgreSQL."""
import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.engine import AsyncSession, Base, engine
from app.db.models import Candle
from app.market.binance_adapter import BinanceAdapter
from app.market.normalizer import normalize_kline
from app.quality.data_quality import QualityStatus, validate_candle
from app.observability.metrics import inc_quality_rejection

logger = logging.getLogger("candle_sync")
SYMBOLS = tuple(os.getenv("MARKET_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT,ADAUSDT,DOGEUSDT,TRXUSDT,AVAXUSDT,LINKUSDT,TONUSDT,SHIBUSDT,DOTUSDT,BCHUSDT,LTCUSDT,UNIUSDT,XLMUSDT,NEARUSDT,ATOMUSDT,APTUSDT").split(","))
SUPPORTED_TIMEFRAMES = ("1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d")
TIMEFRAMES = tuple(
    timeframe.strip()
    for timeframe in os.getenv("MARKET_TIMEFRAMES", "1d,4h,1h,15m,5m").split(",")
    if timeframe.strip() in SUPPORTED_TIMEFRAMES
)
SYNC_INTERVAL_SECONDS = 60


async def persist_klines(session: AsyncSession, symbol: str, timeframe: str, klines: list) -> int:
    if not klines:
        return 0

    timestamps = [int(kline[0]) for kline in klines]
    existing_result = await session.execute(
        select(Candle.open_time).where(
            Candle.symbol == symbol,
            Candle.timeframe == timeframe,
            Candle.open_time.in_(timestamps),
        )
    )
    existing = {row[0] for row in existing_result.all()}
    new_candles = []
    for kline in klines:
        normalized = normalize_kline(symbol, timeframe, kline)
        quality = validate_candle(normalized.__dict__)
        if quality.status is QualityStatus.INVALID:
            inc_quality_rejection("binance_rest")
            logger.warning("skipping invalid candle %s %s: %s", symbol, timeframe, quality.issues)
            continue
        open_time = normalized.open_time
        if open_time in existing:
            continue
        new_candles.append(Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            open=normalized.open,
            high=normalized.high,
            low=normalized.low,
            close=normalized.close,
            volume=normalized.volume,
            close_time=normalized.close_time,
        ))

    if new_candles:
        session.add_all(new_candles)
        await session.commit()
    return len(new_candles)


async def sync_once(adapter: BinanceAdapter) -> None:
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                klines = await adapter.get_candles(symbol, timeframe, limit=500)
                async with AsyncSession() as session:
                    inserted = await persist_klines(session, symbol, timeframe, klines)
                logger.info("%s %s: received=%d inserted=%d", symbol, timeframe, len(klines), inserted)
            except Exception:
                logger.exception("failed to sync %s %s", symbol, timeframe)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            break
        except Exception as error:
            logger.warning("database is not ready; retrying in 5s: %s", error)
            await asyncio.sleep(5)

    adapter = BinanceAdapter()
    try:
        while True:
            await sync_once(adapter)
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(run())