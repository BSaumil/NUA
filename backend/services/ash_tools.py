"""
Ash Tool Registry — the MCP-inspired capability catalog.

Design
──────
Every business capability Ash can invoke is defined ONCE here as a
`Tool` with:
  • name (snake_case) — LLM function name
  • label, description — human-readable
  • module — POS / Inventory / Customers / Reservations / Staff / Marketing / Finance / Ash
  • risk — low | medium | high | critical
  • defaultPermission — auto | approval | disabled
  • schema — JSON schema for arguments (used by GPT-5.2 function calling)
  • execute(args) → awaited outcome dict
  • rollback(outcome) → optional undo fn

Permissions
───────────
Owner-configurable in `db.ash_tool_config` — falls back to defaultPermission.
`Auto` runs immediately, `Approval` enqueues via approval_service,
`Disabled` blocks with a friendly explanation.
"""
from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from database import db
from services import audit_service, approval_service
import uuid
import logging

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Tool:
    name: str
    label: str
    description: str
    module: str
    risk: str                                    # low | medium | high | critical
    default_permission: str                      # auto | approval | disabled
    parameters: Dict[str, Any]                   # JSON schema for LLM
    execute: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    rollback: Optional[Callable[[Dict[str, Any]], Awaitable[Any]]] = None
    expected_impact: str = "informational"       # informational | revenue | cost | csat | compliance


TOOLS: Dict[str, Tool] = {}


def register(tool: Tool) -> None:
    TOOLS[tool.name] = tool


# ═════════════════════════════════════════════════════════════════════════
# Individual tool implementations
# ═════════════════════════════════════════════════════════════════════════
async def _tx_dismiss_insight(a):
    r = await db.ash_insights.update_one({"id": a["insightId"]},
                                          {"$set": {"resolvedAt": _now(), "resolvedBy": "ash-agent"}})
    if r.matched_count == 0:
        return {"error": "insight not found"}
    return {"insightId": a["insightId"], "resolved": True}


async def _tx_approve_pending_approval(a):
    """Ash approves a pending approval on the owner's behalf.
    We never bypass the queue — this only works when caller has permission."""
    from services.rules_engine import ACTION_LIBRARY
    doc = await db.approvals.find_one({"id": a["approvalId"]}, {"_id": 0})
    if not doc:
        return {"error": "approval not found"}
    if doc["status"] != "pending":
        return {"error": f"already {doc['status']}"}
    action_meta = ACTION_LIBRARY.get(doc["actionType"])
    if not action_meta:
        return {"error": f"unknown underlying action {doc['actionType']}"}
    fake_rule = {"id": doc.get("sourceRef") or "ash", "name": "ash-agent approval"}
    fake_event = {"id": "ash", "type": "approval.executed", "payload": doc["params"]}
    async def _run(params): return await action_meta["fn"](fake_rule, fake_event, params)
    return await approval_service.approve(a["approvalId"], actor="ash-agent", execute_fn=_run)


async def _tx_reject_pending_approval(a):
    try:
        return await approval_service.reject(a["approvalId"], actor="ash-agent", reason=a.get("reason"))
    except ValueError as e:
        return {"error": str(e)}


async def _tx_adjust_menu_price(a):
    pid = a["productId"]; new_price = float(a["newPrice"])
    before = await db.products.find_one({"id": pid}, {"_id": 0})
    if not before:
        return {"error": "product not found"}
    await db.products.update_one({"id": pid}, {"$set": {"price": new_price, "updatedAt": _now(), "updatedBy": "ash-agent"}})
    return {"productId": pid, "oldPrice": before.get("price"), "newPrice": new_price}


async def _rollback_menu_price(outcome):
    await db.products.update_one({"id": outcome["productId"]},
                                  {"$set": {"price": outcome["oldPrice"]}})


