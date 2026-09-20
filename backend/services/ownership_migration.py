"""Dry-run-first, idempotent legacy ownership migration.

Tenant-ownership release-closure pass, task #68. `tenant_owns_strict()`
(middleware/actor_context.py) already refuses any read/write against an
untagged (businessId missing/None) document that a mutation-path check
has been converted to guard — that refusal is the actual security
boundary and needed no migration to exist. This module is the separate,
one-time cleanup: give every untagged legacy document a real disposition
(assigned to its true owner, or explicitly quarantined) instead of
leaving it permanently unreachable through the normal app.

Design constraints, from the standing directive:
- Dry-run by default. Nothing is written unless the caller explicitly
  passes dry_run=False.
- Idempotent. Running it twice (dry-run or real) must produce the same
  end state, not double-process or re-flag already-triaged documents.
- Assign ownership ONLY from reliable evidence — never "the first
  business that asks," never a guess.
- Never auto-assign to an arbitrarily-chosen business, never delete an
  ambiguous record. Unresolvable documents are quarantined (marked, not
  destroyed, not silently left as-is either) for the separate,
  authorised resolution workflow (routes/ownership_migration.py) to
  handle.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
from database import db
from utils.ids import now_utc, to_iso

QUARANTINE_FLAG = "_ownershipQuarantined"
QUARANTINE_AT = "_ownershipQuarantinedAt"
QUARANTINE_REASON = "_ownershipQuarantineReason"
MIGRATED_AT = "_ownershipMigratedAt"
MIGRATED_EVIDENCE = "_ownershipMigrationEvidence"

# Collections this migration is safe to run against — deliberately NOT
# every collection in the database. A collection is only added here once
# its own creation paths are confirmed to no longer produce untagged
# documents (see TRUST_RELEASE_FINAL_REPORT.md §11.2/§11.6's per-file
# reasoning) — otherwise "migrating" it would just relabel documents a
# still-active code path recreates as untagged the next time it runs.
MIGRATABLE_COLLECTIONS = (
    "categories", "modifiers", "discounts", "payment_links",
    "bills", "invoices", "deposits", "budgets", "bank_transactions",
    "awards",
    "rules", "temperature_devices", "stock_transfers", "approvals",
    "customer_segments", "campaigns", "appointments", "services",
    "loyalty_rewards", "ab_tests", "booking_experiences", "club_offers",
    "table_combinations", "dock_notifications", "super_weekly_runs",
    "booking_inbox",
)


async def _resolve_via_customer(doc: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """If the document references a real customer (by id) who has a
    single, confirmed businessId of their own, that's reliable evidence
    — the customer relationship is a real, pre-existing link, not
    something the migration invents."""
    customer_id = doc.get("customerId")
    if not customer_id:
        return None
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0, "businessId": 1})
    if customer and customer.get("businessId"):
        return customer["businessId"], f"customerId={customer_id} has businessId={customer['businessId']}"
    return None


async def _resolve_via_sole_business(doc: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """A deployment with exactly one business has no real ambiguity to
    begin with — every untagged legacy document can only ever have been
    that one business's. Mirrors routes/online_orders.py's
    resolve_or_require_business_id reasoning for the same single-tenant
    case."""
    candidates = await db.businesses.find({}, {"_id": 0, "id": 1}).to_list(2)
    if len(candidates) == 1:
        return candidates[0]["id"], "sole business on this deployment"
    return None


# Tried in order; the first resolver to return a match wins. Both are
# deliberately conservative — no resolver here ever guesses.
_RESOLVERS = (_resolve_via_customer, _resolve_via_sole_business)


async def _resolve_ownership(doc: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    for resolver in _RESOLVERS:
        result = await resolver(doc)
        if result:
            return result
    return None


async def migrate_collection(collection_name: str, *, dry_run: bool = True) -> Dict[str, Any]:
    """Scan one collection for untagged documents and either propose
    (dry_run=True) or apply (dry_run=False) a disposition for each:
    resolved-and-assigned, or quarantined. Already-quarantined documents
    are skipped on a repeat run (idempotent) rather than re-flagged.
    """
    if collection_name not in MIGRATABLE_COLLECTIONS:
        raise ValueError(
            f"{collection_name!r} is not in MIGRATABLE_COLLECTIONS — its creation paths "
            "haven't been confirmed safe for this migration (see this module's docstring)"
        )
    coll = getattr(db, collection_name)
    untagged = await coll.find(
        {"$or": [{"businessId": None}, {"businessId": {"$exists": False}}]}, {"_id": 0}
    ).to_list(10000)

    report: Dict[str, Any] = {
        "collection": collection_name, "dryRun": dry_run, "scanned": len(untagged),
        "resolved": [], "quarantined": [], "alreadyQuarantined": 0,
    }

    for doc in untagged:
        doc_id = doc.get("id")
        if doc.get(QUARANTINE_FLAG):
            report["alreadyQuarantined"] += 1
            continue

        match = await _resolve_ownership(doc)
        if match:
            business_id, evidence = match
            report["resolved"].append({"id": doc_id, "businessId": business_id, "evidence": evidence})
            if not dry_run:
                await coll.update_one(
                    {"id": doc_id},
                    {"$set": {
                        "businessId": business_id,
                        MIGRATED_AT: to_iso(now_utc()),
                        MIGRATED_EVIDENCE: evidence,
                    }},
                )
        else:
            reason = "no reliable evidence of ownership found"
            report["quarantined"].append({"id": doc_id, "reason": reason})
            if not dry_run:
                await coll.update_one(
                    {"id": doc_id},
                    {"$set": {
                        QUARANTINE_FLAG: True,
                        QUARANTINE_AT: to_iso(now_utc()),
                        QUARANTINE_REASON: reason,
                    }},
                )

    return report


async def migrate_all(*, dry_run: bool = True) -> List[Dict[str, Any]]:
    return [await migrate_collection(c, dry_run=dry_run) for c in MIGRATABLE_COLLECTIONS]


async def list_quarantined(collection_name: str) -> List[Dict[str, Any]]:
    if collection_name not in MIGRATABLE_COLLECTIONS:
        raise ValueError(f"{collection_name!r} is not in MIGRATABLE_COLLECTIONS")
    coll = getattr(db, collection_name)
    return await coll.find({QUARANTINE_FLAG: True}, {"_id": 0}).to_list(10000)


async def resolve_quarantined(collection_name: str, doc_id: str, business_id: str, *, actor: str) -> Dict[str, Any]:
    """The authorised resolution workflow: a human explicitly assigns a
    quarantined document to a real business after reviewing it —
    routes/ownership_migration.py gates this behind the same
    owner + X-Support-Override pattern routes/licensing.py's ABN-change
    override already uses. Never called automatically."""
    if collection_name not in MIGRATABLE_COLLECTIONS:
        raise ValueError(f"{collection_name!r} is not in MIGRATABLE_COLLECTIONS")
    coll = getattr(db, collection_name)
    existing = await coll.find_one({"id": doc_id}, {"_id": 0})
    if not existing:
        raise LookupError("document not found")
    if not existing.get(QUARANTINE_FLAG):
        raise ValueError("document is not quarantined")
    business = await db.businesses.find_one({"id": business_id}, {"_id": 0, "id": 1})
    if not business:
        raise ValueError("businessId does not match a real business")
    now = to_iso(now_utc())
    await coll.update_one(
        {"id": doc_id},
        {
            "$set": {
                "businessId": business_id,
                MIGRATED_AT: now,
                MIGRATED_EVIDENCE: f"manually resolved by {actor}",
            },
            "$unset": {QUARANTINE_FLAG: "", QUARANTINE_AT: "", QUARANTINE_REASON: ""},
        },
    )
    from services.audit_service import log_event
    await log_event(
        entity_type=collection_name, entity_id=doc_id, action="updated",
        after={"businessId": business_id},
        memo=f"Ownership migration: quarantined document manually resolved to business {business_id} by {actor}",
        severity="notice", tags=["ownership_migration"],
    )
    return {"id": doc_id, "businessId": business_id, "resolvedBy": actor, "resolvedAt": now}
