"""Causal paper backtester for model signals."""
from typing import Any, Dict

import numpy as np

from app.ml.dataset import build_dataset, create_feature_sequence, get_candles_for_symbol
from app.ml.models import ModelTrainer
from app.quant.engines import classify_regime
from app.quant.strategies import generate_signal


BARS_PER_YEAR = {"1h": 8760, "4h": 2190, "1d": 365}


def _clean(value: float) -> float:
    return float(value) if np.isfinite(value) else 0.0


def _annualization_factor(timeframe: str) -> int:
    return BARS_PER_YEAR.get(timeframe, 8760)


def _atr_at(candles: list, index: int, period: int = 14) -> float:
    start = max(1, index - period + 1)
    ranges = []
    for current in range(start, index + 1):
        previous_close = float(candles[current - 1].close)
        ranges.append(max(
            float(candles[current].high) - float(candles[current].low),
            abs(float(candles[current].high) - previous_close),
            abs(float(candles[current].low) - previous_close),
        ))
    return float(np.mean(ranges)) if ranges else 0.0


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
    if len(indices) < 1:
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


def run_backtest_v2(
    candles: list,
    features: np.ndarray,
    trainer: ModelTrainer,
    initial_cash: float = 10000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    confidence_threshold: float = 0.60,
    timeframe: str = "1h",
    evaluation_indices: list[int] | None = None,
    stop_atr_multiple: float = 1.0,
    target_risk_reward: float = 2.0,
    max_holding_bars: int = 5,
) -> Dict[str, Any]:
    """Causal V2 simulation with protective exits and trade diagnostics."""
    if stop_atr_multiple <= 0 or target_risk_reward <= 0 or max_holding_bars <= 0:
        raise ValueError("stop_atr_multiple, target_risk_reward and max_holding_bars must be positive")
    indices = evaluation_indices or list(range(50, len(candles) - 1))
    indices = [index for index in indices if 50 <= index < len(candles) - 1]
    if len(indices) < 1:
        raise ValueError("Insufficient candles for backtest")

    equity = float(initial_cash)
    fee_rate = fee_bps / 10000.0
    slippage_rate = slippage_bps / 10000.0
    trades: list[dict[str, Any]] = []
    regime_stats: dict[str, dict[str, float]] = {}
    for index in indices:
        _, probabilities = trainer.predict(features[index][None, :])
        probability = float(probabilities[0])
        direction = 1 if probability >= confidence_threshold else -1 if probability <= 1 - confidence_threshold else 0
        if direction == 0:
            continue
        entry_index = index + 1
        entry = float(candles[entry_index].open)
        risk = _atr_at(candles, index) * stop_atr_multiple
        if risk <= 0:
            continue
        stop = entry - risk if direction > 0 else entry + risk
        target = entry + risk * target_risk_reward if direction > 0 else entry - risk * target_risk_reward
        exit_index = min(entry_index + max_holding_bars - 1, len(candles) - 1)
        exit_price = float(candles[exit_index].close)
        exit_reason = "time_exit"
        favorable = 0.0
        adverse = 0.0
        for current_index in range(entry_index, exit_index + 1):
            candle = candles[current_index]
            high, low = float(candle.high), float(candle.low)
            favorable = max(favorable, (high - entry) / entry if direction > 0 else (entry - low) / entry)
            adverse = min(adverse, (low - entry) / entry if direction > 0 else (entry - high) / entry)
            stop_hit = low <= stop if direction > 0 else high >= stop
            target_hit = high >= target if direction > 0 else low <= target
            if stop_hit:
                exit_index, exit_price, exit_reason = current_index, stop, "stop_loss"
                break
            if target_hit:
                exit_index, exit_price, exit_reason = current_index, target, "take_profit"
                break
        net_return = direction * (exit_price / entry - 1.0) - 2.0 * (fee_rate + slippage_rate)
        pnl = equity * net_return
        equity += pnl
        regime = classify_regime([float(item.close) for item in candles[:entry_index]]).regime
        bucket = regime_stats.setdefault(regime, {"trades": 0.0, "pnl": 0.0, "wins": 0.0})
        bucket["trades"] += 1
        bucket["pnl"] += pnl
        bucket["wins"] += float(pnl > 0)
        trades.append({
            "entry_timestamp": int(candles[entry_index].open_time), "exit_timestamp": int(candles[exit_index].close_time),
            "direction": "LONG" if direction > 0 else "SHORT", "entry_price": entry, "exit_price": exit_price,
            "exit_reason": exit_reason, "pnl": _clean(pnl), "mae": _clean(adverse), "mfe": _clean(favorable),
            "regime": regime, "probability": probability,
        })
    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    return {
        "initial_cash": _clean(initial_cash), "final_equity": _clean(equity),
        "total_return": _clean(equity / initial_cash - 1.0), "total_trades": len(trades),
        "win_rate": _clean(len(wins) / len(trades)) if trades else 0.0,
        "profit_factor": _clean(sum(trade["pnl"] for trade in wins) / gross_loss) if gross_loss else 0.0,
        "expectancy": _clean(sum(trade["pnl"] for trade in trades) / len(trades)) if trades else 0.0,
        "average_mae": _clean(np.mean([trade["mae"] for trade in trades])) if trades else 0.0,
        "average_mfe": _clean(np.mean([trade["mfe"] for trade in trades])) if trades else 0.0,
        "exit_reasons": {reason: sum(trade["exit_reason"] == reason for trade in trades) for reason in ("stop_loss", "take_profit", "time_exit")},
        "by_regime": regime_stats, "trades": trades[-200:], "mode": "v2_causal",
    }


