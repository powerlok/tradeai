"""Periodic synchronization of public Binance klines into PostgreSQL."""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.engine import AsyncSession, Base, engine
from app.db.models import Candle
from app.market.binance_adapter import BinanceAdapter

logger = logging.getLogger("candle_sync")
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
TIMEFRAMES = ("1h", "4h", "1d")
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
        open_time = int(kline[0])
        if open_time in existing:
            continue
        new_candles.append(Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            open=float(kline[1]),
            high=float(kline[2]),
            low=float(kline[3]),
            close=float(kline[4]),
            volume=float(kline[5]),
            close_time=int(kline[6]),
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