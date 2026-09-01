"""
Law Firm Frontend API Routes
Handles contact forms, consultation requests, and inquiries
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Frontend"])

# ─── MODELS ───

class ConsultationRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    issueType: str
    description: str = None

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    phone: str = None
    service: str = None
    message: str

class ConsultationResponse(BaseModel):
    id: str
    status: str = "pending"
    created_at: datetime
    message: str = "Consultation request received"

# ─── EMAIL NOTIFICATION FUNCTION ───

async def send_consultation_email(data: ConsultationRequest):
    """Send email notification for consultation request"""
    try:
        # TODO: Integrate with email service (SendGrid, etc.)
        subject = f"New Consultation Request from {data.name}"
        body = f"""
        New consultation request received:
        
        Name: {data.name}
        Email: {data.email}
        Phone: {data.phone}
        Issue Type: {data.issueType}
        Description: {data.description or 'Not provided'}
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        logger.info(f"Consultation request from {data.email}: {data.issueType}")
        
        # Send to admin
        # await send_email_async(
        #     to=settings.ADMIN_EMAIL,
        #     subject=subject,
        #     body=body
        # )
        
        # Send confirmation to user
        # await send_email_async(
        #     to=data.email,
        #     subject="Consultation Request Received",
        #     body=f"Thank you {data.name}! We've received your request and will contact you within 24 hours."
        # )
    except Exception as e:
        logger.error(f"Error sending email: {e}")

# ─── ENDPOINTS ───

@router.post("/consultation", response_model=ConsultationResponse)
async def submit_consultation(
    request: ConsultationRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a free consultation request
    
    - **name**: Full name (required)
    - **email**: Email address (required)
    - **phone**: Phone number (required)
    - **issueType**: Type of legal issue (required)
    - **description**: Detailed description (optional)
    """
    
    try:
        # Generate unique ID
        consultation_id = f"cons_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(request.email) % 10000}"
        
        # Store in database
        # await db.execute("""
        #     INSERT INTO consultations (id, name, email, phone, issue_type, description, status, created_at)
        #     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        # """, consultation_id, request.name, request.email, request.phone, request.issueType, request.description, "pending", datetime.now())
        
        # Send email in background
        background_tasks.add_task(send_consultation_email, request)
        
        logger.info(f"Consultation request created: {consultation_id}")
        
        return ConsultationResponse(
            id=consultation_id,
            status="pending",
            created_at=datetime.now(),
            message=f"Consultation request received. We'll contact you at {request.phone} within 24 hours."
        )
    
    except Exception as e:
        logger.error(f"Error processing consultation: {e}")
        raise HTTPException(status_code=500, detail="Error processing consultation request")

@router.post("/contact")
async def submit_contact(
    message: ContactMessage,
    background_tasks: BackgroundTasks
):
    """
    Submit a contact form message
    
    - **name**: Full name (required)
    - **email**: Email address (required)
    - **phone**: Phone number (optional)
    - **service**: Service type (optional)
    - **message**: Message content (required)
    """
    
    try:
        contact_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(message.email) % 10000}"
        
        # Store in database
        # await db.execute("""
        #     INSERT INTO contact_messages (id, name, email, phone, service, message, status, created_at)
        #     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        # """, contact_id, message.name, message.email, message.phone, message.service, message.message, "new", datetime.now())
        
        # Log message
        logger.info(f"Contact message from {message.email} regarding {message.service or 'general inquiry'}")
        
        return {
            "status": "success",
            "message": "Thank you! We've received your message and will respond within 24 hours.",
            "id": contact_id
        }
    
    except Exception as e:
        logger.error(f"Error processing contact message: {e}")
        raise HTTPException(status_code=500, detail="Error processing message")

@router.get("/services")
async def get_services():
    """Get list of all legal services"""
    
    services = [
        {
            "id": "constitutional",
            "name": "Constitutional Law",
            "icon": "🏛️",
            "description": "Expert advice on fundamental rights, constitutional amendments, and judicial review.",
            "tags": ["Rights", "Amendments", "Federalism"],
            "agents": 22
        },
        {
            "id": "contract",
            "name": "Contract Law",
            "icon": "📋",
            "description": "Commercial contracts, M&A agreements, employment contracts, and negotiations.",
            "tags": ["Commercial", "M&A", "Employment"],
            "agents": 22
        },
        {
            "id": "criminal",
            "name": "Criminal Law",
            "icon": "🛡️",
            "description": "White collar crime defense, cybercrime, bail, and appeal proceedings.",
            "tags": ["Defense", "Cybercrime", "Bail"],
            "agents": 22
        },
        {
            "id": "corporate",
            "name": "Corporate Law",
            "icon": "🏢",
            "description": "Company formation, mergers & acquisitions, governance, and compliance.",
            "tags": ["M&A", "Governance", "Compliance"],
            "agents": 22
        },
        {
            "id": "ip",
            "name": "Intellectual Property",
            "icon": "💡",
            "description": "Patents, trademarks, copyrights, and IP litigation expertise.",
            "tags": ["Patents", "Trademarks", "Copyright"],
            "agents": 20
        },
        {
            "id": "tax",
            "name": "Tax Law",
            "icon": "💰",
            "description": "Direct tax, indirect tax (GST), international taxation, and tax planning.",
            "tags": ["Direct Tax", "GST", "International"],
            "agents": 20
        },
        {
            "id": "family",
            "name": "Family Law",
            "icon": "👨‍👩‍👧‍👦",
            "description": "Divorce, child custody, inheritance, maintenance, and succession planning.",
            "tags": ["Divorce", "Custody", "Inheritance"],
            "agents": 20
        },
        {
            "id": "labour",
            "name": "Labour Law",
            "icon": "⚙️",
            "description": "Employment disputes, industrial relations, workplace harassment, and compliance.",
            "tags": ["Employment", "Disputes", "Compliance"],
            "agents": 20
        },
        {
            "id": "realestate",
            "name": "Real Estate Law",
            "icon": "🏠",
            "description": "Property transactions, RERA compliance, land acquisition, and tenant rights.",
            "tags": ["RERA", "Property", "Tenant Rights"],
            "agents": 20
        }
    ]
    
    return {"services": services, "total": len(services)}

@router.get("/consultations/{consultation_id}")
async def get_consultation(consultation_id: str):
    """Get consultation request status"""
    
    try:
        # Fetch from database
        # result = await db.fetch_one("""
        #     SELECT id, name, email, status, created_at, updated_at FROM consultations WHERE id = $1
        # """, consultation_id)
        
        # For now, return mock data
        return {
            "id": consultation_id,
            "status": "pending",
            "message": "Your consultation request is being processed. An agent will contact you shortly."
        }
    
    except Exception as e:
        logger.error(f"Error fetching consultation: {e}")
        raise HTTPException(status_code=404, detail="Consultation not found")

@router.get("/info")
async def get_info():
    """Get general platform info"""
    
    return {
        "name": "Advocacy & Law Firm",
        "version": "1.0",
        "domain": "www.advocacyalawfrim.in",
        "features": {
            "agents": 530,
            "legal_documents": "32.5M",
            "specializations": 12,
            "api_endpoints": "114+",
            "availability": "24/7"
        },
        "contact": {
            "phone": "+91 88000-00000",
            "email": "hello@advocacyalawfrim.in",
            "website": "https://www.advocacyalawfrim.in/"
        }
    }