async def _tx_issue_voucher(a):
    try:
        from routes.commerce_v29 import _issue_voucher
        v = await _issue_voucher({
            "sourceType": "ash_agent",
            "sourceRef": "chat",
            "label": a.get("label", "Ash-issued voucher"),
            "valueType": a.get("valueType", "amount"),
            "value": float(a.get("value") or 10),
            "customerId": a.get("customerId"),
        }, user=None)
        return {"voucherId": v["id"], "code": v["code"]}
    except Exception as e:
        return {"error": str(e), "mocked": True}


async def _tx_create_purchase_order(a):
    pid = a["productId"]; qty = int(a.get("quantity") or 10)
    est = float(a.get("estimatedCost") or (qty * float(a.get("unitCost") or 25)))
    product = await db.products.find_one({"id": pid}, {"_id": 0})
    po = {
        "id": str(uuid.uuid4()),
        "productId": pid,
        "productName": (product or {}).get("name"),
        "quantity": qty,
        "supplierId": a.get("supplierId"),
        "estimatedCost": est,
        "status": "draft",
        "createdBy": "ash-agent",
        "createdAt": _now(),
    }
    await db.purchase_orders.insert_one(dict(po))
    return {"purchaseOrderId": po["id"], "quantity": qty, "estimatedCost": est}


async def _tx_add_customer_note(a):
    cid = a["customerId"]; note = a["note"]
    await db.customers.update_one({"id": cid}, {"$push": {"notes": {"text": note, "by": "ash-agent", "at": _now()}}})
    return {"customerId": cid, "added": True}


async def _tx_add_wallet_credit(a):
    cid = a["customerId"]; amount = float(a["amount"])
    r = await db.customers.update_one({"id": cid}, {"$inc": {"storeCredit": amount}})
    if r.matched_count:
        await db.wallet_ledger.insert_one({
            "id": str(uuid.uuid4()), "customerId": cid, "type": "credit_grant",
            "amount": amount, "sourceType": "ash_agent", "createdAt": _now(),
            "description": a.get("reason", "Ash credit"),
        })
    return {"customerId": cid, "credit": amount, "matched": r.matched_count}


async def _tx_upgrade_customer_tier(a):
    cid = a["customerId"]; tier = a["tier"]
    r = await db.customers.update_one({"id": cid}, {"$set": {"membershipTier": tier, "vipUpgradedAt": _now()}})
    return {"customerId": cid, "newTier": tier, "matched": r.matched_count}


async def _tx_mark_waste(a):
    pid = a["productId"]; qty = float(a.get("quantity") or 1); reason = a.get("reason", "spoilage")
    doc = {"id": str(uuid.uuid4()), "productId": pid, "quantity": qty, "reason": reason,
           "recordedBy": "ash-agent", "createdAt": _now()}
    await db.waste_events.insert_one(dict(doc))
    await db.products.update_one({"id": pid}, {"$inc": {"stock": -qty}})
    return {"wasteId": doc["id"], "productId": pid, "quantity": qty}


async def _tx_mark_dish_86(a):
    r = await db.products.update_one({"id": a["productId"]},
                                     {"$set": {"is86ed": True, "eightySixReason": a.get("reason", "ash-agent")}})
    return {"productId": a["productId"], "matched": r.matched_count}


async def _tx_cancel_reservation(a):
    r = await db.reservations.update_one({"id": a["reservationId"]},
                                          {"$set": {"status": "cancelled", "cancelledBy": "ash-agent",
                                                    "cancellationReason": a.get("reason")}})
    return {"reservationId": a["reservationId"], "matched": r.matched_count}


async def _tx_send_customer_sms(a):
    to = a.get("phone") or "unknown"; text = a["text"]
    try:
        from utils.notifications import send_sms
        await send_sms(to, text)
        return {"sent": True, "to": to}
    except Exception:
        logger.info(f"[ash sms MOCKED] to={to} text={text}")
        return {"sent": False, "mocked": True, "to": to, "text": text}


