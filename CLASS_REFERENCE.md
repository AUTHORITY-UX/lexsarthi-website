# Unknown Verdict - Complete Class Reference

## 📚 Database Models (`db/models.py`)

### User Class
```python
@dataclass
class User:
    id: int                          # Primary key
    email: str                       # Unique email
    name: str                        # User full name
    plan: str                        # "free", "pro", "enterprise"
    queries_today: int               # Daily query count
    created_at: Optional[datetime]   # Account creation date
```

### Conversation Class
```python
@dataclass
class Conversation:
    id: str                          # UUID
    user_id: Optional[int]           # Foreign key to User
    title: str                       # Conversation title
    messages: list                   # List of messages
    created_at: Optional[datetime]   # Start time
```

### LegalDocument Class
```python
@dataclass
class LegalDocument:
    id: str                          # UUID
    title: str                       # Document title
    doc_type: str                    # "Case", "Act", "Rule", "Judgment"
    jurisdiction: str                # "india", "us", "uk", etc.
    content: str                     # Full document text
    metadata: dict                   # Custom metadata
    created_at: Optional[datetime]   # Indexed date
```

### Verdict Class
```python
@dataclass
class Verdict:
    id: str                          # UUID
    user_id: Optional[int]           # Foreign key to User
    query: str                       # Original legal question
    verdict: str                     # AI-generated opinion
    confidence: float                # 0.0 - 1.0 confidence score
    metadata: dict                   # Analysis metadata
    created_at: Optional[datetime]   # Generation date
```

### MoatAgent Class
```python
@dataclass
class MoatAgent:
    id: str                          # UUID
    name: str                        # e.g., "Constitutional Scholar"
    specialty: str                   # Legal specialization
    model: str                       # "sarvam-30b", "sarvam-105b"
    config: dict                     # Agent-specific config
    is_active: bool                  # Operational status
    created_at: Optional[datetime]   # Registration date
```

### MoatVerifier Class
```python
@dataclass
class MoatVerifier:
    id: str                          # UUID
    name: str                        # Verifier name
    version: str                     # "43.0"
    accuracy: float                  # Historical accuracy %
    config: dict                     # Verification rules
    is_active: bool                  # Operational status
    created_at: Optional[datetime]   # Registration date
```

### MoatJudgeRuling Class
```python
@dataclass
class MoatJudgeRuling:
    id: str                          # UUID
    query: str                       # Legal question analyzed
    analysis: str                    # Detailed analysis
    verdict: str                     # Final verdict
    confidence: float                # 0.0 - 1.0 confidence
    dissenting: list                 # Alternative viewpoints
    created_at: Optional[datetime]   # Analysis date
```

### MoatIPAsset Class
```python
@dataclass
class MoatIPAsset:
    id: str                          # UUID
    asset_type: str                  # "trademark", "patent", "copyright"
    title: str                       # Asset name
    content: str                     # Full description
    hash: str                        # Blockchain hash (for immutability)
```

---

## ⚙️ Configuration Class (`core/config.py`)

