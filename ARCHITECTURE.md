# Unknown Verdict · Sovereign Intelligence - Complete Architecture

## 📋 Project Overview

**Unknown Verdict v43.0** is an AI-powered legal intelligence platform featuring:
- **530+ Legal Agents** across 12 specializations
- **114+ REST API Endpoints**
- **32.5M Legal Vectors** (ZVEC Database)
- **Zero Data Retention** Privacy Model
- **Third Eye AI** for news & market intelligence
- **Shakti Judge** for legal verdict analysis
- **Hybrid LLM Stack** (Offline + Online)

---

## 🏗️ System Architecture

### Application Stack
```
Frontend (Static)
  ├─ index.html (Landing Page & Dashboard)
  ├─ third-eye.css (Styling)
  └─ JavaScript (Interactive UI)

FastAPI Backend
  ├─ app.py (Main Application)
  ├─ routes.py (Core API Endpoints)
  ├─ auth_routes.py (Authentication)
  └─ integration.py (External Services)

Database Layer
  ├─ PostgreSQL (Core Data)
  ├─ Redis (Caching & Sessions)
  └─ ZVEC (32.5M Legal Vectors)

LLM Pipeline
  ├─ Offline Stack (LiquidAI/LFM2.5-2.6B)
  ├─ Ollama (Local Model Server)
  └─ Online Providers (Groq, OpenAI, Gemini, DeepSeek, OpenRouter)

AI Agents
  ├─ Registry (530 Specialized Legal Agents)
  ├─ Orchestrator (Agent Coordination)
  ├─ Verifiers (Answer Verification)
  └─ Self-Correction (Quality Assurance)
```

---

## 📚 Core Classes & Data Models

### 1. **Database Models** (`db/models.py`)

```python
@dataclass
class User:
    id: int
    email: str
    name: str
    plan: str              # "free", "pro", "enterprise"
    queries_today: int
    created_at: datetime

@dataclass
class Conversation:
    id: str               # UUID
    user_id: Optional[int]
    title: str
    messages: list       # Message history
    created_at: datetime

@dataclass
class LegalDocument:
    id: str
    title: str
    doc_type: str        # "Case", "Act", "Rule", "Judgment"
    jurisdiction: str    # "india", "us", "uk", etc.
    content: str
    metadata: dict
    created_at: datetime

@dataclass
class Verdict:
    id: str
    user_id: Optional[int]
    query: str
    verdict: str         # AI-generated legal opinion
    confidence: float    # 0.0 - 1.0
    metadata: dict
    created_at: datetime

@dataclass
class MoatAgent:
    id: str
    name: str            # e.g., "Constitutional Scholar Agent"
    specialty: str       # "Constitutional", "Contract", etc.
    model: str          # "sarvam-30b", "sarvam-105b"
    config: dict        # Agent-specific configuration
    is_active: bool
    created_at: datetime

@dataclass
class MoatVerifier:
    id: str
    name: str
    version: str        # "43.0"
    accuracy: float     # Historical accuracy metric
    config: dict
    is_active: bool
    created_at: datetime

@dataclass
class MoatJudgeRuling:
    id: str
    query: str
    analysis: str
    verdict: str
    confidence: float
    dissenting: list    # Alternative viewpoints
    created_at: datetime

@dataclass
class MoatIPAsset:
    id: str
    asset_type: str     # "trademark", "patent", "copyright"
    title: str
    content: str
    hash: str           # Blockchain hash
```

### 2. **Configuration** (`core/config.py`)

