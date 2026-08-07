"""
NUA Cross-Module Rules Engine — REST endpoints.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from database import db
from deps import get_user, require_owner_or_manager
from services import rules_engine as re_svc
import uuid
import os
import json
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rules")


# ═════════════════════════════════════════════════════════════════════════
# CRUD
# ═════════════════════════════════════════════════════════════════════════
@router.get("")
async def list_rules(active: Optional[bool] = None, module: Optional[str] = None, _: dict = Depends(get_user)):
    q: Dict[str, Any] = {}
    if active is not None:
        q["active"] = active
    rows = await db.rules.find(q, {"_id": 0}).sort("priority", -1).to_list(500)
    if module:
        # filter by event catalog module tag
        rows = [r for r in rows if re_svc.EVENT_CATALOG.get(r.get("triggerEvent"), {}).get("module") == module]
    return rows


@router.get("/catalog")
async def catalog(_: dict = Depends(get_user)):
    return {
        "events": re_svc.event_catalog_meta(),
        "actions": re_svc.action_library_meta(),
        "operators": ["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "starts_with", "exists"],
    }


@router.get("/stats")
async def stats(_: dict = Depends(get_user)):
    total = await db.rules.count_documents({})
    active = await db.rules.count_documents({"active": True})
    executions_ct = await db.rule_executions.count_documents({})
    events_ct = await db.rule_events.count_documents({})
    top = await db.rules.find({}, {"_id": 0, "id": 1, "name": 1, "triggerCount": 1, "lastTriggeredAt": 1}).sort("triggerCount", -1).limit(5).to_list(5)
    all_rules = await db.rules.find({}, {"_id": 0, "triggerEvent": 1, "active": 1}).to_list(1000)
    by_module: Dict[str, int] = {}
    for r in all_rules:
        m = re_svc.EVENT_CATALOG.get(r.get("triggerEvent"), {}).get("module", "unknown")
        by_module[m] = by_module.get(m, 0) + 1
    return {
        "totalRules": total, "activeRules": active,
        "totalExecutions": executions_ct, "totalEvents": events_ct,
        "topRules": top, "byModule": by_module,
    }


@router.post("")
async def create_rule(body: dict, user: dict = Depends(require_owner_or_manager)):
    if not body.get("name") or not body.get("triggerEvent"):
        raise HTTPException(400, "name and triggerEvent are required")
    if body["triggerEvent"] not in re_svc.EVENT_CATALOG:
        raise HTTPException(400, f"Unknown event: {body['triggerEvent']}")
    for a in body.get("actions") or []:
        if a.get("type") not in re_svc.ACTION_LIBRARY:
            raise HTTPException(400, f"Unknown action: {a.get('type')}")
    doc = {
        "id": str(uuid.uuid4()),
        "name": body["name"],
        "description": body.get("description"),
        "triggerEvent": body["triggerEvent"],
        "conditions": body.get("conditions") or {},
        "actions": body.get("actions") or [],
        "active": bool(body.get("active", True)),
        "priority": int(body.get("priority") or 0),
        "aiGenerated": bool(body.get("aiGenerated", False)),
        "aiPrompt": body.get("aiPrompt"),
        "triggerCount": 0,
        "lastTriggeredAt": None,
        "createdBy": user.get("email"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.rules.insert_one(dict(doc))
    return doc


@router.get("/{rid}")
async def get_rule(rid: str, _: dict = Depends(get_user)):
    r = await db.rules.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Rule not found")
    return r


@router.patch("/{rid}")
async def update_rule(rid: str, body: dict, _: dict = Depends(require_owner_or_manager)):
    upd = {k: v for k, v in body.items() if k not in ("id", "createdBy", "createdAt", "triggerCount", "lastTriggeredAt")}
    upd["updatedAt"] = datetime.now(timezone.utc).isoformat()
    r = await db.rules.update_one({"id": rid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Rule not found")
    return await db.rules.find_one({"id": rid}, {"_id": 0})


@router.delete("/{rid}")
async def delete_rule(rid: str, _: dict = Depends(require_owner_or_manager)):
    r = await db.rules.delete_one({"id": rid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Rule not found")
    return {"deleted": True}


@router.post("/{rid}/toggle")
async def toggle_rule(rid: str, _: dict = Depends(require_owner_or_manager)):
    rule = await db.rules.find_one({"id": rid}, {"_id": 0})
    if not rule:
        raise HTTPException(404, "Rule not found")
    new_state = not rule.get("active", True)
    await db.rules.update_one({"id": rid}, {"$set": {"active": new_state, "updatedAt": datetime.now(timezone.utc).isoformat()}})
    return {"active": new_state}


# ═════════════════════════════════════════════════════════════════════════
# Event emission (manual test / cross-module producers)
# ═════════════════════════════════════════════════════════════════════════
@router.post("/emit")
async def emit(body: dict, _: dict = Depends(get_user)):
    event_type = body.get("type") or body.get("eventType")
    if not event_type:
        raise HTTPException(400, "type is required")
    if event_type not in re_svc.EVENT_CATALOG:
        raise HTTPException(400, f"Unknown event type: {event_type}")
    return await re_svc.emit_event(event_type, body.get("payload") or {}, body.get("entityId"))


@router.post("/simulate")
async def simulate(body: dict, _: dict = Depends(get_user)):
    """Dry-run a rule against a sample payload without executing actions."""
    rule = body.get("rule")
    payload = body.get("payload") or {}
    if not rule:
        rid = body.get("ruleId")
        if not rid:
            raise HTTPException(400, "rule or ruleId is required")
        rule = await db.rules.find_one({"id": rid}, {"_id": 0})
        if not rule:
            raise HTTPException(404, "Rule not found")
    cond = re_svc.evaluate_conditions(rule.get("conditions"), payload)
    return {
        "ruleName": rule.get("name"),
        "triggerEvent": rule.get("triggerEvent"),
        "conditionResult": cond,
        "wouldFire": cond["passed"],
        "actionsPreview": rule.get("actions") or [],
    }


# ═════════════════════════════════════════════════════════════════════════
# Execution history
# ═════════════════════════════════════════════════════════════════════════
@router.get("/history/executions")
async def executions(limit: int = 100, rule_id: Optional[str] = None, _: dict = Depends(get_user)):
    q: Dict[str, Any] = {}
    if rule_id:
        q["firings.ruleId"] = rule_id
    rows = await db.rule_executions.find(q, {"_id": 0}).sort("ts", -1).limit(limit).to_list(limit)
    return rows


@router.get("/history/events")
async def events(limit: int = 100, event_type: Optional[str] = None, _: dict = Depends(get_user)):
    q: Dict[str, Any] = {}
    if event_type:
        q["type"] = event_type
    rows = await db.rule_events.find(q, {"_id": 0}).sort("ts", -1).limit(limit).to_list(limit)
    return rows


# ═════════════════════════════════════════════════════════════════════════
# AI natural-language rule builder — Emergent LLM key + GPT-5.2
# ═════════════════════════════════════════════════════════════════════════
_AI_SYSTEM = """You are the automation-rule designer for NUA POS (a hospitality platform).

