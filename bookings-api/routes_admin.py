"""Platform-operator surface: partner provisioning and usage reports.
Guarded by the deploy-time admin key — partners never see these routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import generate_key, hash_key, require_platform_admin
from database import db
from models import Partner, PartnerCreate
from usage import monthly_report

router = APIRouter(prefix="/admin", dependencies=[Depends(require_platform_admin)])


@router.post("/partners")
async def create_partner(body: PartnerCreate):
    """Provision a partner. The raw live + sandbox keys are returned ONCE,
    here — only their hashes are stored."""
    live_key = generate_key(test=False)
    test_key = generate_key(test=True)
    partner = Partner(
        **body.dict(),
        api_key_hash=hash_key(live_key),
        test_key_hash=hash_key(test_key),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await db.partners.insert_one(partner.dict())
    out = partner.dict()
    out.pop("api_key_hash"); out.pop("test_key_hash")
    out["api_key"] = live_key
    out["test_api_key"] = test_key
    return out


@router.get("/partners")
async def list_partners():
    rows = await db.partners.find({}, {"_id": 0, "api_key_hash": 0, "test_key_hash": 0}).to_list(500)
    return rows


@router.post("/partners/{partner_id}/rotate-key")
async def rotate_key(partner_id: str, test: bool = False):
    partner = await db.partners.find_one({"id": partner_id}, {"_id": 0})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    new_key = generate_key(test=test)
    field = "test_key_hash" if test else "api_key_hash"
    await db.partners.update_one({"id": partner_id}, {"$set": {field: hash_key(new_key)}})
    return {"partner_id": partner_id, "test": test, "api_key": new_key}


@router.get("/usage/monthly")
async def usage_monthly(month: str):
    """month=YYYY-MM — the wholesale invoicing feed."""
    return {"month": month, "partners": await monthly_report(month)}
