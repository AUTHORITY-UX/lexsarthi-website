# Unknown Verdict - Complete Landing Page & Website Structure

## 📄 Landing Page Overview

The website is a single-page application (SPA) built with vanilla HTML5, CSS3, and JavaScript. It features a sophisticated dark theme with gold and cyan accents, designed for legal professionals and AI researchers.

---

## 🎨 Visual Design System

### Color Palette

```css
:root {
    /* Backgrounds */
    --bg: #0a0e1a;                  /* Main bg - Deep navy */
    --bg-secondary: #0f1422;        /* Secondary bg - Slightly lighter */
    --card: rgba(17, 24, 39, 0.92); /* Card bg - Semi-transparent */
    
    /* Borders */
    --border: rgba(255, 255, 255, 0.06);           /* Subtle borders */
    --border-active: rgba(0, 212, 255, 0.2);       /* Active border */
    
    /* Text */
    --text: #e8edf5;                /* Primary text - Light grey-blue */
    --text-secondary: #94a3b8;      /* Secondary text - Muted */
    --muted: #4a5668;               /* Extra muted text */
    
    /* Accents */
    --accent: #00d4ff;              /* Cyan - Primary accent */
    --accent-dim: rgba(0, 212, 255, 0.08);    /* Dim cyan bg */
    --gold: #f5c542;                /* Gold - Secondary accent */
    --gold-dim: rgba(245, 197, 66, 0.08);     /* Dim gold bg */
    --purple: #7b2fbe;              /* Purple - Tertiary accent */
    --green: #10b981;               /* Green - Success state */
    --green-dim: rgba(16, 185, 129, 0.08);    /* Dim green bg */
    --danger: #ef4444;              /* Red - Error/danger */
    
    /* Spacing */
    --radius: 16px;                 /* Large border radius */
    --radius-sm: 10px;              /* Small border radius */
}
```

### Typography

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Font Weights */
300 - Light (placeholders, secondary text)
400 - Regular (body text)
500 - Medium (labels, buttons)
600 - Semibold (section titles, headers)
700 - Bold (page titles, emphasis)
800-900 - Heavy (not used)

