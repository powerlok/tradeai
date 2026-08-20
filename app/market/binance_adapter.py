import httpx
from typing import Any, Dict, List

BASE = "https://api.binance.com"

class BinanceAdapter:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE, timeout=10)

    async def get_candles(self, symbol: str, interval: str = "1m", limit: int = 500) -> List[Dict[str, Any]]:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        r = await self.client.get("/api/v3/klines", params=params)
        r.raise_for_status()
        return r.json()

    async def get_trades(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        params = {"symbol": symbol, "limit": limit}
        r = await self.client.get("/api/v3/trades", params=params)
        r.raise_for_status()
        return r.json()

    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        params = {"symbol": symbol, "limit": limit}
        r = await self.client.get("/api/v3/depth", params=params)
        r.raise_for_status()
        return r.json()

    async def close(self):
        await self.client.aclose()
