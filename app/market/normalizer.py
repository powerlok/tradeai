"""Normalize Binance REST and WebSocket payloads before persistence."""
from __future__ import annotations

import time
from collections.abc import Sequence

from app.market.contracts import (
    NormalizedBookTicker,
    NormalizedCandle,
    NormalizedOrderBook,
    NormalizedTrade,
)


def _received_time(received_time: int | None) -> int:
    return int(time.time() * 1000) if received_time is None else int(received_time)


def _symbol(value: object) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        raise ValueError("market payload is missing symbol")
    return symbol


def normalize_kline(symbol: str, timeframe: str, payload: Sequence[object]) -> NormalizedCandle:
    if len(payload) < 7:
        raise ValueError("kline payload must contain at least 7 fields")
    return NormalizedCandle(
        symbol=_symbol(symbol), timeframe=timeframe.strip(), open_time=int(payload[0]),
        open=float(payload[1]), high=float(payload[2]), low=float(payload[3]),
        close=float(payload[4]), volume=float(payload[5]), close_time=int(payload[6]),
    )


def normalize_trade(payload: dict, received_time: int | None = None) -> NormalizedTrade:
    return NormalizedTrade(
        symbol=_symbol(payload.get("s")), trade_id=int(payload["t"]),
        price=float(payload["p"]), quantity=float(payload["q"]),
        side="sell" if payload.get("m") else "buy", event_time=int(payload["T"]),
        received_time=_received_time(received_time),
    )


def normalize_order_book(
    symbol: str, payload: dict, received_time: int | None = None, event_time: int | None = None
) -> NormalizedOrderBook:
    received = _received_time(received_time)
    return NormalizedOrderBook(
        symbol=_symbol(symbol), bids=list(payload.get("b", payload.get("bids", []))),
        asks=list(payload.get("a", payload.get("asks", []))),
        event_time=int(event_time if event_time is not None else payload.get("E", received)),
        received_time=received,
    )


def normalize_book_ticker(payload: dict, received_time: int | None = None) -> NormalizedBookTicker:
    return NormalizedBookTicker(
        symbol=_symbol(payload.get("s")), bid_price=float(payload["b"]),
        bid_quantity=float(payload["B"]), ask_price=float(payload["a"]),
        ask_quantity=float(payload["A"]), event_time=int(payload["E"]),
        received_time=_received_time(received_time),
    )