"""Orchestration layer routes/integrations.py calls into — turns a provider
slug + registry entry into an actual connect/sync/status action, and is the
one place that decides what "connected" is allowed to mean for a given
provider (a CDR bank can never report it, no matter what).
"""
from typing import Any, Dict, Optional

from services.connect import credentials as creds_store
from services.connect.base import ConnectorError
from services.connect.registry import ProviderMeta, get_provider
from services.connect.sync_log import SyncRun, list_sync_runs


class ProviderNotFound(Exception):
    pass


class NotImplementedProvider(Exception):
    pass


async def describe_provider(business_id: str, meta: ProviderMeta) -> Dict[str, Any]:
    """The full, honest status block the frontend renders for one provider."""
    base = {
        "slug": meta.slug, "name": meta.name, "category": meta.category,
        "description": meta.description, "website": meta.website,
        "keyLabel": meta.key_label, "credentialFields": meta.credential_fields,
        "capabilities": sorted(meta.connector.capabilities) if meta.connector else [],
    }
    if meta.preconfigured:
        return {**base, "status": "preconfigured" if os_env_has_stripe() else "not_implemented", "requiresKey": False}
    if meta.is_cdr_bank:
        status_doc = await creds_store.get_status_doc(business_id, meta.slug)
        return {
            **base, "status": "pending_accreditation", "requiresKey": True,
            "hasCredentials": status_doc is not None,
            "note": "Real CDR client code is built and tested, but Consumer Data Right "
                    "accreditation is a regulatory process NUA has not completed. This will "
                    "never show connected until that changes.",
        }
    if meta.connector is None:
        return {**base, "status": "not_implemented", "requiresKey": True}

    status_doc = await creds_store.get_status_doc(business_id, meta.slug)
    if not status_doc:
        return {**base, "status": "needs_credentials", "requiresKey": True}
    last_sync = await _last_sync_run(business_id, meta.slug)
    return {
        **base, "status": status_doc.get("status", "needs_credentials"), "requiresKey": True,
        "lastError": status_doc.get("lastError"), "lastCheckedAt": status_doc.get("lastCheckedAt"),
        "lastSyncAt": last_sync.get("finishedAt") if last_sync else None,
        "lastSyncStatus": last_sync.get("status") if last_sync else None,
    }


async def _last_sync_run(business_id: str, slug: str) -> Optional[Dict[str, Any]]:
    """Most recent sync-run for this provider, for the at-a-glance 'last
    synced' line on the integration card — without making the caller open
    the full history dialog just to see whether a sync ever ran."""
    runs = await list_sync_runs(business_id, provider=slug, limit=1)
    return runs[0] if runs else None


def os_env_has_stripe() -> bool:
    import os
    return bool(os.environ.get("STRIPE_API_KEY"))


async def connect_provider(business_id: str, slug: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    meta = get_provider(slug)
    if not meta:
        raise ProviderNotFound(slug)
    if meta.is_cdr_bank:
        # Credentials get stored (so the connector is genuinely ready to run
        # the day accreditation lands) but status is never "connected".
        await creds_store.save_credentials(business_id, slug, creds)
        await creds_store.update_status(business_id, slug, "pending_accreditation")
        return {"status": "pending_accreditation"}
    if meta.connector is None:
        raise NotImplementedProvider(slug)

    await creds_store.save_credentials(business_id, slug, creds)
    try:
        info = await meta.connector.test_connection(creds)
        await creds_store.update_status(business_id, slug, "connected")
        return {"status": "connected", **(info or {})}
    except ConnectorError as e:
        await creds_store.update_status(business_id, slug, "error", str(e))
        return {"status": "error", "error": str(e)}


async def disconnect_provider(business_id: str, slug: str) -> None:
    await creds_store.delete_credentials(business_id, slug)


async def run_sync(business_id: str, slug: str, sync_type: str) -> Dict[str, Any]:
    meta = get_provider(slug)
    if not meta:
        raise ProviderNotFound(slug)
    if meta.connector is None:
        raise NotImplementedProvider(slug)
    if meta.is_cdr_bank:
        raise ConnectorError(f"{meta.name} is pending CDR accreditation — sync unavailable")

    creds = await creds_store.get_credentials(business_id, slug)
    if not creds:
        raise ConnectorError(f"{meta.name} has no credentials on file — connect it first")

    method = {
        "catalog": meta.connector.sync_catalog,
        "sales": meta.connector.sync_sales,
        "customers": meta.connector.sync_customers,
    }.get(sync_type)
    if method is None:
        raise ConnectorError(f"Unknown sync type '{sync_type}' for {meta.name}")

    async with SyncRun(business_id, slug, sync_type, direction="inbound") as run:
        try:
            await method(creds, business_id, run)
        except ConnectorError as e:
            await creds_store.update_status(business_id, slug, "error", str(e))
            raise
        else:
            await creds_store.update_status(business_id, slug, "connected")
        return {
            "runId": run.id, "counts": run.counts,
        }


async def sync_history(business_id: str, slug: Optional[str] = None, limit: int = 50):
    return await list_sync_runs(business_id, slug, limit)