```python
class Config:
    # ─── Application Info ───
    APP_NAME: str = "Unknown Verdict"
    APP_VERSION: str = "43.0"
    PROJECT_NAME: str = "Unknown Verdict"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # ─── Paths ───
    BASE_DIR: Path                  # Root directory
    DATA_DIR: Path                  # /data
    MODELS_DIR: Path                # /models
    STATIC_DIR: Path                # /static
    LOGS_DIR: Path                  # /logs
    
    # ─── LLM Configuration ───
    LLM_MODE: str = "hybrid"        # "offline", "online", "hybrid"
    LLM_MODEL_NAME: str = "LiquidAI/LFM2.5-2.6B"
    EMBEDDING_MODEL: str = "law-ai/InCaseLawBERT"
    DEVICE: str = "cpu"             # "cpu" or "cuda"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    
    # ─── Online Providers ───
    ONLINE_PROVIDERS: List[str] = ["groq", "openai", "gemini", "deepseek", "openrouter", "ollama"]
    PRIMARY_PROVIDER: str = "groq"
    available_llm_providers: List[str]  # Alias for backward compat
    
    # ─── API Keys ───
    GROQ_API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    DEEPSEEK_API_KEY: str
    OPENROUTER_API_KEY: str
    OLLAMA_URL: str = "http://localhost:11434"
    
    # ─── Ollama Configuration ───
    OLLAMA_ENABLED: bool = True
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_HOST: str = "http://localhost:11434"
    
    # ─── Database ───
    DATABASE_URL: str               # PostgreSQL connection string
    DB_POOL_MIN_SIZE: int = 1
    DB_POOL_MAX_SIZE: int = 10
    DB_TIMEOUT: int = 30
    
    # ─── RAG (32.5M Vectors) ───
    ZVEC_PATH: Path                 # Vector database file
    METADATA_PATH: Path             # Metadata JSON
    GRAPH_PATH: Path                # Citation graph pickle
    RAG_BACKEND: str = "zvec"
    RAG_TOP_K: int = 10             # Top vectors to retrieve
    RAG_VECTOR_DIM: int = 768
    RAG_TOTAL_VECTORS: int = 32518048  # 32.5M vectors
    
    # ─── Zero Data Retention ───
    ZERO_DATA_RETENTION: bool = True
    RETENTION_DAYS: int = 0         # Delete immediately
    ANONYMIZE_LOGS: bool = True
    
    # ─── Security & Auth ───
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 10080  # 7 days
    JWT_REFRESH_EXPIRATION_DAYS: int = 30
```

---

## 🤖 Agent Classes (`core/agents.py`)

### Enums

```python
class AgentStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class AgentTier(str, Enum):
    ELITE = "elite"         # Sarvam 105B (most powerful)
    STANDARD = "standard"   # Sarvam 30B (balanced)
    FAST = "fast"           # Sarvam 30B (optimized for speed)
```

### LegalAgent Class

```python
@dataclass
class LegalAgent:
    id: str                          # UUID
    name: str                        # "Constitutional Scholar Agent"
    specialization: str              # "Constitutional", "Contract", etc.
    tier: AgentTier                  # Elite/Standard/Fast
    status: AgentStatus              # Online/Busy/Offline
    accuracy: float                  # 0.0 - 1.0 (historical)
    model: str                       # LLM model name
    system_prompt: str               # Agent's system instructions
    capabilities: List[str]          # List of capabilities
    jurisdiction: List[str]          # ["India", "US", "UK"]
    sub_specialties: List[str]       # Detailed specializations
    config: Dict[str, Any]           # Agent-specific config
    created_at: datetime
```

### Agent Specializations (12 Categories)

