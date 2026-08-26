from app.quality.data_quality import QualityStatus, validate_candle, validate_candle_series


def candle(**overrides):
    value = {
        "open_time": 1_000_000,
        "close_time": 1_003_599,
        "open": 100.0,
        "high": 105.0,
        "low": 95.0,
        "close": 102.0,
        "volume": 12.0,
    }
    value.update(overrides)
    return value


def test_valid_candle_is_accepted():
    result = validate_candle(candle(), now_ms=2_000_000)

    assert result.status is QualityStatus.VALID
    assert result.issues == ()


def test_invalid_ohlc_and_volume_are_rejected():
    result = validate_candle(candle(high=90.0, low=110.0, volume=-1.0), now_ms=2_000_000)

    assert result.status is QualityStatus.INVALID
    assert "high_below_ohlc" in result.issues
    assert "low_above_ohlc" in result.issues
    assert "negative_volume" in result.issues


def test_incomplete_and_extreme_candle_are_warnings():
    result = validate_candle(candle(high=140.0, close_time=2_000_000), now_ms=2_000_000)

    assert result.status is QualityStatus.WARNING
    assert "incomplete_candle" in result.issues
    assert "extreme_range" in result.issues


def test_series_detects_duplicates_ordering_and_gaps():
    result = validate_candle_series(
        [
            candle(open_time=1_000, close_time=1_359),
            candle(open_time=3_000, close_time=3_359),
            candle(open_time=2_000, close_time=2_359),
            candle(open_time=3_000, close_time=3_359),
        ],
        timeframe_ms=1_000,
    )

    assert result.status is QualityStatus.WARNING
    assert "timestamp_gap" in result.issues
    assert "out_of_order" in result.issues
    assert "duplicate_timestamp" in result.issues
