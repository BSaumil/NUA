"""
Graduated trust for NUA agent tools — MVP: earn & promote.

A tool's trust state lives on its `db.ash_tool_config` document (the same
doc that already stores the owner's manual permission override), under a
`trust` key. Every agent-originated approval/rejection resolved via
`approval_service.approve()`/`reject()` feeds `record_decision()`; nothing
else writes this data.

Ladder: approval-gated -> eligible (suggested, nothing changes yet) ->
auto (owner confirmed). A single rejection while still approval-gated
resets the streak to zero — no partial credit.

The "fall" half lives here too: every auto-tier execution already writes
an audit_service entry (nua_tools.execute_tool -> log_event), so
list_recent_executions() replays that trail as a review feed instead of
sampling separately, and demote() gives an owner an instant, one-click
way to flag one of those entries as wrong — immediate revert to
approval-gated plus a reset trust window, not just a dent in the streak,
since the whole point is this ran unsupervised.
"""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from database import db
from services import nua_tools
import uuid
import logging

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "minStreak": 6,       # consecutive clean approvals required to become eligible
    "minStreakDays": 5,   # the streak must span at least this many calendar days
}

TRUST_ELIGIBLE_RISK = {"low", "medium"}  # high/critical never trust-promote, no matter the streak


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_trust(window_size: int) -> dict:
    return {
        "window": [], "windowSize": window_size,
        "consecutiveApproved": 0, "totalApproved": 0, "totalRejected": 0,
        "streakStartedAt": None, "eligibleSince": None,
        "lastPromotedAt": None, "lastDemotedAt": None,
    }


async def get_settings(business_id: Optional[str] = None) -> dict:
    """Defaults business_id from the request's actor context (same
    pattern as notification_service.send()) so existing callers don't
    need editing — this used to be one Ash trust-ladder-promotion policy
    shared by every business on the deployment; see
    services/tenant_settings.py."""
    from services.tenant_settings import get_setting
    value = await get_setting("trust_settings", business_id)
    cfg = dict(DEFAULT_SETTINGS)
    if isinstance(value, dict):
        cfg.update({k: v for k, v in value.items() if v is not None})
    return cfg


async def save_settings(data: dict, business_id: Optional[str] = None) -> dict:
    from services.tenant_settings import set_setting
    cfg = {
        "minStreak": max(int(data.get("minStreak", DEFAULT_SETTINGS["minStreak"]) or 1), 1),
        "minStreakDays": max(int(data.get("minStreakDays", DEFAULT_SETTINGS["minStreakDays"]) or 0), 0),
    }
    await set_setting("trust_settings", cfg, business_id)
    return cfg


def _is_eligible(tool, trust: dict, settings: dict) -> bool:
    """Computed fresh every time rather than trusted from a cached flag —
    so eligibility becomes true purely from calendar time passing, not only
    at the moment a new decision happens to arrive."""
    if not tool or tool.risk not in TRUST_ELIGIBLE_RISK:
        return False
    if trust.get("consecutiveApproved", 0) < settings["minStreak"]:
        return False
    started = trust.get("streakStartedAt")
    if not started:
        return False
    try:
        started_dt = datetime.fromisoformat(started)
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - started_dt) >= timedelta(days=settings["minStreakDays"])


async def _log_event(tool_name: str, kind: str, reason: str, snapshot: dict, actor: str) -> None:
    await db.ash_trust_events.insert_one({
        "id": str(uuid.uuid4()), "toolName": tool_name, "kind": kind,
        "reason": reason, "statsSnapshot": snapshot, "actor": actor, "at": _now(),
    })


async def _mark_eligible_if_needed(tool_name: str, tool, trust: dict, settings: dict) -> None:
    """Log the 'suggested' event + stamp eligibleSince the first time this
    tool is discovered eligible — from wherever that discovery happens.
    Eligibility can be reached purely by calendar time passing with no new
    decision (the streak count was already met, tenure just needed to
    elapse), so this can't only live inside record_decision — list_suggestions
    and get_tool_trust need to be able to trigger it too, or the event log
    stays silent about promotions that were "found," not "just happened."""
    if trust.get("eligibleSince") or not _is_eligible(tool, trust, settings):
        return
    now = _now()
    trust["eligibleSince"] = now
    await db.ash_tool_config.update_one(
        {"toolName": tool_name}, {"$set": {"trust.eligibleSince": now}}
    )
    await _log_event(
        tool_name, "suggested",
        f"{trust['consecutiveApproved']}/{settings['minStreak']} approved, "
        f"streak began {(trust.get('streakStartedAt') or '')[:10]}",
        {"consecutiveApproved": trust["consecutiveApproved"], "minStreak": settings["minStreak"]},
        actor="system",
    )