```python
SPECIALIZATIONS: Dict[str, Dict[str, Any]] = {
    "Constitutional": {
        "count": 22,
        "sub_specialties": [
            "Fundamental Rights", "Directive Principles",
            "Constitutional Amendments", "Judicial Review",
            "Federalism", "Separation of Powers",
            "Emergency Provisions", "Constitutional Remedies",
            "Anti-Defection", "Centre-State Relations",
            "Constitutional Conventions", "Preamble Interpretation"
        ],
        "description": "Constitutional law and fundamental rights jurisprudence"
    },
    
    "Contract": {
        "count": 22,
        "sub_specialties": [
            "Commercial Contracts", "Service Agreements",
            "NDA & Confidentiality", "Employment Contracts",
            "Real Estate Contracts", "Partnership Deeds",
            "M&A Contracts", "Franchise Agreements",
            "Licensing Contracts", "Construction Contracts",
            "Government Tenders", "International Trade Contracts"
        ],
        "description": "Contract formation, interpretation, and dispute resolution"
    },
    
    "Criminal": {
        "count": 22,
        "sub_specialties": [
            "White Collar Crime", "Cybercrime", "Financial Fraud",
            "IPC Offenses", "CrPC Procedure", "Evidence Act",
            "Bail & Anticipatory Bail", "Trial Defense",
            "Appeal & Revision", "NDPS Cases", "POCSO Cases",
            "Economic Offenses"
        ],
        "description": "Criminal law defense and prosecution"
    },
    
    "Corporate": {
        "count": 22,
        "sub_specialties": [
            "Company Formation", "Mergers & Acquisitions",
            "Corporate Governance", "Securities Law",
            "Insolvency & Bankruptcy", "Foreign Investment",
            "Corporate Compliance", "Board Resolution",
            "Shareholder Rights", "Due Diligence",
            "Corporate Restructuring", "Startup Legal"
        ],
        "description": "Corporate law, M&A, and company secretarial practice"
    },
    
    "Intellectual Property": {
        "count": 20,
        "sub_specialties": [
            "Patent Law", "Trademark Registration",
            "Copyright Protection", "Trade Secrets",
            "Design Registration", "Geographical Indications",
            "IP Licensing", "IP Litigation",
            "Open Source Licensing", "Software Patents"
        ],
        "description": "IP rights registration, protection, and enforcement"
    },
    
    "Tax": {
        "count": 20,
        "sub_specialties": [
            "Direct Tax", "Indirect Tax (GST)",
            "International Taxation", "Transfer Pricing",
            "Tax Disputes", "Tax Planning",
            "Customs & Excise", "Corporate Tax",
            "Capital Gains", "Tax Treaties"
        ],
        "description": "Tax law, GST compliance, and tax dispute resolution"
    },
    
    "Family": {
        "count": 20,
        "sub_specialties": [
            "Divorce & Separation", "Child Custody",
            "Maintenance & Alimony", "Property Inheritance",
            "Hindu Marriage Act", "Muslim Personal Law",
            "Adoption Law", "Domestic Violence",
            "Succession Planning", "NRI Family Disputes"
        ],
        "description": "Family law, matrimonial disputes, and inheritance"
    },
    
    "Labour": {
        "count": 20,
        "sub_specialties": [
            "Industrial Disputes", "Employment Law",
            "PF & Gratuity", "Workplace Harassment",
            "Trade Union Law", "Labour Compliance",
            "Termination & Retrenchment", "Factory Law",
            "Minimum Wages", "Contract Labour"
        ],
        "description": "Labour law, employment disputes, and industrial relations"
    },
    
    "International": {
        "count": 20,
        "sub_specialties": [
            "International Arbitration", "Cross-Border Disputes",
            "WTO Law", "International Trade",
            "Human Rights Law", "Refugee Law",
            "Maritime Law", "Aviation Law",
            "Space Law", "Treaty Interpretation"
        ],
        "description": "International law, arbitration, and cross-border disputes"
    },
    
    "Environmental": {
        "count": 20,
        "sub_specialties": [
            "Environmental Clearance", "Pollution Control",
            "Forest Law", "Wildlife Protection",
            "Climate Change Law", "Waste Management",
            "Mining Law", "Coastal Regulation",
            "Green Tribunal", "ESG Compliance"
        ],
        "description": "Environmental law and regulatory compliance"
    },
    
    "Real Estate": {
        "count": 20,
        "sub_specialties": [
            "Property Transactions", "RERA Compliance",
            "Land Acquisition", "Construction Law",
            "Tenant Rights", "Title Verification",
            "Mortgage Law", "Property Tax",
            "Joint Development", "Stamp Duty"
        ],
        "description": "Real estate law, RERA, and property transactions"
    },
    
    "Data Protection": {
        "count": 22,
        "sub_specialties": [
            "DPDP Act 2023", "GDPR Compliance",
            "CCPA Compliance", "HIPAA Compliance",
            "Data Breach Response", "Privacy Policy Drafting",
            "Cross-Border Data Transfer", "Consent Management",
            "Data Subject Rights", "Privacy Impact Assessment",
            "Children's Data Protection", "AI Ethics Law"
        ],
        "description": "Data protection, privacy law, and digital rights"
    }
}
```

