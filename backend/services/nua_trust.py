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

Scope note: this is the "climb" half only. It does not yet ship the
shadow-audit review feed (sampling auto executions + "flag as wrong" +
instant demotion) that makes it safe to walk away from a promoted tool —
that's required before any tool should be promoted in a real production
business, and is intentionally a separate follow-up. Until it ships, an
owner who promotes a tool is relying on the existing manual permission
dropdown to notice and revert anything that goes wrong, not an automated
safety net.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
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


async def get_settings() -> dict:
    s = await db.settings.find_one({"key": "trust_settings"}, {"_id": 0})
    cfg = dict(DEFAULT_SETTINGS)
    if s and isinstance(s.get("value"), dict):
        cfg.update({k: v for k, v in s["value"].items() if v is not None})
    return cfg


async def save_settings(data: dict) -> dict:
    cfg = {
        "minStreak": max(int(data.get("minStreak", DEFAULT_SETTINGS["minStreak"]) or 1), 1),
        "minStreakDays": max(int(data.get("minStreakDays", DEFAULT_SETTINGS["minStreakDays"]) or 0), 0),
    }
    await db.settings.update_one(
        {"key": "trust_settings"}, {"$set": {"key": "trust_settings", "value": cfg}}, upsert=True
    )
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
