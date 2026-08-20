"""Causal paper backtester for model signals."""
from typing import Any, Dict

import numpy as np

from app.ml.dataset import build_dataset, create_feature_sequence, get_candles_for_symbol
from app.ml.models import ModelTrainer


BARS_PER_YEAR = {"1h": 8760, "4h": 2190, "1d": 365}


def _clean(value: float) -> float:
    return float(value) if np.isfinite(value) else 0.0


def _annualization_factor(timeframe: str) -> int:
    return BARS_PER_YEAR.get(timeframe, 8760)


def run_backtest(
    candles: list,
    features: np.ndarray,
    trainer: ModelTrainer,
    initial_cash: float = 10000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    confidence_threshold: float = 0.60,
    timeframe: str = "1h",
    evaluation_indices: list[int] | None = None,
) -> Dict[str, Any]:
    if initial_cash <= 0:
        raise ValueError("initial_cash must be greater than zero")
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee_bps and slippage_bps cannot be negative")
    if not 0.5 < confidence_threshold < 1.0:
        raise ValueError("confidence_threshold must be between 0.5 and 1.0")

    indices = evaluation_indices or list(range(50, len(candles) - 1))
    indices = [index for index in indices if 50 <= index < len(candles) - 1]
    if len(indices) < 2:
        raise ValueError("Insufficient candles for backtest")

    equity = float(initial_cash)
    peak_equity = equity
    position = 0
    total_fees = 0.0
    total_slippage = 0.0
    returns = []
    equity_curve = []
    trades = []

    cost_rate = fee_bps / 10000.0
    slippage_rate = slippage_bps / 10000.0

    for index in indices:
        period_start_equity = equity
        prediction, probabilities = trainer.predict(features[index][None, :])
        probability = float(probabilities[0])
        if probability >= confidence_threshold:
            target_position = 1
            signal = "BUY"
        elif probability <= 1.0 - confidence_threshold:
            target_position = -1
            signal = "SELL"
        else:
            target_position = 0
            signal = "WATCH"

        turnover = abs(target_position - position)
        fees = period_start_equity * turnover * cost_rate
        slippage = period_start_equity * turnover * slippage_rate
        total_fees += fees
        total_slippage += slippage
        equity -= fees + slippage

        entry_price = float(candles[index + 1].open)
        exit_price = float(candles[index + 1].close)
        bar_return = target_position * ((exit_price / entry_price) - 1.0)
        pnl = equity * bar_return
        equity += pnl
        returns.append((equity / max(period_start_equity, 1e-12)) - 1.0)

        if target_position != position:
            trades.append({
                "timestamp": candles[index + 1].open_time,
                "signal": signal,
                "position": target_position,
                "price": entry_price,
                "probability": probability,
                "fees": fees,
                "slippage": slippage,
            })
        position = target_position
        peak_equity = max(peak_equity, equity)
        drawdown = equity / peak_equity - 1.0
        equity_curve.append({
            "timestamp": candles[index + 1].close_time,
            "equity": _clean(equity),
            "drawdown": _clean(drawdown),
            "position": position,
        })

    returns_array = np.asarray(returns, dtype=np.float64)
    mean_return = float(returns_array.mean()) if len(returns_array) else 0.0
    std_return = float(returns_array.std(ddof=1)) if len(returns_array) > 1 else 0.0
    sharpe = mean_return / std_return * np.sqrt(_annualization_factor(timeframe)) if std_return else 0.0
    profitable = int((returns_array > 0).sum()) if len(returns_array) else 0
    buy_hold = float(candles[indices[-1] + 1].close / candles[indices[0] + 1].open - 1.0)
    total_return = equity / initial_cash - 1.0
    max_drawdown = min((point["drawdown"] for point in equity_curve), default=0.0)

    return {
        "initial_cash": _clean(initial_cash),
        "final_equity": _clean(equity),
        "total_return": _clean(total_return),
        "buy_hold_return": _clean(buy_hold),
        "excess_return": _clean(total_return - buy_hold),
        "sharpe_ratio": _clean(sharpe),
        "max_drawdown": _clean(max_drawdown),
        "total_trades": len(trades),
        "win_rate": _clean(profitable / len(returns_array)) if len(returns_array) else 0.0,
        "total_fees": _clean(total_fees),
        "total_slippage": _clean(total_slippage),
        "bars": len(returns_array),
        "evaluation_mode": "temporal_holdout" if evaluation_indices is not None else "full_history",
        "out_of_sample": evaluation_indices is not None,
        "confidence_threshold": confidence_threshold,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "equity_curve": equity_curve[-200:],
        "trades": trades[-100:],
    }


async def backtest_model(
    db,
    symbol: str,
    timeframe: str = "1h",
    model_type: str = "logistic",
    initial_cash: float = 10000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    confidence_threshold: float = 0.60,
) -> Dict[str, Any]:
    candles = await get_candles_for_symbol(db, symbol.upper(), timeframe, limit=500)
    if len(candles) < 100:
        raise ValueError(f"Insufficient candles for {symbol} ({len(candles)}). Need at least 100.")
    features, _ = await create_feature_sequence(db, symbol.upper(), timeframe)
    if features is None:
        raise ValueError("Could not create feature sequence")
    try:
        trainer = ModelTrainer.load(symbol.upper(), model_type, timeframe)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"No active model for {symbol.upper()} {timeframe} {model_type}: {error}")
    dataset = await build_dataset(db, symbol.upper(), timeframe, train_ratio=0.8)
    result = run_backtest(
        candles, features, trainer, initial_cash, fee_bps, slippage_bps,
        confidence_threshold, timeframe, dataset["test_indices"],
    )
    result.update({"symbol": symbol.upper(), "timeframe": timeframe, "model_type": model_type})
    return result
