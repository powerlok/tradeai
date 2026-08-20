from app.api.market import summarize_orderbook


def test_summarize_orderbook_returns_best_bid_ask_and_spread():
    snapshot = {
        "bids": [["100.10", "2.00"], ["100.05", "1.50"]],
        "asks": [["100.25", "1.80"], ["100.30", "2.50"]],
    }

    result = summarize_orderbook(snapshot)

    assert result["best_bid"] == 100.10
    assert result["best_ask"] == 100.25
    assert result["spread"] == 0.15
    assert result["mid_price"] == 100.175
