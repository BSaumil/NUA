"""
AI Concierge — inbound voice reservations.

Twilio hits POST /api/voice/inbound when a customer dials the business's
Twilio number. We greet, gather party-size / date / time / name across up
to MAX_INBOUND_TURNS speech turns, then create a real reservation in
db.reservations with `source="ai_voice"` and hang up gracefully.

Design guardrails:
- If Twilio credentials aren't configured, Twilio never dials the webhook
  in the first place — so this route is only ever reached in a working
  configuration. We validate the request signature anyway.
- Multi-turn state lives in db.voice_calls (same collection as outbound),
  distinguished by direction="inbound". No sticky in-memory state.
- Every guest utterance is stored so staff can review the transcript.
- If we can't extract everything after N turns, we ask staff to call back —
  never invent details.
- Business-hours check refuses politely when the venue is closed.
"""
from __future__ import annotations
import os
import re
import uuid
from datetime import datetime, timezone, timedelta, date, time as dt_time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from database import db
from services import voice_calls as vc


router = APIRouter()

MAX_INBOUND_TURNS = 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return f"INB-{uuid.uuid4().hex[:8].upper()}"


# ─── Extractors ────────────────────────────────────────────────────────────
_WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "a couple": 2, "couple": 2, "few": 3, "several": 4,
}


def extract_party_size(text: str) -> Optional[int]:
    s = (text or "").lower()
    # Digit form: "table for 4", "4 people", "party of six"
    m = re.search(r"\b(\d{1,2})\b", s)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 20:
            return n
    for word, n in _WORD_NUM.items():
        if word in s:
            return n
    return None


def extract_time(text: str) -> Optional[str]:
    """Return an HH:MM 24h string, or None."""
    s = (text or "").lower()
    # "7pm", "7 pm", "7:30pm", "19:00", "half past six"
    m = re.search(r"\b(\d{1,2})[:.]?(\d{2})?\s*(am|pm)?\b", s)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2) or 0)
        ampm = m.group(3)
        if ampm == "pm" and h < 12:
            h += 12
        if ampm == "am" and h == 12:
            h = 0
        if 0 <= h < 24 and 0 <= mm < 60:
            return f"{h:02d}:{mm:02d}"
    if "half past" in s:
        m = re.search(r"half past (\w+)", s)
        if m and m.group(1) in _WORD_NUM:
            h = _WORD_NUM[m.group(1)]
            if "morning" not in s and h < 8:
                h += 12
            return f"{h:02d}:30"
    return None


def extract_date(text: str) -> Optional[str]:
    """Return an ISO YYYY-MM-DD, or None. Handles today/tomorrow/day-of-week."""
    s = (text or "").lower()
    today = datetime.now(timezone.utc).date()
    if "tonight" in s or "today" in s or "this evening" in s:
        return today.isoformat()
    if "tomorrow" in s:
        return (today + timedelta(days=1)).isoformat()
    weekdays = ["monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday"]
    for i, w in enumerate(weekdays):
        if w in s:
            days_ahead = (i - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).isoformat()
    # explicit dd/mm or mm/dd — treat as dd/mm since AU-first
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = today.year
        if m.group(3):
            y = int(m.group(3))
            if y < 100:
                y += 2000
        try:
            return date(y, mo, d).isoformat()
        except Exception:
            return None
    return None


