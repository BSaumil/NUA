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

    # Offline replay can re-send a request whose *response* was lost, not the
    # request — the ticket exists, the till just never heard about it. A
    # client-generated key makes the replay return that ticket instead of
    # creating the table's order twice.
    client_key = body.get("clientKey")
    if client_key:
        existing = await db.kitchen_orders.find_one({"clientKey": client_key}, {"_id": 0})
        if existing:
            return existing

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
    doc["clientKey"] = client_key
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


def _round_update(order: dict, courses: dict, next_round: int,
                  new_items: list, client_key: Optional[str]) -> dict:
    """The Mongo update for appending a round.

    Built here rather than inline because an empty `$addToSet: {}` is invalid
    — the operator has to be omitted entirely when there's no key to record.
    """
    update = {"$set": {
        "courses": courses,
        "rounds": next_round,
        "items": (order.get("items") or []) + new_items,
        # A closed-out ticket reopening for dessert is active again.
        "status": "new" if order.get("status") == "ready" else order.get("status", "new"),
    }}
    if client_key:
        update["$addToSet"] = {"roundKeys": client_key}
    return update


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

    # Same reasoning as send-to-kitchen: a replayed round must not double the
    # table's food.
    client_key = body.get("clientKey")
    if client_key:
        dup = await db.kitchen_orders.find_one(
            {"id": order_id, "roundKeys": client_key}, {"_id": 0})
        if dup:
            return dup

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
        _round_update(order, courses, next_round, new_items, client_key),
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
        seats=body.get("seats"),
    )


@router.post("/coursing/move-ticket")
async def move_ticket(body: dict, user: dict = Depends(get_user)):
    """Follow a moved or merged table with its kitchen ticket."""
    from services import ticket_lifecycle
    src, dst = body.get("fromTable"), body.get("toTable")
    if not src or not dst:
        raise HTTPException(status_code=400, detail="fromTable and toTable are required")
    if str(src) == str(dst):
        return {"movedOrders": [], "from": src, "to": dst}
    return await ticket_lifecycle.move_ticket(
        str(src), str(dst), actor=user.get("name") or user.get("email"))


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
    # Comps and voids are the classic shrinkage vector, so this belongs in the
    # audit log Settings already surfaces — not only on the ticket it deleted
    # items from.
    try:
        from services import course_events
        await course_events.audit(
            "course_void", order, actor=user.get("name") or user.get("email"),
            memo=("Voided " + ", ".join(f"{i['quantity']}x {i.get('productName')}"
                                        for i in result["removed"])
                  + f" from table {order.get('tableNumber') or '?'}"),
            severity="notice", after={"removed": result["removed"],
                                      "printed": bool(cancelled)},
        )
    except Exception as e:
        log.warning("void: audit write failed for %s: %s", order_id, e)
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


@router.get("/print-targets")
async def list_print_targets(_: dict = Depends(get_user)):
    """Network addresses configured for station printers."""
    return await db.printer_targets.find({}, {"_id": 0}).to_list(50)


@router.put("/print-targets/{printer}")
async def set_print_target(printer: str, body: dict, user: dict = Depends(get_user)):
    """Point a station printer at a real device (ESC/POS over TCP)."""
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner or manager only")
    from services import escpos
    doc = {
        "printer": printer,
        "host": (body.get("host") or "").strip() or None,
        "port": int(body.get("port") or 9100),
        "enabled": bool(body.get("enabled", True)),
        # Per-device because they genuinely vary: 58mm paper is 32 columns,
        # non-Latin markets need another codepage, and cut support is the
        # least consistent part of ESC/POS across manufacturers.
        "width": max(24, min(96, int(body.get("width") or escpos.DEFAULT_WIDTH))),
        "codepage": str(body.get("codepage") or escpos.DEFAULT_CODEPAGE),
        "cut": (body.get("cut") if body.get("cut") in escpos.CUT_STYLES else "partial"),
        "updatedAt": _now(),
        "updatedBy": user.get("email"),
    }
    await db.printer_targets.update_one({"printer": printer}, {"$set": doc}, upsert=True)
    return doc


@router.get("/print-targets/health")
async def print_targets_health(_: dict = Depends(get_user)):
    """Is every configured station printer reachable right now?

    The pre-service check: a printer that's off fails one docket at a time in
    the middle of service, which is the worst moment to find out.
    """
    from services import escpos
    rows = await db.printer_targets.find({}, {"_id": 0}).to_list(50)
    out = []
    for row in rows:
        if not row.get("host") or not row.get("enabled", True):
            out.append({**row, "reachable": None, "reason": "no device configured"})
            continue
        out.append({**row, **await escpos.ping(row["host"], row.get("port", 9100))})
    return {"printers": out,
            "allReachable": all(p.get("reachable") for p in out) if out else None,
            "checkedAt": _now()}


