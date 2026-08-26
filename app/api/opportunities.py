import os

from fastapi import APIRouter, Depends, Query

from app.db.engine import AsyncSession
from app.ml.features import build_model_vector, calculate_features
from app.ml.models import ModelTrainer
from app.quant.engines import build_risk_plan, classify_regime, decide_signal
from app.quant.opportunities import rank_opportunities

router = APIRouter()

DEFAULT_OPPORTUNITY_SYMBOLS = os.getenv(
    "MARKET_SYMBOLS",
    "BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT,ADAUSDT,DOGEUSDT,TRXUSDT,AVAXUSDT,LINKUSDT,TONUSDT,SHIBUSDT,DOTUSDT,BCHUSDT,LTCUSDT,UNIUSDT,XLMUSDT,NEARUSDT,ATOMUSDT,APTUSDT",
)


async def get_db():
    async with AsyncSession() as session:
        yield session


@router.get("/opportunities")
async def opportunities(
    symbols: str = Query(DEFAULT_OPPORTUNITY_SYMBOLS),
    timeframe: str = Query("1h"),
    model_type: str = Query("logistic"),
    fee_bps: float = Query(10.0, ge=0.0, le=1000.0),
    slippage_bps: float = Query(5.0, ge=0.0, le=1000.0),
    minimum_net_target_pct: float = Query(0.0, ge=0.0, le=10.0),
    db: AsyncSession = Depends(get_db),
):
    candidates = []
    for symbol in (item.strip().upper() for item in symbols.split(",")):
        features = await calculate_features(db, symbol, timeframe)
        if not features:
            continue
        try:
            trainer = ModelTrainer.load(symbol, model_type, timeframe)
        except FileNotFoundError:
            continue
        vector = build_model_vector(features["indicators"], features["close"])[None, :]
        _, probabilities = trainer.predict(vector)
        risk = build_risk_plan("BUY" if float(probabilities[0]) >= 0.5 else "SELL", features["close"], float(features["indicators"].get("atr_14") or 0))
        decision = decide_signal(float(probabilities[0]), risk, classify_regime([features["close"]]))
        candidates.append((symbol, timeframe, decision))
    return {"timeframe": timeframe, "fee_bps": fee_bps, "slippage_bps": slippage_bps, "minimum_net_target_pct": minimum_net_target_pct, "opportunities": [item.__dict__ for item in rank_opportunities(candidates, fee_bps, slippage_bps, minimum_net_target_pct)]}
