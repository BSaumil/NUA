from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
import logging
from datetime import datetime, timezone
from database import db
from deps import get_user, require_permission
from models.kitchen_order import KitchenOrder, KitchenOrderCreate

router = APIRouter()
log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _course_label(course: int, coursing_config: dict) -> str:
    """The venue's own name for a course, falling back to a generic one."""
    for c in (coursing_config or {}).get("courses") or []:
        try:
            if int(c.get("key")) == int(course):
                return str(c.get("label") or f"Course {course}")
        except (TypeError, ValueError):
            continue
    return {1: "Starter", 2: "Main", 3: "Dessert", 4: "Coffee"}.get(course, f"Course {course}")


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


async def _avg_order_minutes_today() -> tuple[float, int]:
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
    return avg, len(durations)


@router.get("/kitchen/avg-order-time")
async def get_avg_order_time(_: dict = Depends(get_user)):
    """Average minutes from order fired to ready, across today's completed
    tickets — a rough live gauge for the chef to judge pace mid-service."""
    avg, count = await _avg_order_minutes_today()
    return {"avgOrderMinutes": avg, "ordersCompletedToday": count}


async def _active_queue_depth() -> tuple[int, int]:
    """(orders actually cooking, orders whose every course is held).

    A ticket sitting on held courses isn't work the kitchen is doing — a table
    holding its mains for another twenty minutes shouldn't inflate the wait
    quoted to someone at the counter. Tickets with no course map at all count
    as active, which keeps every pre-coursing ticket behaving as before.
    """
    rows = await db.kitchen_orders.find(
        {"status": {"$in": ["new", "preparing"]}}, {"_id": 0, "courses": 1}).to_list(500)
    active = held = 0
    for o in rows:
        courses = o.get("courses") or {}
        if not courses:
            active += 1
            continue
        statuses = [(v or {}).get("status") for v in courses.values()]
        if any(s in ("queued", "fired", "ready") for s in statuses):
            active += 1
        elif all(s == "held" for s in statuses):
            held += 1
    return active, held


@router.get("/kitchen/next-order-eta")
async def get_next_order_eta(_: dict = Depends(get_user)):
    """A quick, honest ballpark for "how long for a takeaway right now?" when
    a customer asks at the counter — today's average ticket time, plus a
    couple of minutes for every order already ahead of it in the queue.
    Not a precise promise, just a fast answer for the person at the till."""
    avg, completed_count = await _avg_order_minutes_today()
    queue_depth, held_depth = await _active_queue_depth()
    baseline = avg if completed_count > 0 else 12.0  # no data yet today — a sane starting guess
    minutes_per_order_ahead = 2.5
    estimated = round(baseline + queue_depth * minutes_per_order_ahead, 1)
    return {
        "avgOrderMinutes": avg, "ordersCompletedToday": completed_count,
        "queueDepth": queue_depth,
        # Surfaced so the counter can see the difference between "the kitchen
        # is slammed" and "there are tables holding their mains".
        "heldOrders": held_depth,
        "estimatedWaitMinutes": estimated,
    }


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
async def hold_course(order_id: str, course: int,
                      user: dict = Depends(require_permission("fire-course"))):
    """Explicitly hold a course — it will NOT fire automatically."""
    from services import course_events
    prior = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0, "courses": 1})
    prev_state = course_events.course_state(prior or {}, course)

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
    await course_events.record_transition(order_id, course, "held",
                                          user.get("name") or user.get("email"), prev_state)
    return result


