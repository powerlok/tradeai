from fastapi import APIRouter, Depends, HTTPException, Query
import numpy as np
import time
from app.db.engine import AsyncSession
from app.ml.features import calculate_features, build_model_vector
from app.ml.models import ModelTrainer

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

    indicator_values = features["indicators"]
    feature_vector = build_model_vector(indicator_values, features["close"])[None, :]
    predictions, probabilities = trainer.predict(feature_vector)
    prediction = int(predictions[0])
    probability = float(probabilities[0])
    confidence_threshold = 0.60
    if 1 - confidence_threshold <= probability <= confidence_threshold:
        signal_name = "WATCH"
    else:
        signal_name = "BUY" if prediction == 1 else "SELL"

    return {
        "signals": [{
            "symbol": normalized_symbol,
            "timeframe": timeframe,
            "model_type": model_type,
            "signal": signal_name,
            "prediction": prediction,
            "probability": probability,
            "price": features["close"],
            "timestamp": features["timestamp"],
            "checked_at": int(time.time() * 1000),
            "checked_at": int(time.time() * 1000),
            "indicators": features["indicators"],
            "summary": features["summary"],
            "model_available": True,
            "confidence_threshold": confidence_threshold,
        }]
    }