/* Font Sizes */
9px   - Tiny labels, tags
10px  - Small labels
11px  - Input labels
12px  - Sub-text, meta info
13px  - Buttons
14px  - Body text, input
15px  - News titles
16px  - Section titles
20px  - Logo text
28px  - Page headers
```

---

## 🏗️ Layout Structure

### Overall Architecture

```
┌─────────────────────────────────────────────────────┐
│                    HEADER (68px)                     │
│  [Logo] [Brand] [Status] [Auth Button]              │
└─────────────────────────────────────────────────────┘
┌──────────────┬───────────────────────────────────────┐
│              │                                       │
│  SIDEBAR     │        CONTENT AREA                   │
│  (220px)     │      (Tabs: Dashboard, Verdict,       │
│              │       Agents, RAG, Intelligence,      │
│  • Dashboard │       Compliance)                     │
│  • Verdict   │                                       │
│  • Agents    │   ┌─────────────────────────────────┐ │
│  • RAG       │   │  Page Header (h1 + subtitle)    │ │
│  • Intelligence   │                                 │ │
│  • Compliance    │  Stats Grid (4 cards)           │ │
│              │   │                                 │ │
│  Footer:     │   │  Section 1: News Feed          │ │
│  v43.0       │   │  Section 2: Regional Latency   │ │
│  114 Endpoints    │  Section 3: Agent Stats       │ │
│              │   └─────────────────────────────────┘ │
└──────────────┴───────────────────────────────────────┘
```

---

## 📋 Page Sections

### 1. HEADER (Fixed, Sticky)

**Position:** Top of page, `position: sticky; top: 0; z-index: 100;`

**Components:**
- **Logo Section (Left)**
  - Gold star icon (⭐)
  - Brand text: "Unknown Verdict"
  - Subtext: "SOVEREIGN INTELLIGENCE" (small caps)

- **Actions Section (Right)**
  - Status pill: "🟢 All Systems Online"
  - Auth button: "Sign In"

**Styling:**
```css
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 32px;
    background: var(--bg-secondary);
    backdrop-filter: blur(16px);    /* Glass morphism */
    border-bottom: 1px solid var(--border);
    height: 68px;
    flex-wrap: wrap;
    gap: 10px;
}
```

---

### 2. SIDEBAR (Sticky, Left)

**Position:** `position: sticky; top: 68px; height: calc(100vh - 68px);`

**Width:** 220px (fixed)

**Content:**
```
┌─────────────────┐
│ NAVIGATION      │
├─────────────────┤
│ 📊 Dashboard    │ ← Active (highlighted)
│ ⚖️ Get Verdict   │
│ 🤖 Agents (530) │
│ 🗂️ RAG (32.5M) │
│ 🧠 Third Eye    │
│ ✅ Compliance   │
├─────────────────┤
│ Footer:         │
│ v43.0           │
│ 114 Endpoints   │
│ Production      │
└─────────────────┘
```

**Styling:**
- Background: `var(--bg-secondary)`
- Border-right: `1px solid var(--border)`
- Padding: 24px 16px
- Overflow-y: auto (scrollable)

---

### 3. MAIN CONTENT AREA

**Position:** Flex: 1 (fills remaining space)

**Padding:** 32px 40px

**Max-height:** `calc(100vh - 68px)` (viewport - header)

**Overflow:** auto (scrollable)

---

## 📑 Tab Content Pages

### **TAB 1: Dashboard**

```
╔════════════════════════════════════════════════════════╗
║ Dashboard                                              ║
║ Real-time legal intelligence & agent status           ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Stats Grid (4 Cards):                                ║
║  ┌────────────┬────────────┬────────────┬───────────┐ ║
║  │ Total      │ Legal      │ API        │ Zero Data │ ║
║  │ Agents     │ Vectors    │ Endpoints  │ Retention │ ║
║  │ 530        │ 32.5M      │ 114+       │ ✓         │ ║
║  │ Across 12  │ ZVEC DB    │ REST &     │ 0 days    │ ║
║  │ specs      │            │ WebSocket  │           │ ║
║  └────────────┴────────────┴────────────┴───────────┘ ║
║                                                        ║
║  📰 Recent Legal Intelligence:                        ║
║  ┌──────────────────────────────────────────────────┐ ║
║  │ [GOVERNANCE] Digital India Act 2024              │ ║
║  │ Compliance Updates                               │ ║
║  │ ⏱️ 2 hours ago · 🗺️ India                        │ ║
║  └──────────────────────────────────────────────────┘ ║
║  ┌──────────────────────────────────────────────────┐ ║
║  │ [LEGAL] Supreme Court Judgment                   │ ║
║  │ Data Protection Ruling                           │ ║
║  │ ⏱️ Yesterday · 🗺️ India                          │ ║
║  └──────────────────────────────────────────────────┘ ║
║                                                        ║
║  🌍 Regional Latency:                                 ║
║  ┌──────────┬──────────┬──────────┬──────────┐       ║
║  │ 🇮🇳 India │ 🇺🇸 US    │ 🇬🇧 UK    │ 🇪🇺 EU    │       ║
║  │ 12ms     │ 85ms     │ 120ms    │ 140ms    │       ║
║  └──────────┴──────────┴──────────┴──────────┘       ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

### **TAB 2: Get Verdict**

```
╔════════════════════════════════════════════════════════╗
║ ⚖️ Get Legal Verdict                                   ║
║ Ask our AI agents any legal question                  ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Your Legal Question:                                 ║
║  ┌──────────────────────────────────────┐ ┌────────┐ ║
║  │ What is your legal question?...      │ │ Ask 📤 │ ║
║  └──────────────────────────────────────┘ └────────┘ ║
║                                                        ║
║  Service Lens (Quick Filters):                        ║
║  [General Query] [Contract Analysis] [IP Rights] ... ║
║                                                        ║
║  Upload Legal Material (Optional):                    ║
║  ┌──────────────────────────────────────────────────┐ ║
║  │ [Upload Document] [Upload Case]                  │ ║
║  │                                                  │ ║
║  │ Or paste legal text, case summary, contract...  │ ║
║  │                                                  │ ║
║  └──────────────────────────────────────────────────┘ ║
║  ✓ Max 50MB · PDF, DOCX, TXT supported               ║
║                                                        ║
║  VERDICT ANALYSIS                                     ║
║  [Copy] [Share] [Export]                              ║
║  ┌──────────────────────────────────────────────────┐ ║
║  │                                                  │ ║
║  │  Enter a question to get an AI-powered verdict  │ ║
║  │                                                  │ ║
║  └──────────────────────────────────────────────────┘ ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

### **TAB 3: Agents (530)**

```
╔════════════════════════════════════════════════════════╗
║ 🤖 Legal Agents (530)                                  ║
║ Specialized AI agents across 12 legal domains         ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Agent Categories Grid (3x4):                         ║
║  ┌──────────────┬──────────────┬──────────────┐      ║
║  │ Constitutional│ Contract     │ Criminal     │      ║
║  │ 22 agents    │ 22 agents    │ 22 agents    │      ║
║  │ Rights,      │ Commercial   │ White-collar │      ║
║  │ Amendments   │ & M&A        │ Cybercrime   │      ║
║  └──────────────┴──────────────┴──────────────┘      ║
║  ┌──────────────┬──────────────┬──────────────┐      ║
║  │ Corporate    │ IP           │ Tax          │      ║
║  │ 22 agents    │ 20 agents    │ 20 agents    │      ║
║  │ Governance   │ Patents,     │ Direct Tax,  │      ║
║  │ M&A          │ Trademarks   │ GST          │      ║
║  └──────────────┴──────────────┴──────────────┘      ║
║  ... more categories                                  ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

