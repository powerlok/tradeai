import asyncio
import json
import time
import logging
from typing import List
import websockets
import httpx
from app.core.config import settings
from app.market.binance_adapter import BinanceAdapter
from app.db.engine import AsyncSession
from app.db.models import Trade, OrderBookSnapshot

logger = logging.getLogger("ws_collector")

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

class WebSocketCollector:
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.ws = None
        self._running = False
        self.rest = BinanceAdapter()

    def _stream_url(self):
        streams = []
        for s in self.symbols:
            streams.append(f"{s.lower()}@trade")
            streams.append(f"{s.lower()}@depth@100ms")
        base = "wss://stream.binance.com:9443/stream"
        return base + "?streams=" + "/".join(streams)

    async def _persist_trade(self, session: AsyncSession, symbol: str, trade_event: dict):
        try:
            t = Trade(
                symbol=symbol,
                trade_id=trade_event.get("t"),
                price=float(trade_event.get("p")),
                qty=float(trade_event.get("q")),
                buyer_maker=str(trade_event.get("m")),
                event_time=int(trade_event.get("T"))
            )
            session.add(t)
            await session.commit()
        except Exception as e:
            logger.exception("failed to persist trade: %s", e)
            await session.rollback()

    async def _persist_snapshot(self, session: AsyncSession, symbol: str, snapshot: dict):
        try:
            s = OrderBookSnapshot(
                symbol=symbol,
                event_time=int(snapshot.get("lastUpdateId", int(time.time()*1000))),
                bids=snapshot.get("bids", []),
                asks=snapshot.get("asks", [])
            )
            session.add(s)
            await session.commit()
        except Exception:
            logger.exception("failed to persist snapshot")
            await session.rollback()

    async def fetch_and_store_snapshot(self, symbol: str):
        snap = await self.rest.get_order_book(symbol, limit=100)
        async with AsyncSession() as session:
            await self._persist_snapshot(session, symbol, snap)

    async def handle_message(self, message: str):
        data = json.loads(message)
        # wrapped stream messages have 'stream' and 'data'
        if "stream" in data and "data" in data:
            stream = data["stream"]
            payload = data["data"]
        else:
            payload = data
            stream = None

        # trade event
        if payload.get("e") == "trade":
            symbol = payload.get("s")
            async with AsyncSession() as session:
                await self._persist_trade(session, symbol, payload)
        # depthUpdate
        elif payload.get("e") == "depthUpdate":
            symbol = payload.get("s")
            # persist snapshot occasionally via REST—here we persist updates as snapshots for simplicity
            async with AsyncSession() as session:
                try:
                    ob = OrderBookSnapshot(
                        symbol=symbol,
                        event_time=int(payload.get("E", int(time.time()*1000))),
                        bids=payload.get("b", []),
                        asks=payload.get("a", [])
                    )
                    session.add(ob)
                    await session.commit()
                except Exception:
                    logger.exception("failed to persist orderbook update")
                    await session.rollback()

    async def run(self):
        url = self._stream_url()
        self._running = True
        reconnect_delay = 1
        while self._running:
            try:
                logger.info("connecting to %s", url)
                async with websockets.connect(url) as ws:
                    self.ws = ws
                    # upon connect, fetch snapshots
                    for s in self.symbols:
                        await self.fetch_and_store_snapshot(s)
                    async for msg in ws:
                        await self.handle_message(msg)
            except Exception as e:
                logger.exception("websocket error: %s", e)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)

    async def stop(self):
        self._running = False
        if self.ws:
            await self.ws.close()
        await self.rest.close()


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    collector = WebSocketCollector()
    asyncio.run(collector.run())