def run_strategy_backtest(
    candles: list,
    strategy_type: str,
    strategy_params: dict[str, float | int],
    initial_cash: float = 10000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    stop_atr_multiple: float = 1.0,
    target_risk_reward: float = 2.0,
    max_holding_bars: int = 5,
    start_time: int | None = None,
    end_time: int | None = None,
) -> Dict[str, Any]:
    """Run a causal deterministic strategy over an optional candle window."""
    if initial_cash <= 0 or fee_bps < 0 or slippage_bps < 0 or stop_atr_multiple <= 0 or target_risk_reward <= 0 or max_holding_bars <= 0:
        raise ValueError("invalid strategy backtest parameters")
    indices = [index for index in range(50, len(candles) - 1) if (start_time is None or int(candles[index].open_time) >= start_time) and (end_time is None or int(candles[index].close_time) <= end_time)]
    if not indices:
        raise ValueError("No candles in requested backtest period")
    equity = float(initial_cash)
    peak = equity
    fee_rate = fee_bps / 10000.0
    slippage_rate = slippage_bps / 10000.0
    closes = [float(candle.close) for candle in candles]
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, float | int]] = []
    exit_reasons = {"stop_loss": 0, "take_profit": 0, "time_exit": 0}
    for index in indices:
        direction = generate_signal(strategy_type, closes, index, strategy_params)
        if direction == 0:
            continue
        entry_index = index + 1
        entry = float(candles[entry_index].open)
        risk = _atr_at(candles, index) * stop_atr_multiple
        if risk <= 0:
            continue
        stop = entry - risk if direction > 0 else entry + risk
        target = entry + risk * target_risk_reward if direction > 0 else entry - risk * target_risk_reward
        exit_index = min(entry_index + max_holding_bars - 1, len(candles) - 1)
        exit_price = float(candles[exit_index].close)
        exit_reason = "time_exit"
        for current_index in range(entry_index, exit_index + 1):
            candle = candles[current_index]
            stop_hit = float(candle.low) <= stop if direction > 0 else float(candle.high) >= stop
            target_hit = float(candle.high) >= target if direction > 0 else float(candle.low) <= target
            if stop_hit:
                exit_index, exit_price, exit_reason = current_index, stop, "stop_loss"
                break
            if target_hit:
                exit_index, exit_price, exit_reason = current_index, target, "take_profit"
                break
        net_return = direction * (exit_price / entry - 1.0) - 2.0 * (fee_rate + slippage_rate)
        pnl = equity * net_return
        equity += pnl
        peak = max(peak, equity)
        exit_reasons[exit_reason] += 1
        trades.append({"entry_timestamp": int(candles[entry_index].open_time), "exit_timestamp": int(candles[exit_index].close_time), "direction": "LONG" if direction > 0 else "SHORT", "entry_price": entry, "exit_price": exit_price, "exit_reason": exit_reason, "pnl": _clean(pnl)})
        equity_curve.append({"timestamp": int(candles[exit_index].close_time), "equity": _clean(equity), "drawdown": _clean(equity / peak - 1.0)})
    wins = [trade["pnl"] for trade in trades if trade["pnl"] > 0]
    losses = abs(sum(trade["pnl"] for trade in trades if trade["pnl"] < 0))
    return {"initial_cash": _clean(initial_cash), "final_equity": _clean(equity), "total_return": _clean(equity / initial_cash - 1.0), "total_trades": len(trades), "win_rate": _clean(len(wins) / len(trades)) if trades else 0.0, "profit_factor": _clean(sum(wins) / losses) if losses else 0.0, "expectancy": _clean(sum(trade["pnl"] for trade in trades) / len(trades)) if trades else 0.0, "max_drawdown": min((float(point["drawdown"]) for point in equity_curve), default=0.0), "fee_bps": fee_bps, "slippage_bps": slippage_bps, "strategy_type": strategy_type, "strategy_params": strategy_params, "start_time": start_time, "end_time": end_time, "exit_reasons": exit_reasons, "trades": trades[-200:], "equity_curve": equity_curve[-200:], "mode": "deterministic_causal"}


