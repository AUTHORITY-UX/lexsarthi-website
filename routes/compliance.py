# routes/compliance.py
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])

COMPLIANCE_FRAMEWORKS = {
    "dpdpa": {"name": "DPDPA (India)", "score": 96, "status": "compliant"},
    "gdpr": {"name": "GDPR (EU)", "score": 94, "status": "compliant"},
    "ccpa": {"name": "CCPA (US)", "score": 92, "status": "compliant"},
    "ai_gov": {"name": "AI Governance", "score": 88, "status": "monitoring"},
    "esg": {"name": "ESG Framework", "score": 85, "status": "monitoring"},
    "iso_27001": {"name": "ISO 27001", "score": 90, "status": "compliant"},
    "iso_42001": {"name": "ISO 42001 (AI)", "score": 87, "status": "monitoring"},
    "soc2": {"name": "SOC 2", "score": 85, "status": "monitoring"},
    "hipaa": {"name": "HIPAA", "score": 80, "status": "partial"},
    "pci_dss": {"name": "PCI DSS", "score": 82, "status": "partial"}
}

@router.get("/dashboard")
async def get_compliance_dashboard():
    """Get global compliance dashboard"""
    overall = sum(f["score"] for f in COMPLIANCE_FRAMEWORKS.values()) / len(COMPLIANCE_FRAMEWORKS)
    return {
        "status": "ok",
        "overall_score": round(overall, 1),
        "frameworks": COMPLIANCE_FRAMEWORKS,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/{framework_id}")
async def get_framework(framework_id: str):
    """Get specific framework details"""
    if framework_id not in COMPLIANCE_FRAMEWORKS:
        raise HTTPException(404, "Framework not found")
    return COMPLIANCE_FRAMEWORKS[framework_id]  