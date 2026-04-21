CREATE TABLE IF NOT EXISTS visited_urls (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGSERIAL NOT NULL,
    job_name TEXT NOT NULL,
    lead_type TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    url TEXT,
    organization_name TEXT,
    job_position TEXT,
    notes TEXT,
    fingerprint VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_url_hash ON visited_urls(url_hash);
CREATE INDEX IF NOT EXISTS idx_fingerprint ON leads(fingerprint);

CREATE TABLE IF NOT EXISTS query_progress (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL UNIQUE,
    last_start_position INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query ON query_progress(query);
