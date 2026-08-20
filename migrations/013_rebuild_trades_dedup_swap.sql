-- Migration 013: Rebuild trades table deduplicated using DISTINCT ON and recreate sequence/index
BEGIN;
-- create deduped table
CREATE TABLE trades_new AS
SELECT DISTINCT ON (symbol, trade_id) id, symbol, trade_id, price, qty, buyer_maker, event_time
FROM trades
ORDER BY symbol, trade_id, id;

-- ensure id not null
ALTER TABLE trades_new ALTER COLUMN id SET NOT NULL;

-- drop old table and rename
DROP TABLE trades;
ALTER TABLE trades_new RENAME TO trades;

-- recreate sequence and set default
CREATE SEQUENCE IF NOT EXISTS trades_id_seq;
SELECT setval('trades_id_seq', COALESCE((SELECT MAX(id) FROM trades), 1), false);
ALTER TABLE trades ALTER COLUMN id SET DEFAULT nextval('trades_id_seq');

-- recreate indexes
CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_symbol_tradeid ON trades (symbol, trade_id);
CREATE INDEX IF NOT EXISTS ix_trade_symbol_event ON trades (symbol, event_time);

COMMIT;