### **TAB 4: RAG (32.5M Vectors)**

```
╔════════════════════════════════════════════════════════╗
║ 🗂️ Legal Vector Database                               ║
║ 32.5M indexed legal documents via semantic search     ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Stats Grid:                                          ║
║  ┌────────────────┬──────────────┬────────────────┐  ║
║  │ Total Vectors  │ Embedding    │ Search Time    │  ║
║  │ 32.5M          │ 768 (dim)    │ 45ms avg       │  ║
║  │ Indexed docs   │ InCaseLaw    │ Latency        │  ║
║  │                │ BERT         │                │  ║
║  └────────────────┴──────────────┴────────────────┘  ║
║                                                        ║
║  Database Features:                                   ║
║  • Semantic search across 32.5M legal documents      ║
║  • Multi-hop citation graph traversal (2-3 hops)     ║
║  • InCaseLawBERT embeddings (768-dim)                ║
║  • Zero data retention after search                  ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

### **TAB 5: Third Eye (Intelligence)**

```
╔════════════════════════════════════════════════════════╗
║ 🧠 Third Eye AI                                        ║
║ Real-time legal news & market intelligence            ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Features:                                            ║
║  • Latest legal news aggregation                      ║
║  • Recent case judgments                              ║
║  • Regulatory updates                                 ║
║  • Market intelligence                                ║
║  • Jurisdiction-specific alerts                       ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

### **TAB 6: Compliance**

```
╔════════════════════════════════════════════════════════╗
║ ✅ Compliance & Governance                             ║
║ Zero Data Retention · AI Ethics · Regulatory Compliance
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Data Retention Policy:                               ║
║  ┌──────────────────────────────────────────────────┐ ║
║  │ [PRIVACY] Zero Data Retention Enabled            │ ║
║  │ All user queries deleted after processing         │ ║
║  └──────────────────────────────────────────────────┘ ║
║                                                        ║
║  Compliance Certifications:                           ║
║  • DPDP Act 2023 (India)                              ║
║  • GDPR Compliant (EU)                                ║
║  • CCPA Ready (US)                                    ║
║  • AI Governance Framework                           ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

---

## 🎯 Interactive Components

### **Stats Card**

```html
<div class="stat-card">
    <div class="label">Total Agents</div>
    <div class="value cyan">530</div>
    <div class="sub-value">Across 12 specializations</div>
</div>
```

**Styling:**
- Background: `var(--card)`
- Border: `1px solid var(--border)`
- Padding: 18px 20px
- Border radius: 16px
- Hover effect: Border changes to `var(--border-active)`
- Grid: `repeat(auto-fill, minmax(180px, 1fr))`

---

### **News Item**

```html
<div class="news-item">
    <span class="tag governance">GOVERNANCE</span>
    <div class="title">Digital India Act 2024 - Compliance Updates</div>
    <div class="meta">
        <i class="fas fa-calendar"></i> 2 hours ago
        <i class="fas fa-map-marker-alt"></i> India
    </div>
</div>
```

**Tags:**
- `.tag.governance` - Green tag
- `.tag.legal` - Gold tag
- `.tag.privacy` - Purple tag

---

### **Input Area (Verdict Question)**

```html
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
        <button class="send-btn">
            <i class="fas fa-paper-plane"></i> Ask
        </button>
    </div>
    <div class="service-lens">
        <button class="lens-btn active">General Query</button>
        <button class="lens-btn">Contract Analysis</button>
        <button class="lens-btn">IP Rights</button>
        <button class="lens-btn">Compliance Check</button>
    </div>
</div>
```

---

### **Verdict Output Box**

```html
<div class="verdict-output">
    <div class="header">
        <h3><i class="fas fa-certificate"></i> VERDICT ANALYSIS</h3>
        <div class="verdict-actions">
            <button><i class="fas fa-copy"></i> Copy</button>
            <button><i class="fas fa-share"></i> Share</button>
            <button><i class="fas fa-download"></i> Export</button>
        </div>
    </div>
    <div class="verdict-body" id="verdict-result">
        <div class="placeholder">Enter a question to get an AI-powered legal verdict...</div>
    </div>
