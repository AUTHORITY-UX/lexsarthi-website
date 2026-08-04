"""
core/governance/compliance.py - Compliance Auditor
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

from core.llm import LLMMessage, get_router
from core.db import db

logger = logging.getLogger(__name__)


@dataclass
class ComplianceReport:
    """Compliance audit report"""
    audit_id: str
    system_name: str
    compliance_score: float
    status: str  # 'compliant', 'non_compliant', 'pending'
    findings: List[Dict]
    recommendations: List[str]
    severity: str  # 'critical', 'high', 'medium', 'low'
    ai_act_status: str


class ComplianceAuditor:
    """Audit AI systems for regulatory compliance"""
    
    def __init__(self):
        self.router = get_router()
    
    async def audit_system(self, system_name: str, 
                           system_description: str,
                           regulations: List[str]) -> ComplianceReport:
        """Audit a system against regulations"""
        
        # Check against EU AI Act
        ai_act_status = await self._check_ai_act(system_name, system_description)
        
        # Check against regulations
        findings = []
        for regulation in regulations:
            finding = await self._check_regulation(system_name, system_description, regulation)
            findings.append(finding)
        
        # Calculate score
        severity = self._calculate_severity(findings)
        compliance_score = self._calculate_score(findings)
        status = "compliant" if compliance_score > 0.7 else "non_compliant"
        
        report = ComplianceReport(
            audit_id=str(uuid4()),
            system_name=system_name,
            compliance_score=compliance_score,
            status=status,
            findings=findings,
            recommendations=self._generate_recommendations(findings),
            severity=severity,
            ai_act_status=ai_act_status
        )
        
        # Store in database
        await self._store_audit(report)
        
        return report
    
    async def _check_ai_act(self, system_name: str, description: str) -> str:
        """Check compliance with EU AI Act"""
        messages = [
            LLMMessage(role="system", content="""You are an EU AI Act compliance expert.
            Analyze the AI system and determine its risk level under the EU AI Act.
            Return one of: 'minimal', 'limited', 'high', 'unacceptable'"""),
            LLMMessage(role="user", content=f"System: {system_name}\nDescription: {description}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return response.content.strip()
    
    async def _check_regulation(self, system_name: str, description: str, 
                                regulation: str) -> Dict:
        """Check against a specific regulation"""
        messages = [
            LLMMessage(role="system", content=f"""You are a compliance expert for {regulation}.
            Analyze the system and identify any compliance issues.
            Return JSON with: requirement, status, issue, severity"""),
            LLMMessage(role="user", content=f"System: {system_name}\nDescription: {description}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        
        try:
            return json.loads(response.content)
        except:
            return {
                'requirement': regulation,
                'status': 'unknown',
                'issue': 'Unable to parse',
                'severity': 'medium'
            }
    
    def _calculate_score(self, findings: List[Dict]) -> float:
        """Calculate compliance score"""
        if not findings:
            return 1.0
        
        scores = []
        for finding in findings:
            severity = finding.get('severity', 'medium')
            severity_map = {
                'critical': 0.0,
                'high': 0.3,
                'medium': 0.6,
                'low': 0.8,
                'minimal': 0.9
            }
            scores.append(severity_map.get(severity.lower(), 0.5))
        
        return sum(scores) / len(scores)
    
    def _calculate_severity(self, findings: List[Dict]) -> str:
        """Calculate overall severity"""
        severities = [f.get('severity', 'medium').lower() for f in findings]
        if 'critical' in severities:
            return 'critical'
        elif 'high' in severities:
            return 'high'
        elif 'medium' in severities:
            return 'medium'
        return 'low'
    
    def _generate_recommendations(self, findings: List[Dict]) -> List[str]:
        """Generate recommendations from findings"""
        recommendations = []
        for finding in findings:
            if finding.get('status') != 'compliant':
                rec = finding.get('recommendation', f"Address {finding.get('requirement', 'issue')}")
                recommendations.append(rec)
        return recommendations
    
    async def _store_audit(self, report: ComplianceReport):
        """Store audit report in database"""
        try:
            await db.execute("""
                INSERT INTO ai_governance 
                (compliance_check, risk_score, ai_act_status, 
                 regulations_applicable, findings, recommendations, severity)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                report.system_name,
                report.compliance_score,
                report.ai_act_status,
                [],  # regulations
                json.dumps(report.findings),
                json.dumps(report.recommendations),
                report.severity
            )
            logger.info(f"Stored governance audit for {report.system_name}")
        except Exception as e:
            logger.error(f"Store audit error: {e}")