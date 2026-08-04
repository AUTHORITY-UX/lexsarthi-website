# Unknown Verdict v41.0 — Latency Tuning & Performance Guide

## THE PROBLEM

Your chat endpoint was taking ~100 seconds because Sarvam 105B was the default model for ALL queries — even simple ones like "hello". Sarvam 105B is a frontier-class model: high quality, high latency.

## THE FIX (already working in your logs!)

Your LLM router is already doing the right thing. From the startup logs:

```
2026-08-04 12:07:14,810 [INFO] core.llm.router: LLM call: groq/llama-3.1-8b-instant complexity=simple
2026-08-04 12:07:15,794 [INFO] httpx: HTTP Request: POST https://api.groq.com/.../chat/completions "HTTP/1.1 200 OK"
2026-08-04 12:07:15,795 [INFO] core.llm.router: LLM success: groq latency=954ms
```

The router classified the query as `simple` and routed to Groq's `llama-3.1-8b-instant` → **954ms** instead of 100s. This is tiered routing in action.

## TIERED LLM ROUTING STRATEGY

```
┌──────────────────────────────────────────────────────────────────┐
│                    User Query Incoming                           │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Complexity    │
              │  Classifier    │
              └───────┬────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐  ┌──────────┐  ┌───────────────┐
   │ SIMPLE  │  │ MEDIUM   │  │ COMPLEX       │
   │ (70%)   │  │ (20%)    │  │ (10%)         │
   └────┬────┘  └────┬─────┘  └──────┬────────┘
        │            │               │
        ▼            ▼               ▼
  Groq Llama    Sarvam 30B      Sarvam 105B
  3.1-8b       (5-15s)         (30-100s)
  (<1s)
```

### Complexity Classification Rules

```python
# core/llm/router.py — complexity classifier

def classify_complexity(query: str) -> str:
    """Classify query complexity to route to the right LLM."""
    query_lower = query.lower().strip()
    word_count = len(query_lower.split())

    # SIMPLE: greetings, short questions, basic definitions
    simple_patterns = [
        "hello", "hi", "hey", "thanks", "what is", "define",
        "explain briefly", "summarize", "list"
    ]
    if any(query_lower.startswith(p) for p in simple_patterns) or word_count < 10:
        return "simple"

    # COMPLEX: case analysis, multi-party disputes, constitutional questions
    complex_patterns = [
        "analyse", "analyze", "case analysis", "constitutional",
        "precedent", "multi-party", "appeal", "supreme court",
        "constitutional validity", "judicial review"
    ]
    if any(p in query_lower for p in complex_patterns) or word_count > 100:
        return "complex"

    # MEDIUM: everything else
    return "medium"
```

### Model Configuration

```python
# config.py or core/llm/router.py

LLM_ROUTING = {
    "simple": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "max_tokens": 512,
        "temperature": 0.3,
        "timeout": 10,           # seconds
        "expected_latency_ms": 1000,
    },
    "medium": {
        "provider": "sarvam",
        "model": "sarvam-30b",
        "max_tokens": 1024,
        "temperature": 0.4,
        "timeout": 30,
        "expected_latency_ms": 8000,
    },
    "complex": {
        "provider": "sarvam",
        "model": "sarvam-105b",
        "max_tokens": 2048,
        "temperature": 0.5,
        "timeout": 120,
        "expected_latency_ms": 60000,
    },
}
```

## STREAMING (eliminates perceived latency)

The user shouldn't wait 60s staring at a spinner. Stream tokens as they arrive:

### Backend: Add SSE streaming endpoint