async def _tx_send_customer_email(a):
    to = a["email"]; subj = a["subject"]; body = a["body"]
    try:
        from utils.notifications import send_email
        await send_email(to, subj, body)
        return {"sent": True, "to": to}
    except Exception:
        logger.info(f"[ash email MOCKED] to={to} subj={subj}")
        return {"sent": False, "mocked": True, "to": to, "subject": subj}


async def _tx_create_task(a):
    doc = {"id": str(uuid.uuid4()), "title": a["title"], "assignee": a.get("assignee", "manager"),
           "priority": a.get("priority", "normal"), "dueAt": a.get("dueAt"),
           "createdBy": "ash-agent", "status": "open", "createdAt": _now()}
    await db.tasks.insert_one(dict(doc))
    return {"taskId": doc["id"]}


async def _tx_create_promotion(a):
    doc = {"id": str(uuid.uuid4()), "name": a["name"], "type": a.get("type", "percent"),
           "discount": float(a.get("discount") or 10), "active": True, "createdBy": "ash-agent",
           "createdAt": _now(), "productId": a.get("productId")}
    await db.promotions.insert_one(dict(doc))
    return {"promotionId": doc["id"]}


async def _tx_run_ash_scan(a):
    from services.ash_intelligence import run_all_insights
    return await run_all_insights(include_summary=False)


async def _tx_generate_weekly_summary(a):
    from services.ash_intelligence import generate_weekly_summary
    doc = await generate_weekly_summary()
    if not doc:
        return {"error": "no summary generated"}
    await db.ash_insights.update_one(
        {"category": doc["category"], "key": doc["key"]},
        {"$set": doc, "$setOnInsert": {"firstSeenAt": doc["createdAt"]}},
        upsert=True,
    )
    return {"summary": doc["body"], "data": doc["data"]}


async def _tx_fetch_kpis(a):
    """Read-only tool — get finance KPIs."""
    from services.accounting_service import profit_and_loss, balance_sheet
    from datetime import date, timedelta
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=int(a.get("days", 7)))).isoformat()
    pnl = await profit_and_loss(start, end)
    bs = await balance_sheet(as_of=end)
    return {"revenue": pnl["totalRevenue"], "grossProfit": pnl["grossProfit"],
            "netProfit": pnl["netProfit"], "cash": bs["totalAssets"],
            "range": f"{start} → {end}"}


async def _tx_fetch_open_insights(a):
    rows = await db.ash_insights.find({"resolvedAt": None}, {"_id": 0}).sort("createdAt", -1).limit(50).to_list(50)
    return {"insights": [{"id": i["id"], "category": i["category"], "severity": i["severity"],
                            "title": i["title"], "body": i["body"]} for i in rows]}


async def _tx_lookup_customer(a):
    q = (a.get("query") or "").strip()
    if not q:
        return {"error": "query required"}
    row = await db.customers.find_one(
        {"$or": [{"email": {"$regex": q, "$options": "i"}},
                 {"name": {"$regex": q, "$options": "i"}},
                 {"phone": {"$regex": q, "$options": "i"}}]},
        {"_id": 0},
    )
    if not row:
        return {"error": "not found"}
    return {"customer": {k: row.get(k) for k in ("id", "name", "email", "phone", "membershipTier", "totalSpent", "visits", "lastVisit")}}


async def _tx_lookup_product(a):
    q = (a.get("query") or "").strip()
    row = await db.products.find_one({"name": {"$regex": q, "$options": "i"}}, {"_id": 0})
    if not row:
        return {"error": "not found"}
    return {"product": {k: row.get(k) for k in ("id", "name", "price", "cost", "stock", "category")}}


async def _tx_generate_daily_briefing(a):
    """Delegate to briefing endpoint for consistency."""
    from services import ash_briefing
    return await ash_briefing.generate_briefing()


