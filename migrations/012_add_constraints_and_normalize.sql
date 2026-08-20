-- Migration: deduplicate trades and snapshots, add unique indexes, convert snapshots bids/asks to jsonb and add counts
BEGIN;
-- Deduplicate trades keeping the lowest id per (symbol, trade_id)
DELETE FROM trades a
USING trades b
WHERE a.id > b.id AND a.symbol = b.symbol AND a.trade_id = b.trade_id;

-- Create unique index for trades
CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_symbol_tradeid ON trades (symbol, trade_id);

-- Deduplicate snapshots keeping lowest id per (symbol, event_time)
DELETE FROM order_book_snapshots a
USING order_book_snapshots b
WHERE a.id > b.id AND a.symbol = b.symbol AND a.event_time = b.event_time;

-- Convert bids/asks to jsonb
ALTER TABLE order_book_snapshots ALTER COLUMN bids TYPE jsonb USING bids::jsonb;
ALTER TABLE order_book_snapshots ALTER COLUMN asks TYPE jsonb USING asks::jsonb;

-- Add counts columns if not present
ALTER TABLE order_book_snapshots ADD COLUMN IF NOT EXISTS bids_count integer DEFAULT 0;
ALTER TABLE order_book_snapshots ADD COLUMN IF NOT EXISTS asks_count integer DEFAULT 0;

-- Populate counts
UPDATE order_book_snapshots SET bids_count = COALESCE(jsonb_array_length(bids),0), asks_count = COALESCE(jsonb_array_length(asks),0);

-- Create unique index for snapshots
CREATE UNIQUE INDEX IF NOT EXISTS uq_snapshot_symbol_event ON order_book_snapshots (symbol, event_time);

COMMIT;
