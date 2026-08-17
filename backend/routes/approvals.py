"""
Approval Queue routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from database import db
from deps import get_user, require_owner_or_manager
from services import approval_service, rules_engine as re_svc

router = APIRouter(prefix="/approvals")


@router.get("")
async def list_approvals(status: Optional[str] = None, limit: int = 100, _: dict = Depends(get_user)):
    q = {"status": status} if status else {}
    return await db.approvals.find(q, {"_id": 0}).sort("createdAt", -1).limit(limit).to_list(limit)


@router.get("/pending/count")
async def pending_count(_: dict = Depends(get_user)):
    return {"count": await db.approvals.count_documents({"status": "pending"})}


@router.get("/{aid}")
async def get_approval(aid: str, _: dict = Depends(get_user)):
    doc = await db.approvals.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Approval not found")
    return doc


async def _execute_action(params: dict, action_type: str, rule_id: Optional[str] = None,
                           source: Optional[str] = None) -> dict:
    """Look up a rule action (rules engine) or an NUA agent tool and execute it.

    Agent-tool approvals (source="ash_agent") are dispatched to nua_tools.TOOLS
    first — action_type is the tool name in that case, e.g. "issue_voucher".
    Everything else goes through the rules-engine ACTION_LIBRARY as before.
    Gated on source rather than name collision: a couple of names (issue_voucher,
    mark_dish_86) exist in both registries with slightly different param shapes,
    so we only redirect when we know the approval actually came from the agent.
    """
    if source == "ash_agent":
        from services import nua_tools
        tool = nua_tools.TOOLS.get(action_type)
        if not tool:
            return {"error": f"Unknown agent tool: {action_type}"}
        return await tool.execute(params)
    if action_type == "marketing.launch_campaign":
        from routes.v25_suite import create_and_send_campaign_from_approval
        return await create_and_send_campaign_from_approval(params, created_by=source or "ash")
    action_meta = re_svc.ACTION_LIBRARY.get(action_type)
    if not action_meta:
        return {"error": f"Unknown action {action_type}"}
    # Best-effort rule context for the handler
    rule = {"id": rule_id or "approval-exec", "name": "manual approval execute"}
    if rule_id:
        found = await db.rules.find_one({"id": rule_id}, {"_id": 0})
        if found:
            rule = found
    event = {"id": "approval", "type": "approval.executed", "payload": params}
    return await action_meta["fn"](rule, event, params)


@router.post("/{aid}/approve")
async def approve(aid: str, user: dict = Depends(require_owner_or_manager)):
    doc = await db.approvals.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Approval not found")

    async def exec_fn(params):
        return await _execute_action(params, doc["actionType"], doc.get("sourceRef"), doc.get("source"))

    try:
        return await approval_service.approve(aid, actor=user["email"], execute_fn=exec_fn)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{aid}/reject")
async def reject(aid: str, body: dict, user: dict = Depends(require_owner_or_manager)):
    try:
        return await approval_service.reject(aid, actor=user["email"], reason=body.get("reason"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/config/policy")
async def policy(_: dict = Depends(get_user)):
    import os
    return {
        "mode": os.environ.get("AI_APPROVAL_MODE", "thresholds"),
        "poAbove": float(os.environ.get("AI_APPROVE_PO_ABOVE", 500)),
        "refundAbove": float(os.environ.get("AI_APPROVE_REFUND_ABOVE", 100)),
        "tierDowngradesAlwaysApprove": bool(int(os.environ.get("AI_APPROVE_TIER_DOWNGRADES", 1))),
    }