async def record_decision(tool_name: str, decision: str, approval_id: str) -> None:
    """Feed one resolved agent-tool approval into its trust window.
    No-ops quietly for anything that isn't a registered tool — callers
    don't need to pre-filter beyond checking the approval's source."""
    tool = nua_tools.TOOLS.get(tool_name)
    if not tool:
        return

    settings = await get_settings()
    now = _now()

    cfg = await db.ash_tool_config.find_one({"toolName": tool_name}, {"_id": 0})
    trust = (cfg or {}).get("trust") or _empty_trust(settings["minStreak"])

    window = trust.get("window") or []
    window.append({"approvalId": approval_id, "decision": decision, "at": now})
    window = window[-settings["minStreak"]:]
    trust["window"] = window
    trust["windowSize"] = settings["minStreak"]

    if decision == "rejected":
        trust["consecutiveApproved"] = 0
        trust["totalRejected"] = trust.get("totalRejected", 0) + 1
        trust["streakStartedAt"] = None
        trust["eligibleSince"] = None
    else:
        trust["totalApproved"] = trust.get("totalApproved", 0) + 1
        if trust.get("consecutiveApproved", 0) == 0:
            trust["streakStartedAt"] = now
        trust["consecutiveApproved"] = trust.get("consecutiveApproved", 0) + 1

    await db.ash_tool_config.update_one(
        {"toolName": tool_name}, {"$set": {"toolName": tool_name, "trust": trust}}, upsert=True
    )
    await _mark_eligible_if_needed(tool_name, tool, trust, settings)


async def list_suggestions() -> List[dict]:
    """Tools currently eligible for promotion but not yet promoted — drives
    the suggestion banner. Computed live, not read off a stale flag, so a
    tool becomes visible here purely once enough calendar time has passed
    even without a fresh decision arriving to trigger the check."""
    settings = await get_settings()
    configs = {c["toolName"]: c for c in await db.ash_tool_config.find({}, {"_id": 0}).to_list(500)}
    out = []
    for name, tool in nua_tools.TOOLS.items():
        if tool.risk not in TRUST_ELIGIBLE_RISK:
            continue
        cfg = configs.get(name)
        current_perm = (cfg or {}).get("permission") or tool.default_permission
        if current_perm in ("auto", "disabled"):
            continue
        trust = (cfg or {}).get("trust") or _empty_trust(settings["minStreak"])
        if _is_eligible(tool, trust, settings):
            await _mark_eligible_if_needed(name, tool, trust, settings)
            out.append({
                "toolName": name, "label": tool.label, "module": tool.module, "risk": tool.risk,
                "consecutiveApproved": trust.get("consecutiveApproved", 0),
                "minStreak": settings["minStreak"],
                "streakStartedAt": trust.get("streakStartedAt"),
                "eligibleSince": trust.get("eligibleSince"),
            })
    out.sort(key=lambda s: s.get("eligibleSince") or "", reverse=True)
    return out


async def get_tool_trust(tool_name: str) -> dict:
    tool = nua_tools.TOOLS.get(tool_name)
    settings = await get_settings()
    cfg = await db.ash_tool_config.find_one({"toolName": tool_name}, {"_id": 0})
    trust = (cfg or {}).get("trust") or _empty_trust(settings["minStreak"])
    if tool:
        await _mark_eligible_if_needed(tool_name, tool, trust, settings)
    events = await db.ash_trust_events.find(
        {"toolName": tool_name}, {"_id": 0}
    ).sort("at", -1).limit(20).to_list(20)
    return {
        "toolName": tool_name,
        "risk": tool.risk if tool else None,
        "trustEligible": bool(tool and tool.risk in TRUST_ELIGIBLE_RISK),
        "permission": (cfg or {}).get("permission") or (tool.default_permission if tool else "disabled"),
        "promotedBy": (cfg or {}).get("promotedBy"),
        "trust": trust,
        "isEligible": _is_eligible(tool, trust, settings) if tool else False,
        "settings": settings,
        "events": events,
    }


