import asyncio
from typing import Any
from app.market.binance_adapter import BinanceAdapter

class MarketDataCollector:
    def __init__(self, provider: BinanceAdapter):
        self.provider = provider
        self._running = False

    async def connect(self):
        self._running = True

    async def disconnect(self):
        self._running = False
        await self.provider.close()

    async def heartbeat(self):
        return {"status": "ok"}

    async def fetch_historical(self, symbol: str, interval: str):
        return await self.provider.get_candles(symbol, interval)

    async def persist(self, data: Any):
        # TODO: implement persistence to PostgreSQL
        pass
