CREATE TABLE IF NOT EXISTS paper_trade_events (
    id BIGSERIAL PRIMARY KEY,
    paper_trade_id BIGINT NOT NULL REFERENCES paper_trades(id),
    symbol VARCHAR(16) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    event_time BIGINT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_paper_trade_events_trade_time
    ON paper_trade_events (paper_trade_id, event_time, id);