```python
class Config:
    # Application Info
    APP_NAME = "Unknown Verdict"
    APP_VERSION = "43.0"
    PROJECT_NAME = "Unknown Verdict"
    ENVIRONMENT = "production"
    
    # Paths
    BASE_DIR: Path          # Root directory
    DATA_DIR: Path          # Data storage
    MODELS_DIR: Path        # Model weights
    STATIC_DIR: Path        # Frontend files
    LOGS_DIR: Path          # Application logs
    
    # LLM Configuration
    LLM_MODE = "hybrid"                 # "offline", "online", "hybrid"
    LLM_MODEL_NAME = "LiquidAI/LFM2.5-2.6B"
    EMBEDDING_MODEL = "law-ai/InCaseLawBERT"
    DEVICE = "cpu"                      # "cpu" or "cuda"
    MAX_TOKENS = 4096
    TEMPERATURE = 0.7
    
    # Online Providers
    ONLINE_PROVIDERS = ["groq", "openai", "gemini", "deepseek", "openrouter", "ollama"]
    PRIMARY_PROVIDER = "groq"
    
    # API Keys
    GROQ_API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    DEEPSEEK_API_KEY: str
    OPENROUTER_API_KEY: str
    OLLAMA_URL = "http://localhost:11434"
    
    # Database
    DATABASE_URL: str                   # PostgreSQL connection
    DB_POOL_MIN_SIZE = 1
    DB_POOL_MAX_SIZE = 10
    DB_TIMEOUT = 30
    
    # RAG (32.5M Vectors)
    ZVEC_PATH: Path                     # Vector database
    METADATA_PATH: Path
    GRAPH_PATH: Path                    # Citation graph
    RAG_BACKEND = "zvec"
    RAG_TOP_K = 10                      # Top vectors to retrieve
    RAG_VECTOR_DIM = 768
    RAG_TOTAL_VECTORS = 32518048        # 32.5M vectors
    
    # Security & Auth
    JWT_SECRET: str
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_MINUTES = 10080      # 7 days
    JWT_REFRESH_EXPIRATION_DAYS = 30
    
    # Zero Data Retention
    ZERO_DATA_RETENTION = True
    RETENTION_DAYS = 0                  # Delete immediately
    ANONYMIZE_LOGS = True
```

### 3. **Legal Agent System** (`core/agents.py`)

```python
class AgentStatus(Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class AgentTier(Enum):
    ELITE = "elite"         # Sarvam 105B
    STANDARD = "standard"   # Sarvam 30B
    FAST = "fast"           # Sarvam 30B (optimized)

@dataclass
class LegalAgent:
    id: str                 # UUID
    name: str              # "Constitutional Scholar Agent"
    specialization: str    # "Constitutional", "Contract", etc.
    tier: AgentTier
    status: AgentStatus
    accuracy: float        # Historical accuracy metric
    model: str
    system_prompt: str
    capabilities: List[str]
    jurisdiction: List[str]
    sub_specialties: List[str]
    config: Dict[str, Any]
    created_at: datetime
```

#### **12 Legal Specializations**
1. **Constitutional** (22 agents)
   - Fundamental Rights, Judicial Review, Constitutional Amendments

2. **Contract** (22 agents)
   - Commercial, M&A, Employment, Real Estate

3. **Criminal** (22 agents)
   - White Collar Crime, Cybercrime, Defense

4. **Corporate** (22 agents)
   - M&A, Governance, Insolvency

5. **Intellectual Property** (20 agents)
   - Patents, Trademarks, Copyright

6. **Tax** (20 agents)
   - Direct Tax, GST, International Taxation

7. **Family** (20 agents)
   - Divorce, Custody, Inheritance

8. **Labour** (20 agents)
   - Industrial Disputes, Employment Law

9. **International** (20 agents)
   - Arbitration, Cross-Border Disputes

10. **Environmental** (20 agents)
    - Regulatory Compliance, Pollution Control

11. **Real Estate** (20 agents)
    - Property Transactions, RERA Compliance

12. **Data Protection** (22 agents)
    - DPDP Act 2023, GDPR, Privacy Law

### 4. **LLM Router** (`core/llm/router.py`)

