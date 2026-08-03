"""Coursing config + the POS's route into the kitchen.

`send-to-kitchen` is the piece that was missing: the POS printed dockets but
never created a kitchen order, so the KDS hold/fire buttons only ever applied
to tickets a chef typed in by hand. Courses assigned on the POS now become a
real kitchen order with real per-course state.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from database import db
from deps import get_user, require_permission
from models.kitchen_order import KitchenOrder
from services import coursing

router = APIRouter()
log = logging.getLogger(__name__)

# How often the SSE stream re-checks for ticket changes. Short enough to
# feel live at the pass, long enough not to hammer Mongo per connection.
SSE_INTERVAL_SECONDS = float(os.environ.get('COURSING_SSE_INTERVAL', '3'))
# Hard cap on a single stream's lifetime. EventSource reconnects by itself, so
# recycling costs the client nothing and stops abandoned tablets holding a
# connection and a poll loop open indefinitely.
SSE_MAX_SECONDS = float(os.environ.get('COURSING_SSE_MAX_SECONDS', '300'))


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

    # A dine-in table that orders again mid-meal belongs on the ticket the
    # kitchen already has, not on a second one the runner has to reconcile.
    # `newTicket: true` forces a fresh one when that's genuinely wanted.
    table_number = body.get("tableNumber")
    if table_number and not body.get("newTicket") and str(order_type).replace("-", "_") == "dine_in":
        existing = await db.kitchen_orders.find_one(
            {"tableNumber": table_number, "status": {"$nin": ["served", "cancelled"]}},
            {"_id": 0}, sort=[("createdAt", -1)],
        )
        if existing:
            return await add_round(existing["id"], body, user)
    straight = coursing.is_straight_fire(order_type, config, bool(body.get("straightFire")))

    priced = [{**it, "round": 1} for it in coursing.assign_courses(items, config)]
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

    # Courses fired at creation never pass through fire_course_internal, so
    # their side effects have to run here too — otherwise the first course
    # reaches the pass without printing a docket or moving the table's pacing.
    fired_now = sorted(int(k) for k, v in (doc.get("courses") or {}).items()
                       if v.get("status") == "fired")
    for course in fired_now:
        label = next((str(c.get("label")) for c in (config.get("courses") or [])
                      if int(c.get("key")) == course), f"Course {course}")
        try:
            from services import print_routing
            fired_items = [{**it, "courseLabel": label} for it in priced
                           if int(it.get("course") or 1) == course]
            if fired_items:
                await print_routing.route_and_queue(
                    fired_items, order_id=doc["id"], table_number=doc.get("tableNumber"),
                    extra={"course": course, "courseLabel": label, "kitchenOrderId": doc["id"]},
                )
        except Exception as e:
            log.warning("send-to-kitchen: docket print failed for %s: %s", doc["id"], e)
    if fired_now:
        try:
            from services import table_pacing
            # Only the last fired course matters for pacing — a straight-fired
            # order shouldn't walk the table through every stage at once.
            await table_pacing.advance_for_course(doc, fired_now[-1], config)
        except Exception as e:
            log.warning("send-to-kitchen: pacing sync failed for %s: %s", doc["id"], e)
    return doc


async def _apply_due_auto_fires(order: dict, config: dict, actor: str = "auto") -> dict:
    """Fire any held course whose timing rule has come due.

    Evaluated lazily whenever the POS reads its ticket, so timing works
    without depending on a background scheduler being alive.
    """
    due = coursing.due_auto_fires(order, config)
    if not due:
        return order
    from routes.kitchen import fire_course_internal
    for course in due:
        try:
            order = await fire_course_internal(order["id"], course, actor)
        except Exception:
            break
    return order


@router.get("/coursing/orders/open")
async def open_kitchen_orders(tableNumber: Optional[str] = None,
                              transactionId: Optional[str] = None,
                              _: dict = Depends(get_user)):
    """Kitchen orders the POS can still fire courses on.

    This is also how the POS re-attaches after a refresh, or how a second
    tablet picks up a table someone else rang in — without it, fire/hold
    only worked in the tab that happened to create the ticket.
    """
    query: dict = {"status": {"$nin": ["served", "cancelled"]}}
    if tableNumber:
        query["tableNumber"] = tableNumber
    if transactionId:
        query["transactionId"] = transactionId
    rows = await db.kitchen_orders.find(query, {"_id": 0}).to_list(50)
    rows.sort(key=lambda r: r.get("createdAt") or "", reverse=True)

    config = await coursing.get_config()
    return [await _apply_due_auto_fires(r, config) for r in rows]


@router.post("/coursing/orders/{order_id}/add-round")
async def add_round(order_id: str, body: dict, user: dict = Depends(get_user)):
    """Append a later order onto the table's existing ticket.

    A table that orders dessert an hour after mains is still one ticket. The
    new items land as the next round, and any course they introduce starts
    held so the kitchen doesn't fire dessert the moment it's rung in.
    """
    items = body.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="No items to add")

    order = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("status") in ("served", "cancelled"):
        raise HTTPException(status_code=409, detail="Order is already closed")

    config = await coursing.get_config()
    now = _now()
    actor = user.get("name") or user.get("email")
    straight = coursing.is_straight_fire(order.get("orderType"), config, bool(body.get("straightFire")))

    next_round = int(order.get("rounds") or 1) + 1
    new_items = [
        {**it, "round": next_round}
        for it in coursing.assign_courses(items, config)
    ]

    courses = dict(order.get("courses") or {})
    for it in new_items:
        key = str(int(it.get("course") or 1))
        if key in courses:
            continue        # course already on the ticket — keep its state
        if straight:
            courses[key] = {"status": "fired", "heldAt": None, "firedAt": now,
                            "firedBy": actor, "readyAt": None, "servedAt": None}
        else:
            courses[key] = {"status": "held", "heldAt": now, "firedAt": None,
                            "firedBy": None, "readyAt": None, "servedAt": None}

    updated = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"courses": courses, "rounds": next_round,
                  "items": (order.get("items") or []) + new_items,
                  # A closed-out ticket reopening for dessert is active again.
                  "status": "new" if order.get("status") == "ready" else order.get("status", "new")}},
        return_document=True,
    )
    updated.pop("_id", None)

    # Straight-fired additions print immediately; held ones print when fired.
    if straight:
        try:
            from services import print_routing
            await print_routing.route_and_queue(
                new_items, order_id=order_id, table_number=updated.get("tableNumber"),
                extra={"kitchenOrderId": order_id, "round": next_round},
            )
        except Exception:
            pass
    return updated


@router.post("/coursing/settle")
async def settle_table(body: dict, user: dict = Depends(get_user)):
    """Close the table's kitchen ticket and hand the table back.

    Called after payment. Idempotent — a retry finds nothing open and simply
    reports nothing closed.
    """
    from services import ticket_lifecycle
    return await ticket_lifecycle.settle(
        table_number=body.get("tableNumber"),
        transaction_id=body.get("transactionId"),
        order_id=body.get("orderId"),
        actor=user.get("name") or user.get("email"),
        release_table=body.get("releaseTable", True),
    )


@router.post("/coursing/orders/{order_id}/void")
async def void_from_ticket(order_id: str, body: dict,
                           user: dict = Depends(require_permission("comp-void"))):
    """Take items off a live ticket and tell the stations that were cooking them.

    Removing a line on the POS used to leave the kitchen plating a dish nobody
    was paying for. Gated on the same comp/void permission as any other
    give-away, because that is what this is once the food is on.
    """
    from services import print_routing, ticket_lifecycle
    result = await ticket_lifecycle.void_items(
        order_id, body.get("items") or [], actor=user.get("name") or user.get("email"))
    if not result["ok"]:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only print a void docket for items that had already been fired — there's
    # nothing to cancel at a station that never saw the dish.
    order = result.get("order") or {}
    fired = {k for k, v in (order.get("courses") or {}).items()
             if v.get("status") in ("fired", "ready", "served")}
    cancelled = [i for i in result["removed"] if str(int(i.get("course") or 1)) in fired]
    if cancelled and body.get("print", True):
        try:
            await print_routing.route_and_queue(
                [{**i, "notes": "*** VOID — DO NOT MAKE ***"} for i in cancelled],
                order_id=order_id, table_number=order.get("tableNumber"),
                extra={"kitchenOrderId": order_id, "voidDocket": True,
                       "courseLabel": "VOID"},
            )
        except Exception as e:
            log.warning("void: docket print failed for %s: %s", order_id, e)
    return {**result, "voidPrinted": bool(cancelled)}


@router.get("/coursing/stream")
async def coursing_stream(request: Request, tableNumber: Optional[str] = None,
                          token: Optional[str] = None):
    """Server-sent events for a table's live ticket.

    Replaces per-tablet polling: one long-lived connection per POS rather than
    a request every fifteen seconds from every device on the floor. The client
    keeps polling as a fallback for proxies that buffer SSE.

    Auth is resolved by hand because EventSource cannot set an Authorization
    header — the token may arrive as a query parameter instead. It's still the
    same JWT, verified the same way; only the transport differs, and this is
    the one endpoint that accepts it.
    """
    from routes.auth import get_current_user
    try:
        await get_current_user(request)
    except HTTPException:
        if not token:
            raise
        from routes.auth import JWT_ALGORITHM, _secret
        import jwt as _jwt
        try:
            payload = _jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            if not await db.auth_users.find_one({"id": payload["sub"]}):
                raise HTTPException(status_code=401, detail="User not found")
        except _jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def events():
        last = None
        started = asyncio.get_event_loop().time()
        # Named event so the client can tell a real update from the keepalive.
        while True:
            # Bounded lifetime: EventSource reconnects on its own, and a stream
            # that can only end when the client disconnects leaks a connection
            # (and a Mongo poll loop) for every tablet that goes to sleep
            # without closing cleanly.
            if asyncio.get_event_loop().time() - started > SSE_MAX_SECONDS:
                return
            if await request.is_disconnected():
                return
            try:
                config = await coursing.get_config()
                query: dict = {"status": {"$nin": ["served", "cancelled"]}}
                if tableNumber:
                    query["tableNumber"] = tableNumber
                rows = await db.kitchen_orders.find(query, {"_id": 0}).to_list(20)
                rows.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
                rows = [await _apply_due_auto_fires(r, config) for r in rows]
                payload = json.dumps(rows, default=str)
                if payload != last:
                    last = payload
                    yield f"event: tickets\ndata: {payload}\n\n"
                else:
                    yield ": keepalive\n\n"
            except Exception as e:
                log.warning("coursing stream error: %s", e)
                yield ": error\n\n"
            await asyncio.sleep(SSE_INTERVAL_SECONDS)

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # nginx buffers SSE by default, which would defeat the whole point.
        "X-Accel-Buffering": "no",
    })


@router.post("/coursing/auto-fire/tick")
async def auto_fire_tick(_: dict = Depends(get_user)):
    """Evaluate timing rules across every open ticket.

    The POS already evaluates its own ticket on read; this covers tables
    nobody happens to be looking at.
    """
    config = await coursing.get_config()
    if not config.get("enabled") or not config.get("autoFireTiming"):
        return {"checked": 0, "fired": []}
    rows = await db.kitchen_orders.find(
        {"status": {"$nin": ["served", "cancelled"]}}, {"_id": 0}).to_list(200)
    fired = []
    for order in rows:
        due = coursing.due_auto_fires(order, config)
        if not due:
            continue
        from routes.kitchen import fire_course_internal
        for course in due:
            await fire_course_internal(order["id"], course, "auto")
            fired.append({"orderId": order["id"], "course": course})
    return {"checked": len(rows), "fired": fired}
