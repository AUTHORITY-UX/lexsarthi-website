"""Feature 6: Emotion-Aware Legal Analysis."""
from __future__ import annotations
from typing import Any, Dict
from .db import db
from .sarvam import sarvam_reason

EMOTION_KEYWORDS = {
    "anxious": ["worried","anxious","nervous","scared","afraid","panic","stress"],
    "angry": ["angry","furious","rage","frustrated","mad","irritated"],
    "sad": ["sad","depressed","hopeless","devastated","crying","hurt"],
    "confused": ["confused","lost","don't understand","unclear","unsure"],
    "urgent": ["urgent","immediately","emergency","asap","deadline","tomorrow"],
    "hopeful": ["hopeful","optimistic","positive","confident","trust"],
}

class EmotionAnalyzer:
    def detect(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        scores = {}
        for emotion, kws in EMOTION_KEYWORDS.items():
            scores[emotion] = sum(1 for kw in kws if kw in t)
        primary = max(scores, key=scores.get) if any(scores.values()) else "neutral"
        score = min(1.0, sum(scores.values()) / 10.0)
        return {"emotion":primary,"intensity":round(score,4),"all_emotions":scores}

    def adjust_tone(self, emotion: str) -> str:
        tones = {
            "anxious": "calm and reassuring, acknowledge their concerns, provide clear next steps",
            "angry": "calm and professional, validate their frustration, focus on solutions",
            "sad": "empathetic and gentle, show understanding, offer support resources",
            "confused": "clear and simple, break down into steps, use plain language",
            "urgent": "responsive and action-oriented, prioritize immediate steps",
            "hopeful": "encouraging and balanced, manage expectations while being positive",
        }
        return tones.get(emotion, "professional and balanced")

    async def analyze_and_respond(self, client_text: str, legal_query: str = "") -> Dict[str, Any]:
        emotion = self.detect(client_text)
        tone = self.adjust_tone(emotion["emotion"])
        raw = await sarvam_reason(
            f"Client emotional state: {emotion['emotion']} (intensity: {emotion['intensity']}).\n"
            f"Client message: {client_text[:1500]}\nLegal query: {legal_query}",
            f"You are an empathetic legal AI. Tone: {tone}. Provide a helpful response.", 0.4, 2000)
        return {"emotion_analysis":emotion,"recommended_tone":tone,
                "response":raw or "I understand your concern. Let me help you with this matter.",
                "sarvam_used":bool(raw)}

emotion = EmotionAnalyzer()
