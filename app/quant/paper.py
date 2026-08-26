"""Virtual paper-trading state machine. It never calls an exchange."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperPosition:
    symbol: str
    direction: str
    quantity: float
    entry_price: float
    stop: float
    target: float
    opened_at: int


class PaperTradingEngine:
    def __init__(self, initial_cash: float = 10000.0, fee_bps: float = 10.0):
        if initial_cash <= 0 or fee_bps < 0:
            raise ValueError("initial_cash must be positive and fee_bps cannot be negative")
        self.cash = float(initial_cash)
        self.fee_rate = fee_bps / 10000.0
        self.positions: dict[str, PaperPosition] = {}
        self.realized_pnl = 0.0

    def open_position(self, position: PaperPosition) -> dict[str, float | str]:
        if position.symbol in self.positions:
            raise ValueError("symbol already has an open paper position")
        if position.quantity <= 0 or position.entry_price <= 0:
            raise ValueError("position quantity and entry price must be positive")
        fee = position.quantity * position.entry_price * self.fee_rate
        if fee >= self.cash:
            raise ValueError("insufficient paper cash for fee")
        self.cash -= fee
        self.positions[position.symbol] = position
        return {"symbol": position.symbol, "status": "OPEN", "fee": fee, "cash": self.cash}

    def mark(self, symbol: str, price: float) -> dict[str, float | str | bool]:
        position = self.positions[symbol]
        direction = 1.0 if position.direction.upper() in {"BUY", "LONG"} else -1.0
        pnl = position.quantity * (price - position.entry_price) * direction
        stop_hit = price <= position.stop if direction > 0 else price >= position.stop
        target_hit = price >= position.target if direction > 0 else price <= position.target
        return {"symbol": symbol, "price": float(price), "unrealized_pnl": pnl, "stop_hit": stop_hit, "target_hit": target_hit}

    def close_position(self, symbol: str, price: float, timestamp: int) -> dict[str, float | str | int]:
        position = self.positions.pop(symbol)
        direction = 1.0 if position.direction.upper() in {"BUY", "LONG"} else -1.0
        gross_pnl = position.quantity * (price - position.entry_price) * direction
        fee = position.quantity * price * self.fee_rate
        net_pnl = gross_pnl - fee
        self.cash += position.quantity * position.entry_price + net_pnl
        self.realized_pnl += net_pnl
        return {"symbol": symbol, "status": "CLOSED", "price": float(price), "pnl": net_pnl, "fee": fee, "timestamp": timestamp, "cash": self.cash}