async def fire_course_internal(order_id: str, course: int, actor: str) -> dict:
    """Fire a course and run every side effect: print the station dockets for
    that course, advance the table's pacing, notify the server.

    Shared by the endpoint below and by the timing rules that fire a course
    automatically, so an auto-fire behaves exactly like a server tapping Fire
    rather than quietly skipping the printing.
    """
    from services import course_events
    prior = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0, "courses": 1})
    prev_state = course_events.course_state(prior or {}, course)

    key = f"courses.{course}"
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {
            "currentCourse": course,
            f"{key}.status": "fired",
            f"{key}.firedAt": _now(),
            f"{key}.firedBy": actor,
            f"{key}.heldAt": None,
        }},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)

    from services import coursing as _coursing
    cfg = await _coursing.get_config()
    label = _course_label(course, cfg)

    await course_events.record_transition(order_id, course, "fired", actor, prev_state)
    await course_events.audit(
        "course_fired", result, course=course, actor=actor,
        memo=f"{label} fired for table {result.get('tableNumber') or '?'}"
             + (" (automatic — timing rule)" if actor == "auto" else ""),
        after={"course": course, "label": label, "firedBy": actor},
    )

    # A station prints when the course is fired, not when the order is rung
    # up — that's the whole point of holding a course. Items carry their
    # course so the docket can label the block.
    try:
        from services import print_routing
        if cfg.get("enabled"):
            fired_items = [
                {**it, "course": course, "courseLabel": label}
                for it in (result.get("items") or [])
                if int(it.get("course") or 1) == int(course)
            ]
            if fired_items:
                await print_routing.route_and_queue(
                    fired_items,
                    order_id=result.get("id"),
                    table_number=result.get("tableNumber"),
                    extra={"course": course, "courseLabel": label,
                           "kitchenOrderId": result.get("id")},
                )
    except Exception as e:
        log.warning("fire-course: docket print failed for %s: %s", order_id, e)

    # Keep the floor plan's pacing in step with what the kitchen just did.
    try:
        from services import table_pacing
        await table_pacing.advance_for_course(result, course, cfg)
    except Exception as e:
        log.warning("fire-course: pacing sync failed for %s: %s", order_id, e)

    try:
        from services import notification_service as ns
        server_email = result.get("serverId") or result.get("createdByEmail")
        title = f"Table {result.get('tableNumber') or '?'} — {label} fired"
        if server_email:
            await ns.send(email=server_email, kind="kitchen", severity="info", title=title,
                          body=f"Kitchen just fired {label} for your order.",
                          link=f"/kitchen?order={order_id}",
                          data={"orderId": order_id, "course": course})
        else:
            await ns.send(role="server", topic="kitchen.fire", kind="kitchen", title=title,
                          body=f"Kitchen just fired {label}.",
                          link=f"/kitchen?order={order_id}",
                          data={"orderId": order_id, "course": course})
    except Exception:
        pass
    return result


@router.post("/kitchen/orders/{order_id}/fire-course/{course}")
async def fire_course(order_id: str, course: int, user: dict = Depends(require_permission("fire-course"))):
    """Fire a specific course — lifts any hold, prints that course's dockets,
    and advances the table's pacing."""
    return await fire_course_internal(order_id, course, user.get("name") or user.get("email"))


@router.post("/kitchen/orders/{order_id}/ready-course/{course}")
async def ready_course(order_id: str, course: int, user: dict = Depends(require_permission("fire-course"))):
    """Mark a single course ready at the pass.

    Order-level `ready` already existed, but with coursing the server needs to
    know that *this* course is up — otherwise they're back to watching the
    pass, which is what coursing was supposed to stop.
    """
    key = f"courses.{course}"
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {f"{key}.status": "ready", f"{key}.readyAt": _now()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    from services import course_events
    await course_events.record_transition(order_id, course, "ready",
                                          user.get("name") or user.get("email"), "fired")
    try:
        from services import coursing as _coursing, notification_service as ns
        label = _course_label(course, await _coursing.get_config())
        server_email = result.get("serverId") or result.get("createdByEmail")
        title = f"Table {result.get('tableNumber') or '?'} — {label} ready"
        body = f"{label} is up at the pass."
        if server_email:
            await ns.send(email=server_email, kind="kitchen", severity="info", title=title,
                          body=body, link=f"/pos?order={order_id}",
                          data={"orderId": order_id, "course": course, "event": "ready"})
        else:
            await ns.send(role="server", topic="kitchen.ready", kind="kitchen", title=title,
                          body=body, link=f"/pos?order={order_id}",
                          data={"orderId": order_id, "course": course, "event": "ready"})
    except Exception as e:
        log.warning("ready-course: notify failed for %s: %s", order_id, e)
    return result


@router.post("/kitchen/orders/{order_id}/serve-course/{course}")
async def serve_course(order_id: str, course: int, user: dict = Depends(require_permission("fire-course"))):
    from services import course_events
    prior = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0, "courses": 1})
    prev_state = course_events.course_state(prior or {}, course)

    key = f"courses.{course}"
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {f"{key}.status": "served", f"{key}.servedAt": _now()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    await course_events.record_transition(order_id, course, "served",
                                          user.get("name") or user.get("email"), prev_state)
    return result


@router.get("/kitchen/orders/{order_id}/timings")
async def course_timings(order_id: str, _: dict = Depends(get_user)):
    """Per-course timings derived from the ticket's history trail.

    `atPassMinutes` is the number that actually costs a venue: food sitting
    under a lamp between the kitchen calling it ready and someone running it.
    """
    from services import course_events
    order = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "orderId": order_id,
        "tableNumber": order.get("tableNumber"),
        "courses": course_events.summarise(order),
        "history": order.get("courseHistory") or [],
    }


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
