import pytest

from app.quant.paper import PaperPosition, PaperTradingEngine
from app.quant.validation import brier_score, create_walk_forward_windows, make_target


def test_dataset_v2_targets_and_windows():
    assert make_target(100, 103, 5).label == "LONG"
    assert make_target(100, 99, 5).label == "SHORT"
    assert make_target(100, 100.1, 5).label == "NO_TRADE"
    assert len(create_walk_forward_windows(100, 50, 20, 10)) == 3


def test_calibration_brier_score():
    assert brier_score([0.9, 0.1], [1, 0]) == pytest.approx(0.01)


def test_paper_engine_is_virtual_and_tracks_pnl():
    engine = PaperTradingEngine(1000, fee_bps=0)
    engine.open_position(PaperPosition("BTCUSDT", "LONG", 1, 100, 95, 110, 1))
    assert engine.mark("BTCUSDT", 105)["unrealized_pnl"] == 5
    result = engine.close_position("BTCUSDT", 105, 2)
    assert result["pnl"] == 5
    assert engine.positions == {}


def test_paper_engine_rejects_duplicate_open_symbol():
    engine = PaperTradingEngine(1000, fee_bps=0)
    position = PaperPosition("BTCUSDT", "LONG", 1, 100, 95, 110, 1)
    engine.open_position(position)
    with pytest.raises(ValueError, match="already has an open"):
        engine.open_position(position)
