-- Vortexia Chatbot — schema V0 (spec 4.3)
-- Runs automatically on first postgres boot via /docker-entrypoint-initdb.d/

CREATE EXTENSION IF NOT EXISTS vector;

-- Tenants (une ligne par démo/client)
CREATE TABLE tenants (
    id               TEXT PRIMARY KEY,
    display_name     TEXT NOT NULL,
    source_url       TEXT NOT NULL,
    logo_url         TEXT,
    primary_color    TEXT DEFAULT '#000000',
    status           TEXT NOT NULL DEFAULT 'active',
    expires_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    fallback_message TEXT DEFAULT 'Je n''ai pas cette information dans ma base.'
);

-- Sources ingérées (traçabilité)
CREATE TABLE sources (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    TEXT REFERENCES tenants(id) ON DELETE CASCADE,
    url          TEXT NOT NULL,
    title        TEXT,
    content_hash TEXT NOT NULL,
    fetched_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, content_hash)
);
CREATE INDEX idx_sources_tenant ON sources(tenant_id);

-- Chunks + embeddings
CREATE TABLE chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT REFERENCES tenants(id) ON DELETE CASCADE,
    source_id   UUID REFERENCES sources(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content     TEXT NOT NULL,
    tokens      INT NOT NULL,
    embedding   VECTOR(1536) NOT NULL,
    metadata    JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_chunks_tenant ON chunks(tenant_id);
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);

-- Suggestions de questions (générées à l'ingestion)
CREATE TABLE suggestions (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
    question  TEXT NOT NULL,
    position  INT NOT NULL
);

-- Sessions (une par conversation)
CREATE TABLE sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    TEXT REFERENCES tenants(id) ON DELETE CASCADE,
    ip_hash      TEXT NOT NULL,
    user_agent   TEXT,
    started_at   TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sessions_tenant ON sessions(tenant_id);

-- Messages (audit + qualité)
CREATE TABLE messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id     TEXT REFERENCES tenants(id) ON DELETE CASCADE,
    role          TEXT NOT NULL,
    content       TEXT NOT NULL,
    sources_cited JSONB DEFAULT '[]'::jsonb,
    latency_ms    INT,
    tokens_in     INT,
    tokens_out    INT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_session ON messages(session_id);
