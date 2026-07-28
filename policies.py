# policies.py - Validation rules
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

from typing import List, Dict

def validate_credit_agreement(data: Dict) -> Dict:
    """Check business rules and return flags."""
    flags = []
    if data.get('interest_rate', 0) > 10:
        flags.append("Interest rate exceeds 10% (high)")
    if data.get('default_penalty', 0) > 5:
        flags.append("Default penalty > 5% – review")
    if data.get('term_months', 0) > 360:
        flags.append("Term > 30 years – unusual")
    return {"flags": flags, "pass": len(flags) == 0}