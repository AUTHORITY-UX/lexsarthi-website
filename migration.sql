-- ============================================================
-- Unknown Verdict Moat v41.0 — Neon Migration
-- Run this in your Neon SQL Editor (production branch)
-- Adds moat_* tables alongside your existing schema.
-- Uses vector(384) to match your all-MiniLM-L6-v2 embeddings.
-- ============================================================

-- 1. Self-evolving agent learnings (extends agent_memories)
CREATE TABLE IF NOT EXISTS moat_learnings (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT,
    interaction_id  TEXT,
    context         TEXT NOT NULL,
    learning        TEXT NOT NULL,
    outcome         TEXT DEFAULT 'unknown',
    confidence_delta REAL DEFAULT 0.0,
    embedding_id    TEXT,
    shared_to_mesh  BOOLEAN DEFAULT FALSE,
    embedding       vector(384),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_moat_learnings_agent ON moat_learnings(agent_id);
CREATE INDEX IF NOT EXISTS idx_moat_learnings_embedding
    ON moat_learnings USING hnsw (embedding vector_cosine_ops);

-- 2. Proprietary IRAC reasoning patterns (IP vault)
CREATE TABLE IF NOT EXISTS moat_reasoning_patterns (
    id                TEXT PRIMARY KEY,
    agent_id          TEXT,
    issue             TEXT,
    rule              TEXT,
    application       TEXT,
    conclusion        TEXT,
    precedent_weights JSONB DEFAULT '{}',
    jurisdiction      TEXT DEFAULT 'IN',
    outcome           TEXT DEFAULT 'unknown',
    confidence        REAL DEFAULT 0.5,
    reasoning_hash    TEXT,
    encrypted         BOOLEAN DEFAULT FALSE,
    embedding         vector(384),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_moat_rp_hash ON moat_reasoning_patterns(reasoning_hash);
CREATE INDEX IF NOT EXISTS idx_moat_rp_embedding
    ON moat_reasoning_patterns USING hnsw (embedding vector_cosine_ops);

-- 3. Versioned judgment documents for dynamic RAG
CREATE TABLE IF NOT EXISTS moat_judgment_docs (
    id            TEXT PRIMARY KEY,
    source_url    TEXT,
    title         TEXT,
    citation      TEXT,
    jurisdiction  TEXT,
    court         TEXT,
    date          TEXT,
    parties       TEXT,
    summary       TEXT,
    full_text     TEXT,
    key_holdings  JSONB DEFAULT '[]',
    embedding_id  TEXT,
    version       INTEGER DEFAULT 1,
    superseded_by TEXT,
    crawled_at    TIMESTAMPTZ DEFAULT NOW(),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_moat_jd_citation ON moat_judgment_docs(citation);

-- 4. Judge evolution — verdicts with feedback loop
CREATE TABLE IF NOT EXISTS moat_verdicts (
    id                     TEXT PRIMARY KEY,
    case_summary           TEXT NOT NULL,
    reasoning_pattern_id   TEXT,
    decision               TEXT,
    confidence             REAL DEFAULT 0.5,
    predicted_appeal_outcome TEXT,
    actual_outcome         TEXT,
    feedback_score         REAL,
    judge_signature        TEXT,
    embedding              vector(384),
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    resolved_at            TIMESTAMPTZ
);

-- 5. Predictive analytics records
CREATE TABLE IF NOT EXISTS moat_predictions (
    id              TEXT PRIMARY KEY,
    case_summary    TEXT NOT NULL,
    prediction_type TEXT,
    predicted_value TEXT,
    confidence      REAL,
    rationale       TEXT,
    actual_value    TEXT,
    embedding       vector(384),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Client profiles with emotion tracking
CREATE TABLE IF NOT EXISTS moat_client_profiles (
    id                TEXT PRIMARY KEY,
    external_ref      TEXT,
    emotion_state     TEXT DEFAULT 'neutral',
    emotion_score     REAL DEFAULT 0.5,
    satisfaction_score REAL,
    preferences       JSONB DEFAULT '{}',
    interaction_count INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_moat_cp_ref ON moat_client_profiles(external_ref);

-- 7. Audit trail (immutable forensic log)
CREATE TABLE IF NOT EXISTS moat_audit_entries (
    id            TEXT PRIMARY KEY,
    actor         TEXT,
    action        TEXT,
    entity_type   TEXT,
    entity_id     TEXT,
    payload_hash  TEXT,
    metadata_json JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_moat_audit_created ON moat_audit_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_moat_audit_entity ON moat_audit_entries(entity_id);

-- 8. Agent version history (evolution tracking)
CREATE TABLE IF NOT EXISTS moat_agent_versions (
    id            TEXT PRIMARY KEY,
    agent_id      TEXT,
    version       INTEGER DEFAULT 1,
    persona       JSONB DEFAULT '{}',
    confidence    REAL DEFAULT 0.5,
    change_reason TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_moat_av_agent ON moat_agent_versions(agent_id);

-- 9. Content drafts for auto-publishing
CREATE TABLE IF NOT EXISTS moat_content_drafts (
    id          TEXT PRIMARY KEY,
    kind        TEXT,
    title       TEXT,
    body_md     TEXT,
    tags        JSONB DEFAULT '[]',
    status      TEXT DEFAULT 'draft',
    target_site TEXT DEFAULT 'https://www.advocacayalawfrim.in',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Legal strategies
CREATE TABLE IF NOT EXISTS moat_strategies (
    id              TEXT PRIMARY KEY,
    case_summary    TEXT NOT NULL,
    strategy        TEXT,
    argument_strengths JSONB DEFAULT '[]',
    opposing_args   JSONB DEFAULT '[]',
    predicted_judge_questions JSONB DEFAULT '[]',
    alternative_theories JSONB DEFAULT '[]',
    confidence      REAL DEFAULT 0.5,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Marketplace listings
CREATE TABLE IF NOT EXISTS moat_marketplace_listings (
    id            TEXT PRIMARY KEY,
    listing_type   TEXT,
    title          TEXT NOT NULL,
    description    TEXT,
    price_inr      INTEGER DEFAULT 0,
    creator_id     TEXT,
    metadata       JSONB DEFAULT '{}',
    status         TEXT DEFAULT 'active',
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Pricing records
CREATE TABLE IF NOT EXISTS moat_pricing_records (
    id              TEXT PRIMARY KEY,
    case_summary    TEXT NOT NULL,
    predicted_outcome TEXT,
    outcome_confidence REAL,
    base_fee_inr    INTEGER,
    success_fee_pct REAL,
    estimated_value_inr INTEGER,
    pricing_model   TEXT DEFAULT 'outcome_based',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Verify
SELECT 'moat_learnings', COUNT(*) FROM moat_learnings
UNION ALL SELECT 'moat_reasoning_patterns', COUNT(*) FROM moat_reasoning_patterns
UNION ALL SELECT 'moat_judgment_docs', COUNT(*) FROM moat_judgment_docs
UNION ALL SELECT 'moat_verdicts', COUNT(*) FROM moat_verdicts
UNION ALL SELECT 'moat_predictions', COUNT(*) FROM moat_predictions;