</div>
```

---

## 🎬 Animations

```css
/* Fade-in for tab transitions */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
.tab-content.active {
    animation: fadeIn 0.3s ease;
}

/* Pulsing status indicator */
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.status-pill .dot {
    animation: pulse-dot 2s infinite;
}

/* Microphone recording pulse */
@keyframes pulse-mic {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
    50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
}
.voice-btn.listening {
    animation: pulse-mic 1s infinite;
}

/* Hover button scale */
.send-btn:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 20px rgba(245, 197, 66, 0.2);
}
```

---

## 📱 Responsive Behavior

The design uses:
- **Flexbox** for layout flexibility
- **CSS Grid** for card layouts with `grid-template-columns: repeat(auto-fill, minmax(...))`
- **Flex-wrap** to handle smaller screens
- **Overflow-y: auto** for scrollable sections

**Breakpoints:**
- Sidebar hides on mobile (< 768px)
- Content padding reduces
- Header wraps items with gap spacing

---

## 🔐 Security Features in UI

1. **JWT Token Display** - Hidden in localStorage
2. **HTTPS Enforced** - All API calls
3. **CSRF Protection** - Token in headers
4. **Input Sanitization** - XSS prevention
5. **No Passwords Logged** - Auth info cleared after 30 minutes

---

## 🌙 Dark Mode Only

The entire UI is designed for dark mode:
- Background: Deep navy (#0a0e1a)
- Text: Light grey-blue (#e8edf5)
- Accents: Cyan (#00d4ff), Gold (#f5c542)
- No light mode variant

---

## 💾 Session Storage

```javascript
// User session data (client-side)
localStorage.setItem('jwt_token', token);
localStorage.setItem('user_id', userId);
localStorage.setItem('email', userEmail);

// Sensitive data cleared after:
- 30-minute inactivity
- Logout
- Page reload (for JWT)
```

---

## 🎓 User Experience Flow

```
1. User visits homepage
   ↓
2. Redirected to login/register
   ↓
3. Authenticated with JWT
   ↓
4. Dashboard loads with:
   - Agent status (530 online)
   - Recent legal news
   - Regional latency info
   ↓
5. User clicks "Get Verdict" tab
   ↓
6. Enters legal question
   ↓
7. Selects service lens (optional)
   ↓
8. Uploads document (optional)
   ↓
9. Clicks "Ask"
   ↓
10. API routes to best agent
    ↓
11. Searches 32.5M vectors
    ↓
12. LLM generates verdict
    ↓
13. Verifier checks accuracy
    ↓
14. Response streams to UI
    ↓
15. User can:
    - Copy verdict
    - Share on social media
    - Export as PDF
    - Start new query
```

---

## 📊 Component Hierarchy

```
<html>
  <head>
    <!-- Meta tags, fonts, styles -->
  </head>
  <body>
    <header class="header">
      <div class="logo">...</div>
      <div class="header-actions">...</div>
    </header>
    
    <div class="main">
      <aside class="sidebar">
        <div class="nav-label">Navigation</div>
        <button class="sidebar-item active">Dashboard</button>
        <button class="sidebar-item">Get Verdict</button>
        <!-- More nav items -->
        <div class="sidebar-footer">v43.0 · 114 Endpoints</div>
      </aside>
      
      <div class="content">
        <div id="dashboard" class="tab-content active">
          <div class="page-header">...</div>
          <div class="stats-grid">...</div>
          <div class="section-title">...</div>
          <div class="news-feed">...</div>
          <div class="regions-grid">...</div>
        </div>
        
        <div id="verdict" class="tab-content">
          <div class="verdict-input-area">...</div>
          <div class="material-area">...</div>
          <div class="verdict-output">...</div>
        </div>
        
        <!-- More tabs -->
      </div>
    </div>
    
    <script>
      // Tab switching
      // API calls
      // Event handlers
    </script>
  </body>
</html>
```

---

## 🎨 Design Principles

1. **Minimalism** - Only essential UI elements
2. **Dark First** - Eye-friendly for long sessions
3. **Consistency** - Same styling throughout
4. **Accessibility** - High contrast ratios
5. **Performance** - No heavy animations
6. **Professional** - Enterprise appearance
7. **Clarity** - Clear navigation paths

---

Generated: 2024 | Unknown Verdict v43.0
