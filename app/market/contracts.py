from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


@dataclass(frozen=True)
class NormalizedCandle:
    symbol: str
    timeframe: str
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class NormalizedTrade:
    symbol: str
    trade_id: int
    price: float
    quantity: float
    side: str
    event_time: int
    received_time: int


@dataclass(frozen=True)
class NormalizedOrderBook:
    symbol: str
    bids: list[list[str]]
    asks: list[list[str]]
    event_time: int
    received_time: int


@dataclass(frozen=True)
class NormalizedBookTicker:
    symbol: str
    bid_price: float
    bid_quantity: float
    ask_price: float
    ask_quantity: float
    event_time: int
    received_time: int

class MarketDataProvider(Protocol):
    async def get_candles(self, symbol: str, timeframe: str, limit: int) -> List[Dict[str, Any]]: ...
    async def get_trades(self, symbol: str, limit: int) -> List[Dict[str, Any]]: ...
    async def get_order_book(self, symbol: str, depth: int) -> Dict[str, Any]: ...
    async def get_book_ticker(self, symbol: str) -> Dict[str, Any]: ...
    async def subscribe_trades(self, symbol: str): ...
    async def subscribe_order_book(self, symbol: str): ...
    async def subscribe_book_ticker(self, symbol: str): ...
