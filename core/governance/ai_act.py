"""
core/governance/ai_act.py - Latest AI Laws Integration
EU AI Act, India's DPDPA, US AI Bill of Rights, Global Regulations
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from core.llm import LLMMessage, get_router
from core.db import db

logger = logging.getLogger(__name__)


@dataclass
class AIActCompliance:
    """AI Act compliance status"""
    regulation_name: str
    jurisdiction: str
    status: str  # 'compliant', 'non_compliant', 'partial', 'unknown'
    risk_level: str  # 'minimal', 'limited', 'high', 'unacceptable'
    score: float
    findings: List[Dict]
    requirements_met: List[str]
    requirements_missing: List[str]
    recommendations: List[str]
    last_checked: datetime = field(default_factory=datetime.now)


class EUAIAct:
    """EU AI Act compliance checker"""
    
    REQUIREMENTS = {
        'risk_classification': {
            'description': 'Classify AI system risk level',
            'critical': True
        },
        'transparency': {
            'description': 'Provide transparency about AI system capabilities',
            'critical': True
        },
        'human_oversight': {
            'description': 'Ensure human oversight of AI decisions',
            'critical': True
        },
        'data_governance': {
            'description': 'Implement proper data governance',
            'critical': True
        },
        'technical_documentation': {
            'description': 'Maintain technical documentation',
            'critical': False
        },
        'accuracy_robustness': {
            'description': 'Ensure accuracy and robustness',
            'critical': False
        },
        'cybersecurity': {
            'description': 'Implement cybersecurity measures',
            'critical': False
        },
        'post_market_monitoring': {
            'description': 'Monitor after market deployment',
            'critical': False
        }
    }
    
    @classmethod
    async def check_compliance(cls, system_name: str, system_description: str) -> AIActCompliance:
        """Check system against EU AI Act requirements"""
        
        findings = []
        requirements_met = []
        requirements_missing = []
        
        router = get_router()
        
        for req_name, req_info in cls.REQUIREMENTS.items():
            messages = [
                LLMMessage(role="system", content=f"""You are an EU AI Act compliance expert.
                Check if the AI system meets the requirement: {req_info['description']}
                Return JSON: {{"met": true/false, "evidence": "...", "notes": "..."}}"""),
                LLMMessage(role="user", content=f"System: {system_name}\nDescription: {system_description}")
            ]
            
            try:
                response = await router.chat(messages, complexity="complex")
                result = json.loads(response.content)
                
                if result.get('met', False):
                    requirements_met.append(req_name)
                else:
                    requirements_missing.append(req_name)
                    
                findings.append({
                    'requirement': req_name,
                    'met': result.get('met', False),
                    'evidence': result.get('evidence', ''),
                    'notes': result.get('notes', ''),
                    'critical': req_info['critical']
                })
            except Exception as e:
                logger.error(f"Error checking {req_name}: {e}")
                requirements_missing.append(req_name)
        
        # Determine compliance
        critical_met = all(f['met'] for f in findings if f['critical'])
        total_met = len(requirements_met) / len(cls.REQUIREMENTS)
        
        if critical_met and total_met >= 0.8:
            status = 'compliant'
        elif critical_met:
            status = 'partial'
        else:
            status = 'non_compliant'
        
        # Determine risk level
        risk_level = await cls._assess_risk(system_description)
        
        # Generate recommendations
        recommendations = [
            f"Address missing requirements: {', '.join(requirements_missing)}"
        ]
        
        return AIActCompliance(
            regulation_name='EU AI Act',
            jurisdiction='European Union',
            status=status,
            risk_level=risk_level,
            score=total_met,
            findings=findings,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            recommendations=recommendations
        )
    
    @classmethod
    async def _assess_risk(cls, description: str) -> str:
        """Assess risk level of the AI system"""
        description_lower = description.lower()
        
        high_risk_keywords = ['biometric', 'critical infrastructure', 'healthcare', 
                             'employment', 'education', 'justice', 'law enforcement']
        limited_risk_keywords = ['chatbot', 'recommendation', 'document analysis']
        
        if any(kw in description_lower for kw in high_risk_keywords):
            return 'high'
        elif any(kw in description_lower for kw in limited_risk_keywords):
            return 'limited'
        else:
            return 'minimal'


class IndiaDPDPA:
    """India's Digital Personal Data Protection Act compliance"""
    
    PRINCIPLES = [
        'lawful_processing',
        'purpose_limitation',
        'data_minimization',
        'accuracy',
        'storage_limitation',
        'security_safeguards',
        'transparency',
        'accountability'
    ]
    
    @classmethod
    async def check_compliance(cls, system_name: str, system_description: str) -> AIActCompliance:
        """Check system against DPDPA requirements"""
        
        findings = []
        requirements_met = []
        requirements_missing = []
        
        router = get_router()
        
        for principle in cls.PRINCIPLES:
            messages = [
                LLMMessage(role="system", content=f"""You are an India DPDPA compliance expert.
                Check if the AI system follows the principle: {principle}
                Return JSON: {{"met": true/false, "evidence": "...", "notes": "..."}}"""),
                LLMMessage(role="user", content=f"System: {system_name}\nDescription: {system_description}")
            ]
            
            try:
                response = await router.chat(messages, complexity="complex")
                result = json.loads(response.content)
                
                if result.get('met', False):
                    requirements_met.append(principle)
                else:
                    requirements_missing.append(principle)
                    
                findings.append({
                    'principle': principle,
                    'met': result.get('met', False),
                    'evidence': result.get('evidence', ''),
                    'notes': result.get('notes', '')
                })
            except Exception as e:
                logger.error(f"Error checking {principle}: {e}")
                requirements_missing.append(principle)
        
        total_met = len(requirements_met) / len(cls.PRINCIPLES)
        
        if total_met >= 0.8:
            status = 'compliant'
        elif total_met >= 0.5:
            status = 'partial'
        else:
            status = 'non_compliant'
        
        return AIActCompliance(
            regulation_name='DPDPA (India)',
            jurisdiction='India',
            status=status,
            risk_level='medium',
            score=total_met,
            findings=findings,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            recommendations=[f"Address: {', '.join(requirements_missing)}"]
        )


