ALTER TABLE paper_trades
    ADD COLUMN IF NOT EXISTS decision_snapshot JSONB;

CREATE INDEX IF NOT EXISTS ix_paper_trades_assessment_id
    ON paper_trades ((decision_snapshot->>'assessment_id'));