from app.db.models import PaperTrade, PaperTradeEvent, Trade, User
import asyncio
import json
import time
import logging
import os
from typing import List
import websockets
import httpx
from app.core.config import settings
from app.market.binance_adapter import BinanceAdapter
from app.market.normalizer import normalize_book_ticker, normalize_order_book, normalize_trade
from app.db.engine import AsyncSession
from app.db.models import BookTicker, Trade, OrderBookSnapshot, PaperTrade, User
from sqlalchemy import select
from redis.asyncio import Redis
from app.services.notifications import NotificationService

logger = logging.getLogger("ws_collector")

DEFAULT_SYMBOLS = os.getenv("MARKET_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT,ADAUSDT,DOGEUSDT,TRXUSDT,AVAXUSDT,LINKUSDT,TONUSDT,SHIBUSDT,DOTUSDT,BCHUSDT,LTCUSDT,UNIUSDT,XLMUSDT,NEARUSDT,ATOMUSDT,APTUSDT").split(",")

class WebSocketCollector:
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.ws = None
        self._running = False
        self.rest = BinanceAdapter()
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def _stream_url(self):
        streams = []
        for s in self.symbols:
            streams.append(f"{s.lower()}@trade")
            streams.append(f"{s.lower()}@depth@100ms")
            streams.append(f"{s.lower()}@bookTicker")
        base = "wss://stream.binance.com:9443/stream"
        return base + "?streams=" + "/".join(streams)

    async def _persist_trade(self, session: AsyncSession, symbol: str, trade_event: dict):
        try:
            normalized = normalize_trade(trade_event)
            t = Trade(
                symbol=normalized.symbol, trade_id=normalized.trade_id,
                price=normalized.price, qty=normalized.quantity,
                buyer_maker=normalized.side, event_time=normalized.event_time,
                received_time=normalized.received_time,
            )
            session.add(t)
            await session.commit()
            await self.redis.publish("market:prices", json.dumps({
                "type": "price", "symbol": normalized.symbol, "price": normalized.price,
                "event_time": normalized.event_time, "source": "binance_ws",
            }))
            await self._close_triggered_paper_positions(normalized.symbol, normalized.price, normalized.event_time)
        except Exception as e:
            logger.exception("failed to persist trade: %s", e)
            await session.rollback()

    async def _close_triggered_paper_positions(self, symbol: str, price: float, event_time: int):
        async with AsyncSession() as session:
            result = await session.execute(select(PaperTrade).where(PaperTrade.symbol == symbol, PaperTrade.status == "OPEN"))
            positions = result.scalars().all()
            triggered = []
            for position in positions:
                direction = 1.0 if position.direction in {"BUY", "LONG"} else -1.0
                stop_hit = price <= position.stop if direction > 0 else price >= position.stop
                target_hit = price >= position.target if direction > 0 else price <= position.target
                if not stop_hit and not target_hit:
                    continue
                position.pnl = position.quantity * (price - position.entry_price) * direction
                position.exit_price = price
                position.exit_reason = "STOP" if stop_hit else "TARGET"
                position.closed_at = event_time
                position.status = "CLOSED"
                session.add(PaperTradeEvent(paper_trade_id=position.id, symbol=position.symbol, event_type="CLOSED", event_time=event_time, payload={"exit_reason": position.exit_reason, "exit_price": price, "pnl": position.pnl}))
                reason = "stop_loss" if stop_hit else "take_profit"
                triggered.append((position, reason))
            if triggered:
                await session.commit()
                users = (await session.execute(select(User.username))).scalars().all()
                for position, reason in triggered:
                    title = "Stop Loss acionado" if reason == "stop_loss" else "Alvo atingido"
                    for username in users:
                        await NotificationService().publish(
                            username,
                            "opportunity_alert",
                            title,
                            f"{symbol} {position.direction} encerrado a {price:.2f} USDT. PnL: {position.pnl:+.2f} USDT.",
                            {"event": reason, "symbol": symbol, "trade_id": position.id, "price": price, "pnl": position.pnl},
                        )
                logger.info("auto-closed paper positions %s at %s %s", [item[0].id for item in triggered], symbol, price)

    async def _persist_snapshot(self, session: AsyncSession, symbol: str, snapshot: dict):
        try:
            normalized = normalize_order_book(symbol, snapshot)
            s = OrderBookSnapshot(
                symbol=normalized.symbol, event_time=normalized.event_time,
                received_time=normalized.received_time, bids=normalized.bids,
                asks=normalized.asks
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
                    normalized = normalize_order_book(symbol, payload)
                    ob = OrderBookSnapshot(
                        symbol=normalized.symbol, event_time=normalized.event_time,
                        received_time=normalized.received_time, bids=normalized.bids,
                        asks=normalized.asks
                    )
                    session.add(ob)
                    await session.commit()
                except Exception:
                    logger.exception("failed to persist orderbook update")
                    await session.rollback()
        elif payload.get("e") == "bookTicker":
            symbol = payload.get("s")
            async with AsyncSession() as session:
                try:
                    normalized = normalize_book_ticker(payload)
                    ticker = BookTicker(
                        symbol=normalized.symbol, event_time=normalized.event_time,
                        received_time=normalized.received_time, bid_price=normalized.bid_price,
                        bid_qty=normalized.bid_quantity, ask_price=normalized.ask_price,
                        ask_qty=normalized.ask_quantity,
                    )
                    session.add(ticker)
                    await session.commit()
                except Exception:
                    logger.exception("failed to persist book ticker")
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
        await self.redis.close()


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    collector = WebSocketCollector()
    asyncio.run(collector.run())
