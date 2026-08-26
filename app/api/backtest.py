from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.engine import AsyncSession
from app.ml.backtester import backtest_model, run_strategy_backtest, run_strategy_walk_forward
from app.quant.strategies import available_strategies
from app.ml.dataset import get_candles_for_symbol

router = APIRouter()


async def get_db():
    async with AsyncSession() as session:
        yield session


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    model_type: str = "logistic"
    initial_cash: float = Field(default=10000.0, gt=0)
    fee_bps: float = Field(default=10.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    confidence_threshold: float = Field(default=0.60, gt=0.5, lt=1.0)
    engine_version: str = Field(default="v1", pattern="^v[12]$")
    stop_atr_multiple: float = Field(default=1.0, gt=0)
    target_risk_reward: float = Field(default=2.0, gt=0)
    max_holding_bars: int = Field(default=5, gt=0)


class StrategyBacktestRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=20)
    timeframes: list[str] = Field(default=["1h"], min_length=1, max_length=5)
    strategy_type: str = "moving_average"
    strategy_params: dict[str, float | int] = Field(default_factory=dict)
    initial_cash: float = Field(default=10000.0, gt=0)
    fee_bps: float = Field(default=10.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    stop_atr_multiple: float = Field(default=1.0, gt=0)
    target_risk_reward: float = Field(default=2.0, gt=0)
    max_holding_bars: int = Field(default=5, gt=0)
    start_time: int | None = None
    end_time: int | None = None


class WalkForwardRequest(StrategyBacktestRequest):
    train_bars: int = Field(default=200, gt=0, le=5000)
    validation_bars: int = Field(default=100, gt=0, le=5000)
    test_bars: int = Field(default=100, gt=0, le=5000)
    max_windows: int = Field(default=5, gt=0, le=20)


@router.post("/run")
async def run_backtest(request: BacktestRequest, db: AsyncSession = Depends(get_db)):
    """Run a causal paper backtest; it never submits exchange orders."""
    try:
        return await backtest_model(
            db,
            symbol=request.symbol,
            timeframe=request.timeframe,
            model_type=request.model_type,
            initial_cash=request.initial_cash,
            fee_bps=request.fee_bps,
            slippage_bps=request.slippage_bps,
            confidence_threshold=request.confidence_threshold,
            engine_version=request.engine_version,
            stop_atr_multiple=request.stop_atr_multiple,
            target_risk_reward=request.target_risk_reward,
            max_holding_bars=request.max_holding_bars,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=409, detail=f"No active model approved for {request.symbol.upper()} {request.timeframe} {request.model_type}. Train and approve a model before running the backtest.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {error}")


@router.post("/run-walk-forward")
async def run_walk_forward_endpoint(request: WalkForwardRequest, db: AsyncSession = Depends(get_db)):
    if request.strategy_type not in {item["id"] for item in available_strategies()}:
        raise HTTPException(status_code=400, detail="Unsupported strategy_type")
    results = []
    for symbol in request.symbols:
        for timeframe in request.timeframes:
            try:
                candles = await get_candles_for_symbol(db, symbol.upper(), timeframe, limit=2000)
                result = run_strategy_walk_forward(
                    candles, request.strategy_type, request.strategy_params,
                    request.initial_cash, request.fee_bps, request.slippage_bps,
                    request.stop_atr_multiple, request.target_risk_reward,
                    request.max_holding_bars, request.train_bars,
                    request.validation_bars, request.test_bars, request.max_windows,
                )
                result.update({"symbol": symbol.upper(), "timeframe": timeframe})
                results.append(result)
            except ValueError:
                continue
    if not results:
        raise HTTPException(status_code=409, detail="No valid data for the selected assets and walk-forward windows")
    return {"strategy_type": request.strategy_type, "results": results}


@router.get("/info")
async def backtest_info():
    return {
        "description": "Causal paper backtester v1/v2 with costs; v2 adds stops, targets, time exit, MAE/MFE and regimes",
        "endpoint": "POST /api/ml/backtest/run",
        "defaults": {
            "initial_cash": 10000.0,
            "fee_bps": 10.0,
            "slippage_bps": 5.0,
            "confidence_threshold": 0.60,
            "engine_version": "v1",
            "stop_atr_multiple": 1.0,
            "target_risk_reward": 2.0,
            "max_holding_bars": 5,
        },
        "execution": "Signals are decided at candle close and executed on the next candle open; no exchange orders are submitted.",
    }


@router.get("/strategies")
async def strategies_info():
    return {"strategies": available_strategies(), "execution": "Causal: signal at close, entry at next open, stop/target intrabar, costs on round trip."}


@router.post("/run-strategy")
async def run_strategy_backtest_endpoint(request: StrategyBacktestRequest, db: AsyncSession = Depends(get_db)):
    if request.strategy_type not in {item["id"] for item in available_strategies()}:
        raise HTTPException(status_code=400, detail="Unsupported strategy_type")
    results = []
    for symbol in request.symbols:
        for timeframe in request.timeframes:
            try:
                candles = await get_candles_for_symbol(db, symbol.upper(), timeframe, limit=500)
                if len(candles) < 100:
                    continue
                result = run_strategy_backtest(candles, request.strategy_type, request.strategy_params, request.initial_cash, request.fee_bps, request.slippage_bps, request.stop_atr_multiple, request.target_risk_reward, request.max_holding_bars, request.start_time, request.end_time)
                result.update({"symbol": symbol.upper(), "timeframe": timeframe})
                results.append(result)
            except ValueError:
                continue
    if not results:
        raise HTTPException(status_code=409, detail="No valid data for the selected assets and period")
    return {"strategy_type": request.strategy_type, "results": results}
