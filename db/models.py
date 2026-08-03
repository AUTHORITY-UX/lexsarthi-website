"""Async Neon Postgres with pgvector (384-dim)."""
from __future__ import annotations
import datetime as dt, hashlib, json, uuid
from typing import Any, Dict, List, Optional
import asyncpg
from loguru import logger as log

try:
    from ..config import settings as _s
    _DB_URL = _s.DATABASE_URL
except Exception:
    import os
    _DB_URL = os.environ.get("DATABASE_URL", "")

def _uid(): return uuid.uuid4().hex
def _now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def _hash(s: str) -> str: return hashlib.sha256(s.encode()).hexdigest()[:32]
def _pg(u: str) -> str:
    if u.startswith("postgresql+asyncpg://"): return u.replace("postgresql+asyncpg://","postgresql://",1)
    return u

class DB:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._url = _pg(_DB_URL)

    @property
    def is_configured(self) -> bool:
        return bool(self._url) and "localhost" not in self._url and "user:password" not in self._url

    async def init(self) -> bool:
        if not self.is_configured:
            log.warning("⚠️ Moat DB: DATABASE_URL not set — degraded mode")
            return False
        try:
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=8, command_timeout=30)
            async with self._pool.acquire() as c:
                await c.fetchval("SELECT 1")
            log.info("✅ Moat DB connected to Neon")
            # Auto-migrate: ensure all moat_* tables exist
            await self._migrate()
            return True
        except Exception as e:
            log.error(f"❌ Moat DB: {e}")
            self._pool = None
            return False

    async def _migrate(self):
        """Auto-create all moat_* tables if they don't exist. Idempotent."""
        if not self._pool: return
        statements = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            """CREATE TABLE IF NOT EXISTS moat_learnings (
                id TEXT PRIMARY KEY, agent_id TEXT, interaction_id TEXT,
                context TEXT NOT NULL, learning TEXT NOT NULL,
                outcome TEXT DEFAULT 'unknown', confidence_delta REAL DEFAULT 0.0,
                embedding_id TEXT, shared_to_mesh BOOLEAN DEFAULT FALSE,
                embedding vector(384), created_at TIMESTAMPTZ DEFAULT NOW())""",
            "CREATE INDEX IF NOT EXISTS idx_moat_learnings_agent ON moat_learnings(agent_id)",
            """CREATE TABLE IF NOT EXISTS moat_reasoning_patterns (
                id TEXT PRIMARY KEY, agent_id TEXT, issue TEXT, rule TEXT,
                application TEXT, conclusion TEXT, precedent_weights JSONB DEFAULT '{}',
                jurisdiction TEXT DEFAULT 'IN', outcome TEXT DEFAULT 'unknown',
                confidence REAL DEFAULT 0.5, reasoning_hash TEXT, encrypted BOOLEAN DEFAULT FALSE,
                embedding vector(384), created_at TIMESTAMPTZ DEFAULT NOW())""",
            "CREATE INDEX IF NOT EXISTS idx_moat_rp_hash ON moat_reasoning_patterns(reasoning_hash)",
            """CREATE TABLE IF NOT EXISTS moat_judgment_docs (
                id TEXT PRIMARY KEY, source_url TEXT, title TEXT, citation TEXT,
                jurisdiction TEXT, court TEXT, date TEXT, parties TEXT, summary TEXT,
                full_text TEXT, key_holdings JSONB DEFAULT '[]', embedding_id TEXT,
                version INTEGER DEFAULT 1, superseded_by TEXT,
                crawled_at TIMESTAMPTZ DEFAULT NOW(), created_at TIMESTAMPTZ DEFAULT NOW())""",
            "CREATE INDEX IF NOT EXISTS idx_moat_jd_citation ON moat_judgment_docs(citation)",
            """CREATE TABLE IF NOT EXISTS moat_verdicts (
                id TEXT PRIMARY KEY, case_summary TEXT NOT NULL,
                reasoning_pattern_id TEXT, decision TEXT, confidence REAL DEFAULT 0.5,
                predicted_appeal_outcome TEXT, actual_outcome TEXT, feedback_score REAL,
                judge_signature TEXT, embedding vector(384),
                created_at TIMESTAMPTZ DEFAULT NOW(), resolved_at TIMESTAMPTZ)""",
            """CREATE TABLE IF NOT EXISTS moat_predictions (
                id TEXT PRIMARY KEY, case_summary TEXT NOT NULL,
                prediction_type TEXT, predicted_value TEXT, confidence REAL,
                rationale TEXT, actual_value TEXT, embedding vector(384),
                created_at TIMESTAMPTZ DEFAULT NOW())""",
            """CREATE TABLE IF NOT EXISTS moat_client_profiles (
                id TEXT PRIMARY KEY, external_ref TEXT, emotion_state TEXT DEFAULT 'neutral',
                emotion_score REAL DEFAULT 0.5, satisfaction_score REAL,
                preferences JSONB DEFAULT '{}', interaction_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())""",
            "CREATE INDEX IF NOT EXISTS idx_moat_cp_ref ON moat_client_profiles(external_ref)",
            """CREATE TABLE IF NOT EXISTS moat_audit_entries (
                id TEXT PRIMARY KEY, actor TEXT, action TEXT,
                entity_type TEXT, entity_id TEXT, payload_hash TEXT,
                metadata_json JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW())""",
            "CREATE INDEX IF NOT EXISTS idx_moat_audit_created ON moat_audit_entries(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_moat_audit_entity ON moat_audit_entries(entity_id)",
            """CREATE TABLE IF NOT EXISTS moat_agent_versions (
                id TEXT PRIMARY KEY, agent_id TEXT, version INTEGER DEFAULT 1,
                persona JSONB DEFAULT '{}', confidence REAL DEFAULT 0.5,
                change_reason TEXT, created_at TIMESTAMPTZ DEFAULT NOW())""",
            "CREATE INDEX IF NOT EXISTS idx_moat_av_agent ON moat_agent_versions(agent_id)",
            """CREATE TABLE IF NOT EXISTS moat_content_drafts (
                id TEXT PRIMARY KEY, kind TEXT, title TEXT, body_md TEXT,
                tags JSONB DEFAULT '[]', status TEXT DEFAULT 'draft',
                target_site TEXT DEFAULT 'https://www.advocacayalawfrim.in',
                created_at TIMESTAMPTZ DEFAULT NOW())""",
            """CREATE TABLE IF NOT EXISTS moat_strategies (
                id TEXT PRIMARY KEY, case_summary TEXT NOT NULL, strategy TEXT,
                argument_strengths JSONB DEFAULT '[]', opposing_args JSONB DEFAULT '[]',
                predicted_judge_questions JSONB DEFAULT '[]', alternative_theories JSONB DEFAULT '[]',
                confidence REAL DEFAULT 0.5, created_at TIMESTAMPTZ DEFAULT NOW())""",
            """CREATE TABLE IF NOT EXISTS moat_marketplace_listings (
                id TEXT PRIMARY KEY, listing_type TEXT, title TEXT NOT NULL,
                description TEXT, price_inr INTEGER DEFAULT 0, creator_id TEXT,
                metadata JSONB DEFAULT '{}', status TEXT DEFAULT 'active',
                created_at TIMESTAMPTZ DEFAULT NOW())""",
            """CREATE TABLE IF NOT EXISTS moat_pricing_records (
                id TEXT PRIMARY KEY, case_summary TEXT NOT NULL, predicted_outcome TEXT,
                outcome_confidence REAL, base_fee_inr INTEGER, success_fee_pct REAL,
                estimated_value_inr INTEGER, pricing_model TEXT DEFAULT 'outcome_based',
                created_at TIMESTAMPTZ DEFAULT NOW())""",
            """CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY, content TEXT, metadata JSONB DEFAULT '{}',
                embedding vector(384), created_at TIMESTAMPTZ DEFAULT NOW())""",
        ]
        async with self._pool.acquire() as c:
            for sql in statements:
                try:
                    await c.execute(sql)
                except Exception as e:
                    log.debug(f"migration skip: {e}")
        log.info("✅ Moat DB migration complete (12 tables verified)")

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def available(self) -> bool:
        return self._pool is not None

    async def execute(self, sql, *p):
        if not self._pool: return ""
        async with self._pool.acquire() as c: return await c.execute(sql, *p)

    async def fetchrow(self, sql, *p):
        if not self._pool: return None
        async with self._pool.acquire() as c: return await c.fetchrow(sql, *p)

    async def fetch(self, sql, *p):
        if not self._pool: return []
        async with self._pool.acquire() as c: return await c.fetch(sql, *p)

    async def fetchval(self, sql, *p):
        if not self._pool: return None
        async with self._pool.acquire() as c: return await c.fetchval(sql, *p)

    async def vector_search(self, table, col, qvec, top_k=8, where="", params=()):
        if not self._pool: return []
        vs = f"[{','.join(str(v) for v in qvec)}]"
        wc = f"WHERE {where}" if where else ""
        sql = f"SELECT *, 1-({col} <=> $1::vector) AS sim FROM {table} {wc} ORDER BY {col} <=> $1::vector LIMIT {top_k}"
        try:
            return [dict(r) for r in await self.fetch(sql, vs, *params)]
        except Exception as e:
            log.error(f"vector_search {table}: {e}")
            return []

    async def insert_vec(self, table, cols, embedding, ecol="embedding"):
        if not self._pool: return None
        rid = cols.get("id", _uid()); cols["id"] = rid
        vs = f"[{','.join(str(v) for v in embedding)}]"
        cn = list(cols.keys()) + [ecol]
        ph = [f"${i}" for i in range(1,len(cols)+1)] + [f"${len(cols)+1}::vector"]
        vals = list(cols.values()) + [vs]
        try:
            await self.execute(f"INSERT INTO {table} ({','.join(cn)}) VALUES ({','.join(ph)})", *vals)
            return rid
        except Exception as e:
            log.error(f"insert_vec: {e}")
            return None

    async def add_learning(self, agent_id, context, learning, outcome="unknown",
                           delta=0.0, iid="", embedding=None, share=False):
        lid = _uid()
        if embedding:
            return await self.insert_vec("moat_learnings", {
                "id":lid,"agent_id":agent_id,"interaction_id":iid,"context":context,
                "learning":learning,"outcome":outcome,"confidence_delta":delta,
                "shared_to_mesh":share}, embedding)
        await self.execute(
            "INSERT INTO moat_learnings (id,agent_id,interaction_id,context,learning,outcome,confidence_delta,shared_to_mesh) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
            lid,agent_id,iid,context,learning,outcome,delta,share)
        return lid

    async def add_reasoning(self, issue, rule, app_text, conclusion,
                            weights=None, jur="IN", outcome="unknown", conf=0.5,
                            agent_id="", enc=False, embedding=None):
        rid=_uid(); rh=_hash(f"{issue}|{rule}|{app_text}|{conclusion}")
        pw=json.dumps(weights or {})
        if embedding:
            return await self.insert_vec("moat_reasoning_patterns", {
                "id":rid,"agent_id":agent_id,"issue":issue,"rule":rule,"application":app_text,
                "conclusion":conclusion,"precedent_weights":pw,"jurisdiction":jur,"outcome":outcome,
                "confidence":conf,"reasoning_hash":rh,"encrypted":enc}, embedding)
        await self.execute(
            "INSERT INTO moat_reasoning_patterns (id,agent_id,issue,rule,application,conclusion,precedent_weights,jurisdiction,outcome,confidence,reasoning_hash,encrypted) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)",
            rid,agent_id,issue,rule,app_text,conclusion,pw,jur,outcome,conf,rh,enc)
        return rid

    async def add_verdict(self, case, decision, conf, rpid="", appeal="", sig="", embedding=None):
        vid=_uid()
        if embedding:
            return await self.insert_vec("moat_verdicts", {
                "id":vid,"case_summary":case,"reasoning_pattern_id":rpid,"decision":decision,
                "confidence":conf,"predicted_appeal_outcome":appeal,"judge_signature":sig}, embedding)
        await self.execute(
            "INSERT INTO moat_verdicts (id,case_summary,reasoning_pattern_id,decision,confidence,predicted_appeal_outcome,judge_signature) VALUES ($1,$2,$3,$4,$5,$6,$7)",
            vid,case,rpid,decision,conf,appeal,sig)
        return vid

    async def resolve_verdict(self, vid, actual, feedback=0.0):
        await self.execute("UPDATE moat_verdicts SET actual_outcome=$1,feedback_score=$2,resolved_at=NOW() WHERE id=$3", actual, feedback, vid)

    async def add_prediction(self, case, ptype, pval, conf, rationale="", embedding=None):
        pid=_uid()
        if embedding:
            return await self.insert_vec("moat_predictions", {
                "id":pid,"case_summary":case,"prediction_type":ptype,"predicted_value":pval,
                "confidence":conf,"rationale":rationale}, embedding)
        await self.execute(
            "INSERT INTO moat_predictions (id,case_summary,prediction_type,predicted_value,confidence,rationale) VALUES ($1,$2,$3,$4,$5,$6)",
            pid,case,ptype,pval,conf,rationale)
        return pid

    async def add_judgment_doc(self, url, title, citation, jur, court, summary, full="", holdings=None, date="", parties=""):
        jid=_uid(); ver=1
        if citation:
            ex = await self.fetchrow("SELECT id,version FROM moat_judgment_docs WHERE citation=$1 ORDER BY version DESC LIMIT 1", citation)
            if ex:
                ver = ex["version"]+1
                await self.execute("UPDATE moat_judgment_docs SET superseded_by=$1 WHERE id=$2", jid, ex["id"])
        await self.execute(
            "INSERT INTO moat_judgment_docs (id,source_url,title,citation,jurisdiction,court,date,parties,summary,full_text,key_holdings,version) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)",
            jid,url,title,citation,jur,court,date,parties,summary,full,json.dumps(holdings or []),ver)
        return jid

    async def audit(self, actor, action, etype, eid, meta=None):
        aid=_uid(); p=json.dumps(meta or {},sort_keys=True); ph=_hash(p)
        await self.execute(
            "INSERT INTO moat_audit_entries (id,actor,action,entity_type,entity_id,payload_hash,metadata_json) VALUES ($1,$2,$3,$4,$5,$6,$7)",
            aid,actor,action,etype,eid,ph,p)
        return aid

    async def add_content(self, kind, title, body, tags=None, site="https://www.advocacayalawfrim.in"):
        cid=_uid()
        await self.execute(
            "INSERT INTO moat_content_drafts (id,kind,title,body_md,tags,status,target_site) VALUES ($1,$2,$3,$4,$5,'draft',$6)",
            cid,kind,title,body,json.dumps(tags or []),site)
        return cid

    async def add_agent_version(self, agent_id, persona, conf, reason=""):
        vid=_uid()
        await self.execute(
            "INSERT INTO moat_agent_versions (id,agent_id,version,persona,confidence,change_reason) VALUES ($1,$2,$3,$4,$5,$6)",
            vid,agent_id,1,json.dumps(persona),conf,reason)
        return vid

    async def add_strategy(self, case, strategy, strengths, opposing, questions, theories, conf=0.5):
        sid=_uid()
        await self.execute(
            "INSERT INTO moat_strategies (id,case_summary,strategy,argument_strengths,opposing_args,predicted_judge_questions,alternative_theories,confidence) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
            sid,case,strategy,json.dumps(strengths),json.dumps(opposing),json.dumps(questions),json.dumps(theories),conf)
        return sid

    async def add_pricing(self, case, outcome, conf, base, pct, value, model="outcome_based"):
        pid=_uid()
        await self.execute(
            "INSERT INTO moat_pricing_records (id,case_summary,predicted_outcome,outcome_confidence,base_fee_inr,success_fee_pct,estimated_value_inr,pricing_model) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
            pid,case,outcome,conf,base,pct,value,model)
        return pid

    async def add_listing(self, ltype, title, desc, price, creator, meta=None):
        lid=_uid()
        await self.execute(
            "INSERT INTO moat_marketplace_listings (id,listing_type,title,description,price_inr,creator_id,metadata,status) VALUES ($1,$2,$3,$4,$5,$6,$7,'active')",
            lid,ltype,title,desc,price,creator,json.dumps(meta or {}))
        return lid

    async def stats(self):
        if not self._pool: return {"status":"disconnected"}
        t=["moat_learnings","moat_reasoning_patterns","moat_verdicts","moat_predictions",
           "moat_judgment_docs","moat_audit_entries","moat_content_drafts","moat_agent_versions",
           "moat_strategies","moat_pricing_records","moat_marketplace_listings"]
        c={}
        for tn in t:
            try: c[tn]=await self.fetchval(f"SELECT COUNT(*) FROM {tn}")
            except: c[tn]=0
        c["status"]="connected"; c["backend"]="neon-postgres"
        return c

db = DB()
 