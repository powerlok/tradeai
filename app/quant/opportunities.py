"""Ranking of already-computed quantitative opportunities."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable

from app.quant.engines import SignalDecision


@dataclass(frozen=True)
class Opportunity:
    assessment_id: str
    status: str
    action: str
    reason_codes: tuple[str, ...]
    symbol: str
    timeframe: str
    direction: str
    state: str
    score: float
    probability: float
    risk_reward: float
    trade_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_per_unit: float
    exit_rule: str
    fee_bps: float
    slippage_bps: float
    round_trip_cost_pct: float
    gross_target_pct: float
    net_target_pct: float
    net_stop_pct: float
    cost_viable: bool
    directional_probability: float
    break_even_probability: float
    expected_value_pct: float
    safety_buffer_pct: float
    required_move_pct: float
    opportunity_quality: str


def _assessment_id(symbol: str, timeframe: str, decision: SignalDecision) -> str:
    payload = f"{symbol.upper()}:{timeframe}:{decision.direction}:{decision.risk.entry:.8f}:{decision.risk.stop:.8f}:{decision.risk.target:.8f}"
    return hashlib.sha256(payload.encode("ascii")).hexdigest()[:16]


def rank_opportunities(items: Iterable[tuple[str, str, SignalDecision]], fee_bps: float = 10.0, slippage_bps: float = 5.0, minimum_net_target_pct: float = 0.0) -> list[Opportunity]:
    round_trip_cost_pct = 2.0 * (fee_bps + slippage_bps) / 10000.0
    result = []
    for symbol, timeframe, decision in items:
        if decision.state == "NO_TRADE" or not decision.risk.valid:
            continue
        direction_multiplier = 1.0 if decision.direction == "BUY" else -1.0
        entry_distance = abs(decision.risk.entry - decision.risk.stop) / decision.risk.entry
        target_distance = abs(decision.risk.target - decision.risk.entry) / decision.risk.entry
        if entry_distance <= 0.001 or target_distance <= 0.001:
            continue
        gross_target_pct = direction_multiplier * (decision.risk.target - decision.risk.entry) / decision.risk.entry
        gross_stop_pct = direction_multiplier * (decision.risk.stop - decision.risk.entry) / decision.risk.entry
        net_target_pct = gross_target_pct - round_trip_cost_pct
        net_stop_pct = gross_stop_pct - round_trip_cost_pct
        directional_probability = decision.probability if direction_multiplier > 0 else 1.0 - decision.probability
        win_amount = max(net_target_pct, 0.0)
        loss_amount = abs(net_stop_pct)
        break_even_probability = (loss_amount / (win_amount + loss_amount)) if win_amount + loss_amount else 1.0
        expected_value_pct = directional_probability * win_amount - (1.0 - directional_probability) * loss_amount
        safety_buffer_pct = max(round_trip_cost_pct * 0.5, loss_amount * 0.10)
        required_move_pct = round_trip_cost_pct + safety_buffer_pct
        edge = directional_probability - break_even_probability
        cost_viable = net_target_pct >= required_move_pct and net_target_pct >= minimum_net_target_pct and expected_value_pct > safety_buffer_pct and edge >= 0.05
        quality = "FORTE" if edge >= 0.15 and expected_value_pct >= safety_buffer_pct * 2 else "MODERADA" if cost_viable else "FRACA"
        result.append(Opportunity(
            _assessment_id(symbol, timeframe, decision), "APPROVED", "PAPER_ENTRY",
            ("DATA_QUALITY_VALID", "MODEL_SIGNAL_VALID", "COST_VIABLE", "EDGE_ABOVE_REQUIRED_MOVE"),
            symbol.upper(), timeframe, decision.direction, decision.state, decision.score,
            decision.probability, decision.risk.reward_risk, "LONG" if decision.direction == "BUY" else "SHORT",
            decision.risk.entry, decision.risk.stop, decision.risk.target, decision.risk.risk_per_unit,
            "Encerrar no stop ou no alvo", fee_bps, slippage_bps, round_trip_cost_pct,
            gross_target_pct, net_target_pct, net_stop_pct, cost_viable,
            directional_probability, break_even_probability, expected_value_pct, safety_buffer_pct,
            required_move_pct, quality,
        ))
    return sorted((item for item in result if item.cost_viable), key=lambda item: (item.net_target_pct, item.score, item.risk_reward), reverse=True)
