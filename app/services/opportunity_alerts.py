from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import settings
from app.db.engine import AsyncSession
from app.db.models import PaperTrade, Trade, User
from app.ml.features import build_model_vector, calculate_features
from app.ml.models import ModelTrainer
from app.quant.engines import build_risk_plan, classify_regime, decide_signal
from app.services.notifications import NotificationService

logger = logging.getLogger("opportunity_alerts")

DEFAULT_SYMBOLS = "BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT,ADAUSDT,DOGEUSDT,TRXUSDT,AVAXUSDT,LINKUSDT,TONUSDT,SHIBUSDT,DOTUSDT,BCHUSDT,LTCUSDT,UNIUSDT,XLMUSDT,NEARUSDT,ATOMUSDT,APTUSDT"
ALERT_TIMEFRAME = "1h"
ALERT_INTERVAL_SECONDS = 60
ALERT_COOLDOWN_SECONDS = 900
NEAR_LEVEL_RATIO = 0.20


def build_viability_summary(entry: float, stop: float, target: float, direction: str, fee_bps: float = 10.0, slippage_bps: float = 5.0) -> str:
    round_trip_cost_pct = 2.0 * (fee_bps + slippage_bps) / 10000.0
    gross_target_pct = ((target - entry) / entry) if direction.upper() == "BUY" else ((entry - target) / entry)
    net_target_pct = gross_target_pct - round_trip_cost_pct
    gross_stop_pct = ((stop - entry) / entry) if direction.upper() == "BUY" else ((entry - stop) / entry)
    safety_buffer_pct = max(round_trip_cost_pct * 0.5, abs(gross_stop_pct) * 0.10)
    minimum_required_pct = round_trip_cost_pct + safety_buffer_pct
    margin_pct = net_target_pct - minimum_required_pct
    return (
        f"viabilidade: alvo líquido {net_target_pct * 100:.2f}% | mínimo exigido {minimum_required_pct * 100:.2f}% | "
        f"margem {margin_pct * 100:.2f}% | custos estimados {round_trip_cost_pct * 100:.2f}%"
    )


def _symbols() -> list[str]:
    return [item.strip().upper() for item in os.getenv("MARKET_SYMBOLS", DEFAULT_SYMBOLS).split(",") if item.strip()]


def _near_level(price: float, level: float, entry: float, risk: float) -> bool:
    tolerance = max(risk * NEAR_LEVEL_RATIO, entry * 0.001)
    return abs(price - level) <= tolerance


async def _notify_users(notification_type: str, title: str, message: str, metadata: dict) -> None:
    async with AsyncSession() as db:
        users = (await db.execute(select(User.username))).scalars().all()
    for username in users:
        await NotificationService().publish(username, notification_type, title, message, metadata)


async def scan_once() -> None:
    async with AsyncSession() as db:
        previous_state = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            open_symbols = set((await db.execute(select(PaperTrade.symbol).where(PaperTrade.status == "OPEN"))).scalars().all())
            opportunities = []
            for symbol in _symbols():
                features = await calculate_features(db, symbol, ALERT_TIMEFRAME)
                if not features:
                    continue
                try:
                    trainer = ModelTrainer.load(symbol, "logistic", ALERT_TIMEFRAME)
                except FileNotFoundError:
                    continue
                vector = build_model_vector(features["indicators"], features["close"])[None, :]
                _, probabilities = trainer.predict(vector)
                probability = float(probabilities[0])
                direction = "BUY" if probability >= 0.5 else "SELL"
                risk = build_risk_plan(direction, features["close"], float(features["indicators"].get("atr_14") or 0.0))
                decision = decide_signal(probability, risk, classify_regime([features["close"]]))
                if decision.state == "NO_TRADE" or not risk.valid:
                    continue
                price_result = await db.execute(select(Trade).where(Trade.symbol == symbol).order_by(Trade.event_time.desc()).limit(1))
                latest_trade = price_result.scalars().first()
                if latest_trade is None:
                    continue
                opportunities.append((symbol, risk, float(latest_trade.price), decision))

            current_signatures = {f"{symbol}:{decision.direction}:{round(risk.entry, 8)}:{round(risk.stop, 8)}:{round(risk.target, 8)}" for symbol, risk, _, decision in opportunities}
            previous_raw = await previous_state.get("opportunity-alerts:active")
            previous_signatures = set(json.loads(previous_raw)) if previous_raw else set()
            for symbol, risk, price, decision in opportunities:
                signature = f"{symbol}:{decision.direction}:{round(risk.entry, 8)}:{round(risk.stop, 8)}:{round(risk.target, 8)}"
                metadata = {"symbol": symbol, "timeframe": ALERT_TIMEFRAME, "direction": decision.direction, "entry": risk.entry, "stop": risk.stop, "target": risk.target, "probability": decision.probability, "score": decision.score}
                viability_summary = build_viability_summary(risk.entry, risk.stop, risk.target, decision.direction)
                if signature not in previous_signatures:
                    await _notify_users("opportunity_alert", "Nova oportunidade", f"{symbol} {decision.direction}: entrada {risk.entry:.2f}, stop {risk.stop:.2f}, alvo {risk.target:.2f}. {viability_summary}.", metadata | {"viability_summary": viability_summary})
                if symbol not in open_symbols:
                    continue
                level = "stop" if _near_level(price, risk.stop, risk.entry, risk.risk_per_unit) else "target" if _near_level(price, risk.target, risk.entry, risk.risk_per_unit) else None
                stop_hit = price <= risk.stop if decision.direction == "BUY" else price >= risk.stop
                target_hit = price >= risk.target if decision.direction == "BUY" else price <= risk.target
                event = "stop_hit" if stop_hit else "target_hit" if target_hit else f"near_{level}" if level else None
                if event:
                    cooldown_key = f"opportunity-alert:{event}:{signature}"
                    if await previous_state.set(cooldown_key, "1", ex=ALERT_COOLDOWN_SECONDS, nx=True):
                        label = "stop" if "stop" in event else "alvo"
                        status = "atingiu" if event.endswith("hit") else "está próxima do"
                        message = f"{symbol} {decision.direction} {status} {label}: preço {price:.2f}, nível {risk.stop if label == 'stop' else risk.target:.2f}. {viability_summary}."
                        await _notify_users("opportunity_alert", f"Alerta de {label}", message, metadata | {"price": price, "event": event, "viability_summary": viability_summary})
            await previous_state.set("opportunity-alerts:active", json.dumps(sorted(current_signatures)), ex=ALERT_INTERVAL_SECONDS * 3)
        finally:
            await previous_state.aclose()


async def monitor() -> None:
    while True:
        try:
            await scan_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("opportunity alert scan failed")
        await asyncio.sleep(ALERT_INTERVAL_SECONDS)