---

## 🧠 LLM Classes (`core/llm/`)

### LLMRouter Class (`core/llm/router.py`)

```python
class LLMRouter:
    def __init__(self):
        self.mode: str                      # "offline", "online", "hybrid"
        self.primary_provider: str          # Default provider
        self.fallback_providers: List[str]  # Backup providers
        self.config: Dict[str, Any]
    
    async def route_request(
        self,
        prompt: str,
        context: Dict,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Route query to optimal LLM"""
        pass
    
    async def fallback(
        self,
        original_response: str
    ) -> LLMResponse:
        """Use fallback provider if primary fails"""
        pass
    
    def get_latency(self, provider: str) -> float:
        """Get provider latency"""
        pass
    
    def get_cost(self, provider: str, tokens: int) -> float:
        """Calculate provider cost"""
        pass
```

### LLMMessage Class

```python
@dataclass
class LLMMessage:
    role: str                       # "user", "assistant", "system"
    content: str                    # Message text
    timestamp: datetime
```

### LLMResponse Class

```python
@dataclass
class LLMResponse:
    content: str                    # Generated response
    tokens_used: int                # Token count
    latency_ms: float               # Response time
    provider: str                   # Which provider generated it
    confidence: float               # 0.0 - 1.0
    citations: List[str]            # Source citations
```

### OllamaProvider Class (`core/llm/ollama_provider.py`)

```python
class OllamaProvider:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host: str
        self.model: str              # Model name
        self.timeout: int            # Request timeout
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Generate response locally"""
        pass
    
    async def stream_generate(
        self,
        prompt: str
    ) -> AsyncIterator[str]:
        """Stream generation"""
        pass
```

### LocalModel Class (`core/llm/local_model.py`)

```python
class LocalModel:
    def __init__(self, model_name: str = "LiquidAI/LFM2.5-2.6B"):
        self.model_name: str
        self.model: Any                 # Loaded model
        self.tokenizer: Any
        self.device: str                # "cpu" or "cuda"
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate using local model"""
        pass
```

---

## 🔍 RAG Classes (`core/rag/`)

### FreeIndianRAG Class (`core/rag/free_indian_rag.py`)

```python
class FreeIndianRAG:
    def __init__(self):
        self.vector_db: ZVECDatabase        # 32.5M vectors
        self.metadata: Dict                 # Document metadata
        self.embedding_model: SentenceTransformer  # InCaseLawBERT
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5
    ) -> List[Document]:
        """Semantic search through 32.5M vectors"""
        pass
    
    async def batch_retrieve(
        self,
        queries: List[str],
        top_k: int = 10
    ) -> List[List[Document]]:
        """Batch retrieval"""
        pass
    
    async def index_document(
        self,
        doc: LegalDocument
    ) -> str:
        """Add new document to index"""
        pass
```

### GraphRAG Class (`core/rag/graph_rag.py`)

```python
class GraphRAG:
    def __init__(self):
        self.graph: nx.DiGraph                  # Citation network
        self.embeddings: np.ndarray             # Vector embeddings
        self.metadata: Dict                     # Node metadata
    
    async def retrieve_with_context(
        self,
        query: str,
        hops: int = 2,
        top_k: int = 10
    ) -> List[Document]:
        """Multi-hop reasoning over citation graph"""
        pass
    
    def add_citation(
        self,
        source_doc: str,
        target_doc: str,
        strength: float
    ) -> None:
        """Add citation edge"""
        pass
    
    def get_related_docs(
        self,
        doc_id: str,
        hops: int = 2
    ) -> List[str]:
        """Get related documents via graph traversal"""
        pass
```

### Document Class

```python
@dataclass
class Document:
    id: str                         # UUID
    title: str
    content: str
    doc_type: str                  # "Case", "Act", "Judgment"
    jurisdiction: str
    embedding: np.ndarray          # 768-dim vector
    metadata: Dict
    relevance_score: float         # 0.0 - 1.0
```