@router.post("/print-targets/{printer}/test")
async def print_target_test(printer: str, user: dict = Depends(get_user)):
    """Send a self-test page so the width, codepage and cut can be eyeballed."""
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner or manager only")
    from services import escpos
    target = await escpos.printer_target(printer)
    if not target:
        raise HTTPException(status_code=404, detail=f"No device configured for '{printer}'")
    payload = escpos.self_test(
        printer,
        width=target.get("width") or escpos.DEFAULT_WIDTH,
        codepage=target.get("codepage") or escpos.DEFAULT_CODEPAGE,
        cut=target.get("cut") or "partial",
    )
    result = await escpos.send(target["host"], payload, port=target.get("port", 9100))
    return {"sent": bool(result.get("ok")), "bytes": len(payload), **result}


@router.post("/print-jobs/{job_id}/escpos")
async def print_job_escpos(job_id: str, body: dict = None, _: dict = Depends(get_user)):
    """Render a queued docket as ESC/POS and send it to the station printer.

    Returns `sent: False` with a reason when no device is configured or it
    can't be reached — the caller then falls back to the browser print path,
    so a station without an IP still prints exactly as it does today.
    """
    from services import escpos
    job = await db.print_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")

    target = await escpos.printer_target(job.get("printer"))
    payload = escpos.render(
        job,
        width=(target or {}).get("width") or escpos.DEFAULT_WIDTH,
        codepage=(target or {}).get("codepage") or escpos.DEFAULT_CODEPAGE,
        cut=(target or {}).get("cut") or "partial",
    )
    if not target or not target.get("enabled", True):
        return {"sent": False, "reason": "no device configured for this printer",
                "bytes": len(payload), "printer": job.get("printer")}

    result = await escpos.send(target["host"], payload, port=target.get("port", 9100))
    if result.get("ok"):
        await db.print_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "printed", "printedAt": _now(),
                      "printedVia": f"escpos://{target['host']}:{target.get('port', 9100)}"}},
        )
        return {"sent": True, **result}
    return {"sent": False, "reason": result.get("error"), "bytes": len(payload)}


@router.get("/coursing/analytics")
async def coursing_analytics(days: int = 7, _: dict = Depends(get_user)):
    """Where time actually goes, per course and per station.

    `atPass` is the number worth acting on: minutes between the kitchen
    calling a course ready and someone running it. Everything here comes from
    the durable course-event trail, so it survives a ticket's own capped
    history window.
    """
    from datetime import timedelta
    from services import course_events

    since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(90, days)))).isoformat()
    events = await db.course_events.find({"at": {"$gte": since}}, {"_id": 0}).to_list(20000)
    if not events:
        return {"days": days, "sampled": 0, "courses": {}, "byDay": {}, "slowestAtPass": []}

    by_order: dict = {}
    for e in events:
        by_order.setdefault(e["orderId"], []).append(e)

    config = await coursing.get_config()
    labels = {str(c["key"]): c.get("label") for c in (config.get("courses") or [])}

    buckets: dict = {}
    per_day: dict = {}
    slowest: list = []
    for order_id, rows in by_order.items():
        rows.sort(key=lambda r: r.get("at") or "")
        for course in {int(r["course"]) for r in rows}:
            held = course_events.minutes_between(rows, course, "held", "fired")
            cook = course_events.minutes_between(rows, course, "fired", "ready")
            at_pass = course_events.minutes_between(rows, course, "ready", "served")
            key = str(course)
            b = buckets.setdefault(key, {"label": labels.get(key, f"Course {course}"),
                                         "held": [], "cook": [], "atPass": []})
            if held is not None: b["held"].append(held)
            if cook is not None: b["cook"].append(cook)
            if at_pass is not None:
                b["atPass"].append(at_pass)
                slowest.append({"orderId": order_id, "course": course,
                                "label": labels.get(key, f"Course {course}"),
                                "atPassMinutes": at_pass})
            day = (rows[0].get("at") or "")[:10]
            d = per_day.setdefault(day, {"atPass": [], "cook": []})
            if at_pass is not None: d["atPass"].append(at_pass)
            if cook is not None: d["cook"].append(cook)

    def _stats(values):
        if not values:
            return {"count": 0, "avg": None, "worst": None}
        return {"count": len(values),
                "avg": round(sum(values) / len(values), 1),
                "worst": round(max(values), 1)}

    return {
        "days": days,
        "sampled": len(by_order),
        "courses": {k: {"label": v["label"], "held": _stats(v["held"]),
                        "cook": _stats(v["cook"]), "atPass": _stats(v["atPass"])}
                    for k, v in sorted(buckets.items(), key=lambda kv: int(kv[0]))},
        "byDay": {d: {"atPass": _stats(v["atPass"]), "cook": _stats(v["cook"])}
                  for d, v in sorted(per_day.items())},
        # The specific tickets to go and look at, not just an average.
        "slowestAtPass": sorted(slowest, key=lambda r: -r["atPassMinutes"])[:10],
    }


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
