from app.api.chat import build_market_context_prompt, extract_requested_symbols


def test_extract_requested_symbols_normalizes_names_and_pairs():
    assert extract_requested_symbols("Compare Bitcoin, ETHUSDT e Solana") == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_build_market_context_prompt_includes_allowed_scope_and_current_market_context():
    prompt = build_market_context_prompt(
        message="Qual a tendência do BTCUSDT?",
        symbol="BTCUSDT",
        timeframe="1h",
        signal="BUY",
        last_price=67250.12,
        spread=0.18,
        market_state="tendência de alta",
    )

    assert "BTCUSDT" in prompt
    assert "1h" in prompt
    assert "BUY" in prompt
    assert "spread" in prompt.lower()
    assert "somente" in prompt.lower()
    assert "não responder" in prompt.lower()
    assert "tendência" in prompt.lower()
    assert "análise condicional" in prompt.lower()


def test_build_market_context_prompt_includes_live_binance_snapshot():
    prompt = build_market_context_prompt(
        message="Me fale o cenário atual do BTC",
        symbol="BTCUSDT",
        timeframe="1h",
        live_context={
            "source": "Binance public REST",
            "current_price": 77000.0,
            "change_24h_percent": 2.4,
            "volume_24h": 123.5,
            "sma_20": 67000.0,
        },
    )

    assert "Binance public REST" in prompt
    assert "current_price" in prompt
    assert "change_24h_percent" in prompt
    assert "sma_20" in prompt
    assert "USD/USDT" in prompt