---

## 🎯 Agent Orchestrator Classes (`core/agents/`)

### AgentOrchestrator Class (`core/agents/orchestrator.py`)

```python
class AgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, LegalAgent]
        self.verifiers: List[MoatVerifier]
        self.router: LLMRouter
        self.rag: RAGSystem
    
    async def route_query(
        self,
        query: str,
        context: Dict
    ) -> LegalResponse:
        """
        1. Select best agent(s)
        2. Retrieve relevant documents
        3. Generate answer
        4. Verify accuracy
        5. Self-correct if needed
        """
        pass
    
    async def parallel_analysis(
        self,
        query: str,
        num_agents: int = 3
    ) -> ConsensusResponse:
        """Get opinions from multiple agents and reach consensus"""
        pass
    
    def select_agent(
        self,
        query: str,
        specialization: str
    ) -> LegalAgent:
        """Select best agent for query"""
        pass
```

### AgentRegistry Class (`core/agents/registry.py`)

```python
class AgentRegistry:
    def __init__(self):
        self.agents: Dict[str, LegalAgent]
        self.categories: Dict[str, List[LegalAgent]]
    
    def get_all_agents(self) -> List[LegalAgent]:
        """Get all 530 agents"""
        pass
    
    def get_agent(self, agent_id: str) -> Optional[LegalAgent]:
        """Get specific agent"""
        pass
    
    def get_agents_by_category(
        self,
        specialization: str
    ) -> List[LegalAgent]:
        """Get agents by legal specialization"""
        pass
    
    def get_agent_categories(self) -> List[str]:
        """Get all 12 specializations"""
        pass
    
    def get_agents_by_jurisdiction(
        self,
        jurisdiction: str
    ) -> List[LegalAgent]:
        """Get agents for specific jurisdiction"""
        pass
```

---

## ✅ Verification Classes (`core/verifiers.py`)

### AnswerVerifier Class

```python
class AnswerVerifier:
    def __init__(self):
        self.rules: List[Rule]
        self.fact_checker: FactChecker
        self.source_verifier: SourceVerifier
    
    async def verify(
        self,
        query: str,
        answer: str,
        sources: List[str]
    ) -> VerificationResult:
        """Verify answer accuracy and consistency"""
        pass
    
    def check_legal_accuracy(self, answer: str) -> float:
        """Check against known legal facts"""
        pass
    
    def check_consistency(
        self,
        answer: str,
        historical_answers: List[str]
    ) -> float:
        """Check consistency with previous answers"""
        pass
```

### SourceVerifier Class

```python
class SourceVerifier:
    async def verify_sources(
        self,
        citations: List[Citation]
    ) -> List[VerificationResult]:
        """Verify that cited cases/acts exist"""
        pass
    
    async def validate_case_number(self, case_num: str) -> bool:
        """Validate case citation format"""
        pass
    
    async def validate_statute(self, statute: str) -> bool:
        """Validate act/statute citation"""
        pass
```

### VerificationResult Class

```python
@dataclass
class VerificationResult:
    is_valid: bool                  # True if verified
    confidence: float               # 0.0 - 1.0
    issues: List[str]               # List of problems found
    suggestions: List[str]          # Suggested corrections
    sources_verified: int           # Number of sources checked
```

---

## 📝 Request/Response Models (`routes.py`)

### ChatRequest

```python
class ChatRequest(BaseModel):
    message: str                    # User message
    conversation_id: Optional[str]  # Existing conversation
    service_lens: str = "general"   # Filter type
    include_sources: bool = True    # Include citations
    agents: Optional[List[str]]     # Specific agents to use
```

### VerdictRequest

```python
class VerdictRequest(BaseModel):
    query: str                      # Legal question
    context: Optional[str]          # Additional context
    jurisdiction: str = "india"     # Legal jurisdiction
    document: Optional[str]         # Uploaded document
    confidence_threshold: float = 0.5
```

