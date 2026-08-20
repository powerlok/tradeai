import asyncio
import logging
import json
from typing import List

from sqlalchemy import text

from app.market.ws_collector import WebSocketCollector, DEFAULT_SYMBOLS
from app.market.binance_adapter import BinanceAdapter
from app.db.engine import AsyncSession
from app.db.models import Trade, OrderBookSnapshot
from app.observability import metrics

logger = logging.getLogger("run_collector")


async def persist_trade(symbol: str, t: dict):
    stmt = text(
        """
        INSERT INTO trades (symbol, trade_id, price, qty, buyer_maker, event_time)
        VALUES (:symbol, :trade_id, :price, :qty, :buyer_maker, :event_time)
        ON CONFLICT (symbol, trade_id) DO NOTHING
        """
    )
    params = {
        "symbol": symbol,
        "trade_id": int(t.get("id") or t.get("t")),
        "price": float(t.get("price") or t.get("p")),
        "qty": float(t.get("qty") or t.get("q")),
        "buyer_maker": str(t.get("isBuyerMaker") if "isBuyerMaker" in t else t.get("m")),
        "event_time": int(t.get("time") or t.get("T")),
    }
    async with AsyncSession() as session:
        try:
            await session.execute(stmt, params)
            await session.commit()
            try:
                metrics.inc_trade(symbol)
            except Exception:
                pass
        except Exception:
            await session.rollback()


async def rest_poller(symbols: List[str], interval: int = 5):
    adapter = BinanceAdapter()
    try:
        while True:
            for s in symbols:
                try:
                    trades = await adapter.get_trades(s)
                    for t in trades:
                        await persist_trade(s, t)
                    # fetch and persist snapshot
                    snap = await adapter.get_order_book(s, limit=100)
                    async with AsyncSession() as session:
                        # use upsert to avoid duplicate snapshots
                        bids_list = snap.get("bids", [])
                        asks_list = snap.get("asks", [])
                        snap_stmt = text(
                            """
                            INSERT INTO order_book_snapshots (symbol, event_time, bids, asks, bids_count, asks_count)
                            VALUES (:symbol, :event_time, :bids::jsonb, :asks::jsonb, :bids_count, :asks_count)
                            ON CONFLICT (symbol, event_time) DO NOTHING
                            """
                        )
                        params = {
                            "symbol": s,
                            "event_time": int(snap.get("lastUpdateId", 0)),
                            "bids": json.dumps(bids_list),
                            "asks": json.dumps(asks_list),
                            "bids_count": len(bids_list),
                            "asks_count": len(asks_list),
                        }
                        try:
                            await session.execute(snap_stmt, params)
                            await session.commit()
                            try:
                                metrics.inc_snapshot(s)
                            except Exception:
                                pass
                        except Exception as e:
                            await session.rollback()
                            logger.exception("snapshot insert failed: %s", e)
                except Exception as e:
                    logger.exception("rest poll error for %s: %s", s, e)
            await asyncio.sleep(interval)
    finally:
        await adapter.close()


async def test_ws_connect(timeout: int = 8) -> bool:
    import websockets

    url = WebSocketCollector()._stream_url()
    try:
        async with websockets.connect(url, open_timeout=timeout):
            return True
    except Exception as e:
        logger.info("ws test failed: %s", e)
        return False


async def main():
    logging.basicConfig(level=logging.INFO)
    # start prometheus metrics endpoint on port 8001
    try:
        metrics.start_metrics_server(port=8001)
    except Exception:
        logger.exception("failed to start metrics server")
    symbols = DEFAULT_SYMBOLS
    ok = await test_ws_connect()
    if ok:
        logger.info("WebSocket reachable — starting WebSocketCollector")
        collector = WebSocketCollector(symbols=symbols)
        await collector.run()
    else:
        logger.warning("WebSocket unreachable — falling back to REST polling")
        await rest_poller(symbols, interval=5)


if __name__ == "__main__":
    asyncio.run(main())
