from types import SimpleNamespace

import numpy as np

from app.ml.backtester import run_backtest_v2


class LongTrainer:
    def predict(self, features):
        return np.array([1]), np.array([0.9])


def make_candle(index, open_price, high, low, close):
    return SimpleNamespace(open_time=index * 1000, close_time=index * 1000 + 999, open=open_price, high=high, low=low, close=close)


def test_backtest_v2_records_take_profit_and_mae_mfe():
    candles = [make_candle(index, 100, 101, 99, 100) for index in range(70)]
    candles[56] = make_candle(56, 100, 104, 99, 103)
    result = run_backtest_v2(candles, np.zeros((70, 1)), LongTrainer(), evaluation_indices=[55], fee_bps=0, slippage_bps=0, max_holding_bars=3)
    assert result["total_trades"] == 1
    assert result["exit_reasons"]["take_profit"] == 1
    assert result["trades"][0]["mfe"] > 0
    assert result["trades"][0]["mae"] < 0


def test_backtest_v2_uses_stop_before_target_on_same_bar():
    candles = [make_candle(index, 100, 101, 99, 100) for index in range(70)]
    candles[56] = make_candle(56, 100, 104, 95, 100)
    result = run_backtest_v2(candles, np.zeros((70, 1)), LongTrainer(), evaluation_indices=[55], fee_bps=0, slippage_bps=0, max_holding_bars=2)
    assert result["exit_reasons"]["stop_loss"] == 1