```python
class LLMRouter:
    def __init__(self):
        self.mode: str                  # "offline", "online", "hybrid"
        self.primary_provider: str      # Selected LLM provider
        self.fallback_providers: List[str]
    
    async def route_request(
        self, 
        prompt: str, 
        context: Dict, 
        temperature: float = 0.7
    ) -> LLMResponse:
        # Route to optimal LLM based on latency, cost, accuracy
        pass
    
    async def fallback(self, original_response: str) -> LLMResponse:
        # If primary fails, use fallback provider
        pass
```

### 5. **RAG System** (`core/rag/`)

```python
class FreeIndianRAG:
    def __init__(self):
        self.vector_db: ZVECDatabase  # 32.5M legal vectors
        self.metadata: Dict            # Document metadata
        self.embedding_model: SentenceTransformer
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 10
    ) -> List[Document]:
        # Semantic search through 32.5M legal vectors
        pass

class GraphRAG:
    def __init__(self):
        self.graph: nx.DiGraph         # Citation network
        self.embeddings: np.ndarray
    
    async def retrieve_with_context(
        self, 
        query: str, 
        hops: int = 2
    ) -> List[Document]:
        # Multi-hop reasoning over citation graph
        pass
```

### 6. **Agent Orchestrator** (`core/agents/orchestrator.py`)

```python
class AgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, LegalAgent]
        self.verifiers: List[MoatVerifier]
    
    async def route_query(
        self, 
        query: str, 
        context: Dict
    ) -> LegalResponse:
        # 1. Select best agent(s) based on specialization
        # 2. Generate answer
        # 3. Verify using verifiers
        # 4. Self-correct if needed
        pass
    
    async def parallel_analysis(
        self, 
        query: str, 
        num_agents: int = 3
    ) -> ConsensusResponse:
        # Get opinions from multiple agents
        # Return consensus + dissenting views
        pass
```

### 7. **Verifiers** (`core/verifiers.py`)

```python
class AnswerVerifier:
    def __init__(self):
        self.rules: List[Rule]
        self.fact_checker: FactChecker
    
    async def verify(
        self, 
        query: str, 
        answer: str
    ) -> VerificationResult:
        # Check for legal accuracy, citations, consistency
        pass

class SourceVerifier:
    async def verify_sources(
        self, 
        citations: List[Citation]
    ) -> List[VerificationResult]:
        # Verify that cited cases/acts exist
        pass
```

---

## 🎨 Frontend Architecture

### **Landing Page Structure** (`static/index.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Unknown Verdict · Sovereign Intelligence</title>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    
    <!-- Styling -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
    <style>
        /* CSS Variables */
        :root {
            --bg: #0a0e1a;              /* Dark background */
            --bg-secondary: #0f1422;    /* Secondary bg */
            --card: rgba(17, 24, 39, 0.92);
            --border: rgba(255, 255, 255, 0.06);
            --border-active: rgba(0, 212, 255, 0.2);
            --text: #e8edf5;            /* Main text */
            --text-secondary: #94a3b8;  /* Secondary text */
            --accent: #00d4ff;          /* Cyan accent */
            --gold: #f5c542;            /* Gold accent */
            --green: #10b981;           /* Green accent */
        }
    </style>
