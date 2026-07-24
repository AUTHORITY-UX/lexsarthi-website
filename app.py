# ═══════════════════════════════════════════════════════════════════════
# DATABASE HELPERS (inside register_routes)
# ═══════════════════════════════════════════════════════════════════════

async def _create_tables():
    if not database:
        logger.warning("⚠️ Cannot create tables - database not connected")
        return
    try:
        await database.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("✅ pgvector extension enabled")
    except Exception as e:
        logger.warning(f"pgvector extension warning: {e}")
    
    tables = [
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            is_premium BOOLEAN DEFAULT FALSE,
            tier VARCHAR(20) DEFAULT 'free',
            queries_used_today INTEGER DEFAULT 0,
            last_query_reset TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            api_key VARCHAR(64) UNIQUE,
            preferences JSONB,
            memory JSONB DEFAULT '[]'
        )""",
        """CREATE TABLE IF NOT EXISTS queries (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT,
            response TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS blog_posts (
            id SERIAL PRIMARY KEY,
            title TEXT,
            content TEXT,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            published BOOLEAN DEFAULT TRUE
        )""",
        """CREATE TABLE IF NOT EXISTS deliberations (
            id SERIAL PRIMARY KEY,
            query TEXT NOT NULL,
            domain TEXT,
            persona TEXT,
            provider TEXT,
            initial_answer TEXT,
            verifier_results JSONB,
            final_answer TEXT,
            confidence TEXT,
            sources JSONB,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS user_feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS fine_tune_data (
            id SERIAL PRIMARY KEY,
            query TEXT NOT NULL,
            initial_answer TEXT,
            final_answer TEXT NOT NULL,
            confidence TEXT,
            is_low_confidence BOOLEAN DEFAULT FALSE,
            used_for_training BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL,
            embedding vector(384) NOT NULL
        )""",
        """CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding 
            ON knowledge_chunks 
            USING hnsw (embedding vector_cosine_ops)"""
    ]
    
    for stmt in tables:
        try:
            await database.execute(stmt)
            logger.info(f"✅ Table created/verified")
        except Exception as e:
            logger.warning(f"Table creation warning: {e}")

async def _ensure_test_user():
    if not database:
        logger.warning("⚠️ Cannot create test user - database not connected")
        return
    existing = await database.fetch_one(users.select().where(users.c.username == "counsel"))
    if not existing:
        await database.execute(users.insert().values(
            username="counsel",
            email="counsel@advocacyalawfrim.in",
            password_hash=hash_password("Password123!"),
            full_name="Counsel User",
            tier="enterprise",
            api_key="".join(random.choices(string.ascii_letters + string.digits, k=32)),
            memory=json.dumps([])
        ))
        logger.info("✅ Seeded test user 'counsel'.")
    else:
        logger.info("✅ Test user 'counsel' already exists.")

# Make helpers available to app.py
register_routes._create_tables = _create_tables
register_routes._ensure_test_user = _ensure_test_user