async def _tx_remember(a):
    from services import ash_memory
    doc = await ash_memory.remember(
        text=a["text"],
        scope=a.get("scope", "global"),
        kind=a.get("kind", "fact"),
        confidence=float(a.get("confidence") or 0.7),
        source="ash_agent",
        tags=a.get("tags") or [],
    )
    return {"memoryId": doc["id"], "reinforced": bool(doc.get("reinforced")),
            "confidence": doc.get("confidence"), "scope": doc.get("scope")}


async def _tx_recall(a):
    from services import ash_memory
    rows = await ash_memory.recall(scope=a.get("scope", "global"),
                                     limit=int(a.get("limit") or 10),
                                     kind=a.get("kind"))
    return {"memories": [{"id": r["id"], "kind": r["kind"], "text": r["text"],
                            "confidence": r["confidence"], "scope": r["scope"]}
                            for r in rows]}


# ═════════════════════════════════════════════════════════════════════════
# Registration
# ═════════════════════════════════════════════════════════════════════════
_TOOL_DEFS: List[Dict[str, Any]] = [
    # ── Ash / read-only ──
    {"n": "fetch_open_insights", "l": "Fetch open Ash insights", "m": "Ash", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {}}, "fn": _tx_fetch_open_insights, "impact": "informational"},
    {"n": "fetch_kpis", "l": "Fetch financial KPIs", "m": "Finance", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}}, "fn": _tx_fetch_kpis},
    {"n": "lookup_customer", "l": "Look up a customer", "m": "Customers", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
     "fn": _tx_lookup_customer},
    {"n": "lookup_product", "l": "Look up a product", "m": "Inventory", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
     "fn": _tx_lookup_product},
    {"n": "run_ash_scan", "l": "Run all Ash generators now", "m": "Ash", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {}}, "fn": _tx_run_ash_scan},
    {"n": "generate_weekly_summary", "l": "Generate the weekly business summary", "m": "Ash", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {}}, "fn": _tx_generate_weekly_summary},
    {"n": "generate_daily_briefing", "l": "Generate this morning's briefing", "m": "Ash", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {}}, "fn": _tx_generate_daily_briefing},
    {"n": "remember", "l": "Save a long-term memory / preference / pattern", "m": "Ash", "r": "low", "p": "auto",
     "params": {"type": "object",
                 "properties": {"text": {"type": "string"},
                                 "scope": {"type": "string",
                                             "description": "global | customer:<id> | staff:<id> | product:<id> | supplier:<id>"},
                                 "kind": {"type": "string", "enum": ["preference", "pattern", "fact", "note"]},
                                 "confidence": {"type": "number"},
                                 "tags": {"type": "array", "items": {"type": "string"}}},
                 "required": ["text"]},
     "fn": _tx_remember, "impact": "informational"},
    {"n": "recall", "l": "Retrieve long-term memories for a scope", "m": "Ash", "r": "low", "p": "auto",
     "params": {"type": "object",
                 "properties": {"scope": {"type": "string"},
                                 "kind": {"type": "string"},
                                 "limit": {"type": "integer", "default": 10}}},
     "fn": _tx_recall},

    # ── Ash / dismiss / approvals ──
    {"n": "dismiss_insight", "l": "Dismiss an Ash insight", "m": "Ash", "r": "low", "p": "auto",
     "params": {"type": "object", "properties": {"insightId": {"type": "string"}}, "required": ["insightId"]},
     "fn": _tx_dismiss_insight},
    {"n": "approve_pending_approval", "l": "Approve a pending approval", "m": "Ash", "r": "high", "p": "approval",
     "params": {"type": "object", "properties": {"approvalId": {"type": "string"}}, "required": ["approvalId"]},
     "fn": _tx_approve_pending_approval},
    {"n": "reject_pending_approval", "l": "Reject a pending approval", "m": "Ash", "r": "medium", "p": "approval",
     "params": {"type": "object", "properties": {"approvalId": {"type": "string"},
                                                    "reason": {"type": "string"}},
                "required": ["approvalId"]},
     "fn": _tx_reject_pending_approval},

    # ── Inventory / write ──
    {"n": "create_purchase_order", "l": "Create a purchase order", "m": "Inventory", "r": "high", "p": "approval",
     "params": {"type": "object",
                 "properties": {"productId": {"type": "string"}, "quantity": {"type": "integer"},
                                 "supplierId": {"type": "string"}, "unitCost": {"type": "number"},
                                 "estimatedCost": {"type": "number"}},
                 "required": ["productId", "quantity"]},
     "fn": _tx_create_purchase_order, "impact": "cost"},
    {"n": "mark_waste", "l": "Log a waste event & deduct stock", "m": "Inventory", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"productId": {"type": "string"}, "quantity": {"type": "number"},
                                 "reason": {"type": "string"}}, "required": ["productId", "quantity"]},
     "fn": _tx_mark_waste, "impact": "cost"},
    {"n": "mark_dish_86", "l": "Mark a dish as 86'd", "m": "Inventory", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"productId": {"type": "string"}, "reason": {"type": "string"}},
                 "required": ["productId"]},
     "fn": _tx_mark_dish_86, "impact": "revenue"},
    {"n": "adjust_menu_price", "l": "Change a product price", "m": "Inventory", "r": "high", "p": "approval",
     "params": {"type": "object",
                 "properties": {"productId": {"type": "string"}, "newPrice": {"type": "number"},
                                 "reason": {"type": "string"}},
                 "required": ["productId", "newPrice"]},
     "fn": _tx_adjust_menu_price, "rollback": _rollback_menu_price, "impact": "revenue"},

    # ── Customers / write ──
    {"n": "add_customer_note", "l": "Add a note to a customer", "m": "Customers", "r": "low", "p": "auto",
     "params": {"type": "object",
                 "properties": {"customerId": {"type": "string"}, "note": {"type": "string"}},
                 "required": ["customerId", "note"]},
     "fn": _tx_add_customer_note},
    {"n": "add_wallet_credit", "l": "Grant store credit", "m": "Customers", "r": "high", "p": "approval",
     "params": {"type": "object",
                 "properties": {"customerId": {"type": "string"}, "amount": {"type": "number"},
                                 "reason": {"type": "string"}},
                 "required": ["customerId", "amount"]},
     "fn": _tx_add_wallet_credit, "impact": "cost"},
    {"n": "issue_voucher", "l": "Issue a voucher to a customer", "m": "Customers", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"customerId": {"type": "string"}, "value": {"type": "number"},
                                 "label": {"type": "string"}, "valueType": {"type": "string"}},
                 "required": ["value"]},
     "fn": _tx_issue_voucher, "impact": "cost"},
    {"n": "upgrade_customer_tier", "l": "Change a customer's loyalty tier", "m": "Customers", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"customerId": {"type": "string"}, "tier": {"type": "string"}},
                 "required": ["customerId", "tier"]},
     "fn": _tx_upgrade_customer_tier, "impact": "csat"},

    # ── Reservations ──
    {"n": "cancel_reservation", "l": "Cancel a reservation", "m": "Reservations", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"reservationId": {"type": "string"}, "reason": {"type": "string"}},
                 "required": ["reservationId"]},
     "fn": _tx_cancel_reservation, "impact": "csat"},

    # ── Marketing ──
    {"n": "send_customer_sms", "l": "Send an SMS to a customer", "m": "Marketing", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"phone": {"type": "string"}, "text": {"type": "string"}},
                 "required": ["text"]},
     "fn": _tx_send_customer_sms, "impact": "csat"},
    {"n": "send_customer_email", "l": "Send an email to a customer", "m": "Marketing", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"email": {"type": "string"}, "subject": {"type": "string"},
                                 "body": {"type": "string"}},
                 "required": ["email", "subject", "body"]},
     "fn": _tx_send_customer_email},
    {"n": "create_promotion", "l": "Create a promotion", "m": "Marketing", "r": "medium", "p": "approval",
     "params": {"type": "object",
                 "properties": {"name": {"type": "string"}, "discount": {"type": "number"},
                                 "type": {"type": "string"}, "productId": {"type": "string"}},
                 "required": ["name"]},
     "fn": _tx_create_promotion, "impact": "revenue"},

    # ── Staff ──
    {"n": "create_staff_task", "l": "Create a task for a staff member", "m": "Staff", "r": "low", "p": "auto",
     "params": {"type": "object",
                 "properties": {"title": {"type": "string"}, "assignee": {"type": "string"},
                                 "priority": {"type": "string"}, "dueAt": {"type": "string"}},
                 "required": ["title"]},
     "fn": _tx_create_task},
]