### LegalResponse

```python
@dataclass
class LegalResponse:
    id: str                         # UUID
    verdict: str                    # AI-generated opinion
    confidence: float               # 0.0 - 1.0
    sources: List[Citation]         # Cited sources
    analysis: str                   # Detailed analysis
    dissenting: List[str]           # Alternative views
    agent_id: str                   # Which agent responded
    latency_ms: float               # Response time
```

### ConsensusResponse

```python
@dataclass
class ConsensusResponse:
    id: str                         # UUID
    query: str                      # Original question
    consensus_verdict: str          # Majority opinion
    confidence: float               # Average confidence
    agent_responses: List[LegalResponse]  # Individual responses
    agreement_percentage: float     # % of agents agreeing
    dissenting_views: List[str]     # Minority opinions
```

---

## 🗃️ Database Classes (`core/db.py`)

### Database Class

```python
class Database:
    def __init__(self, database_url: str):
        self.pool: asyncpg.Pool        # Connection pool
        self.redis: redis.Redis        # Cache
    
    async def initialize(self) -> None:
        """Initialize connections"""
        pass
    
    async def close(self) -> None:
        """Close all connections"""
        pass
    
    async def execute(
        self,
        query: str,
        *args
    ) -> List[Any]:
        """Execute query"""
        pass
    
    async def fetch_one(
        self,
        query: str,
        *args
    ) -> Optional[Dict]:
        """Fetch one row"""
        pass
    
    async def fetch_all(
        self,
        query: str,
        *args
    ) -> List[Dict]:
        """Fetch all rows"""
        pass
```

---

## 🔌 External Integration Classes

### SarvamClient (`sarvam/client.py`)

```python
class SarvamClient:
    def __init__(self, api_key: str):
        self.api_key: str
        self.base_url: str
    
    async def generate(
        self,
        prompt: str,
        model: str = "sarvam-30b"
    ) -> str:
        """Generate using Sarvam API"""
        pass
```

### Integration Providers (`core/integrations/`)

```python
class DocuChatIntegration:
    """Document Q&A integration"""
    pass

class LegalIntelligenceIntegration:
    """Market intelligence integration"""
    pass

class LiqaiIntegration:
    """LQAI provider integration"""
    pass

class RedditCrawlerIntegration:
    """Social media legal discussions"""
    pass
```

---

## 📊 Summary Statistics

| Category | Count | Details |
|----------|-------|---------|
| **Database Models** | 8 | User, Conversation, Document, Verdict, Agent, Verifier, Ruling, IPAsset |
| **Agent Specializations** | 12 | Constitutional, Contract, Criminal, Corporate, IP, Tax, Family, Labour, International, Environmental, Real Estate, Data Protection |
| **Total Agents** | 530 | Distributed across specializations |
| **LLM Classes** | 5+ | Router, Ollama, Local, Online Providers |
| **RAG Systems** | 2 | ZVEC (32.5M vectors), Graph (citation network) |
| **API Endpoints** | 114+ | REST & WebSocket |
| **Configuration Options** | 40+ | LLM, Database, Auth, RAG, etc. |
| **Verifier Types** | 2 | Answer, Source |
| **Request/Response Models** | 5+ | Chat, Verdict, Legal Response, Consensus Response |

---

## 🚀 Key Design Patterns

1. **Router Pattern** - LLMRouter selects optimal provider
2. **Orchestrator Pattern** - AgentOrchestrator coordinates agents
3. **Registry Pattern** - AgentRegistry manages all agents
4. **Factory Pattern** - Config creates instances
5. **Dataclass Pattern** - Models use @dataclass for clarity
6. **Async/Await** - All I/O operations are async
7. **Enum Pattern** - AgentStatus, AgentTier for type safety
8. **Singleton Pattern** - Database connection pool

---

Generated: 2024 | Unknown Verdict v43.0
