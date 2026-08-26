CREATE TABLE IF NOT EXISTS paper_trades (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    direction VARCHAR(8) NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION,
    stop DOUBLE PRECISION NOT NULL,
    target DOUBLE PRECISION NOT NULL,
    status VARCHAR(16) NOT NULL,
    opened_at BIGINT NOT NULL,
    closed_at BIGINT,
    pnl DOUBLE PRECISION,
    fees DOUBLE PRECISION NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_paper_trades_symbol_status ON paper_trades (symbol, status);