async def promote(tool_name: str, actor: str) -> dict:
    """Owner-confirmed promotion. Re-validates eligibility server-side —
    never trusts the client's view of whether the streak still holds."""
    tool = nua_tools.TOOLS.get(tool_name)
    if not tool:
        raise ValueError(f"Unknown tool: {tool_name}")
    if tool.risk not in TRUST_ELIGIBLE_RISK:
        raise ValueError(
            f"'{tool_name}' is risk={tool.risk} — trust promotion isn't available for high/critical-risk tools"
        )
    settings = await get_settings()
    cfg = await db.ash_tool_config.find_one({"toolName": tool_name}, {"_id": 0})
    if (cfg or {}).get("permission") == "disabled":
        raise ValueError(f"'{tool_name}' is disabled — enable it manually before promoting")
    trust = (cfg or {}).get("trust") or _empty_trust(settings["minStreak"])
    if not _is_eligible(tool, trust, settings):
        raise ValueError(
            f"'{tool_name}' hasn't earned promotion yet "
            f"({trust.get('consecutiveApproved', 0)}/{settings['minStreak']} clean decisions)"
        )
    now = _now()
    trust["lastPromotedAt"] = now
    await db.ash_tool_config.update_one(
        {"toolName": tool_name},
        {"$set": {"toolName": tool_name, "permission": "auto", "promotedBy": "trust",
                  "updatedAt": now, "trust": trust}},
        upsert=True,
    )
    await _log_event(
        tool_name, "promoted",
        f"{trust.get('consecutiveApproved', 0)}/{settings['minStreak']} approved — promoted by {actor}",
        {"consecutiveApproved": trust.get("consecutiveApproved", 0)}, actor=actor,
    )
    return {"toolName": tool_name, "permission": "auto", "promotedBy": "trust"}


async def demote(tool_name: str, actor: str, reason: str = "") -> dict:
    """Instant demotion — an owner has flagged an auto-executed action as
    wrong. Unlike a rejected approval (which only zeroes the streak and
    leaves permission alone), this immediately revokes 'auto' back to
    'approval', since a promoted tool doing the wrong thing unsupervised is
    exactly the failure mode the streak was supposed to have ruled out.
    Re-earning auto requires a fresh clean streak from zero, same as any
    other reset."""
    tool = nua_tools.TOOLS.get(tool_name)
    settings = await get_settings()
    cfg = await db.ash_tool_config.find_one({"toolName": tool_name}, {"_id": 0})
    trust = (cfg or {}).get("trust") or _empty_trust(settings["minStreak"])
    now = _now()
    trust["consecutiveApproved"] = 0
    trust["totalRejected"] = trust.get("totalRejected", 0) + 1
    trust["streakStartedAt"] = None
    trust["eligibleSince"] = None
    trust["lastDemotedAt"] = now
    await db.ash_tool_config.update_one(
        {"toolName": tool_name},
        {"$set": {"toolName": tool_name, "permission": "approval", "promotedBy": None,
                  "updatedAt": now, "trust": trust}},
        upsert=True,
    )
    await _log_event(
        tool_name, "demoted", reason or "Flagged as wrong from the auto-execution review feed",
        {"consecutiveApproved": 0}, actor=actor,
    )
    return {"toolName": tool_name, "permission": "approval", "demoted": True,
            "label": tool.label if tool else tool_name}


async def list_recent_executions(limit: int = 50) -> List[dict]:
    """Shadow-audit review feed. Every auto-tier tool call already writes an
    audit_service entry (see nua_tools.execute_tool) — this just replays
    that trail filtered to ash-agent executions, newest first, so an owner
    can spot-check what ran unsupervised without a separate logging path."""
    rows = await db.audit_events.find(
        {"tags": "ash_agent", "action": "executed", "entityType": {"$regex": "^ash_tool:"}},
        {"_id": 0},
    ).sort("ts", -1).limit(limit).to_list(limit)
    out = []
    for r in rows:
        tool_name = r.get("entityId")
        tool = nua_tools.TOOLS.get(tool_name)
        after = r.get("after") or {}
        out.append({
            "auditId": r.get("id"),
            "toolName": tool_name,
            "label": tool.label if tool else tool_name,
            "module": tool.module if tool else None,
            "risk": tool.risk if tool else None,
            "rollbackAvailable": bool(tool and tool.rollback),
            "args": after.get("args"),
            "outcome": after.get("outcome"),
            "actor": r.get("actor"),
            "ts": r.get("ts"),
            "flagged": bool(r.get("flagged")),
            "flaggedBy": r.get("flaggedBy"),
            "flagReason": r.get("flagReason"),
        })
    return out
