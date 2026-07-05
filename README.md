---
title: "LEXSARTHI v10 – ATMA Universal OS"
emoji: "🔱"
colorFrom: "yellow"
colorTo: "yellow"
sdk: "docker"
app_file: "app.py"
pinned: false
license: "other"
---

# 🔱 LEXSARTHI v10 – ATMA Universal OS

## The First Self‑Verifying AI OS for Every Domain – Law, Science, Philosophy, Finance, Life & Beyond

### 🏛️ Owned by **THE ADVOCACY – A LAW FIRM**  
**Proprietor:** Upmanyu Kumar  
**UDYAM:** UP-09-0043193 | **PAN:** CHFPK3464A  

---

## 📌 Overview

LexSarthi v10 is a **self‑verifying, domain‑agnostic AI** powered by the **Atma router** – an intelligent orchestration layer that dynamically selects specialists, retrieves authoritative knowledge, and runs a **jury of 3 verifiers + a judge** to produce answers with **confidence scores** and **source citations**.  

With **OpenRouter** as the primary LLM provider (offering 100+ models with no rate limits) and **Redis semantic caching**, LexSarthi is now capable of serving **1 million users** at near‑zero cost. Whether you ask about **contract law**, **quantum physics**, **Vedanta**, **financial markets**, or **the meaning of life**, LexSarthi responds with transparency, citing both your **ingested documents** and **live official websites** (e.g., Supreme Court, Parliament, SEBI, SEC, WHO, CERN).

---

## 🚀 What's New in v10

| Feature | Description |
| :------ | :---------- |
| **OpenRouter Primary** | Unlimited, low‑cost access to 100+ LLMs (Llama‑3, GPT‑4, Claude, etc.) – no more rate‑limit errors. |
| **Redis Semantic Cache** | Frequently asked questions are cached, reducing API calls by **70%+** and cutting costs. |
| **Cost‑Optimised Retrieval** | `top_k=3` and query truncation (2000 chars) keep token usage minimal – perfect for high‑volume free users. |
| **Multi‑Provider Fallback** | Seamless fallback: OpenRouter → Groq → OpenAI → Gemini → Local PDF library – **zero downtime**. |
| **Production‑Ready Scaling** | Designed for horizontal scaling (Cloudflare Workers, multiple replicas) – ready for 1M+ daily active users. |
| **Future‑Ready** | Easy to swap in a self‑hosted `vLLM` endpoint for even lower costs (next phase). |

---

## 🧠 Core Capabilities

| Domain | Examples |
| :----- | :------- |
| **Law** | Contract review, draft SLP/civil suits, DPDPA/GST compliance, criminal bail arguments. |
| **Science** | Evaluate forensic evidence, interpret DNA reports, explain quantum mechanics. |
| **Psychology** | Analyse witness testimony, assess mental state, understand cognitive biases. |
| **Philosophy/Mythology** | Frame ethical arguments using Dharma, Karma, Vedantic principles. |
| **Finance** | Analyse market trends, interpret SEBI regulations, run compliance checks. |
| **General Knowledge** | Answer any question with cited sources and confidence. |

---

## ⚙️ How It Works (The Atma Flow)

1. **User Input** – Text, document upload (PDF/DOCX/Image/OCR), or voice (Speech‑to‑Text).
2. **Atma Router** – Classifies the domain (e.g., Corporate Law, Forensic Science) and selects one of **250+ specialist personas**.
3. **RAG (Retrieval)** – Converts the query to an embedding (local `all-MiniLM-L6-v2`), searches `pgvector` (PostgreSQL) for the most relevant chunks from your uploaded knowledge base.
4. **Initial Answer** – The selected LLM (via OpenRouter or fallback) drafts a response using the retrieved context.
5. **Jury of 3 Verifiers** – Independently check the answer for accuracy, completeness, and consistency.
6. **Judge Shakti** – Synthesises the answer and critiques, producing a final response with **confidence (HIGH/MEDIUM/LOW)** and a list of **sources**.
7. **Streaming Response** – The final answer is streamed in real‑time, ending with a `verification` JSON block.
8. **Redis Cache** – The response is cached for 24 hours; identical queries are answered instantly.

---

## 🛠️ Tech Stack (v10)

- **Backend:** FastAPI (Python), PostgreSQL + pgvector (Neon), SQLAlchemy, JWT auth, Razorpay, APScheduler (auto‑purge).
- **AI Providers:** OpenRouter (primary), Groq, OpenAI, Google Gemini – with graceful fallback.
- **Embeddings:** Local `sentence-transformers/all-MiniLM-L6-v2` – **100% free**, no API key needed.
- **Caching:** Redis (Upstash / Redis Cloud) – reduces token usage and latency.
- **Frontend:** Cloudflare Pages, HTML5, CSS3, JavaScript, Font Awesome, Web Speech API (voice I/O).
- **Search:** SerpAPI (optional) for real‑time web references.
- **Deployment:** Hugging Face Spaces (Docker), Cloudflare DNS.
- **Additional:** SlowAPI (rate limiting), PyPDF2, pdfplumber, python‑docx, Pillow, pytesseract, httpx.

---

## 🧪 Live Demo

🔗 **Backend API:** [https://upamnyu12-lex.hf.space/](https://upamnyu12-lex.hf.space/)  
🌐 **Frontend:** [https://www.advocacyalawfrim.in/](https://www.advocacyalawfrim.in/)

**Test Credentials:**  
- **Username:** `counsel`  
- **Password:** `Password123!`

---

## 💰 Pricing Plans (₹ INR)

| Plan | Price | Features |
| :--- | :--- | :--- |
| **Free** | ₹0 | 10 queries/day, basic agents, no caching. |
| **Lifetime** | ₹2 (limited to first 1000 users) | Unlimited queries, all agents, zero retention, full access forever. |
| **Premium** | ₹102/month | Unlimited queries, custom agents, analytics dashboard, priority response. |
| **Enterprise** | ₹1011/month | All premium + API access, white‑glove onboarding, dedicated support. |

---

## 🏁 Getting Started

### For End‑Users
1. Visit [https://www.advocacyalawfrim.in/](https://www.advocacyalawfrim.in/)
2. Click **Login** and use the test credentials or register a new account.
3. **Select your language** from the Settings panel (English, Hindi, Bengali, Sanskrit, Arabic).
4. Ask any question – about law, science, philosophy, finance, or life itself.
5. **Upload a document** (PDF, DOCX, image) or **click the Voice button** to speak your query.
6. Toggle **Web Search** for real‑time references.
7. Watch the **spinning ॐ** while the divine intelligence processes your request.
8. Click **Speak** to hear the response aloud in your chosen language.
9. Explore **My Usage** to track your activity.
10. Upgrade to **Lifetime** for ₹2 (limited offer) or choose a subscription plan.

### For Developers (API Access)
- Enterprise users can obtain an API key from the Settings panel.
- Use the key to integrate LexSarthi’s agents into your own applications.

---

## 📁 Repository Structure