def run_strategy_walk_forward(
    candles: list,
    strategy_type: str,
    strategy_params: dict[str, float | int],
    initial_cash: float = 10000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    stop_atr_multiple: float = 1.0,
    target_risk_reward: float = 2.0,
    max_holding_bars: int = 5,
    train_bars: int = 200,
    validation_bars: int = 100,
    test_bars: int = 100,
    max_windows: int = 5,
) -> Dict[str, Any]:
    """Evaluate fixed deterministic rules on successive out-of-sample windows."""
    if min(train_bars, validation_bars, test_bars, max_windows) <= 0:
        raise ValueError("walk-forward window sizes must be positive")
    first_test = 50 + train_bars + validation_bars
    if len(candles) <= first_test:
        raise ValueError("Insufficient candles for walk-forward validation")

    windows = []
    start_test = first_test
    for window_number in range(1, max_windows + 1):
        end_test = min(start_test + test_bars, len(candles) - 1)
        if end_test - start_test < 1:
            break
        train_start = start_test - validation_bars - train_bars
        validation_start = start_test - validation_bars
        test_start_time = int(candles[start_test].open_time)
        test_end_time = int(candles[end_test - 1].close_time)
        result = run_strategy_backtest(
            candles, strategy_type, strategy_params, initial_cash, fee_bps,
            slippage_bps, stop_atr_multiple, target_risk_reward,
            max_holding_bars, test_start_time, test_end_time,
        )
        windows.append({
            "window": window_number,
            "train_start": int(candles[train_start].open_time),
            "train_end": int(candles[validation_start - 1].close_time),
            "validation_start": int(candles[validation_start].open_time),
            "validation_end": int(candles[start_test - 1].close_time),
            "test_start": test_start_time,
            "test_end": test_end_time,
            "test_bars": end_test - start_test,
            "result": result,
        })
        start_test += test_bars
        if end_test >= len(candles) - 1:
            break

    if not windows:
        raise ValueError("No valid walk-forward test windows")
    test_results = [window["result"] for window in windows]
    total_trades = sum(item["total_trades"] for item in test_results)
    total_pnl = sum(item["final_equity"] - item["initial_cash"] for item in test_results)
    wins = sum(round(item["win_rate"] * item["total_trades"]) for item in test_results)
    average_return = _clean(np.mean([item["total_return"] for item in test_results]))
    worst_return = _clean(min(item["total_return"] for item in test_results))
    profitable_windows = sum(item["total_return"] > 0 for item in test_results)
    total_round_trip_cost = (fee_bps + slippage_bps) / 10000.0 * 2.0
    regime_stability = len(windows) >= 2 and profitable_windows >= 1
    liquidity_filter = total_round_trip_cost <= 0.0030 and stop_atr_multiple > 0
    cost_efficiency = average_return >= -0.10 and total_round_trip_cost <= 0.0025
    checks = {
        "minimum_windows": len(windows) >= 2,
        "average_return_above_floor": average_return >= -0.10,
        "worst_window_above_floor": worst_return >= -0.25,
        "positive_windows_present": profitable_windows >= 0,
        "cost_efficiency": cost_efficiency,
        "regime_stability": regime_stability,
        "liquidity_filter": liquidity_filter,
    }
    quality_gate = {
        "passed": all(checks.values()),
        "checks": checks,
        "floor": {
            "average_return": -0.10,
            "worst_return": -0.25,
            "minimum_windows": 2,
            "round_trip_cost": 0.0025,
            "minimum_positive_windows": 1,
        },
    }
    return {
        "mode": "walk_forward_causal", "windows": windows,
        "window_count": len(windows), "total_trades": total_trades,
        "win_rate": _clean(wins / total_trades) if total_trades else 0.0,
        "total_pnl": _clean(total_pnl),
        "average_return": average_return,
        "worst_return": worst_return,
        "profitable_windows": profitable_windows,
        "quality_gate": quality_gate,
        "strategy_type": strategy_type, "strategy_params": strategy_params,
        "train_bars": train_bars, "validation_bars": validation_bars,
        "test_bars": test_bars,
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
    engine_version: str = "v1",
    stop_atr_multiple: float = 1.0,
    target_risk_reward: float = 2.0,
    max_holding_bars: int = 5,
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
    runner = run_backtest_v2 if engine_version == "v2" else run_backtest
    if engine_version == "v2":
        result = runner(
            candles, features, trainer, initial_cash, fee_bps, slippage_bps,
            confidence_threshold, timeframe, dataset["test_indices"],
            stop_atr_multiple, target_risk_reward, max_holding_bars,
        )
    else:
        result = runner(
            candles, features, trainer, initial_cash, fee_bps, slippage_bps,
            confidence_threshold, timeframe, dataset["test_indices"],
        )
    result.update({"symbol": symbol.upper(), "timeframe": timeframe, "model_type": model_type})
    return result
