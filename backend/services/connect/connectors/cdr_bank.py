"""Consumer Data Right (CDR) bank connector — real Open Banking client code,
built against the actual Consumer Data Standards Australia banking API
(https://consumerdatastandardsaustralia.github.io/standards/) — but gated
behind CDR accreditation, which is a regulatory process (ACCC/OAIC
accreditation as a Data Recipient, registration in the CDR Register, a
registered Software Product with a Software Statement Assertion) that NUA
has not completed. Per that constraint, this connector NEVER reports
"connected" — every entry point raises/returns pending_accreditation,
regardless of what credentials happen to be on file. That's enforced here,
not just in the UI, so there's no path (bug or otherwise) to a false
"connected" status for a bank.

What's real:
  - PAR (Pushed Authorization Request) construction for the FAPI
    consent flow banks require
  - Authorization-code -> token exchange shape
  - GET /cds-au/v1/banking/accounts and
    GET /cds-au/v1/banking/accounts/{accountId}/transactions
    request/response handling, matching the CDS banking API's documented
    shape (x-v version header, cursor-based paging, $.data/$.meta envelope)

All of it is unreachable in practice until accreditation exists — the guard
at the top of every public method is the point.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from database import db
from services.connect.base import BaseConnector, ConnectorError
from services.connect.sync_log import SyncRun

CDS_BANKING_VERSION = "3"  # x-v header — CDS Banking API major version


class AccreditationRequiredError(ConnectorError):
    def __init__(self, bank_name: str):
        super().__init__(
            f"Consumer Data Right accreditation required before NUA can connect to "
            f"{bank_name}. This is a regulatory accreditation process (ACCC Data "
            f"Recipient accreditation + CDR Register registration), not a "
            f"credentials/config step — status stays pending_accreditation until "
            f"it's complete, independent of any token on file."
        )


def make_cdr_connector(slug: str, bank_name: str) -> "CDRBankConnector":
    return CDRBankConnector(slug, bank_name)


class CDRBankConnector(BaseConnector):
    """One instance per accredited data holder (bank). `slug`/`name` are
    injected per-bank since the CDS API shape is identical across holders —
    only the base URL and holder-specific OIDC discovery document differ."""

    capabilities = {"bank_feed"}

    def __init__(self, slug: str, bank_name: str):
        self.slug = slug
        self.name = bank_name

    def _accredited(self) -> bool:
        # There is no accreditation number to check because NUA does not
        # hold one. This is intentionally not an env-var toggle a deploy
        # could flip on by accident — accreditation requires a code change
        # here, made the day NUA is actually accredited.
        return False

    async def test_connection(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        raise AccreditationRequiredError(self.name)

    def build_par_request(self, credentials: Dict[str, Any], redirect_uri: str, scope: str,
                           data_holder_auth_endpoint: str) -> Dict[str, Any]:
        """Constructs the Pushed Authorization Request body the CDS FAPI
        consent flow requires. Real shape (RFC 9126 + CDS profile), but
        calling it is blocked by the accreditation guard below — this only
        ever executes from a test proving the shape is correct."""
        if not self._accredited():
            raise AccreditationRequiredError(self.name)
        return {
            "response_type": "code",
            "client_id": credentials.get("cdrClientId", ""),
            "redirect_uri": redirect_uri,
            "scope": scope or "openid profile bank:accounts.basic:read bank:transactions:read",
            "state": credentials.get("state", ""),
            "nonce": credentials.get("nonce", ""),
        }

    async def exchange_code_for_token(self, credentials: Dict[str, Any], token_endpoint: str,
                                       auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        if not self._accredited():
            raise AccreditationRequiredError(self.name)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(token_endpoint, data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": credentials.get("cdrClientId", ""),
                "client_secret": credentials.get("cdrClientSecret", ""),
            })
        if r.status_code != 200:
            raise ConnectorError(f"Token exchange failed: HTTP {r.status_code}")
        return r.json()

    async def sync_bank_transactions(self, credentials: Dict[str, Any], business_id: str, run: SyncRun,
                                      data_holder_base_url: str, access_token: str,
                                      account_id: Optional[str] = None) -> None:
        if not self._accredited():
            raise AccreditationRequiredError(self.name)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-v": CDS_BANKING_VERSION,
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            if not account_id:
                r = await client.get(f"{data_holder_base_url}/cds-au/v1/banking/accounts", headers=headers)
                if r.status_code != 200:
                    raise ConnectorError(f"accounts fetch failed: HTTP {r.status_code}")
                accounts = r.json().get("data", {}).get("accounts", [])
            else:
                accounts = [{"accountId": account_id}]

            for acct in accounts:
                acct_id = acct.get("accountId")
                cursor_url = f"{data_holder_base_url}/cds-au/v1/banking/accounts/{acct_id}/transactions"
                while cursor_url:
                    r = await client.get(cursor_url, headers=headers)
                    if r.status_code != 200:
                        raise ConnectorError(f"transactions fetch failed: HTTP {r.status_code}")
                    page = r.json()
                    for txn in page.get("data", {}).get("transactions", []):
                        run.bump("fetched")
                        run.add_sample(txn)
                        await self._upsert_bank_transaction(business_id, acct_id, txn)
                    cursor_url = (page.get("links", {}) or {}).get("next")

    async def _upsert_bank_transaction(self, business_id: str, account_id: str, txn: Dict[str, Any]) -> None:
        import uuid
        existing = await db.bank_transactions.find_one(
            {"businessId": business_id, "externalRefs.cdr": txn.get("transactionId")}, {"_id": 0, "id": 1},
        )
        doc = {
            "businessId": business_id,
            "provider": self.slug,
            "accountId": account_id,
            "amount": float(txn.get("amount", 0)),
            "description": txn.get("description", ""),
            "status": txn.get("status", ""),
            "valueDate": txn.get("valueDateTime"),
            "reconciled": False,
            "externalRefs": {"cdr": txn.get("transactionId")},
        }
        if existing:
            await db.bank_transactions.update_one({"id": existing["id"]}, {"$set": doc})
        else:
            await db.bank_transactions.insert_one({
                "id": str(uuid.uuid4()), "createdAt": datetime.now(timezone.utc).isoformat(), **doc,
            })
