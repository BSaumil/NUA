"""
Ash — the autonomous operating layer endpoints.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from database import db
from deps import get_user, require_owner_or_manager
from services import ash_intelligence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ash")


@router.get("/insights")
async def list_insights(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    include_resolved: bool = False,
    limit: int = 200,
    _: dict = Depends(get_user),
):
    q = {}
    if category: q["category"] = category
    if severity: q["severity"] = severity
    if not include_resolved:
        q["resolvedAt"] = None
    rows = await db.ash_insights.find(q, {"_id": 0}).sort("createdAt", -1).limit(limit).to_list(limit)
    return rows


@router.get("/insights/summary")
async def insights_summary(_: dict = Depends(get_user)):
    """Grouped counts for the dashboard."""
    pipeline = [
        {"$match": {"resolvedAt": None}},
        {"$group": {"_id": {"category": "$category", "severity": "$severity"}, "count": {"$sum": 1}}},
    ]
    rows = await db.ash_insights.aggregate(pipeline).to_list(200)
    by_cat = {}
    for r in rows:
        c = r["_id"]["category"]; s = r["_id"]["severity"]
        by_cat.setdefault(c, {"info": 0, "notice": 0, "warning": 0, "high": 0})
        by_cat[c][s] = by_cat[c].get(s, 0) + r["count"]
    total = sum(sum(v.values()) for v in by_cat.values())
    high = sum(v.get("high", 0) for v in by_cat.values())
    warning = sum(v.get("warning", 0) for v in by_cat.values())
    return {"total": total, "high": high, "warning": warning, "byCategory": by_cat}


@router.post("/run")
async def run(include_summary: bool = False, _: dict = Depends(require_owner_or_manager)):
    """Manually trigger a full Ash pass — normally run on a cadence."""
    return await ash_intelligence.run_all_insights(include_summary=include_summary)


@router.post("/summary/weekly")
async def weekly_summary(_: dict = Depends(require_owner_or_manager)):
    doc = await ash_intelligence.generate_weekly_summary()
    if doc:
        await db.ash_insights.update_one(
            {"category": doc["category"], "key": doc["key"]},
            {"$set": doc, "$setOnInsert": {"firstSeenAt": doc["createdAt"]}},
            upsert=True,
        )
    return doc


@router.post("/insights/{iid}/dismiss")
async def dismiss_insight(iid: str, _: dict = Depends(require_owner_or_manager)):
    from datetime import datetime, timezone
    r = await db.ash_insights.update_one({"id": iid}, {"$set": {"resolvedAt": datetime.now(timezone.utc).isoformat(), "resolvedBy": "manual"}})
    if r.matched_count == 0:
        raise HTTPException(404, "Insight not found")
    return {"dismissed": True}


@router.get("/capabilities")
async def capabilities(_: dict = Depends(get_user)):
    """Enumerate what Ash watches for — used by the intro dashboard card."""
    return {
        "capabilities": [
            {"key": "staffing",         "label": "Predict staffing shortages"},
            {"key": "theft",            "label": "Detect theft"},
            {"key": "fraud",            "label": "Detect fraud"},
            {"key": "pricing",          "label": "Recommend pricing"},
            {"key": "promotion",        "label": "Suggest promotions"},
            {"key": "waste",            "label": "Predict food waste"},
            {"key": "labour",           "label": "Detect unusual labour costs"},
            {"key": "menu",             "label": "Detect menu underperformance"},
            {"key": "weather",          "label": "Forecast weather impact"},
            {"key": "demand",           "label": "Forecast public holiday demand"},
            {"key": "purchasing",       "label": "Recommend purchasing"},
            {"key": "roster",           "label": "Recommend roster changes"},
            {"key": "burnout",          "label": "Predict staff burnout"},
            {"key": "churn",            "label": "Predict customer churn"},
            {"key": "menu_engineering", "label": "Recommend menu engineering"},
            {"key": "summary",          "label": "Auto-write weekly business summary"},
        ],
    }


# ═════════════════════════════════════════════════════════════════════════
# Scheduler + Digest
# ═════════════════════════════════════════════════════════════════════════
from services import ash_scheduler


@router.get("/scheduler/status")
async def scheduler_status(_: dict = Depends(get_user)):
    return await ash_scheduler.digest_status()


@router.post("/scheduler/digest-now")
async def force_digest(_: dict = Depends(require_owner_or_manager)):
    return await ash_scheduler.force_digest_now()


# ═════════════════════════════════════════════════════════════════════════
# Ash Chat — GPT-5.2 grounded on audit events + open insights
# ═════════════════════════════════════════════════════════════════════════
import os
import uuid as _uuid
from datetime import datetime, timezone


@router.post("/chat")
async def chat(body: dict, user: dict = Depends(get_user)):
    """Conversational surface. Grounded on live audit events + Ash insights.

    Body: { message, sessionId?, context? }
    """
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "message is required")
    session_id = body.get("sessionId") or f"ash-chat-{_uuid.uuid4()}"

    # ── Pull grounding context (small enough to fit in a single prompt) ──
    recent_audit = await db.audit_events.find({}, {"_id": 0}).sort("ts", -1).limit(30).to_list(30)
    open_insights = await db.ash_insights.find({"resolvedAt": None}, {"_id": 0}).sort("createdAt", -1).limit(20).to_list(20)
    pending_approvals = await db.approvals.count_documents({"status": "pending"})
    kpis_txn = await db.transactions.count_documents({})

    system_prompt = f"""You are Ash, NUA's autonomous hospitality operating layer.