class GlobalRegulatoryTracker:
    """Track global AI regulations"""
    
    REGULATIONS = {
        'eu_ai_act': {
            'name': 'EU AI Act',
            'jurisdiction': 'EU',
            'effective_date': '2024-08-01',
            'risk_levels': ['unacceptable', 'high', 'limited', 'minimal']
        },
        'india_dpdpa': {
            'name': 'Digital Personal Data Protection Act',
            'jurisdiction': 'India',
            'effective_date': '2023-08-11',
            'risk_levels': ['high', 'medium', 'low']
        },
        'us_ai_bill_of_rights': {
            'name': 'US AI Bill of Rights',
            'jurisdiction': 'USA',
            'effective_date': '2022-10-04',
            'principles': ['safe', 'effective', 'transparent', 'fair', 'accountable']
        },
        'china_ai_law': {
            'name': 'China AI Law (Draft)',
            'jurisdiction': 'China',
            'effective_date': '2023-07-01',
            'requirements': ['content review', 'security', 'algorithm registry']
        },
        'uk_ai_regulation': {
            'name': 'UK AI Regulation',
            'jurisdiction': 'UK',
            'effective_date': '2024-01-01',
            'principles': ['safety', 'security', 'transparency', 'fairness']
        },
        'canada_ai_data_act': {
            'name': 'Canada AI and Data Act',
            'jurisdiction': 'Canada',
            'effective_date': '2024-06-01',
            'requirements': ['risk assessment', 'transparency', 'oversight']
        }
    }
    
    @classmethod
    async def get_latest_regulations(cls) -> Dict:
        """Get all latest regulations with status"""
        regulations = {}
        
        for key, reg in cls.REGULATIONS.items():
            # Check if this regulation applies to the system
            reg_info = {
                'name': reg['name'],
                'jurisdiction': reg['jurisdiction'],
                'effective_date': reg.get('effective_date', 'Unknown'),
                'status': 'active',
                'requirements': reg.get('requirements', []) or reg.get('principles', [])
            }
            
            # Check compliance status from database
            try:
                result = await db.fetchone("""
                    SELECT COUNT(*) as count FROM ai_governance 
                    WHERE regulations_applicable @> ARRAY[$1]
                """, reg['name'])
                reg_info['systems_compliant'] = result['count'] if result else 0
            except:
                reg_info['systems_compliant'] = 0
            
            regulations[key] = reg_info
        
        return regulations
    
    @classmethod
    async def track_global_compliance(cls, system_name: str, system_description: str) -> Dict:
        """Track compliance across all global regulations"""
        results = {}
        
        # EU AI Act
        eu_result = await EUAIAct.check_compliance(system_name, system_description)
        results['eu_ai_act'] = {
            'status': eu_result.status,
            'score': eu_result.score,
            'risk_level': eu_result.risk_level,
            'findings': eu_result.findings
        }
        
        # India DPDPA
        india_result = await IndiaDPDPA.check_compliance(system_name, system_description)
        results['india_dpdpa'] = {
            'status': india_result.status,
            'score': india_result.score,
            'findings': india_result.findings
        }
        
        # Check other regulations
        for reg_key in ['us_ai_bill_of_rights', 'uk_ai_regulation']:
            # Simulate checking other regulations
            results[reg_key] = {
                'status': 'unknown',
                'score': 0.0,
                'message': 'Compliance check not implemented'
            }
        
        return results