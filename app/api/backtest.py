from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.engine import AsyncSession
from app.ml.backtester import backtest_model

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
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=409, detail=f"No active model approved for {request.symbol.upper()} {request.timeframe} {request.model_type}. Train and approve a model before running the backtest.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {error}")


@router.get("/info")
async def backtest_info():
    return {
        "description": "Causal paper backtester with fees, slippage, drawdown and Sharpe",
        "endpoint": "POST /api/ml/backtest/run",
        "defaults": {
            "initial_cash": 10000.0,
            "fee_bps": 10.0,
            "slippage_bps": 5.0,
            "confidence_threshold": 0.60,
        },
        "execution": "Signals are decided at candle close and executed on the next candle open; no exchange orders are submitted.",
    }