You have READ-ONLY access to the last 30 audit events and 20 open insights, provided below.
Answer the owner's question briefly and precisely. Cite specifics from the data when relevant.
If they ask "who changed X" or "what happened yesterday", scan the audit log for actor / entity / time.
If they ask "what should I do next", pick the highest-severity open insight and recommend its first recommendedAction.
Never invent transactions, staff, or customers not present in the data.
If the data doesn't contain the answer, say so honestly and suggest what to check.

Total transactions in system: {kpis_txn}. Pending approvals: {pending_approvals}.

RECENT AUDIT EVENTS (newest first):
{[{"ts": e.get("ts"), "actor": e.get("actor"), "action": e.get("action"),
   "entity": f"{e.get('entityType')}:{(e.get('entityId') or '')[:8]}",
   "memo": e.get("memo")} for e in recent_audit]}

OPEN INSIGHTS:
{[{"category": i.get("category"), "severity": i.get("severity"),
   "title": i.get("title"), "actions": [a.get("type") for a in (i.get("recommendedActions") or [])]}
  for i in open_insights]}
"""
    reply = None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        key = os.environ.get("EMERGENT_LLM_KEY")
        if key:
            chat_client = LlmChat(api_key=key, session_id=session_id, system_message=system_prompt)\
                .with_model("openai", "gpt-5.2")
            reply = await chat_client.send_message(UserMessage(text=message))
    except Exception as e:
        logger.warning(f"[ash chat] LLM fell back: {e}")

    if not reply:
        # Deterministic fallback — surface the top open insight
        if open_insights:
            top = open_insights[0]
            reply = (f"I couldn't reach the LLM, but the top open insight is: "
                     f"[{top['severity']}] {top['title']} — {top['body']}. "
                     f"There are {pending_approvals} pending approvals waiting for you.")
        else:
            reply = ("I couldn't reach the LLM right now, and there are no open Ash insights. "
                     "Everything looks calm — check /finance for KPIs or /approvals for anything waiting on you.")

    doc = {
        "id": str(_uuid.uuid4()),
        "sessionId": session_id,
        "actor": user.get("email"),
        "message": message,
        "reply": reply,
        "context": {"auditRows": len(recent_audit), "openInsights": len(open_insights), "pendingApprovals": pending_approvals},
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.ash_chat_log.insert_one(dict(doc))
    except Exception:
        pass
    return {"sessionId": session_id, "reply": reply, "context": doc["context"]}


@router.get("/chat/history/{session_id}")
async def chat_history(session_id: str, limit: int = 40, _: dict = Depends(get_user)):
    rows = await db.ash_chat_log.find({"sessionId": session_id}, {"_id": 0}).sort("ts", 1).limit(limit).to_list(limit)
    return rows


# ═════════════════════════════════════════════════════════════════════════
# Ash v3.0 — Tool-calling Agent, Health Score, Daily Briefing, Permissions
# ═════════════════════════════════════════════════════════════════════════
from services import ash_tools, ash_agent, health_score, ash_briefing


@router.post("/agent")
async def agent(body: dict, user: dict = Depends(get_user)):
    """The Ash v3 tool-calling agent. Accepts { message, sessionId? } and may
    invoke up to 4 tool-calls before returning a final reply.
    """
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "message is required")
    session_id = body.get("sessionId") or f"ash-agent-{_uuid.uuid4()}"

    result = await ash_agent.run_agent_turn(message, session_id=session_id, actor=user.get("email") or "ash-agent")

    doc = {
        "id": str(_uuid.uuid4()),
        "sessionId": session_id,
        "actor": user.get("email"),
        "message": message,
        "reply": result["reply"],
        "reasoning": result.get("reasoning"),
        "toolResults": result.get("toolResults"),
        "trace": result.get("trace"),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.ash_agent_log.insert_one(dict(doc))
    except Exception:
        pass
    return {"sessionId": session_id, **result}


@router.get("/tools")
async def tool_catalog(_: dict = Depends(get_user)):
    """Enumerate available agent tools with current effective permissions."""
    catalog = ash_tools.catalog()
    overrides = {c["toolName"]: c for c in await db.ash_tool_config.find({}, {"_id": 0}).to_list(200)}
    for t in catalog:
        t["effectivePermission"] = (overrides.get(t["name"]) or {}).get("permission") or t["defaultPermission"]
    return catalog


@router.post("/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, body: dict, user: dict = Depends(require_owner_or_manager)):
    """Manual tool invocation with permission enforcement."""
    return await ash_tools.execute_tool(tool_name, body.get("args") or {}, actor=user.get("email"))


@router.put("/tools/{tool_name}/permission")
async def set_tool_permission(tool_name: str, body: dict, _: dict = Depends(require_owner_or_manager)):
    """Owner sets per-tool permission — 'auto' | 'approval' | 'disabled'."""
    perm = (body.get("permission") or "").lower()
    if perm not in ("auto", "approval", "disabled"):
        raise HTTPException(400, "permission must be auto|approval|disabled")
    if tool_name not in ash_tools.TOOLS:
        raise HTTPException(404, "Unknown tool")
    await db.ash_tool_config.update_one(
        {"toolName": tool_name},
        {"$set": {"toolName": tool_name, "permission": perm,
                    "updatedAt": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"toolName": tool_name, "permission": perm}


@router.get("/health-score")
async def get_health_score(_: dict = Depends(get_user)):
    return await health_score.compute_health()


@router.get("/briefing")
async def get_briefing(force: bool = False, _: dict = Depends(get_user)):
    """Return today's briefing — cached in db.ash_briefings, regenerate if force=true."""
    today = datetime.now(timezone.utc).date().isoformat()
    if not force:
        existing = await db.ash_briefings.find_one({"date": today}, {"_id": 0})
        if existing:
            return existing
    return await ash_briefing.generate_briefing()


@router.post("/briefing/regenerate")
async def regenerate_briefing(_: dict = Depends(require_owner_or_manager)):
    return await ash_briefing.generate_briefing()


@router.get("/agent/trace/{session_id}")
async def get_agent_trace(session_id: str, limit: int = 50, _: dict = Depends(get_user)):
    rows = await db.ash_agent_traces.find({"sessionId": session_id}, {"_id": 0}).sort("ts", 1).limit(limit).to_list(limit)
    return rows
