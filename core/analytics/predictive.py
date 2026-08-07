"""
core/analytics/predictive.py - Predictive Analytics for Legal Outcomes
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, field

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Prediction result structure"""
    outcome: str
    confidence: float
    factors: List[Dict]
    similar_cases: List[Dict]
    recommendations: List[str]
    timeline: str
    risk_level: str


class PredictiveAnalytics:
    """Predictive analytics for legal outcomes"""
    
    def __init__(self):
        self.router = get_router()
        self.confidence_threshold = 0.6
    
    async def predict_case_outcome(self, case_details: Dict) -> PredictionResult:
        """Predict likely case outcome"""
        
        # 1. Analyze case factors
        factors = await self._analyze_factors(case_details)
        
        # 2. Find similar cases
        similar_cases = await self._find_similar_cases(case_details)
        
        # 3. Generate prediction
        prediction = await self._generate_prediction(case_details, factors, similar_cases)
        
        # 4. Calculate confidence
        confidence = await self._calculate_confidence(factors, similar_cases)
        
        # 5. Generate recommendations
        recommendations = await self._generate_recommendations(prediction, factors)
        
        return PredictionResult(
            outcome=prediction,
            confidence=confidence,
            factors=factors,
            similar_cases=similar_cases[:5],
            recommendations=recommendations,
            timeline=self._estimate_timeline(case_details),
            risk_level=self._assess_risk(confidence, factors)
        )
    
    async def _analyze_factors(self, case_details: Dict) -> List[Dict]:
        """Analyze case factors"""
        messages = [
            LLMMessage(role="system", content="""Analyze these case details and identify key factors.
            Return JSON array of factors with: name, impact (high/medium/low), description"""),
            LLMMessage(role="user", content=json.dumps(case_details, indent=2))
        ]
        
        try:
            response = await self.router.chat(messages, complexity="complex")
            return json.loads(response.content)
        except:
            return [
                {'name': 'Jurisdiction', 'impact': 'high', 'description': 'Court jurisdiction'},
                {'name': 'Evidence', 'impact': 'high', 'description': 'Quality of evidence'},
                {'name': 'Precedent', 'impact': 'medium', 'description': 'Similar cases'}
            ]
    
    async def _find_similar_cases(self, case_details: Dict) -> List[Dict]:
        """Find similar cases from database"""
        try:
            query = case_details.get('query', '')
            rows = await db.fetchall("""
                SELECT id, citation, title, decision, score
                FROM case_law 
                WHERE search_vector @@ plainto_tsquery('english', $1)
                ORDER BY score DESC
                LIMIT 10
            """, query)
            return [dict(row) for row in rows] if rows else []
        except:
            return []
    
    async def _generate_prediction(self, case_details: Dict, factors: List[Dict], similar: List[Dict]) -> str:
        """Generate prediction using AI"""
        context = f"""
        Case Details: {json.dumps(case_details, indent=2)}
        Key Factors: {json.dumps(factors, indent=2)}
        Similar Cases: {len(similar)} found
        """
        
        messages = [
            LLMMessage(role="system", content="""Predict the likely outcome of this legal case.
            Return one of: plaintiff_wins, defendant_wins, settlement, dismissal, appeal"""),
            LLMMessage(role="user", content=context)
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        outcomes = ['plaintiff_wins', 'defendant_wins', 'settlement', 'dismissal', 'appeal']
        prediction = response.content.strip().lower()
        
        for outcome in outcomes:
            if outcome in prediction:
                return outcome
        return 'settlement'
    
    async def _calculate_confidence(self, factors: List[Dict], similar: List[Dict]) -> float:
        """Calculate confidence score"""
        base_confidence = 0.5
        
        # Adjust based on factors
        high_impact = sum(1 for f in factors if f.get('impact') == 'high')
        confidence = base_confidence + (high_impact * 0.05)
        
        # Adjust based on similar cases
        if similar:
            confidence += min(len(similar) * 0.02, 0.2)
        
        return min(confidence, 0.95)
    
    async def _generate_recommendations(self, prediction: str, factors: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        messages = [
            LLMMessage(role="system", content=f"""Generate 3-5 actionable recommendations based on:
            Predicted outcome: {prediction}
            Key factors: {json.dumps(factors, indent=2)}
            Return as JSON array of strings."""),
            LLMMessage(role="user", content="Generate recommendations")
        ]
        
        try:
            response = await self.router.chat(messages, complexity="medium")
            return json.loads(response.content)
        except:
            return [
                "Strengthen evidence presentation",
                "Consider settlement options",
                "Review similar case outcomes",
                "Prepare for appeals"
            ]
    
    def _estimate_timeline(self, case_details: Dict) -> str:
        """Estimate case timeline"""
        case_type = case_details.get('case_type', 'civil')
        timelines = {
            'civil': '6-12 months',
            'criminal': '12-24 months',
            'family': '3-6 months',
            'corporate': '8-18 months',
            'constitutional': '12-36 months'
        }
        return timelines.get(case_type, '6-18 months')
    
    def _assess_risk(self, confidence: float, factors: List[Dict]) -> str:
        """Assess risk level"""
        if confidence > 0.8:
            return 'low'
        elif confidence > 0.6:
            return 'medium'
        else:
            return 'high'


predictive_analytics = PredictiveAnalytics()