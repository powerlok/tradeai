CREATE TABLE IF NOT EXISTS news_items (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(64) NOT NULL,
    title VARCHAR(512) NOT NULL,
    published_at VARCHAR(128) NOT NULL DEFAULT '',
    url VARCHAR(1024) NOT NULL UNIQUE,
    assets JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_type VARCHAR(32) NOT NULL,
    sentiment VARCHAR(16) NOT NULL,
    impact VARCHAR(16) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    first_seen_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_news_items_source ON news_items (source);
CREATE INDEX IF NOT EXISTS ix_news_items_first_seen ON news_items (first_seen_at);