Return STRICT JSON matching this schema — no prose, no markdown fences:
{
  "name": "<short label>",
  "description": "<one sentence>",
  "triggerEvent": "<one of the catalog event types>",
  "conditions": {"mode":"all|any","clauses":[{"path":"<payload dot-path>","op":"<eq|ne|gt|gte|lt|lte|in|not_in|contains|starts_with>","value":<any>}]},
  "actions": [{"type":"<action type>","params":{...}}],
  "priority": 0,
  "active": true
}

Available EVENT TYPES: pos.sale.completed, pos.refund.issued, voucher.redeemed, gift_card.sold,
inventory.low_stock, inventory.stockout, inventory.received, customer.created,
customer.spend_milestone, customer.birthday, customer.no_show, customer.review,
booking.created, booking.confirmed, booking.cancelled, booking.no_show,
labour.staff_late, labour.overtime, labour.no_show, kitchen.wait_time_high,
kitchen.dish_86, kitchen.temp_abnormal, finance.ap_due_soon, finance.cash_low.

Available ACTION TYPES: dock_notify, send_email, send_sms, create_purchase_order,
upgrade_vip_tier, apply_customer_credit, issue_voucher, dispatch_task, post_journal,
mark_dish_86, apply_discount, webhook.

Guidelines: keep conditions minimal; prefer common event field names (productId, customerId,
stock, threshold, total, minutesLate). If unsure of a payload path, pick a sensible default.
"""


@router.post("/ai-build")
async def ai_build(body: dict, _: dict = Depends(get_user)):
    """Natural-language → rule spec via GPT-5.2."""
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    parsed: Dict[str, Any] = {}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise RuntimeError("EMERGENT_LLM_KEY missing")
        chat = LlmChat(
            api_key=api_key,
            session_id=f"rules-{uuid.uuid4()}",
            system_message=_AI_SYSTEM,
        ).with_model("openai", "gpt-5.2")
        raw = await chat.send_message(UserMessage(text=prompt))
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
    except Exception as e:
        logger.warning(f"AI rule build fell back to template: {e}")

    # Fallback if AI failed or produced invalid JSON
    if not parsed.get("triggerEvent") or parsed.get("triggerEvent") not in re_svc.EVENT_CATALOG:
        # Guess event from keywords
        p = prompt.lower()
        event = "inventory.low_stock"
        if "birthday" in p: event = "customer.birthday"
        elif "no-show" in p or "no show" in p: event = "booking.no_show"
        elif "vip" in p or "loyalty" in p or "spend" in p: event = "customer.spend_milestone"
        elif "temp" in p or "fridge" in p or "freezer" in p: event = "kitchen.temp_abnormal"
        elif "late" in p: event = "labour.staff_late"
        elif "wait" in p or "backlog" in p: event = "kitchen.wait_time_high"
        parsed = {
            "name": parsed.get("name") or f"Automation: {prompt[:40]}",
            "description": parsed.get("description") or prompt,
            "triggerEvent": event,
            "conditions": parsed.get("conditions") or {"mode": "all", "clauses": []},
            "actions": parsed.get("actions") or [{"type": "dock_notify", "params": {"message": "Rule triggered"}}],
            "priority": parsed.get("priority") or 0,
            "active": True,
        }

    # Validate action types
    parsed["actions"] = [a for a in (parsed.get("actions") or []) if a.get("type") in re_svc.ACTION_LIBRARY]
    if not parsed["actions"]:
        parsed["actions"] = [{"type": "dock_notify", "params": {"message": "Rule triggered"}}]

    parsed["aiGenerated"] = True
    parsed["aiPrompt"] = prompt
    return parsed


# ═════════════════════════════════════════════════════════════════════════
# End of file
# ═════════════════════════════════════════════════════════════════════════
