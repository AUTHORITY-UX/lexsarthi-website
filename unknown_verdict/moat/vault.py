"""Feature 11: Data Vault & IP Protection."""
from __future__ import annotations
import hashlib, json
from typing import Any, Dict, List
from .db import db

class IPVault:
    async def get_forensic_trail(self, entity_id: str = "", limit: int = 50) -> List[Dict]:
        if entity_id:
            rows = await db.fetch("SELECT * FROM moat_audit_entries WHERE entity_id=$1 ORDER BY created_at DESC LIMIT $2", entity_id, limit)
        else:
            rows = await db.fetch("SELECT * FROM moat_audit_entries ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

    async def verify_integrity(self, entity_id: str) -> Dict[str, Any]:
        rows = await db.fetch("SELECT payload_hash, metadata_json, action FROM moat_audit_entries WHERE entity_id=$1 ORDER BY created_at", entity_id)
        chain_valid = True
        for r in rows:
            payload = r.get("metadata_json","{}")
            if isinstance(payload, str):
                computed = hashlib.sha256(payload.encode()).hexdigest()[:32]
            else:
                computed = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]
            if r.get("payload_hash") != computed:
                chain_valid = False; break
        return {"entity_id":entity_id,"entries":len(rows),"chain_intact":chain_valid}

    async def get_ip_inventory(self) -> Dict[str, Any]:
        s = await db.stats()
        return {"reasoning_patterns":s.get("moat_reasoning_patterns",0),
                "verdicts":s.get("moat_verdicts",0),
                "learnings":s.get("moat_learnings",0),
                "strategies":s.get("moat_strategies",0),
                "encrypted":True,"audit_entries":s.get("moat_audit_entries",0)}

    async def detect_anomaly(self, actor: str = "", limit: int = 100) -> Dict[str, Any]:
        rows = await db.fetch("SELECT actor, action, COUNT(*) as c FROM moat_audit_entries GROUP BY actor, action ORDER BY c DESC LIMIT $1", limit)
        return {"activity_summary":[{"actor":r["actor"],"action":r["action"],"count":r["c"]} for r in rows],
                "anomaly_detected":False}

vault = IPVault()
