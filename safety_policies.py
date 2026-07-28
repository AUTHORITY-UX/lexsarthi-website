# safety_policies.py - Custom policy definitions
from safety_monitor import SafetyMonitor

# You can extend the monitor with additional policies via API
# Example: add a new blocked domain
# monitor = get_safety_monitor()
# await monitor.set_policy("blocked_domains", ["new-danger.com", "evil.net"])