import pytest

from app.market.normalizer import (
    normalize_book_ticker,
    normalize_kline,
    normalize_order_book,
    normalize_trade,
)


def test_normalize_kline_maps_binance_array():
    result = normalize_kline("btcusdt", "5m", [1000, "10", "12", "9", "11", "25", 1299])

    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "5m"
    assert result.open == 10.0
    assert result.close_time == 1299


def test_normalize_trade_derives_side_and_preserves_times():
    result = normalize_trade(
        {"s": "ethusdt", "t": 42, "p": "2000.5", "q": "0.25", "m": True, "T": 1234},
        received_time=1250,
    )

    assert result.symbol == "ETHUSDT"
    assert result.quantity == 0.25
    assert result.side == "sell"
    assert result.event_time == 1234
    assert result.received_time == 1250


def test_normalize_order_book_supports_rest_and_websocket_shapes():
    rest = normalize_order_book(
        "btcusdt", {"lastUpdateId": 99, "bids": [["10", "1"]], "asks": [["11", "2"]]}, received_time=100
    )
    websocket = normalize_order_book(
        "btcusdt", {"E": 101, "b": [["10", "1"]], "a": [["11", "2"]]}, received_time=102
    )

    assert rest.event_time == 100
    assert rest.bids == [["10", "1"]]
    assert websocket.event_time == 101
    assert websocket.asks == [["11", "2"]]


def test_normalize_book_ticker_maps_quote_fields():
    result = normalize_book_ticker(
        {"s": "solusdt", "E": 200, "b": "100", "B": "3", "a": "101", "A": "4"},
        received_time=201,
    )

    assert result.symbol == "SOLUSDT"
    assert result.bid_price == 100.0
    assert result.ask_quantity == 4.0
    assert result.event_time == 200
    assert result.received_time == 201


def test_normalizers_reject_incomplete_payloads():
    with pytest.raises((KeyError, ValueError)):
        normalize_kline("BTCUSDT", "1h", [1, 2])
    with pytest.raises(KeyError):
        normalize_book_ticker({"s": "BTCUSDT"})