def extract_name(text: str) -> Optional[str]:
    """Simple heuristic — grab the token after 'name is' or after 'this is'."""
    s = (text or "").strip()
    m = re.search(r"(?:name(?:'s)? is|this is|it'?s|i'?m)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                  s, re.IGNORECASE)
    if m:
        return m.group(1).title()
    # If the whole utterance is 1-3 title-case words, treat as a name.
    tokens = re.findall(r"[A-Za-z]+", s)
    if 1 <= len(tokens) <= 3 and all(t.isalpha() for t in tokens):
        return " ".join(t.capitalize() for t in tokens)
    return None


# ─── Business greeting + hours ─────────────────────────────────────────────
async def _greeting_and_context() -> dict:
    """Fetch the business's inbound-call greeting + open hours. Falls back to
    a generic greeting if the business hasn't customised anything."""
    biz = await db.businesses.find_one({}, {"_id": 0}) or {}
    inbound = (biz.get("inboundVoice") or {}) if isinstance(biz.get("inboundVoice"), dict) else {}
    name = biz.get("name") or "our restaurant"
    return {
        "businessId": biz.get("id"),
        "businessName": name,
        "greeting": inbound.get("greeting")
                    or f"Thanks for calling {name}. I can help you book a table — how many people?",
        "closedMessage": inbound.get("closedMessage")
                    or f"Sorry, we're closed right now. Please try again during business hours, or book online at {biz.get('domain') or 'our website'}. Goodbye.",
        "hoursCheckEnabled": bool(inbound.get("hoursCheckEnabled", False)),
        "openHours": inbound.get("openHours") or {},  # {mon:{open,close,closed}, ...}
    }


def _is_open_now(open_hours: dict) -> bool:
    if not open_hours:
        return True
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    now = datetime.now(timezone.utc)  # NOTE: assumes venue TZ ≈ UTC for MVP
    today = open_hours.get(weekdays[now.weekday()], {})
    if today.get("closed"):
        return False
    o, c = today.get("open"), today.get("close")
    if not o or not c:
        return True
    now_hm = now.strftime("%H:%M")
    return o <= now_hm < c


def _next_prompt(state: dict) -> str:
    if not state.get("partySize"):
        return "How many people would you like to book for?"
    if not state.get("date"):
        return "Great. What day were you thinking — tonight, tomorrow, or a specific date?"
    if not state.get("time"):
        return "And what time would suit you?"
    if not state.get("name"):
        return "Perfect. Can I grab a name for the booking?"
    return "Wonderful. I've got you down — let me confirm."


def _confirmation(state: dict) -> str:
    return (f"Booking {state.get('partySize')} people for {state.get('name')} "
            f"on {state.get('date')} at {state.get('time')}. "
            "We'll send a confirmation text if we have your number. Thanks for calling — goodbye.")


async def _load_call(call_id: str) -> Optional[dict]:
    return await db.voice_calls.find_one({"id": call_id}, {"_id": 0})


async def _finalise_booking(state: dict, call_id: str, caller: str) -> Optional[str]:
    """Insert a real reservation. Returns the reservation id, or None on
    validation failure. The reservation is stamped source='ai_voice' so
    staff can see it came from the phone concierge."""
    if not (state.get("partySize") and state.get("date") and state.get("time")):
        return None
    ctx = state.get("_ctx", {}) or {}
    res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
    booking = {
        "id": res_id,
        "businessId": ctx.get("businessId"),
        "date": state["date"],
        "time": state["time"],
        "partySize": int(state["partySize"]),
        "guestName": state.get("name") or "Phone booking",
        "guestPhone": caller,
        "status": "confirmed",
        "source": "ai_voice",
        "callId": call_id,
        "createdAt": _now(),
    }
    await db.reservations.insert_one(booking)
    return res_id


# ─── Twilio validation ─────────────────────────────────────────────────────
def _public_url(request: Request) -> str:
    override = os.environ.get("TWILIO_WEBHOOK_BASE_URL")
    if override:
        return f"{override.rstrip('/')}{request.url.path}"
    return str(request.url)


async def _verify(request: Request, form: dict) -> None:
    signature = request.headers.get("X-Twilio-Signature")
    if not vc.validate_signature(_public_url(request), form, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


# ─── Webhooks ──────────────────────────────────────────────────────────────
@router.post("/voice/inbound")
async def voice_inbound(request: Request):
    """Twilio POSTs here when a customer dials the business number. We create
    a new voice_calls record and hand back the greeting + open Gather."""
    form = dict(await request.form())
    await _verify(request, form)

    caller = form.get("From", "unknown")
    twilio_sid = form.get("CallSid", "")
    ctx = await _greeting_and_context()

    if ctx["hoursCheckEnabled"] and not _is_open_now(ctx["openHours"]):
        twiml = vc.say_and_gather_twiml(say=ctx["closedMessage"], gather_action_url="", end_call=True)
        return Response(content=twiml, media_type="application/xml")

    call_id = _uid()
    doc = {
        "id": call_id,
        "direction": "inbound",
        "purpose": "book_reservation",
        "phone": caller,
        "twilioCallSid": twilio_sid,
        "businessId": ctx["businessId"],
        "openingMessage": ctx["greeting"],
        "transcript": [{"speaker": "nua", "text": ctx["greeting"], "at": _now()}],
        "state": {"_ctx": {"businessId": ctx["businessId"], "businessName": ctx["businessName"]}},
        "turns": 0,
        "status": "in_progress",
        "outcome": None,
        "createdAt": _now(),
    }
    await db.voice_calls.insert_one(dict(doc))

    base = str(request.base_url).rstrip("/")
    gather_url = f"{base}/api/voice/inbound/gather/{call_id}"
    twiml = vc.say_and_gather_twiml(say=ctx["greeting"], gather_action_url=gather_url)
    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/inbound/gather/{call_id}")
async def voice_inbound_gather(call_id: str, request: Request):
    form = dict(await request.form())
    await _verify(request, form)

    call = await _load_call(call_id)
    if not call:
        twiml = vc.say_and_gather_twiml(say="Sorry, something went wrong. Goodbye.", gather_action_url="", end_call=True)
        return Response(content=twiml, media_type="application/xml")

    speech = form.get("SpeechResult", "").strip()
    state = dict(call.get("state") or {})
    turns = int(call.get("turns", 0)) + 1

    # Extract in slot-filling order; each turn may supply multiple slots.
    if not state.get("partySize"):
        v = extract_party_size(speech)
        if v: state["partySize"] = v
    if not state.get("date"):
        v = extract_date(speech)
        if v: state["date"] = v
    if not state.get("time"):
        v = extract_time(speech)
        if v: state["time"] = v
    if not state.get("name"):
        v = extract_name(speech)
        if v: state["name"] = v

    complete = all(state.get(k) for k in ("partySize", "date", "time", "name"))
    exhausted = turns >= MAX_INBOUND_TURNS

    entry_guest = {"speaker": "guest", "text": speech, "at": _now()}

    if complete:
        confirmation = _confirmation(state)
        booking_id = await _finalise_booking(state, call_id, call.get("phone") or "unknown")
        await db.voice_calls.update_one({"id": call_id}, {"$set": {
            "state": state, "turns": turns, "status": "completed",
            "outcome": "booked" if booking_id else "extraction_failed",
            "bookingId": booking_id, "endedAt": _now(),
        }, "$push": {"transcript": {"$each": [entry_guest, {"speaker": "nua", "text": confirmation, "at": _now()}]}}})
        twiml = vc.say_and_gather_twiml(say=confirmation, gather_action_url="", end_call=True)
        return Response(content=twiml, media_type="application/xml")

    if exhausted:
        closing = ("Sorry, I didn't quite catch everything. A team member will call you back "
                   "shortly to finish the booking. Thanks for calling — goodbye.")
        await db.voice_calls.update_one({"id": call_id}, {"$set": {
            "state": state, "turns": turns, "status": "completed",
            "outcome": "handoff", "endedAt": _now(),
        }, "$push": {"transcript": {"$each": [entry_guest, {"speaker": "nua", "text": closing, "at": _now()}]}}})
        twiml = vc.say_and_gather_twiml(say=closing, gather_action_url="", end_call=True)
        return Response(content=twiml, media_type="application/xml")

    prompt = _next_prompt(state)
    base = str(request.base_url).rstrip("/")
    gather_url = f"{base}/api/voice/inbound/gather/{call_id}"
    await db.voice_calls.update_one({"id": call_id}, {"$set": {
        "state": state, "turns": turns,
    }, "$push": {"transcript": {"$each": [entry_guest, {"speaker": "nua", "text": prompt, "at": _now()}]}}})
    twiml = vc.say_and_gather_twiml(say=prompt, gather_action_url=gather_url)
    return Response(content=twiml, media_type="application/xml")


# ─── Owner-facing config + inbox ───────────────────────────────────────────
from routes.auth import get_current_user  # noqa: E402


@router.get("/voice/inbound/status")
async def inbound_status(request: Request):
    user = await get_current_user(request)
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    ctx = await _greeting_and_context()
    inbound_number = os.environ.get("TWILIO_INBOUND_NUMBER")
    return {
        "configured": vc.is_configured() and bool(inbound_number),
        "inboundNumber": inbound_number,
        "greeting": ctx["greeting"],
        "closedMessage": ctx["closedMessage"],
        "hoursCheckEnabled": ctx["hoursCheckEnabled"],
        "openHours": ctx["openHours"],
    }


@router.post("/voice/inbound/config")
async def inbound_config(request: Request):
    user = await get_current_user(request)
    if user.get("role") not in ("owner",):
        raise HTTPException(403, "Owner only")
    body = await request.json()
    patch = {}
    for k in ("greeting", "closedMessage"):
        if k in body:
            patch[f"inboundVoice.{k}"] = body[k]
    if "hoursCheckEnabled" in body:
        patch["inboundVoice.hoursCheckEnabled"] = bool(body["hoursCheckEnabled"])
    if "openHours" in body:
        patch["inboundVoice.openHours"] = body["openHours"]
    if patch:
        await db.businesses.update_one({}, {"$set": patch})
    return {"ok": True, "patch": patch}


@router.get("/voice/inbound/recent")
async def inbound_recent(request: Request, limit: int = 20):
    user = await get_current_user(request)
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    limit = max(1, min(100, limit))
    rows = await db.voice_calls.find(
        {"direction": "inbound"}, {"_id": 0}
    ).sort("createdAt", -1).to_list(limit)
    return rows
