# safety_monitor.py - AI Safety & Surveillance Core
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger("unknown_verdict.safety")

class ActionType(Enum):
    LLM_CALL = "llm_call"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK_REQUEST = "network_request"
    CODE_EXECUTION = "code_execution"
    SHELL_COMMAND = "shell_command"
    ACCESS_KEY = "access_key"

class SafetyVerdict(Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    FLAGGED = "flagged"
    KILLED = "killed"

class SafetyMonitor:
    """Singleton that intercepts and logs all agent actions."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.rules = self._load_default_rules()
        self.audit_log = []
        self.alerts = []
        self.kill_switch_active = False
        self.killed_agents = set()
        self._lock = asyncio.Lock()

    def _load_default_rules(self) -> Dict:
        """Default safety policies."""
        return {
            "blocked_domains": ["private.api", "internal-server", "secret-storage"],
            "blocked_commands": ["rm -rf", "sudo", "shutdown", "kill", "pkill"],
            "blocked_paths": ["/etc/passwd", "/root/", "/proc/"],
            "max_llm_tokens": 8192,
            "max_file_size": 10 * 1024 * 1024,  # 10 MB
            "allow_github_push": False,         # per the article
            "allow_external_upload": False,
            "require_human_approval_for": ["shell", "code_execution"],
            "suspicious_patterns": [
                "reconstruct.*key", "bypass.*security", "escape.*sandbox",
                "access.*private", "terminate.*process"
            ]
        }

    async def intercept_action(
        self,
        agent_id: str,
        action_type: ActionType,
        payload: Dict,
        source: str = "agent"
    ) -> Dict:
        """
        Intercept and evaluate an action.
        Returns:
            {
                "verdict": "allowed" | "blocked" | "flagged" | "killed",
                "reason": str,
                "log_id": str
            }
        """
        async with self._lock:
            # 1. Check if agent is already killed
            if agent_id in self.killed_agents:
                return self._block("Agent is terminated (Kill Switch)")

            # 2. Evaluate against rules
            verdict, reason = self._evaluate_action(action_type, payload)

            # 3. Log everything
            log_entry = {
                "log_id": f"log_{int(time.time())}_{agent_id}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "action_type": action_type.value,
                "payload": payload,
                "source": source,
                "verdict": verdict,
                "reason": reason,
                "details": {}
            }
            self.audit_log.append(log_entry)

            # 4. Trigger alert if flagged or blocked
            if verdict in [SafetyVerdict.FLAGGED, SafetyVerdict.BLOCKED]:
                self._create_alert(log_entry)

            # 5. If killed, add to kill list
            if verdict == SafetyVerdict.KILLED:
                self.killed_agents.add(agent_id)
                self._create_alert(log_entry, severity="critical")
                logger.critical(f"🛑 KILL SWITCH ACTIVATED for agent {agent_id}: {reason}")

            return {
                "verdict": verdict.value,
                "reason": reason,
                "log_id": log_entry["log_id"]
            }

    def _evaluate_action(self, action_type: ActionType, payload: Dict) -> tuple:
        """Evaluate against rules and return (verdict, reason)."""
        # Example checks
        if action_type == ActionType.NETWORK_REQUEST:
            url = payload.get("url", "")
            for blocked in self.rules["blocked_domains"]:
                if blocked in url:
                    return SafetyVerdict.BLOCKED, f"Domain {blocked} is blocked"
            if not self.rules["allow_external_upload"] and "upload" in url:
                return SafetyVerdict.FLAGGED, "External upload is disallowed by policy"

        if action_type == ActionType.SHELL_COMMAND:
            cmd = payload.get("command", "")
            for blocked in self.rules["blocked_commands"]:
                if blocked in cmd:
                    return SafetyVerdict.KILLED, f"Command '{blocked}' is prohibited (KILL)"
            if any(p in cmd for p in self.rules["blocked_paths"]):
                return SafetyVerdict.BLOCKED, "Access to system path blocked"

        if action_type == ActionType.ACCESS_KEY:
            key = payload.get("key", "")
            # Detect reconstruction attempts (simple)
            if "reconstruct" in key.lower():
                return SafetyVerdict.KILLED, "Reconstructing access key detected – KILL"

        if action_type == ActionType.LLM_CALL:
            prompt = payload.get("prompt", "")
            for pattern in self.rules["suspicious_patterns"]:
                if pattern.lower() in prompt.lower():
                    return SafetyVerdict.FLAGGED, f"Suspicious pattern: {pattern}"

        # Default: allow
        return SafetyVerdict.ALLOWED, "Allowed by policy"

    def _block(self, reason: str) -> Dict:
        return {
            "verdict": SafetyVerdict.BLOCKED.value,
            "reason": reason,
            "log_id": None
        }

    def _create_alert(self, log_entry: Dict, severity: str = "medium"):
        alert = {
            "alert_id": f"alert_{int(time.time())}",
            "timestamp": log_entry["timestamp"],
            "agent_id": log_entry["agent_id"],
            "action": log_entry["action_type"],
            "verdict": log_entry["verdict"],
            "reason": log_entry["reason"],
            "severity": severity,
            "resolved": False
        }
        self.alerts.append(alert)
        logger.warning(f"🚨 ALERT: {alert['reason']} (agent {alert['agent_id']})")

    # ─── ADMIN FUNCTIONS ──────────────────────────────────────

    async def get_audit_log(self, limit: int = 100, agent_id: Optional[str] = None) -> List[Dict]:
        if agent_id:
            return [e for e in self.audit_log if e["agent_id"] == agent_id][-limit:]
        return self.audit_log[-limit:]

    async def get_alerts(self, resolved: Optional[bool] = None) -> List[Dict]:
        if resolved is None:
            return self.alerts
        return [a for a in self.alerts if a["resolved"] == resolved]

    async def resolve_alert(self, alert_id: str):
        for alert in self.alerts:
            if alert["alert_id"] == alert_id:
                alert["resolved"] = True
                return True
        return False

    async def activate_kill_switch(self, agent_id: str):
        """Manually kill an agent."""
        self.killed_agents.add(agent_id)
        self._create_alert({
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "action_type": "manual_kill",
            "verdict": "killed",
            "reason": "Admin initiated kill switch"
        }, severity="critical")
        logger.critical(f"🛑 MANUAL KILL for agent {agent_id}")

    async def deactivate_kill_switch(self, agent_id: str):
        if agent_id in self.killed_agents:
            self.killed_agents.remove(agent_id)
            logger.info(f"✅ Kill switch removed for agent {agent_id}")

    async def set_policy(self, key: str, value: Any):
        self.rules[key] = value
        logger.info(f"📝 Policy updated: {key} = {value}")

    def get_status(self) -> Dict:
        return {
            "active": True,
            "total_agents": len(self.killed_agents),  # we could track from registry
            "killed_agents": list(self.killed_agents),
            "alerts_pending": len([a for a in self.alerts if not a["resolved"]]),
            "log_entries": len(self.audit_log)
        }

# Singleton
_safety_monitor = None
def get_safety_monitor() -> SafetyMonitor:
    global _safety_monitor
    if _safety_monitor is None:
        _safety_monitor = SafetyMonitor()
    return _safety_monitor