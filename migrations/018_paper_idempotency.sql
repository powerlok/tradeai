CREATE UNIQUE INDEX IF NOT EXISTS uq_paper_trades_open_symbol
    ON paper_trades (symbol)
    WHERE status = 'OPEN';