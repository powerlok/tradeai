from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
import numpy as np
import time
from app.db.engine import AsyncSession
from app.ml.features import calculate_features, build_model_vector, get_recent_candles
from app.ml.models import ModelTrainer
from app.quant.engines import build_risk_plan, calculate_microstructure, classify_regime, decide_signal
from app.db.models import OrderBookSnapshot
from app.observability.metrics import inc_signal

router = APIRouter()


async def get_db():
    async with AsyncSession() as session:
        yield session


@router.get("/signals/latest")
async def latest(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    model_type: str = Query("logistic"),
    db: AsyncSession = Depends(get_db),
):
    """Return the latest model-backed signal for a symbol."""
    normalized_symbol = symbol.upper()
    features = await calculate_features(db, normalized_symbol, timeframe)
    if not features:
        raise HTTPException(status_code=404, detail="No candle data found for the requested symbol")

    try:
        trainer = ModelTrainer.load(normalized_symbol, model_type, timeframe)
    except FileNotFoundError:
        return {
            "signals": [{
                "symbol": normalized_symbol,
                "timeframe": timeframe,
                "model_type": model_type,
                "signal": "WATCH",
                "prediction": None,
                "probability": None,
                "price": features["close"],
                "timestamp": features["timestamp"],
                "indicators": features["indicators"],
                "summary": features["summary"],
                "model_available": False,
                "message": "No trained model for this symbol and timeframe",
            }]
        }

    recent_candles = await get_recent_candles(db, normalized_symbol, timeframe, limit=200)
    regime = classify_regime([candle.close for candle in recent_candles])
    orderbook_result = await db.execute(
        select(OrderBookSnapshot).where(OrderBookSnapshot.symbol == normalized_symbol).order_by(OrderBookSnapshot.event_time.desc()).limit(1)
    )
    orderbook = orderbook_result.scalar_one_or_none()
    indicator_values = features["indicators"]
    feature_vector = build_model_vector(indicator_values, features["close"])[None, :]
    predictions, probabilities = trainer.predict(feature_vector)
    prediction = int(predictions[0])
    probability = float(probabilities[0])
    confidence_threshold = 0.60
    raw_direction = "BUY" if prediction == 1 else "SELL"
    risk = build_risk_plan(raw_direction, features["close"], float(indicator_values.get("atr_14") or 0.0))
    microstructure = calculate_microstructure(orderbook.bids, orderbook.asks) if orderbook else None
    decision = decide_signal(probability, risk, regime=regime, microstructure=microstructure)
    inc_signal(decision.direction, decision.state)

    return {
        "signals": [{
            "symbol": normalized_symbol,
            "timeframe": timeframe,
            "model_type": model_type,
            "signal": decision.direction,
            "state": decision.state,
            "score": decision.score,
            "confidence": decision.confidence,
            "evidence": decision.evidence,
            "risk": {
                "entry": risk.entry,
                "stop": risk.stop,
                "target": risk.target,
                "reward_risk": risk.reward_risk,
                "valid": risk.valid,
                "reason": risk.reason,
            },
            "regime": {
                "name": regime.regime,
                "volatility": regime.volatility,
                "trend_strength": regime.trend_strength,
                "confidence": regime.confidence,
            },
            "microstructure": microstructure.__dict__ if microstructure else None,
            "prediction": prediction,
            "probability": probability,
            "price": features["close"],
            "timestamp": features["timestamp"],
            "checked_at": int(time.time() * 1000),
            "indicators": features["indicators"],
            "summary": features["summary"],
            "model_available": True,
            "confidence_threshold": confidence_threshold,
        }]
    }
