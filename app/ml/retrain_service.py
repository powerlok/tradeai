"""Periodic candidate training with conservative automatic promotion."""
import asyncio
import logging
import os

from app.db.engine import AsyncSession, Base, engine
from app.ml.dataset import build_dataset
from app.ml.models import train_model
from app.ml.registry import approve_version, get_active

logger = logging.getLogger("ml_retrain")
SYMBOLS = tuple(os.getenv("RETRAIN_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT,ADAUSDT,DOGEUSDT,TRXUSDT,AVAXUSDT,LINKUSDT,TONUSDT,SHIBUSDT,DOTUSDT,BCHUSDT,LTCUSDT,UNIUSDT,XLMUSDT,NEARUSDT,ATOMUSDT,APTUSDT").split(","))
TIMEFRAMES = tuple(os.getenv("RETRAIN_TIMEFRAMES", "1d,4h,1h,15m,5m").split(","))
MODEL_TYPE = os.getenv("RETRAIN_MODEL_TYPE", "logistic")
INTERVAL_SECONDS = int(os.getenv("RETRAIN_INTERVAL_SECONDS", "21600"))
MIN_TEST_AUC = float(os.getenv("RETRAIN_MIN_TEST_AUC", "0.55"))
MIN_REGIME_ACCURACY = float(os.getenv("RETRAIN_MIN_REGIME_ACCURACY", "0.45"))


def score(record: dict) -> float:
    value = record.get("metrics", {}).get("test_auc")
    if value is None:
        value = record.get("metrics", {}).get("test_accuracy")
    return float(value or 0.0)


def calibration_score(record: dict) -> float:
    metrics = record.get("metrics", {})
    return float(metrics.get("test_brier", 1.0) or 1.0)


def regime_stability_ok(record: dict) -> bool:
    value = record.get("metrics", {}).get("min_regime_accuracy")
    return value is None or float(value) >= MIN_REGIME_ACCURACY


async def retrain_once() -> None:
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                async with AsyncSession() as session:
                    dataset = await build_dataset(session, symbol.strip(), timeframe.strip(), train_ratio=0.8)
                result = await train_model(dataset, model_type=MODEL_TYPE, cv_folds=5, promote=False)
                active = get_active(symbol, timeframe, MODEL_TYPE)
                candidate_score = score(result)
                active_score = score(active) if active else 0.0
                candidate_brier = calibration_score(result)
                active_brier = calibration_score(active) if active else 1.0
                calibration_ok = active is None or candidate_brier <= active_brier + 0.05
                stability_ok = regime_stability_ok(result)
                should_promote = candidate_score >= MIN_TEST_AUC and calibration_ok and stability_ok and (active is None or candidate_score > active_score)
                if should_promote:
                    approve_version(symbol, timeframe, MODEL_TYPE, result["version"])
                    logger.info("approved improved model %s %s %s version=%s score=%.4f", symbol, timeframe, MODEL_TYPE, result["version"], candidate_score)
                else:
                    logger.info("kept candidate pending %s %s %s version=%s score=%.4f active=%.4f brier=%.4f active_brier=%.4f regime_ok=%s", symbol, timeframe, MODEL_TYPE, result["version"], candidate_score, active_score, candidate_brier, active_brier, stability_ok)
            except Exception:
                logger.exception("retraining failed for %s %s", symbol, timeframe)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            break
        except Exception as error:
            logger.warning("database is not ready; retrying in 5s: %s", error)
            await asyncio.sleep(5)
    while True:
        await retrain_once()
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
