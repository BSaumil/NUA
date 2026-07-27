from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from datetime import datetime, timezone
from database import db
from deps import get_user
from models.kitchen_order import KitchenOrder, KitchenOrderCreate

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def _clear_overnight_tickets() -> int:
    """A ticket left in new/preparing/ready from a previous day (chef forgot
    to mark it served, or it was superseded by close of service) shouldn't
    carry over and clutter tomorrow's board. Runs on every board read rather
    than a scheduled job, so it's correct even if the server restarted
    overnight or the scheduler missed a beat — the board self-heals the
    moment anyone opens it."""
    today = _today_str()
    stale = await db.kitchen_orders.find(
        {"status": {"$in": ["new", "preparing", "ready"]}},
        {"_id": 0, "id": 1, "createdAt": 1},
    ).to_list(500)
    stale_ids = [o["id"] for o in stale if (o.get("createdAt") or "")[:10] < today]
    if stale_ids:
        await db.kitchen_orders.update_many(
            {"id": {"$in": stale_ids}},
            {"$set": {"status": "cancelled", "cancelledAt": _now(),
                      "autoCleared": True, "notes": "Auto-cleared overnight — not served by close of previous day"}},
        )
    return len(stale_ids)


# ============ KITCHEN DISPLAY (KDS) API ============
@router.get("/kitchen/orders")
async def get_kitchen_orders(status: Optional[str] = None):
    await _clear_overnight_tickets()
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = {"$in": ["new", "preparing", "ready"]}
    orders = await db.kitchen_orders.find(query, {"_id": 0}).sort("createdAt", 1).to_list(100)
    return orders


@router.get("/kitchen/avg-order-time")
async def get_avg_order_time(_: dict = Depends(get_user)):
    """Average minutes from order fired to ready, across today's completed
    tickets — a rough live gauge for the chef to judge pace mid-service."""
    today = _today_str()
    orders = await db.kitchen_orders.find(
        {"createdAt": {"$gte": today}, "readyAt": {"$ne": None}},
        {"_id": 0, "createdAt": 1, "readyAt": 1},
    ).to_list(1000)
    durations = []
    for o in orders:
        try:
            created = datetime.fromisoformat(o["createdAt"])
            ready = datetime.fromisoformat(o["readyAt"])
            mins = (ready - created).total_seconds() / 60
            if mins >= 0:
                durations.append(mins)
        except (ValueError, TypeError, KeyError):
            continue
    avg = round(sum(durations) / len(durations), 1) if durations else 0
    return {"avgOrderMinutes": avg, "ordersCompletedToday": len(durations)}


@router.post("/kitchen/orders")
async def create_kitchen_order(order: KitchenOrderCreate, request: Request, user: dict = Depends(get_user)):
    """Create a kitchen ticket. Auto-enriches docket fields from the request context:
    who created (user), device (X-Device-Label header or User-Agent), covers
    (from reservation if reservationId present), guest name (from reservation).
    """
    order_dict = order.dict()

    # Actor metadata — always set unless already provided (e.g. by table QR flow)
    order_dict["createdByEmail"] = order_dict.get("createdByEmail") or user.get("email")
    order_dict["createdByName"] = order_dict.get("createdByName") or user.get("name") or user.get("email")

    # Device metadata — prefer explicit header, fall back to UA
    hdr_dev = request.headers.get("X-Device-Label") or request.headers.get("x-device-label")
    hdr_devid = request.headers.get("X-Device-Id") or request.headers.get("x-device-id")
    ua = request.headers.get("user-agent", "")
    if not order_dict.get("deviceLabel"):
        order_dict["deviceLabel"] = hdr_dev or ("Mobile" if "Mobile" in ua else "Web POS")
    if not order_dict.get("deviceId"):
        order_dict["deviceId"] = hdr_devid or (request.client.host if request.client else "?")

    # Enrich from reservation if present
    if order_dict.get("reservationId") and (not order_dict.get("covers") or not order_dict.get("guestName")):
        res = await db.reservations.find_one({"id": order_dict["reservationId"]}, {"_id": 0})
        if res:
            order_dict["covers"] = order_dict.get("covers") or res.get("partySize") or res.get("guests")
            order_dict["guestName"] = order_dict.get("guestName") or res.get("customerName") or res.get("guestName")

    order_obj = KitchenOrder(**order_dict)
    await db.kitchen_orders.insert_one(order_obj.dict())
    return order_obj.dict()


@router.post("/kitchen/orders/{order_id}/start")
async def start_kitchen_order(order_id: str, _: dict = Depends(get_user)):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "preparing", "startedAt": _now()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result


@router.post("/kitchen/orders/{order_id}/ready")
async def mark_order_ready(order_id: str, user: dict = Depends(get_user)):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "ready", "readyAt": _now()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    try:
        from services import notification_service as ns
        server_email = result.get("serverId") or result.get("createdByEmail")
        if server_email:
            await ns.send(email=server_email, kind="kitchen", severity="info",
                            title=f"Table {result.get('tableNumber') or '?'} — order ready",
                            body=f"All items are ready to run for order {order_id[:8]}.",
                            link=f"/kitchen?order={order_id}",
                            data={"orderId": order_id, "tableNumber": result.get("tableNumber")})
        else:
            await ns.send(role="server", topic="kitchen.ready", kind="kitchen",
                            title=f"Table {result.get('tableNumber') or '?'} — order ready",
                            body=f"Order {order_id[:8]} is ready to run.",
                            link=f"/kitchen?order={order_id}",
                            data={"orderId": order_id})
    except Exception:
        pass
    return result


@router.post("/kitchen/orders/{order_id}/served")
async def mark_order_served(order_id: str, _: dict = Depends(get_user)):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "served", "servedAt": _now()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result


