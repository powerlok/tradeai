ALTER TABLE trades ADD COLUMN IF NOT EXISTS received_time BIGINT;
UPDATE trades SET received_time = COALESCE(event_time, 0) WHERE received_time IS NULL;
ALTER TABLE trades ALTER COLUMN received_time SET NOT NULL;

ALTER TABLE order_book_snapshots ADD COLUMN IF NOT EXISTS received_time BIGINT;
UPDATE order_book_snapshots SET received_time = COALESCE(event_time, 0) WHERE received_time IS NULL;
ALTER TABLE order_book_snapshots ALTER COLUMN received_time SET NOT NULL;

ALTER TABLE order_book_updates ADD COLUMN IF NOT EXISTS received_time BIGINT;
UPDATE order_book_updates SET received_time = COALESCE(event_time, 0) WHERE received_time IS NULL;
ALTER TABLE order_book_updates ALTER COLUMN received_time SET NOT NULL;

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

CREATE INDEX IF NOT EXISTS ix_book_ticker_symbol_event
    ON book_tickers (symbol, event_time);