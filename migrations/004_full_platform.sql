-- Unknown Verdict v41.0 - Full Platform Migration
-- This creates all tables for the complete legal AI platform

-- ============================================================================
-- EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- CASE LAW DATABASE
-- ============================================================================
CREATE TABLE IF NOT EXISTS case_law (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citation TEXT UNIQUE NOT NULL,
    title TEXT,
    court TEXT,
    judges TEXT[],
    date DATE,
    year INTEGER,
    headnotes TEXT,
    facts TEXT,
    issues TEXT[],
    arguments TEXT,
    ratio DECIDENDI TEXT,
    obiter_dicta TEXT,
    decision TEXT,
    final_order TEXT,
    case_type TEXT, -- 'civil', 'criminal', 'constitutional', etc.
    subject_matter TEXT[],
    statutes_cited TEXT[],
    cases_cited TEXT[],
    cases_citing TEXT[],
    judgments TEXT[],
    full_text TEXT,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_case_law_citation ON case_law(citation);
CREATE INDEX idx_case_law_court ON case_law(court);
CREATE INDEX idx_case_law_year ON case_law(year);
CREATE INDEX idx_case_law_case_type ON case_law(case_type);
CREATE INDEX idx_case_law_embedding ON case_law USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- STATUTES / ACTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS statutes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    act_name TEXT NOT NULL,
    act_number INTEGER,
    act_year INTEGER,
    title TEXT,
    chapter TEXT,
    section VARCHAR(50),
    subsection VARCHAR(50),
    clause TEXT,
    content TEXT,
    keywords TEXT[],
    parent_section VARCHAR(50),
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_statutes_act_name ON statutes(act_name);
CREATE INDEX idx_statutes_section ON statutes(section);
CREATE INDEX idx_statutes_embedding ON statutes USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- IRAC GRAPH
-- ============================================================================
CREATE TABLE IF NOT EXISTS irac_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type TEXT NOT NULL, -- 'issue', 'rule', 'application', 'conclusion'
    content TEXT,
    case_id UUID REFERENCES case_law(id),
    statute_id UUID REFERENCES statutes(id),
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS irac_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES irac_nodes(id),
    target_id UUID REFERENCES irac_nodes(id),
    edge_type TEXT, -- 'supports', 'contradicts', 'extends', 'distinguishes'
    weight FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_irac_nodes_embedding ON irac_nodes USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- DOCTRINAL CONFLICT DETECTION
-- ============================================================================
CREATE TABLE IF NOT EXISTS doctrinal_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id_1 UUID REFERENCES case_law(id),
    case_id_2 UUID REFERENCES case_law(id),
    issue TEXT,
    principle_1 TEXT,
    principle_2 TEXT,
    conflict_type TEXT, -- 'direct', 'implied', 'apparent'
    severity INTEGER, -- 1-10
    resolution TEXT,
    resolved_by UUID REFERENCES case_law(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doctrinal_principles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    cases_applying UUID[],
    cases_excepting UUID[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- ETHICS AUDIT (PERSISTED)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ethics_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT,
    response TEXT,
    model_used TEXT,
    audit_type TEXT, -- 'refusal', 'pii', 'bias', 'hallucination', 'disclaimer'
    passed BOOLEAN,
    score FLOAT,
    details JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ethics_audits_type ON ethics_audits(audit_type);
CREATE INDEX idx_ethics_audits_passed ON ethics_audits(passed);

-- ============================================================================
-- AI GOVERNANCE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ai_governance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    compliance_check TEXT,
    risk_score FLOAT,
    ai_act_status TEXT, -- 'compliant', 'non-compliant', 'pending'
    regulations_applicable TEXT[],
    findings TEXT,
    recommendations TEXT,
    severity TEXT, -- 'critical', 'high', 'medium', 'low'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_regulatory_intelligence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regulation_name TEXT,
    jurisdiction TEXT,
    effective_date DATE,
    summary TEXT,
    key_requirements TEXT[],
    penalties TEXT,
    impact_area TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- CONTRACT REVIEW / REDLINING
-- ============================================================================
CREATE TABLE IF NOT EXISTS contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    parties TEXT[],
    contract_type TEXT, -- 'nda', 'service', 'employment', 'sales', 'lease'
    jurisdiction TEXT,
    clauses JSONB,
    redlines JSONB,
    risk_score FLOAT,
    review_status TEXT, -- 'pending', 'in_review', 'completed'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contract_clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID REFERENCES contracts(id),
    clause_identifier TEXT,
    clause_text TEXT,
    clause_type TEXT,
    issue TEXT,
    risk_level TEXT,
    suggested_amendment TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- eCOURTS INTEGRATION CACHE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ecourts_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number TEXT UNIQUE NOT NULL,
    case_status TEXT,
    court_name TEXT,
    judge TEXT,
    filing_date DATE,
    next_hearing DATE,
    party_names TEXT[],
    cause_title TEXT,
    orders JSONB,
    cause_list TEXT,
    raw_data JSONB,
    cache_expiry TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ecourts_case_number ON ecourts_cache(case_number);
CREATE INDEX idx_ecourts_next_hearing ON ecourts_cache(next_hearing);

-- ============================================================================
-- LEGAL DOCUMENTS (Court Format Drafting)
-- ============================================================================
CREATE TABLE IF NOT EXISTS legal_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type TEXT, -- 'petition', 'complaint', 'appeal', 'affidavit', 'judgment'
    court_type TEXT, -- 'SC', 'HC', 'NCLT', 'ITAT', 'DRT'
    title TEXT,
    body TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- SEARCH & RETRIEVAL
-- ============================================================================
-- Add full-text search to case_law
ALTER TABLE case_law ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;
CREATE INDEX IF NOT EXISTS idx_case_law_search ON case_law USING GIN (search_vector);

-- Create trigger for search vector updates
CREATE OR REPLACE FUNCTION update_case_law_search() RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.facts, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.ratio_decidendi, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.decision, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(NEW.full_text, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS case_law_search_trigger ON case_law;
CREATE TRIGGER case_law_search_trigger
    BEFORE INSERT OR UPDATE ON case_law
    FOR EACH ROW
    EXECUTE FUNCTION update_case_law_search();

-- ============================================================================
-- VIEWS
-- ============================================================================
CREATE OR REPLACE VIEW case_law_summary AS
SELECT 
    id, citation, title, court, date, year, case_type,
    ARRAY_LENGTH(judges, 1) AS judge_count,
    ARRAY_LENGTH(subject_matter, 1) AS subject_count,
    created_at
FROM case_law;

CREATE OR REPLACE VIEW conflict_risk_summary AS
SELECT 
    COUNT(*) AS total_conflicts,
    AVG(severity) AS avg_severity,
    COUNT(CASE WHEN resolution IS NOT NULL THEN 1 END) AS resolved,
    COUNT(CASE WHEN resolution IS NULL THEN 1 END) AS unresolved
FROM doctrinal_conflicts;

-- ============================================================================
-- RLS POLICIES (for multi-tenant)
-- ============================================================================
-- Enable RLS
ALTER TABLE ethics_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecourts_cache ENABLE ROW LEVEL SECURITY;

-- Create policies (admin only for now)
CREATE POLICY admin_all ON ethics_audits USING (true) WITH CHECK (true);
CREATE POLICY admin_all ON contracts USING (true) WITH CHECK (true);
CREATE POLICY admin_all ON ecourts_cache USING (true) WITH CHECK (true);

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE case_law IS 'Complete case law database with embeddings for semantic search';
COMMENT ON TABLE irac_nodes IS 'IRAC graph nodes extracted from case law';
COMMENT ON TABLE doctrinal_conflicts IS 'Detected conflicts between legal doctrines';
COMMENT ON TABLE ethics_audits IS 'Persistent storage for ethics audit results';
COMMENT ON TABLE ai_governance IS 'AI governance compliance and risk tracking';
COMMENT ON TABLE contracts IS 'Contract review and redlining storage';
COMMENT ON TABLE ecourts_cache IS 'Cache for eCourts API responses';

-- ============================================================================
-- CREATE FUNCTIONS
-- ============================================================================
-- Hybrid search function (dense + sparse)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INTEGER DEFAULT 10
)
RETURNS TABLE(
    id UUID,
    citation TEXT,
    title TEXT,
    court TEXT,
    year INTEGER,
    score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.citation,
        c.title,
        c.court,
        c.year,
        (
            -- Sparse score (ts_rank)
            ts_rank(c.search_vector, plainto_tsquery('english', query_text)) * 0.3 +
            -- Dense score (vector similarity)
            (1 - (c.embedding <=> query_embedding)) * 0.7
        ) AS score
    FROM case_law c
    WHERE c.search_vector @@ plainto_tsquery('english', query_text)
       OR c.embedding IS NOT NULL
    ORDER BY score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;