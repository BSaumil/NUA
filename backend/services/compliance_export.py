"""
Compliance export — every autonomous or approval-gated decision this app
makes already lands somewhere: db.approvals (what was requested, who
resolved it, how), db.rule_executions (what a rule matched and did),
db.ash_trust_events (when a tool earned or lost autonomy). None of it was
ever assembled into one thing an operator could actually hand to an
auditor or a franchisor asking "prove an AI didn't do something it
shouldn't have." This builds that: one chronological timeline across all
three sources for a date range, with the actor, the decision, and the
outcome on every row — nothing new is tracked, this only reads what
already exists.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from database import db
from utils.dates import date_range_filter


async def build_timeline(*, business_id: Optional[str], start_date: Optional[str],
                          end_date: Optional[str], limit: int = 5000) -> List[Dict[str, Any]]:
    approvals = await db.approvals.find(
        date_range_filter("createdAt", start_date, end_date), {"_id": 0},
    ).sort("createdAt", 1).to_list(limit)
    rule_execs = await db.rule_executions.find(
        date_range_filter("ts", start_date, end_date), {"_id": 0},
    ).sort("ts", 1).to_list(limit)
    trust_events = await db.ash_trust_events.find(
        date_range_filter("at", start_date, end_date), {"_id": 0},
    ).sort("at", 1).to_list(limit)

    timeline: List[Dict[str, Any]] = []

    for a in approvals:
        matched_action = a.get("actionType", "action")
        if a["status"] == "pending":
            summary = f"{matched_action} requested — awaiting approval"
        elif a["status"] == "approved":
            summary = f"{matched_action} approved by {a.get('resolvedBy') or 'unknown'}"
        else:
            summary = f"{matched_action} rejected by {a.get('resolvedBy') or 'unknown'}" + \
                      (f" ({a['resolution']})" if a.get("resolution") else "")
        timeline.append({
            "at": a["createdAt"], "kind": "approval", "source": a.get("source") or "unknown",
            "summary": summary, "actor": a.get("requestedBy"), "decidedBy": a.get("resolvedBy"),
            "status": a["status"], "reference": a.get("id"),
        })

    for r in rule_execs:
        matched = [f for f in (r.get("firings") or []) if f.get("matched")]
        for f in matched:
            action_types = ", ".join(o.get("type", "?") for o in (f.get("outcomes") or [])) or "no action"
            timeline.append({
                "at": r["ts"], "kind": "rule_execution", "source": "rules_engine",
                "summary": f"Rule '{f.get('name')}' fired on {r['eventType']} → {action_types}",
                "actor": "system", "decidedBy": f.get("name"), "status": "executed",
                "reference": r.get("id"),
            })

    for t in trust_events:
        timeline.append({
            "at": t["at"], "kind": "trust_change", "source": "nua_trust",
            "summary": f"{t['toolName']}: {t['kind']} — {t.get('reason', '')}",
            "actor": t.get("actor"), "decidedBy": t.get("actor"), "status": t["kind"],
            "reference": t.get("id"),
        })

    timeline.sort(key=lambda x: x["at"] or "")
    return timeline


async def build_report(*, business_id: Optional[str] = None, start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Dict[str, Any]:
    timeline = await build_timeline(business_id=business_id, start_date=start_date, end_date=end_date)
    counts: Dict[str, int] = {}
    for row in timeline:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
    return {
        "range": {"start": start_date, "end": end_date},
        "totalEvents": len(timeline),
        "counts": counts,
        "timeline": timeline,
    }
