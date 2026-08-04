"""
core/agents/verification.py - Three-agent verification pipeline
Researcher → Auditor → Adjudicator
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core.llm import LLMMessage, get_router
from core.verifiers import verify_all

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of the verification pipeline"""
    researcher_findings: str = ""
    auditor_findings: str = ""
    adjudicator_verdict: str = ""
    confidence: float = 0.0
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    verified: bool = False


class ResearcherAgent:
    """First agent: Researches and analyzes the query"""
    
    def __init__(self):
        self.router = get_router()
    
    async def research(self, query: str, context: str = "") -> str:
        """Research the query thoroughly"""
        system = """You are a Legal Researcher Agent. Your task is to:
        1. Analyze the legal query thoroughly
        2. Identify relevant statutes and case law
        3. Extract key legal principles
        4. Provide comprehensive research findings
        
        Be thorough and cite specific legal sources."""

        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=f"Query: {query}\n\nContext: {context}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return response.content


class AuditorAgent:
    """Second agent: Audits the researcher's findings"""
    
    def __init__(self):
        self.router = get_router()
    
    async def audit(self, query: str, research_findings: str) -> Dict:
        """Audit the researcher's findings"""
        system = """You are a Legal Auditor Agent. Your task is to:
        1. Review the researcher's findings critically
        2. Identify any errors, gaps, or biases
        3. Verify citations and legal principles
        4. Rate the quality of the research
        
        Return your audit as JSON with:
        - quality_score: 0-100
        - issues: list of issues found
        - strengths: list of strengths
        - recommendations: improvements needed"""

        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=f"Query: {query}\n\nResearch: {research_findings}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        
        try:
            # Try to parse as JSON
            return json.loads(response.content)
        except:
            return {
                "quality_score": 70,
                "issues": ["Unable to parse audit"],
                "strengths": [],
                "recommendations": ["Please try again with more specific query"]
            }


class AdjudicatorAgent:
    """Third agent: Makes final determination"""
    
    def __init__(self):
        self.router = get_router()
    
    async def adjudicate(self, query: str, research: str, audit: Dict) -> VerificationResult:
        """Make final determination based on research and audit"""
        system = """You are a Legal Adjudicator Agent. Your task is to:
        1. Review the research findings and audit results
        2. Make a final determination on the legal question
        3. Provide a clear, well-reasoned verdict
        4. Rate your confidence in the determination
        
        Be balanced and objective."""

        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=f"""Query: {query}

Research Findings:
{research}

Audit Results:
{json.dumps(audit, indent=2)}

Please provide your final determination.""" )
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        
        result = VerificationResult()
        result.adjudicator_verdict = response.content
        result.confidence = self._extract_confidence(response.content)
        
        # Extract issues and recommendations
        issues = re.findall(r'Issue[:\s]+([^\n]+)', response.content)
        recommendations = re.findall(r'Recommendation[:\s]+([^\n]+)', response.content)
        
        result.issues_found = issues[:5]
        result.recommendations = recommendations[:5]
        result.verified = True
        
        # Run verifiers for extra validation
        verification = verify_all(query, response.content)
        result.verified = verification.get('avg_score', 0) > 0.5
        
        return result
    
    def _extract_confidence(self, text: str) -> float:
        """Extract confidence score from text"""
        patterns = [
            r'confidence[:\s]+(\d+)',
            r'Confidence[:\s]+(\d+)',
            r'(\d+)%\s+confidence',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1)) / 100
        
        return 0.5


class VerificationPipeline:
    """Complete three-agent verification pipeline"""
    
    def __init__(self):
        self.researcher = ResearcherAgent()
        self.auditor = AuditorAgent()
        self.adjudicator = AdjudicatorAgent()
    
    async def verify(self, query: str, context: str = "", 
                     auto_correct: bool = True) -> VerificationResult:
        """Run the complete verification pipeline"""
        
        # Step 1: Research
        logger.info("🔍 Researcher Agent: Starting research...")
        research = await self.researcher.research(query, context)
        
        # Step 2: Audit
        logger.info("📋 Auditor Agent: Auditing research...")
        audit = await self.auditor.audit(query, research)
        
        # Step 3: Adjudicate
        logger.info("⚖️ Adjudicator Agent: Making final determination...")
        result = await self.adjudicator.adjudicate(query, research, audit)
        
        # Store the complete result
        result.researcher_findings = research
        result.auditor_findings = json.dumps(audit)
        
        # Self-correction: If confidence is low, run again with feedback
        if auto_correct and result.confidence < 0.7:
            logger.info("🔄 Self-correction loop: Confidence low, re-running...")
            # Run again with the issues identified
            correction_prompt = f"""
            Previous attempt had the following issues:
            {', '.join(result.issues_found)}
            
            Please provide an improved response addressing these issues.
            """
            
            result = await self.verify(query, correction_prompt, auto_correct=False)
        
        return result