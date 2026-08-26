-- Initial schema for Trading AI

CREATE TABLE IF NOT EXISTS candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    timeframe VARCHAR(8) NOT NULL,
    open_time BIGINT NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    close_time BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_candle_symbol_timeframe_time ON candles (symbol, timeframe, open_time);

CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    trade_id BIGINT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    buyer_maker VARCHAR(8),
    event_time BIGINT,
    received_time BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_trade_symbol_event ON trades (symbol, event_time);

CREATE TABLE IF NOT EXISTS order_book_snapshots (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    event_time BIGINT NOT NULL,
    received_time BIGINT NOT NULL,
    bids JSON NOT NULL,
    asks JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS order_book_updates (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    event_time BIGINT NOT NULL,
    received_time BIGINT NOT NULL,
    bids JSON,
    asks JSON
);

CREATE TABLE IF NOT EXISTS book_tickers (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    event_time BIGINT NOT NULL,
    received_time BIGINT NOT NULL,
    bid_price DOUBLE PRECISION NOT NULL,
    bid_qty DOUBLE PRECISION NOT NULL,
    ask_price DOUBLE PRECISION NOT NULL,
    ask_qty DOUBLE PRECISION NOT NULL,
    CONSTRAINT uq_book_ticker_symbol_event_time UNIQUE (symbol, event_time)
);