for d in _TOOL_DEFS:
    register(Tool(
        name=d["n"], label=d["l"], description=d.get("desc", d["l"]),
        module=d["m"], risk=d["r"], default_permission=d["p"],
        parameters=d["params"], execute=d["fn"],
        rollback=d.get("rollback"), expected_impact=d.get("impact", "informational"),
    ))


# ═════════════════════════════════════════════════════════════════════════
# Permission resolution & execution
# ═════════════════════════════════════════════════════════════════════════
async def resolve_permission(tool_name: str) -> str:
    """Look up owner override, else fall back to tool default."""
    tool = TOOLS.get(tool_name)
    if not tool:
        return "disabled"
    override = await db.ash_tool_config.find_one({"toolName": tool_name}, {"_id": 0})
    return (override or {}).get("permission") or tool.default_permission


async def execute_tool(tool_name: str, args: Dict[str, Any], *, actor: str = "ash-agent") -> Dict[str, Any]:
    """Run a tool through the permission gate. Always returns a dict."""
    tool = TOOLS.get(tool_name)
    if not tool:
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}
    perm = await resolve_permission(tool_name)
    if perm == "disabled":
        return {"status": "blocked", "reason": f"Tool '{tool_name}' is disabled by policy",
                 "tool": tool_name, "permission": perm}
    if perm == "approval":
        appr = await approval_service.enqueue_approval(
            action_type=tool_name, params=args, requested_by=actor,
            source="ash_agent",
            context={"toolName": tool_name, "label": tool.label, "risk": tool.risk},
        )
        return {"status": "pending_approval", "approvalId": appr["id"],
                 "tool": tool_name, "permission": perm, "expectedImpact": tool.expected_impact,
                 "risk": tool.risk}
    # auto
    try:
        outcome = await tool.execute(args)
    except Exception as e:
        logger.warning(f"[ash tool] {tool_name} failed: {e}")
        outcome = {"error": str(e)}
    await audit_service.log_event(
        entity_type=f"ash_tool:{tool.module}",
        entity_id=tool_name,
        action="executed",
        after={"args": args, "outcome": outcome},
        memo=f"Ash-agent executed {tool.label}",
        severity="notice",
        tags=["ash_agent", f"risk_{tool.risk}"],
    )
    return {"status": "executed", "tool": tool_name, "outcome": outcome,
             "risk": tool.risk, "expectedImpact": tool.expected_impact,
             "rollbackAvailable": tool.rollback is not None}


# ═════════════════════════════════════════════════════════════════════════
# Public catalog helpers
# ═════════════════════════════════════════════════════════════════════════
def catalog() -> List[Dict[str, Any]]:
    return [
        {
            "name": t.name, "label": t.label, "module": t.module,
            "risk": t.risk, "defaultPermission": t.default_permission,
            "parameters": t.parameters, "rollbackAvailable": t.rollback is not None,
            "expectedImpact": t.expected_impact,
        }
        for t in sorted(TOOLS.values(), key=lambda x: (x.module, x.name))
    ]


def openai_schema() -> List[Dict[str, Any]]:
    """Return the tool list in OpenAI function-calling shape."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": f"[{t.module}] {t.label} (risk={t.risk})",
                "parameters": t.parameters,
            },
        }
        for t in TOOLS.values()
    ]
