ALTER TABLE paper_trades
    ADD COLUMN IF NOT EXISTS exit_reason VARCHAR(32);

UPDATE paper_trades
SET exit_reason = 'MANUAL'
WHERE status = 'CLOSED' AND exit_reason IS NULL;