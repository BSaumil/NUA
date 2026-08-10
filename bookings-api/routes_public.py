"""Public, unauthenticated surface — the other half of partner
provisioning. /admin/partners requires the platform admin key by design
(only the platform operator should mint keys directly); this is how an
outside integrator gets in front of that gate at all: submit an
application, wait for a human to approve it.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from auth import rate_limiter
from database import db
from models import PartnerApplication, PartnerApplicationCreate

router = APIRouter(prefix="/public")

APPLICATION_RATE_LIMIT = 5  # per IP per minute — this is a form, not an API


@router.post("/partner-applications")
async def submit_application(body: PartnerApplicationCreate, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"partner-app:{client_ip}", APPLICATION_RATE_LIMIT):
        raise HTTPException(status_code=429, detail="Too many applications from this address — try again shortly")

    if not body.company_name.strip() or not body.contact_email.strip():
        raise HTTPException(status_code=400, detail="company_name and contact_email are required")

    app_obj = PartnerApplication(
        **body.dict(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await db.partner_applications.insert_one(app_obj.dict())
    # No API key is ever issued here — that only happens once a human
    # reviews and approves the application via /admin/partner-applications.
    return {"id": app_obj.id, "status": "pending"}