</head>
<body>
    <!-- HEADER -->
    <div class="header">
        <div class="logo">
            <span class="star">⭐</span>
            <div class="brand">
                <div class="name">Unknown Verdict</div>
                <div class="sub">SOVEREIGN INTELLIGENCE</div>
            </div>
        </div>
        <div class="header-actions">
            <div class="status-pill">
                <span class="dot"></span>
                All Systems Online
            </div>
            <button class="auth-btn">
                <i class="fas fa-sign-in-alt"></i> Sign In
            </button>
        </div>
    </div>

    <!-- MAIN LAYOUT -->
    <div class="main">
        <!-- SIDEBAR -->
        <div class="sidebar">
            <div class="nav-label">Navigation</div>
            <button class="sidebar-item active" onclick="switchTab('dashboard')">
                <i class="fas fa-chart-line"></i> Dashboard
            </button>
            <button class="sidebar-item" onclick="switchTab('verdict')">
                <i class="fas fa-gavel"></i> Get Verdict
            </button>
            <button class="sidebar-item" onclick="switchTab('agents')">
                <i class="fas fa-users"></i> Agents (530)
            </button>
            <button class="sidebar-item" onclick="switchTab('rag')">
                <i class="fas fa-database"></i> RAG (32.5M)
            </button>
            <button class="sidebar-item" onclick="switchTab('intelligence')">
                <i class="fas fa-brain"></i> Third Eye
            </button>
            <button class="sidebar-item" onclick="switchTab('compliance')">
                <i class="fas fa-certificate"></i> Compliance
            </button>
            <div class="sidebar-footer">
                v43.0 · <span class="highlight">114 Endpoints</span> · Production
            </div>
        </div>

        <!-- CONTENT AREA -->
        <div class="content">
            <!-- DASHBOARD TAB -->
            <div id="dashboard" class="tab-content active">
                <div class="page-header">
                    <div>
                        <h1>Dashboard</h1>
                        <div class="sub">Real-time legal intelligence & agent status</div>
                    </div>
                </div>

                <!-- STATS GRID -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">Total Agents</div>
                        <div class="value cyan">530</div>
                        <div class="sub-value">Across 12 specializations</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Legal Vectors</div>
                        <div class="value gold">32.5M</div>
                        <div class="sub-value">ZVEC Database</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">API Endpoints</div>
                        <div class="value green">114+</div>
                        <div class="sub-value">REST & WebSocket</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Zero Data</div>
                        <div class="value purple">✓</div>
                        <div class="sub-value">Retention: 0 days</div>
                    </div>
                </div>

                <!-- RECENT INTELLIGENCE -->
                <div class="section-title">
                    <i class="fas fa-newspaper"></i> Recent Legal Intelligence
                </div>
                <div class="news-feed">
                    <div class="news-item">
                        <span class="tag governance">GOVERNANCE</span>
                        <div class="title">Digital India Act 2024 - Compliance Updates</div>
                        <div class="meta">
                            <i class="fas fa-calendar"></i> 2 hours ago
                            <i class="fas fa-map-marker-alt" style="margin-left: 8px;"></i> India
                        </div>
                    </div>
                    <div class="news-item">
                        <span class="tag legal">LEGAL</span>
                        <div class="title">Supreme Court Judgment - Data Protection Ruling</div>
                        <div class="meta">
                            <i class="fas fa-calendar"></i> Yesterday
                            <i class="fas fa-map-marker-alt" style="margin-left: 8px;"></i> India
                        </div>
                    </div>
                </div>

                <!-- REGIONAL STATUS -->
                <div class="section-title">
                    <i class="fas fa-globe"></i> Regional Latency
                </div>
                <div class="regions-grid">
                    <div class="region-card">
                        <div class="flag">🇮🇳</div>
                        <div class="name">India</div>
                        <div class="latency"><span class="ms">12ms</span></div>
                    </div>
                    <div class="region-card">
                        <div class="flag">🇺🇸</div>
                        <div class="name">US</div>
                        <div class="latency"><span class="ms">85ms</span></div>
                    </div>
                    <div class="region-card">
                        <div class="flag">🇬🇧</div>
                        <div class="name">UK</div>
                        <div class="latency"><span class="ms">120ms</span></div>
                    </div>
                </div>
            </div>

            <!-- VERDICT TAB -->
            <div id="verdict" class="tab-content">
                <div class="page-header">
                    <div>
                        <h1><span>⚖️</span> Get Legal Verdict</h1>
                        <div class="sub">Ask our AI agents any legal question</div>
                    </div>
                </div>

                <!-- VERDICT INPUT -->
                <div class="verdict-input-area">
                    <div class="label">
                        <i class="fas fa-question-circle"></i> Your Legal Question
                    </div>
                    <div class="input-row">
                        <input 
                            type="text" 
                            id="verdict-query" 
                            placeholder="What is your legal question?..."
                        />
                        <button class="send-btn" onclick="submitVerdict()">
                            <i class="fas fa-paper-plane"></i> Ask
                        </button>
                    </div>
                    <div class="service-lens">
                        <button class="lens-btn active" data-lens="general">General Query</button>
                        <button class="lens-btn" data-lens="contract">Contract Analysis</button>
                        <button class="lens-btn" data-lens="ip">IP Rights</button>
                        <button class="lens-btn" data-lens="compliance">Compliance Check</button>
                    </div>
                </div>

                <!-- MATERIAL UPLOAD -->
                <div class="material-area">
                    <div class="header">
                        <label><i class="fas fa-paperclip"></i> Upload Legal Material (Optional)</label>
                        <div class="material-actions">
                            <button onclick="uploadDocument()">Upload Document</button>
                            <button onclick="uploadCase()">Case Study</button>
                        </div>
                    </div>
                    <textarea 
                        id="material-input" 
                        placeholder="Or paste legal text, case summary, contract, etc."
                    ></textarea>
                    <div class="hint">
                        <i class="fas fa-check-circle"></i> Max 50MB · PDF, DOCX, TXT supported
                    </div>
                </div>

                <!-- VERDICT OUTPUT -->
                <div class="verdict-output">
                    <div class="header">
                        <h3><i class="fas fa-certificate"></i> VERDICT ANALYSIS</h3>
                        <div class="verdict-actions">
                            <button onclick="copySummary()">
                                <i class="fas fa-copy"></i> Copy
                            </button>
                            <button onclick="shareSummary()">
                                <i class="fas fa-share"></i> Share
                            </button>
                            <button onclick="exportPDF()">
                                <i class="fas fa-download"></i> Export
                            </button>
                        </div>
                    </div>
                    <div class="verdict-body" id="verdict-result">
                        <div class="placeholder">
                            Enter a question to get an AI-powered legal verdict...
                        </div>
                    </div>
                </div>
            </div>

            <!-- AGENTS TAB -->
            <div id="agents" class="tab-content">
                <div class="page-header">
                    <div>
                        <h1><span>🤖</span> Legal Agents (530)</h1>
                        <div class="sub">Specialized AI agents across 12 legal domains</div>
                    </div>
                </div>

                <!-- AGENT CARDS GRID -->
                <div class="stats-grid">
                    <div class="stat-card" onclick="viewAgentCategory('Constitutional')">
                        <div class="label">Constitutional</div>
                        <div class="value cyan">22</div>
                        <div class="sub-value">Fundamental Rights</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('Contract')">
                        <div class="label">Contract</div>
                        <div class="value gold">22</div>
                        <div class="sub-value">Commercial & M&A</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('Criminal')">
                        <div class="label">Criminal</div>
                        <div class="value purple">22</div>
                        <div class="sub-value">Defense & Prosecution</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('Corporate')">
                        <div class="label">Corporate</div>
                        <div class="value green">22</div>
                        <div class="sub-value">Governance & M&A</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('IP')">
                        <div class="label">IP</div>
                        <div class="value cyan">20</div>
                        <div class="sub-value">Patents & Trademarks</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('Tax')">
                        <div class="label">Tax</div>
                        <div class="value gold">20</div>
                        <div class="sub-value">Direct & GST</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('Family')">
                        <div class="label">Family</div>
                        <div class="value purple">20</div>
                        <div class="sub-value">Divorce & Custody</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('Labour')">
                        <div class="label">Labour</div>
                        <div class="value green">20</div>
                        <div class="sub-value">Employment Law</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('International')">
                        <div class="label">International</div>
                        <div class="value cyan">20</div>
                        <div class="sub-value">Arbitration</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('Environmental')">
                        <div class="label">Environmental</div>
                        <div class="value gold">20</div>
                        <div class="sub-value">Regulatory</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('RealEstate')">
                        <div class="label">Real Estate</div>
                        <div class="value purple">20</div>
                        <div class="sub-value">RERA & Property</div>
                    </div>
                    <div class="stat-card" onclick="viewAgentCategory('DataProtection')">
                        <div class="label">Data Protection</div>
                        <div class="value green">22</div>
                        <div class="sub-value">DPDP & GDPR</div>
                    </div>
                </div>
            </div>

            <!-- RAG TAB -->
            <div id="rag" class="tab-content">
                <div class="page-header">
                    <div>
                        <h1><span>🗂️</span> Legal Vector Database</h1>
                        <div class="sub">32.5M indexed legal documents via semantic search</div>
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">Total Vectors</div>
                        <div class="value cyan">32.5M</div>
                        <div class="sub-value">Indexed documents</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Embedding Dim</div>
                        <div class="value gold">768</div>
                        <div class="sub-value">InCaseLawBERT</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Search Time</div>
                        <div class="value green">45ms</div>
                        <div class="sub-value">Avg latency</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Graph Hops</div>
                        <div class="value purple">2-3</div>
                        <div class="sub-value">Citation analysis</div>
                    </div>
                </div>
            </div>

            <!-- COMPLIANCE TAB -->
            <div id="compliance" class="tab-content">
                <div class="page-header">
                    <div>
                        <h1><span>✅</span> Compliance & Governance</h1>
                        <div class="sub">Zero Data Retention · AI Governance · Regulatory Compliance</div>
                    </div>
                </div>

                <div class="section-title">
                    <i class="fas fa-lock"></i> Data Retention Policy
                </div>
                <div class="news-feed">
                    <div class="news-item">
                        <span class="tag legal">PRIVACY</span>
                        <div class="title">Zero Data Retention Enabled</div>
                        <div class="meta">All user queries deleted after processing</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            
            // Update sidebar active state
            document.querySelectorAll('.sidebar-item').forEach(item => {
                item.classList.remove('active');
            });
            event.target.closest('.sidebar-item').classList.add('active');
        }

        async function submitVerdict() {
            const query = document.getElementById('verdict-query').value;
            const material = document.getElementById('material-input').value;
            
            const response = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    context: material
                })
            });
            
            const result = await response.json();
            document.getElementById('verdict-result').innerHTML = result.verdict;
        }

        function copySummary() {
            const text = document.getElementById('verdict-result').innerText;
            navigator.clipboard.writeText(text);
        }

        function exportPDF() {
            const element = document.getElementById('verdict-result');
            const opt = { margin: 10, filename: 'verdict.pdf', image: { type: 'png', quality: 0.98 }, html2canvas: { scale: 2 }, jsPDF: { orientation: 'portrait', unit: 'mm', format: 'a4' } };
            html2pdf().set(opt).save();
        }
    </script>