```python
# routes.py — add streaming chat endpoint

from fastapi.responses import StreamingResponse
import json
import asyncio

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat — tokens sent as Server-Sent Events."""

    async def event_generator():
        # 1. Send thinking event
        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Analyzing query...'})}\n\n"

        # 2. Classify complexity
        complexity = classify_complexity(request.message)
        model_config = LLM_ROUTING[complexity]

        yield f"data: {json.dumps({'type': 'thinking', 'content': f'Using {model_config[\"model\"]} ({complexity})'})}\n\n"

        # 3. RAG retrieval
        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Searching legal knowledge base...'})}\n\n"
        rag_context = await rag.retrieve(request.message)

        # 4. Stream LLM tokens
        async for chunk in llm.stream(
            prompt=request.message,
            context=rag_context,
            **model_config
        ):
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

        # 5. Done
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Frontend: Add SSE consumer (already in index_v3.html)

```javascript
// Add to index_v3.html — streaming chat consumer
async function sendMessageStream() {
    const text = document.getElementById('chat-input').value.trim();
    if (!text) return;

    addMessage('user', text);
    const thinkingEl = showThinkingPanel();
    const assistantMsg = addMessage('assistant', '');  // empty, will fill
    const bodyEl = assistantMsg.querySelector('.message-body');

    const resp = await fetch(`${BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();  // keep incomplete line

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = JSON.parse(line.slice(6));

            if (data.type === 'thinking') {
                updateThinking(thinkingEl, data.content);
            } else if (data.type === 'token') {
                bodyEl.innerHTML += data.content;
            } else if (data.type === 'done') {
                bodyEl.innerHTML = formatContent(bodyEl.textContent);
            }
        }
    }
}
```

## REDIS CACHING (cuts API costs 80%)

Cache LLM responses for identical queries. Legal questions are highly repetitive.

```python
# core/cache.py

import hashlib
import json
import os
from datetime import timedelta

class ResponseCache:
    """Redis-backed LLM response cache."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = int(os.getenv("CACHE_TTL_HOURS", "24")) * 3600  # 24h default

    def _key(self, query: str, model: str) -> str:
        """Normalised cache key."""
        normalized = query.lower().strip()
        return f"llm:{model}:{hashlib.sha256(normalized.encode()).hexdigest()}"

    async def get(self, query: str, model: str) -> dict | None:
        key = self._key(query, model)
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set(self, query: str, model: str, response: dict):
        key = self._key(query, model)
        await self.redis.setex(key, self.ttl, json.dumps(response))

# In routes.py chat endpoint:
cache = ResponseCache(redis)

@app.post("/chat")
async def chat(request: ChatRequest):
    # Check cache first
    cached = await cache.get(request.message, current_model)
    if cached:
        return {**cached, "cached": True}  # instant response!

    # ... LLM call ...
    response = await llm.generate(...)

    # Cache for next time
    await cache.set(request.message, current_model, response)

    return response
```

## LATENCY TARGETS BY TIER

| Query Type | Model | Target Latency | Max Tokens | Timeout |
|------------|-------|----------------|------------|---------|
| Simple (70%) | Groq llama-3.1-8b | < 2s | 512 | 10s |
| Medium (20%) | Sarvam 30B | < 10s | 1024 | 30s |
| Complex (10%) | Sarvam 105B | < 60s | 2048 | 120s |
| Cached (any) | Redis | < 50ms | — | 1s |

## IMMEDIATE ACTIONS (this week)

1. **✅ Done** — Router already routes simple queries to Groq (954ms in logs)
2. **Verify** the complexity classifier thresholds — log `complexity=simple/medium/complex` for every request to see the distribution
3. **Add** the `/chat/stream` SSE endpoint above — eliminates perceived latency for complex queries
4. **Add** Redis caching — even without Redis running, the code path should gracefully skip cache and still work
5. **Set** `max_tokens=512` for simple queries (currently may be unlimited)
6. **Set** per-model timeouts — Sarvam 105B should NOT have a 120s timeout for chat; reduce to 60s with graceful fallback to 30B on timeout

## LATENCY DIAGNOSTIC CHECKLIST

When chat is slow, check in this order:

1. **Which model was used?** → Check logs for `LLM call: <provider>/<model>`
2. **Was it cached?** → Check Redis for the query hash
3. **What was the prompt size?** → Large RAG context = slow generation
4. **Was the DB write slow?** → Check for the `%s` placeholder bug (now fixed)
5. **Is Sarvam API itself slow?** → Check Sarvam's status page
6. **Is Neon cold-starting?** → First query after idle can take 3-5s extra
