---
title: LEXSARTHI v9.1 – ATMA Universal OS
emoji: 🔱
colorFrom: yellow
colorTo: yellow
sdk: docker
app_file: app.py
pinned: false
license: other
---

# 🔱 LEXSARTHI v9.1 – ATMA Universal OS

## The First Self‑Verifying AI OS for Every Domain – Law, Science, Philosophy, Finance, Life & Beyond

### 🏛️ Owned by **THE ADVOCACY – A LAW FIRM**  
**Proprietor:** Upmanyu Kumar  
**UDYAM:** UP-09-0043193 | **PAN:** CHFPK3464A  

---

## 📌 Overview

LexSarthi v9.1 evolves into a **self‑verifying, domain‑agnostic AI** powered by the **Atma router** – an intelligent orchestration layer that dynamically selects specialists, retrieves authoritative knowledge, and runs a **jury of 3 verifiers + a judge** to produce answers with **confidence scores** and **source citations**.  

Whether you ask about **contract law**, **quantum physics**, **Vedanta**, **financial markets**, or **the meaning of life**, LexSarthi responds with transparency, citing both your **ingested documents** and **live official websites** (e.g., Supreme Court, Parliament, SEC, WHO, CERN).

---

## 🚀 New in v9.1 – The Atma Engine

| Feature | Description |
| :------ | :---------- |
| **Atma Router** | Classifies the query domain (constitutional, criminal, corporate, general, etc.), selects the best specialist persona from 250+ agents, and picks the optimal LLM provider (Groq / OpenAI / Gemini) with automatic fallback. |
| **pgvector RAG** | All legal and knowledge documents are embedded into PostgreSQL with pgvector, enabling **high‑speed, scalable retrieval** of relevant chunks. |
| **Jury + Judge Shakti** | Every answer is cross‑checked by 3 verifiers (Accuracy, Completeness, Consistency) and synthesised by Judge Shakti, producing a **HIGH / MEDIUM / LOW confidence** rating and a list of **sources** (PDF filenames + live URLs). |
| **Targeted Web Search** | Configurable real‑time search on **official websites** (Supreme Court, Parliament, SEBI, SEC, WHO, CERN, etc.) – verifies claims against live authoritative data. |
| **Zero‑Retention (24h)** | All queries, responses, and uploaded files are automatically purged after 24 hours – no data is stored or used for training. |
| **Universal Domain Support** | Built‑in personas for Law, Mathematics, Physics, Chemistry, Medicine, Philosophy, Finance, History, AI Ethics, Climate Science, and 40+ more – with a `general` fallback for any query. |
| **Auto‑Ingestion** | On first startup, all PDFs in the `legal_docs/` folder are automatically embedded into pgvector – no manual steps required. |
| **Deliberation Logging** | Every query, the jury’s verdicts, the final answer, and the confidence score are stored in the `deliberations` table for continuous self‑improvement and auditing. |
| **Multilingual Voice I/O** | Speak in English, Hindi, Bengali, Sanskrit, or Arabic – the system transcribes and replies in the same language with TTS playback. |
| **Om Thinking Indicator** | A spinning **ॐ** appears while the divine intelligence is processing your request. |
| **Multi‑Modal Input** | Text, PDF, DOCX, Images (OCR), and Voice Transcription (Speech‑to‑Text). |
| **Sovereign Fallback** | If all external AI services are rate‑limited or unavailable, LexSarthi retrieves authoritative text from your **local PDF library** (Contract Act, IPC, Constitution, DPDPA, Companies Act, AI Act, etc.) – guaranteeing a response. |
| **Payment Integration** | Razorpay – supports ₹2 Lifetime (first 1000 users), ₹102/month Premium, ₹1011/month Enterprise. |
| **User Dashboard** | “My Usage” shows total queries, today’s count, agents used, and recent history. |
| **Enterprise Analytics** | Global stats (total users, queries, DAU, paid users) for enterprise subscribers. |
| **Referral System** | Generate and share referral codes; both referrer and referee get bonus queries. |
| **Agent Customisation** | Enterprise users can create and edit custom agents with personalised prompts. |

---

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python), PostgreSQL + pgvector (Neon), SQLAlchemy, JWT auth, Razorpay payments, APScheduler for auto‑delete.
- **AI Providers:** Groq (Llama 3.3), OpenAI (GPT‑4o), Google Gemini – with graceful fallback to local PDF library.
- **Embeddings:** Local `sentence-transformers/all-MiniLM-L6-v2` (no API key needed) – free, private, fast.
- **Frontend:** Cloudflare Pages, HTML5, CSS3, JavaScript, Font Awesome, 3D Om animation, Speech Recognition API, Speech Synthesis API.
- **Search:** SerpAPI for web search (with configurable targeted domains).
- **Deployment:** Hugging Face Spaces (Docker), Cloudflare DNS.
- **Additional:** SlowAPI rate limiting, PyPDF2, pdfplumber, python‑docx, Pillow, pytesseract, httpx.

---

## 🧪 Live Demo

🔗 **Backend API:** [https://upamnyu12-lex.hf.space/](https://upamnyu12-lex.hf.space/)  
🌐 **Frontend:** [https://www.advocacyalawfrim.in/](https://www.advocacyalawfrim.in/)

**Test Credentials:**  
- **Username:** `counsel`  
- **Password:** `Password123!`

---

## 📈 Pricing Plans

| Plan | Price | Features |
| :--- | :--- | :--- |
| **Free** | ₹0 | 10 queries/day, basic agents, no customisation. |
| **Lifetime** | ₹2 (limited to first 1000 users) | Unlimited queries, all agents, zero retention, full access forever. |
| **Premium** | ₹102/month | Unlimited queries, custom agents, analytics dashboard. |
| **Enterprise** | ₹1011/month | All premium + API access, priority support, white‑glove onboarding. |

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
