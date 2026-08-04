"""
core/governance/audit.py - Complete AI Governance Module
Compliance auditing, risk classification, regulatory intelligence
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from core.llm import LLMMessage, get_router
from core.db import db
from core.governance.ai_act import EUAIAct, IndiaDPDPA, GlobalRegulatoryTracker

logger = logging.getLogger(__name__)


@dataclass
class SystemProfile:
    """AI System Profile for governance"""
    system_id: str
    name: str
    description: str
    type: str  # 'chatbot', 'research', 'analysis', 'generation'
    jurisdiction: str
    data_processed: List[str]
    risk_level: str
    compliance_score: float
    regulations: List[str]
    audit_history: List[Dict]
    last_audit: datetime


class AIGovernanceAuditor:
    """Complete AI governance auditing system"""
    
    def __init__(self):
        self.router = get_router()
        self.regulatory_tracker = GlobalRegulatoryTracker()
    
    async def audit_ai_system(self, system_name: str, system_description: str) -> Dict:
        """Complete AI system audit"""
        
        # 1. Compliance Check
        compliance = await self._check_compliance(system_name, system_description)
        
        # 2. Risk Assessment
        risk = await self._assess_risk(system_name, system_description)
        
        # 3. Regulatory Intelligence
        regulations = await self.regulatory_tracker.track_global_compliance(
            system_name, system_description
        )
        
        # 4. Generate Recommendations
        recommendations = await self._generate_recommendations(
            system_name, compliance, risk, regulations
        )
        
        # 5. Store Audit
        audit_id = await self._store_audit(
            system_name, system_description, compliance, risk, regulations, recommendations
        )
        
        return {
            'audit_id': audit_id,
            'system_name': system_name,
            'compliance': compliance,
            'risk_assessment': risk,
            'regulations': regulations,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _check_compliance(self, system_name: str, system_description: str) -> Dict:
        """Check compliance across all regulations"""
        
        results = {}
        
        # EU AI Act
        eu_act = await EUAIAct.check_compliance(system_name, system_description)
        results['eu_ai_act'] = {
            'status': eu_act.status,
            'score': eu_act.score,
            'risk_level': eu_act.risk_level,
            'requirements_met': eu_act.requirements_met,
            'requirements_missing': eu_act.requirements_missing
        }
        
        # India DPDPA
        dpdpa = await IndiaDPDPA.check_compliance(system_name, system_description)
        results['india_dpdpa'] = {
            'status': dpdpa.status,
            'score': dpdpa.score,
            'requirements_met': dpdpa.requirements_met,
            'requirements_missing': dpdpa.requirements_missing
        }
        
        # Calculate overall compliance score
        scores = [r['score'] for r in results.values() if 'score' in r]
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'overall_score': overall_score,
            'status': 'compliant' if overall_score > 0.7 else 'non_compliant',
            'details': results
        }
    
    async def _assess_risk(self, system_name: str, system_description: str) -> Dict:
        """Assess AI system risk"""
        
        messages = [
            LLMMessage(role="system", content="""Assess the risk level of this AI system.
            Return JSON with:
            - risk_level: 'critical', 'high', 'medium', 'low'
            - score: 0-100
            - factors: list of risk factors
            - mitigation: list of mitigation strategies"""),
            LLMMessage(role="user", content=f"System: {system_name}\nDescription: {system_description}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        
        try:
            return json.loads(response.content)
        except:
            return {
                'risk_level': 'medium',
                'score': 50,
                'factors': ['Could not assess fully'],
                'mitigation': ['Full assessment required']
            }
    
    async def _generate_recommendations(self, system_name: str, compliance: Dict, 
                                        risk: Dict, regulations: Dict) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Compliance recommendations
        if compliance.get('status') == 'non_compliant':
            for reg, details in compliance.get('details', {}).items():
                missing = details.get('requirements_missing', [])
                if missing:
                    recommendations.append(f"For {reg}: Address {', '.join(missing)}")
        
        # Risk recommendations
        risk_level = risk.get('risk_level', 'medium')
        if risk_level in ['critical', 'high']:
            recommendations.append(f"Implement immediate risk mitigation: {', '.join(risk.get('mitigation', []))}")
        
        # Regulatory recommendations
        if regulations:
            for reg, status in regulations.items():
                if status.get('status') == 'non_compliant':
                    recommendations.append(f"Check {reg} compliance")
        
        return recommendations
    
    async def _store_audit(self, system_name: str, system_description: str,
                           compliance: Dict, risk: Dict, regulations: Dict,
                           recommendations: List[str]) -> str:
        """Store audit results in database"""
        
        try:
            result = await db.execute("""
                INSERT INTO ai_governance 
                (compliance_check, risk_score, ai_act_status, 
                 regulations_applicable, findings, recommendations, severity)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """,
                system_name,
                compliance.get('overall_score', 0.0),
                compliance.get('status', 'unknown'),
                list(regulations.keys()),
                json.dumps(compliance),
                json.dumps(recommendations),
                risk.get('risk_level', 'medium')
            )
            
            logger.info(f"Stored AI governance audit for {system_name}")
            return result
            
        except Exception as e:
            logger.error(f"Store audit error: {e}")
            return ""
    
    async def get_governance_dashboard(self) -> Dict:
        """Get complete governance dashboard"""
        
        try:
            # Get all audits
            audits = await db.fetchall("""
                SELECT * FROM ai_governance 
                ORDER BY created_at DESC 
                LIMIT 50
            """)
            
            # Get regulatory intelligence
            regulations = await GlobalRegulatoryTracker.get_latest_regulations()
            
            # Calculate statistics
            total_audits = len(audits)
            compliant = sum(1 for a in audits if a.get('ai_act_status') == 'compliant')
            non_compliant = total_audits - compliant
            
            return {
                'total_audits': total_audits,
                'compliant': compliant,
                'non_compliant': non_compliant,
                'compliance_rate': compliant / total_audits if total_audits > 0 else 0,
                'regulations': regulations,
                'recent_audits': [dict(a) for a in audits[:10]]
            }
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return {
                'total_audits': 0,
                'compliant': 0,
                'non_compliant': 0,
                'compliance_rate': 0,
                'regulations': {},
                'recent_audits': []
            }