"""Feature 10: Legal Strategy Generator."""
from __future__ import annotations
from typing import Any, Dict, List
from .db import db
from .sarvam import sarvam_reason

class StrategyGenerator:
    async def generate_strategy(self, case_summary: str, jurisdiction: str = "IN") -> Dict[str, Any]:
        raw = await sarvam_reason(
            f"Case: {case_summary[:2500]}\nJurisdiction: {jurisdiction}",
            "Generate a winning legal strategy. Include: 1) Main strategy 2) Argument strengths "
            "3) Likely opposing counsel arguments 4) Predicted judge questions 5) Alternative theories.",
            0.4, 4000)
        # Parse the response into sections (best-effort)
        sections = self._parse(raw) if raw else {}
        strategy = sections.get("strategy", raw or "Strategy generation requires more case details.")
        strengths = sections.get("strengths", ["Strong documentary evidence","Clear statutory basis"])
        opposing = sections.get("opposing", ["Statute of limitations","Burden of proof challenges"])
        questions = sections.get("questions", ["What is the timeline of events?","What evidence supports the claim?"])
        theories = sections.get("theories", ["Primary: direct legal claim","Alternative: estoppel argument"])
        sid = await db.add_strategy(case_summary, strategy, strengths, opposing, questions, theories, 0.65)
        return {"strategy_id":sid or "","strategy":strategy,"argument_strengths":strengths,
                "opposing_arguments":opposing,"predicted_judge_questions":questions,
                "alternative_theories":theories,"confidence":0.65,"sarvam_used":bool(raw)}

    def _parse(self, text: str) -> Dict[str, List[str]]:
        import re
        result = {"strategy":"", "strengths":[], "opposing":[], "questions":[], "theories":[]}
        if not text: return result
        lines = text.split("\n")
        current = None
        for line in lines:
            low = line.lower().strip()
            if "strategy" in low and ":" in low: current = "strategy"; result["strategy"] = line.split(":",1)[1].strip(); continue
            if "strength" in low and ":" in low: current = "strengths"; continue
            if "opposing" in low or "counter" in low: current = "opposing"; continue
            if "judge" in low and "question" in low: current = "questions"; continue
            if "alternative" in low or "theory" in low: current = "theories"; continue
            if current and line.strip().startswith(("-","*","•",str(1),str(2),str(3))):
                item = re.sub(r'^[-*•\d.\)\s]+', '', line.strip())
                if item and current in result and isinstance(result[current], list):
                    result[current].append(item)
                elif current == "strategy":
                    result["strategy"] += " " + line.strip()
        return result

strategy_gen = StrategyGenerator()
