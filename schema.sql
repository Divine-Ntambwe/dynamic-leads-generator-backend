CREATE TABLE IF NOT EXISTS visited_urls (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schools (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    website TEXT,
    fingerprint VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_url_hash ON visited_urls(url_hash);
CREATE INDEX IF NOT EXISTS idx_fingerprint ON schools(fingerprint);

CREATE TABLE IF NOT EXISTS query_progress (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL UNIQUE,
    last_start_position INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query ON query_progress(query);
