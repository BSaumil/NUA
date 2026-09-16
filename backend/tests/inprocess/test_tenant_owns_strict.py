"""middleware/actor_context.py's tenant_owns_strict() — the new mutation-
safe counterpart to tenant_owns(), added during a bounded release-closure
pass that enumerated every fail-open fallback path in the codebase.

tenant_owns() is deliberately fail-open ("either side missing/null means
allow") because it protects READS: never hide a pre-tenant-stamping legacy
document from the one business that actually created it. That reasoning
has no equivalent for a WRITE or DELETE — this codebase's own history
includes a real bug (_stamp_new()'s old setdefault() no-op) that left rows
created by MANY DIFFERENT businesses all sharing businessId=None, so an
untagged document is not reliably "this one caller's own legacy data".
tenant_owns_strict() closes that: an exact match only, refusing (not
auto-assigning, not deleting) whenever either side is missing.
"""
from middleware.actor_context import tenant_owns, tenant_owns_strict


def test_strict_allows_an_exact_match():
    assert tenant_owns_strict("biz-a", "biz-a") is True


def test_strict_refuses_a_disagreeing_match():
    assert tenant_owns_strict("biz-a", "biz-b") is False


def test_strict_refuses_when_the_document_has_no_businessId():
    """The core behavioral difference from tenant_owns(): a document with
    no businessId at all must be refused for a mutation, not allowed."""
    assert tenant_owns_strict(None, "biz-a") is False
    assert tenant_owns(None, "biz-a") is True, "tenant_owns() itself must remain fail-open — unchanged by this fix"


def test_strict_refuses_when_the_caller_businessId_is_unknown():
    assert tenant_owns_strict("biz-a", None) is False
    assert tenant_owns("biz-a", None) is True, "tenant_owns() itself must remain fail-open — unchanged by this fix"


def test_strict_refuses_when_both_sides_are_missing():
    assert tenant_owns_strict(None, None) is False
    assert tenant_owns(None, None) is True, "tenant_owns() itself must remain fail-open — unchanged by this fix"
