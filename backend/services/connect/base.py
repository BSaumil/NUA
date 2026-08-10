"""The connector interface every provider implements against.

A connector doesn't have to implement every method — e.g. an accounting
provider only ever does outbound posting, a bank only ever does inbound
transaction feeds. Base implementations raise NotImplementedError so a
half-built connector fails loudly in a test rather than silently returning
nothing.
"""
from abc import ABC
from typing import Any, Dict, Optional

from services.connect.sync_log import SyncRun


class ConnectorError(Exception):
    """A provider call failed in a way the caller should see (bad
    credentials, HTTP error, malformed response)."""


class BaseConnector(ABC):
    slug: str = ""
    name: str = ""
    # subset of {"catalog", "sales", "customers", "webhook", "accounting_post"}
    capabilities: set = set()

    async def test_connection(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Verify credentials actually work against the provider. Returns a
        small dict of provider-confirmed identity info (e.g. location name)
        on success; raises ConnectorError on failure."""
        raise NotImplementedError

    async def sync_catalog(self, credentials: Dict[str, Any], business_id: str, run: SyncRun) -> None:
        raise NotImplementedError

    async def sync_sales(self, credentials: Dict[str, Any], business_id: str, run: SyncRun,
                          since: Optional[str] = None) -> None:
        raise NotImplementedError

    async def sync_customers(self, credentials: Dict[str, Any], business_id: str, run: SyncRun) -> None:
        raise NotImplementedError

    def verify_webhook(self, body: bytes, headers: Dict[str, str], credentials: Dict[str, Any]) -> bool:
        raise NotImplementedError

    async def handle_webhook_event(self, event: Dict[str, Any], business_id: str, run: SyncRun) -> None:
        raise NotImplementedError