</body>
</html>
```

---

## 🔌 API Endpoints (114+)

### **Authentication Routes** (`auth_routes.py`)
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh JWT token
- `POST /auth/logout` - Logout
- `GET /auth/me` - Current user info

### **Chat & Verdict Routes** (`routes.py`)
- `POST /api/v1/chat` - Submit legal query
- `GET /api/v1/chat/{conversation_id}` - Get conversation history
- `POST /api/v1/verdict` - Get legal verdict
- `GET /api/v1/verdict/{verdict_id}` - Retrieve verdict details
- `WebSocket /ws/chat` - Real-time chat streaming

### **Agent Routes**
- `GET /api/v1/agents` - List all 530 agents
- `GET /api/v1/agents/{specialization}` - Get agents by specialty
- `GET /api/v1/agents/{id}/status` - Agent status
- `POST /api/v1/agents/{id}/query` - Query specific agent
- `GET /api/v1/agents/categories` - List all categories

### **RAG Routes**
- `POST /api/v1/rag/search` - Semantic search (32.5M vectors)
- `POST /api/v1/rag/graph-search` - Multi-hop graph search
- `GET /api/v1/rag/metadata/{doc_id}` - Document metadata
- `POST /api/v1/rag/index` - Index new document

### **Intelligence Routes** (Third Eye)
- `GET /api/v1/intelligence/news` - Latest legal news
- `GET /api/v1/intelligence/cases` - Recent case judgments
- `GET /api/v1/intelligence/regulations` - Regulatory updates
- `GET /api/v1/intelligence/market` - Market intelligence

### **Compliance Routes**
- `GET /api/v1/compliance/dpdp` - DPDP Act 2023 compliance
- `GET /api/v1/compliance/gdpr` - GDPR compliance status
- `GET /api/v1/compliance/audit` - Audit logs

---

## 🗄️ Database Schema

```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'free',
    queries_today INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id INT REFERENCES users(id),
    title VARCHAR(255),
    messages JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Verdicts
