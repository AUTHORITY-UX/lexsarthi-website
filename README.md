---
title: Unknown Verdict
emoji: ⚖️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
license: mit
fullWidth: true
header: mini
---

# ⚖️ Unknown Verdict v11.0

**Enterprise AI Legal Advisory Platform with 250 Specialist Personas, 10 Verifiers, and Judge Shakti**

[![Hugging Face](https://img.shields.io/badge/Hugging_Face-Space-yellow)](https://huggingface.co/spaces/upamnyu12/LEX)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

---

## 🏛️ **Overview**

**Unknown Verdict** is a cutting-edge Enterprise Legal AI Platform that combines:

- **250 Specialist Personas** - Domain-specific legal experts
- **10-Verifier Jury System** - Multi-layer response validation
- **Judge Shakti** - Final verdict with confidence scoring
- **Constitutional AI** - Ethical and constitutional compliance
- **Edge AI Integration** - On-device AI processing
- **Enterprise Features** - Multi-tenancy, API keys, white-labeling

---

## ✨ **Features**

### 🤖 **Core AI Capabilities**
| Feature | Description | Status |
|---------|-------------|--------|
| **250 Specialist Personas** | Legal experts across 50+ domains | ✅ |
| **10 Verifier Jury** | Multi-layer response validation | ✅ |
| **Judge Shakti** | Final verdict with confidence scoring | ✅ |
| **Constitutional AI** | Ethical and constitutional compliance | ✅ |
| **RAG Knowledge Base** | 1,047+ legal documents indexed | ✅ |
| **Web Search** | Real-time legal research | ✅ |

### 📡 **Edge AI Features**
| Feature | Description | Status |
|---------|-------------|--------|
| **Audio Processing** | Courtroom audio analysis | ✅ |
| **Vision Processing** | Document & signature verification | ✅ |
| **Multi-modal Analysis** | Combined audio + vision | ✅ |
| **Emotion Detection** | Voice emotion analysis | ✅ |

### 🔒 **Enterprise Features**
| Feature | Description | Status |
|---------|-------------|--------|
| **Multi-tenancy** | White-label support | ✅ |
| **API Keys** | RESTful API with rate limiting | ✅ |
| **Custom Personas** | Create custom legal personas | ✅ |
| **Bulk Upload** | Batch document processing | ✅ |
| **Drafts System** | Review and approve AI drafts | ✅ |
| **Legal Templates** | 5+ legal document templates | ✅ |
| **Payments** | Razorpay integration | ✅ |

---

## 🚀 **Quick Start**

### **Try it Now!**

```bash
# 1. Login to get token
curl -X POST https://upamnyu12-LEX.hf.space/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"counsel","password":"Password123!"}'

# 2. Ask a legal question
curl -X POST https://upamnyu12-LEX.hf.space/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "query=What are my fundamental rights?"

# 3. Check health
curl https://upamnyu12-LEX.hf.space/health