# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import os
import json
import requests
from typing import Optional

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o"  # or "anthropic/claude-3.5-sonnet"

def call_openrouter(
    system_prompt: str,
    user_message: str,
    response_format: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1
) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:7860"),
        "X-Title": "Lexsarthi Agent System"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": temperature,
        "max_tokens": 2000,
    }
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]