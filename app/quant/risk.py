"""Portfolio risk checks for the virtual trading environment."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RiskLimits:
    initial_equity: float = 10_000.0
    max_trade_risk_pct: float = 0.02
    max_portfolio_risk_pct: float = 0.05
    max_exposure_pct: float = 0.50
    max_daily_loss_pct: float = 0.03


@dataclass(frozen=True)
class RiskAssessment:
    approved: bool
    reason_codes: tuple[str, ...]
    initial_equity: float
    open_exposure: float
    proposed_exposure: float
    open_risk: float
    proposed_risk: float
    realized_pnl_today: float
    max_trade_risk: float
    max_portfolio_risk: float
    max_exposure: float
    max_daily_loss: float

    def as_dict(self) -> dict[str, object]:
        return {
            "approved": self.approved,
            "reason_codes": list(self.reason_codes),
            "initial_equity": self.initial_equity,
            "open_exposure": self.open_exposure,
            "proposed_exposure": self.proposed_exposure,
            "open_risk": self.open_risk,
            "proposed_risk": self.proposed_risk,
            "realized_pnl_today": self.realized_pnl_today,
            "max_trade_risk": self.max_trade_risk,
            "max_portfolio_risk": self.max_portfolio_risk,
            "max_exposure": self.max_exposure,
            "max_daily_loss": self.max_daily_loss,
        }


def assess_portfolio_risk(
    open_positions: Iterable[object],
    realized_pnl_today: float,
    quantity: float,
    entry_price: float,
    stop: float,
    limits: RiskLimits = RiskLimits(),
) -> RiskAssessment:
    """Assess a proposed position using stop-defined loss and notional exposure."""
    open_exposure = sum(float(item.quantity) * float(item.entry_price) for item in open_positions)
    open_risk = sum(float(item.quantity) * abs(float(item.entry_price) - float(item.stop)) for item in open_positions)
    proposed_exposure = quantity * entry_price
    proposed_risk = quantity * abs(entry_price - stop)
    max_trade_risk = limits.initial_equity * limits.max_trade_risk_pct
    max_portfolio_risk = limits.initial_equity * limits.max_portfolio_risk_pct
    max_exposure = limits.initial_equity * limits.max_exposure_pct
    max_daily_loss = limits.initial_equity * limits.max_daily_loss_pct
    reasons: list[str] = []
    if proposed_risk > max_trade_risk:
        reasons.append("TRADE_RISK_LIMIT")
    if open_exposure + proposed_exposure > max_exposure:
        reasons.append("PORTFOLIO_EXPOSURE_LIMIT")
    if open_risk + proposed_risk > max_portfolio_risk:
        reasons.append("PORTFOLIO_RISK_LIMIT")
    if realized_pnl_today <= -max_daily_loss:
        reasons.append("DAILY_LOSS_LIMIT")
    return RiskAssessment(
        not reasons, tuple(reasons), limits.initial_equity, open_exposure,
        proposed_exposure, open_risk, proposed_risk, realized_pnl_today,
        max_trade_risk, max_portfolio_risk, max_exposure, max_daily_loss,
    )