"""Coursing config + the POS's route into the kitchen.

`send-to-kitchen` is the piece that was missing: the POS printed dockets but
never created a kitchen order, so the KDS hold/fire buttons only ever applied
to tickets a chef typed in by hand. Courses assigned on the POS now become a
real kitchen order with real per-course state.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from database import db
from deps import get_user
from models.kitchen_order import KitchenOrder
from services import coursing

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/coursing/config")
async def get_coursing_config(_: dict = Depends(get_user)):
    """Readable by any logged-in user — the POS needs it to render the cart."""
    return await coursing.get_config()


@router.put("/coursing/config")
async def update_coursing_config(body: dict, user: dict = Depends(get_user)):
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner or manager only")
    patch = coursing.sanitize_config(body)
    patch["updatedAt"] = _now()
    patch["updatedBy"] = user.get("email")
    await db.coursing_config.update_one(
        {"_id": coursing.CONFIG_ID},
        {"$set": {"_id": coursing.CONFIG_ID, **patch}},
        upsert=True,
    )
    return await coursing.get_config()


@router.post("/coursing/preview")
async def preview_courses(body: dict, _: dict = Depends(get_user)):
    """What course would each of these items land on? Used by the POS so the
    client and server can't disagree about assignment."""
    config = await coursing.get_config()
    items = coursing.assign_courses(body.get("items") or [], config)
    return {
        "enabled": bool(config.get("enabled")),
        "straightFire": coursing.is_straight_fire(
            body.get("orderType"), config, bool(body.get("straightFire"))),
        "items": items,
    }


@router.post("/coursing/send-to-kitchen")
async def send_to_kitchen(body: dict, request: Request, user: dict = Depends(get_user)):
    """Turn the POS cart into a kitchen order with per-course fire state."""
    items = body.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="No items to send")

    config = await coursing.get_config()
    order_type = body.get("orderType") or "dine_in"
    straight = coursing.is_straight_fire(order_type, config, bool(body.get("straightFire")))

    priced = coursing.assign_courses(items, config)
    now = _now()
    actor = user.get("name") or user.get("email")

    ua = request.headers.get("user-agent", "")
    order = KitchenOrder(
        transactionId=body.get("transactionId"),
        reservationId=body.get("reservationId"),
        tableNumber=body.get("tableNumber"),
        orderType=str(order_type).replace("-", "_"),
        items=priced,
        notes=body.get("notes"),
        priority=body.get("priority") or "normal",
        serverId=body.get("serverId") or user.get("email"),
        covers=body.get("covers"),
        guestName=body.get("guestName"),
        deviceLabel=request.headers.get("X-Device-Label") or ("Mobile" if "Mobile" in ua else "Web POS"),
        deviceId=request.headers.get("X-Device-Id") or (request.client.host if request.client else "?"),
        createdByName=actor,
        createdByEmail=user.get("email"),
        # Explicit states override the model's auto-seed, which assumes
        # everything is queued.
        courses=coursing.initial_course_states(
            priced, config, order_type, straight, fired_by=actor, now=now),
    )
    doc = order.dict()
    doc["straightFired"] = straight
    await db.kitchen_orders.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/coursing/orders/open")
async def open_kitchen_orders(tableNumber: Optional[str] = None,
                              transactionId: Optional[str] = None,
                              _: dict = Depends(get_user)):
    """Kitchen orders the POS can still fire courses on."""
    query: dict = {"status": {"$nin": ["served", "cancelled"]}}
    if tableNumber:
        query["tableNumber"] = tableNumber
    if transactionId:
        query["transactionId"] = transactionId
    rows = await db.kitchen_orders.find(query, {"_id": 0}).to_list(50)
    rows.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
    return rows