CREATE TABLE verdicts (
    id UUID PRIMARY KEY,
    user_id INT REFERENCES users(id),
    query TEXT,
    verdict TEXT,
    confidence FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agents
CREATE TABLE moat_agents (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    specialization VARCHAR(100),
    model VARCHAR(100),
    config JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector Embeddings (via pgvector)
CREATE TABLE legal_documents (
    id UUID PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔄 Data Flow

```
User Query
    ↓
Authentication (JWT)
    ↓
Agent Selection & Routing
    ├─ Determine specialization
    ├─ Select best agent tier (Elite/Standard/Fast)
    └─ Load agent system prompt
    ↓
RAG Retrieval
    ├─ Query embedding (InCaseLawBERT)
    ├─ Vector search (32.5M vectors)
    ├─ Graph traversal (citation links)
    └─ Return top-k documents
    ↓
LLM Generation
    ├─ Route to optimal provider (Groq/OpenAI/Ollama)
    ├─ Include agent context & retrieved documents
    ├─ Generate response with citations
    └─ Stream to frontend
    ↓
Verification
    ├─ Fact-check claims
    ├─ Verify sources
    └─ Self-correct if needed
    ↓
Response to User
    ├─ Send verdict + confidence
    ├─ Include dissenting views
    ├─ Log metadata only (zero data retention)
    └─ Delete query after processing
```

---

## 📊 Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI, Python 3.11+ |
| **Frontend** | HTML5, CSS3, Vanilla JS |
| **Database** | PostgreSQL + pgvector (32.5M vectors) |
| **Cache** | Redis |
| **LLM Offline** | LiquidAI/LFM2.5-2.6B, Ollama |
| **LLM Online** | Groq, OpenAI, Gemini, DeepSeek, OpenRouter |
| **Embeddings** | law-ai/InCaseLawBERT |
| **Graph** | NetworkX (citation analysis) |
| **Vector DB** | ZVEC (32.5M legal vectors) |
| **Auth** | JWT (HS256) |
| **Deployment** | Docker, Kubernetes |

---

## ✨ Key Features

1. **530+ Specialized Legal Agents** - Each with unique expertise
2. **32.5M Legal Vectors** - Comprehensive legal knowledge base
3. **114+ REST Endpoints** - Full-featured API
4. **Zero Data Retention** - Privacy-first architecture
5. **Hybrid LLM Stack** - Offline + Online fallback
6. **Real-time Streaming** - WebSocket support
7. **Multi-hop Reasoning** - Citation graph analysis
8. **Consensus Verdicts** - Get opinions from multiple agents
9. **Self-Correction** - Automatic answer verification
10. **Third Eye AI** - News & market intelligence

---

## 🚀 Getting Started

### Installation
```bash
git clone https://github.com/AUTHORITY-UX/lexsarthi-website
cd lexsarthi-website
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Fill in API keys and database URL
```

### Running
```bash
# Offline mode (Ollama)
python app.py

# Online mode (Groq/OpenAI)
OLLAMA_ENABLED=false python app.py

# Hybrid mode
LLM_MODE=hybrid python app.py
```

---

Generated: 2024 | Version 43.0