@router.post("/kitchen/orders/{order_id}/cancel")
async def cancel_kitchen_order(order_id: str, _: dict = Depends(get_user)):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "cancelled", "cancelledAt": _now()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result


# ─── Course lifecycle — HOLD / FIRE / SERVE per course ────────────────────
@router.post("/kitchen/orders/{order_id}/hold-course/{course}")
async def hold_course(order_id: str, course: int, _: dict = Depends(get_user)):
    """Explicitly hold a course — it will NOT fire automatically."""
    key = f"courses.{course}"
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {f"{key}.status": "held", f"{key}.heldAt": _now(),
                    f"{key}.firedAt": None, f"{key}.firedBy": None}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result


@router.post("/kitchen/orders/{order_id}/fire-course/{course}")
async def fire_course(order_id: str, course: int, user: dict = Depends(get_user)):
    """Fire a specific course — sets courseX.firedAt, courseX.firedBy and
    updates the order's currentCourse pointer. Held courses can be fired
    with this call too (the hold is lifted)."""
    key = f"courses.{course}"
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {
            "currentCourse": course,
            f"{key}.status": "fired",
            f"{key}.firedAt": _now(),
            f"{key}.firedBy": user.get("name") or user.get("email"),
            f"{key}.heldAt": None,
        }},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    try:
        from services import notification_service as ns
        server_email = result.get("serverId") or result.get("createdByEmail")
        course_label = {1: "Starter", 2: "Main", 3: "Dessert", 4: "Coffee"}.get(course, f"Course {course}")
        if server_email:
            await ns.send(email=server_email, kind="kitchen", severity="info",
                            title=f"Table {result.get('tableNumber') or '?'} — {course_label} fired",
                            body=f"Kitchen just fired {course_label} for your order.",
                            link=f"/kitchen?order={order_id}",
                            data={"orderId": order_id, "course": course})
        else:
            await ns.send(role="server", topic="kitchen.fire", kind="kitchen",
                            title=f"Table {result.get('tableNumber') or '?'} — {course_label} fired",
                            body=f"Kitchen just fired {course_label}.",
                            link=f"/kitchen?order={order_id}",
                            data={"orderId": order_id, "course": course})
    except Exception:
        pass
    return result


@router.post("/kitchen/orders/{order_id}/serve-course/{course}")
async def serve_course(order_id: str, course: int, _: dict = Depends(get_user)):
    key = f"courses.{course}"
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {f"{key}.status": "served", f"{key}.servedAt": _now()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result


@router.post("/kitchen/orders/{order_id}/priority")
async def set_order_priority(order_id: str, priority: str = "rush", _: dict = Depends(get_user)):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"priority": priority}}, return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result


# ─── Owner-configurable docket display ────────────────────────────────────
DEFAULT_DOCKET_CONFIG = {
    "showStaffName": True,
    "showDevice": True,
    "showCovers": True,
    "showFireTime": True,
    "showTable": True,
    "showGuestName": True,
    "showElapsedTimer": True,
    "showItemNotes": True,
    "showOrderNotes": True,
    "showModifiers": True,
    "fontSize": "medium",           # small | medium | large
    "colourByCourse": True,
    "warnMinutes": 15,              # elapsed threshold for amber warning
    "criticalMinutes": 25,          # elapsed threshold for red critical
}


@router.get("/kitchen/docket-config")
async def get_docket_config(_: dict = Depends(get_user)):
    row = await db.kitchen_docket_config.find_one({"_id": "singleton"}, {"_id": 0})
    if not row:
        row = dict(DEFAULT_DOCKET_CONFIG)
        await db.kitchen_docket_config.insert_one({"_id": "singleton", **row})
    return row


@router.put("/kitchen/docket-config")
async def update_docket_config(body: dict, user: dict = Depends(get_user)):
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner or manager only")
    allowed = set(DEFAULT_DOCKET_CONFIG.keys())
    patch = {k: v for k, v in body.items() if k in allowed}
    patch["updatedAt"] = _now()
    patch["updatedBy"] = user.get("email")
    await db.kitchen_docket_config.update_one(
        {"_id": "singleton"},
        {"$set": {"_id": "singleton", **patch}},
        upsert=True,
    )
    row = await db.kitchen_docket_config.find_one({"_id": "singleton"}, {"_id": 0})
    return row


# ============ PREP MANAGEMENT API ============
@router.get("/kitchen/prep-list")
async def get_prep_list():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    reservations = await db.reservations.find({"date": today}, {"_id": 0}).to_list(100)
    total_covers = sum(r.get("partySize", 0) for r in reservations)

    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    all_txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)

    product_popularity = {}
    for txn in all_txns:
        for item in txn.get("items", []):
            pid = item.get("productId", "")
            product_popularity[pid] = product_popularity.get(pid, 0) + item.get("quantity", 0)

    total_qty = sum(product_popularity.values()) or 1

    prep_items = []
    for p in products:
        pop_qty = product_popularity.get(p["id"], 0)
        popularity_pct = (pop_qty / total_qty) * 100
        est_qty = max(1, int((pop_qty / max(len(all_txns), 1)) * max(total_covers, 10)))
        prep_items.append({
            "productId": p["id"], "name": p["name"], "category": p.get("category", "Other"),
            "currentStock": p.get("stock", 0), "estimatedNeeded": est_qty,
            "popularityPct": round(popularity_pct, 1), "prepStatus": "pending",
        })

    prep_items.sort(key=lambda x: x["estimatedNeeded"], reverse=True)
    return {"date": today, "expectedCovers": total_covers, "totalReservations": len(reservations), "prepItems": prep_items[:20]}
