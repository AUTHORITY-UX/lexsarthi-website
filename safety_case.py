# =============================================================================
# safety_case.py – Safety Case Documentation
# =============================================================================

import json
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger("unknown_verdict.safety_case")

class SafetyCase:
    """Generate and maintain safety case documentation."""
    
    def __init__(self, pg_pool):
        self.pg_pool = pg_pool
    
    async def generate_safety_report(self, period_days: int = 30) -> Dict:
        metrics = {
            "constitutional_compliance": await self._get_constitutional_metrics(period_days),
            "red_team_results": await self._get_red_team_metrics(period_days),
            "incident_reporting": await self._get_incident_metrics(period_days)
        }
        
        assessment = {
            "overall_safety_score": self._calculate_safety_score(metrics),
            "critical_vulnerabilities": self._identify_vulnerabilities(metrics),
            "recommendations": self._generate_recommendations(metrics),
            "report_date": datetime.now().isoformat(),
            "period_days": period_days,
            "metrics_summary": metrics
        }
        
        await self._store_safety_report(assessment)
        return assessment
    
    async def _get_constitutional_metrics(self, period_days: int) -> Dict:
        try:
            async with self.pg_pool.acquire() as conn:
                violations = await conn.fetchrow("""
                    SELECT COUNT(*) as total_violations,
                           AVG(confidence_score) as avg_confidence
                    FROM constitutional_violations
                    WHERE detected_at > NOW() - INTERVAL '$1 days'
                """, period_days)
                return {
                    "total_violations": violations['total_violations'] or 0,
                    "compliance_rate": max(0, 100 - (violations['total_violations'] or 0) * 2)
                }
        except Exception as e:
            logger.error(f"Failed to get constitutional metrics: {e}")
            return {"error": str(e)}
    
    async def _get_red_team_metrics(self, period_days: int) -> Dict:
        try:
            async with self.pg_pool.acquire() as conn:
                results = await conn.fetchrow("""
                    SELECT COUNT(*) as total_tests,
                           SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_failures
                    FROM red_team_tests
                    WHERE tested_at > NOW() - INTERVAL '$1 days'
                """, period_days)
                return {
                    "total_tests": results['total_tests'] or 0,
                    "critical_failures": results['critical_failures'] or 0,
                    "overall_safety": max(0, 100 - (results['critical_failures'] or 0) * 10)
                }
        except Exception as e:
            logger.error(f"Failed to get red team metrics: {e}")
            return {"error": str(e)}
    
    async def _get_incident_metrics(self, period_days: int) -> Dict:
        return {"total_incidents": 0, "critical_incidents": 0}
    
    def _calculate_safety_score(self, metrics: Dict) -> float:
        scores = []
        if 'constitutional_compliance' in metrics and 'compliance_rate' in metrics['constitutional_compliance']:
            scores.append(metrics['constitutional_compliance']['compliance_rate'] * 0.4)
        if 'red_team_results' in metrics and 'overall_safety' in metrics['red_team_results']:
            scores.append(metrics['red_team_results']['overall_safety'] * 0.3)
        return sum(scores) if scores else 0
    
    def _identify_vulnerabilities(self, metrics: Dict) -> List[Dict]:
        vulnerabilities = []
        if metrics.get('red_team_results', {}).get('critical_failures', 0) > 0:
            vulnerabilities.append({
                "type": "RED_TEAM_FAILURE",
                "severity": "CRITICAL",
                "description": f"{metrics['red_team_results']['critical_failures']} critical failures detected",
                "recommendation": "Immediate investigation and patching required"
            })
        return vulnerabilities
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        recommendations = []
        if metrics.get('constitutional_compliance', {}).get('compliance_rate', 100) < 95:
            recommendations.append("Enhance Constitutional AI training with more Indian legal cases")
        if metrics.get('red_team_results', {}).get('critical_failures', 0) > 0:
            recommendations.append("Strengthen system prompts and safety guardrails")
        return recommendations
    
    async def _store_safety_report(self, report: Dict):
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO safety_reports (report_data, generated_at, safety_score)
                    VALUES ($1, NOW(), $2)
                """, json.dumps(report), report.get('overall_safety_score', 0))
        except Exception as e:
            logger.error(f"Failed to store safety report: {e}")