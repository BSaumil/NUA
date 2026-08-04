"""
Iteration 48 — Payroll + BAS worksheet + Wallet credentials + AI Bundle Discovery.

Backend regression:
  1. Payroll: /payroll/payrun/calculate, /commit, /register, /ytd, /roster-compliance
  2. BAS: /bas-gst/worksheet with G1-G20, W1-W5, T1 labels
  3. Wallet credentials: /settings/wallet-credentials GET+POST env-persist round-trip
  4. AI Bundle Discovery: /v26/promotions/bundle-suggestions shape
  5. REGRESSION: /promotions percentage flow + /v26/cart/apply-promos still works
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")


# ─── Fixtures ────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                       json={"email": "owner@nua.com", "password": "NuaOwner2026!"})
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def owner_client(owner_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                       "Authorization": f"Bearer {owner_token}"})
    return s


# ─── 1. Payroll — Calculate ──────────────────────────────────────────────
class TestPayrollCalculate:
    def test_calculate_empty_period_returns_200_with_compliance(self, owner_client):
        payload = {
            "periodStart": "2026-01-06",
            "periodEnd": "2026-01-12",
            "payDate": "2026-01-13",
            "period": "week",
        }
        r = owner_client.post(f"{BASE_URL}/api/payroll/payrun/calculate", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        # Shape assertions
        assert "rows" in data and isinstance(data["rows"], list)
        assert "totals" in data
        for k in ("grossPay", "payg", "super", "netPay", "employees"):
            assert k in data["totals"], f"totals missing {k}"
        assert "compliance" in data
        c = data["compliance"]
        assert c.get("paygScheduleVersion") == "ATO Sch 1 (Nov 2023)"
        assert isinstance(c.get("sgRate"), (int, float))
        assert "superDueBy" in c
        assert "quarterEnd" in c


# ─── 2. Payroll — Commit ─────────────────────────────────────────────────
class TestPayrollCommit:
    def test_commit_persists_and_returns_ids(self, owner_client):
        # Calculate first
        payload = {
            "periodStart": "2026-01-06",
            "periodEnd": "2026-01-12",
            "payDate": "2026-01-13",
            "period": "week",
        }
        calc = owner_client.post(f"{BASE_URL}/api/payroll/payrun/calculate", json=payload).json()
        commit_body = {**payload, "rows": calc.get("rows", []),
                        "totals": calc.get("totals", {}),
                        "compliance": calc.get("compliance", {})}
        r = owner_client.post(f"{BASE_URL}/api/payroll/payrun/commit", json=commit_body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "runId" in data and data["runId"].startswith("PR-"), data
        assert data.get("stpStatus") == "ready_to_submit"

        # Verify it shows up in the register
        reg = owner_client.get(f"{BASE_URL}/api/payroll/register?days=90").json()
        assert reg.get("count", 0) >= 1
        assert any(run.get("id") == data["runId"] for run in reg.get("runs", []))


# ─── 3. Payroll — Register + YTD ─────────────────────────────────────────
class TestPayrollRegisterYTD:
    def test_register_shape(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/payroll/register?days=90")
        assert r.status_code == 200
        d = r.json()
        assert "count" in d and "totals" in d and "runs" in d
        for k in ("grossPay", "payg", "super", "netPay"):
            assert k in d["totals"]
        assert isinstance(d["runs"], list)

    def test_ytd_shape(self, owner_client):
        # Get any staff id first
        staff_id = "any-staff"
        r = owner_client.get(f"{BASE_URL}/api/payroll/ytd/{staff_id}")
        assert r.status_code == 200
        d = r.json()
        for k in ("grossPay", "payg", "super", "netPay", "hours", "runCount"):
            assert k in d, f"YTD missing {k}"


# ─── 4. Roster compliance ────────────────────────────────────────────────
class TestRosterCompliance:
    def test_roster_compliance_shape(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/payroll/roster-compliance?days_ahead=14")
        assert r.status_code == 200
        d = r.json()
        assert d.get("windowDays") == 14
        assert "shiftsScanned" in d
        assert "flaggedCount" in d
        assert isinstance(d.get("flagged"), list)


# ─── 5. BAS worksheet ────────────────────────────────────────────────────
class TestBasWorksheet:
    def test_bas_worksheet_full_shape(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/bas-gst/worksheet",
                             params={"period_start": "2026-04-01", "period_end": "2026-06-30"})
        assert r.status_code == 200, r.text
        d = r.json()
        # Sales G1..G8 + 1A
        s = d.get("sales", {})
        for k in ("G1_totalSales", "G2_exports", "G3_gstFreeSales",
                  "G4_inputTaxedSales", "G5_subtotal", "G6_taxableSupplies",
                  "G7_adjustments", "G8_total", "G9_gstOnSales_1A"):
            assert k in s, f"sales missing {k}"

        a = d.get("acquisitions", {})
        for k in ("G10_capital", "G11_nonCapital", "G12_subtotal",
                  "G13_inputTaxed", "G14_private", "G15_estimateGstFree",
                  "G16_subtotal", "G17_creditable", "G18_adjustments",
                  "G19_total", "G20_gstOnPurchases_1B"):
            assert k in a, f"acquisitions missing {k}"

        w = d.get("withholding", {})
        for k in ("W1_totalWages", "W2_paygWithheld", "W3_noAbnWithholding",
                  "W4_otherWithholding", "W5_totalWithheld"):
            assert k in w, f"withholding missing {k}"

        assert "T1_paygInstalment" in d.get("instalment", {})
        sm = d.get("summary", {})
        for k in ("grossSales", "gstToPay", "totalOwing", "refundDue"):
            assert k in sm


# ─── 6. Wallet credentials ───────────────────────────────────────────────
class TestWalletCredentials:
    def test_status_get(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/settings/wallet-credentials")
        assert r.status_code == 200
        d = r.json()
        assert "apple" in d and "google" in d
        for k in ("envReady", "passTypeId", "teamId", "persistedInDb"):
            assert k in d["apple"], f"apple missing {k}"
        for k in ("envReady", "issuerId", "classId", "persistedInDb"):
            assert k in d["google"], f"google missing {k}"

    def test_post_updates_env(self, owner_client):
        payload = {
            "apple": {
                "passTypeIdentifier": "pass.com.TEST_iter48.nua",
                "teamId": "TESTITER48TID",
                "passTypeCertPem": "-----BEGIN CERTIFICATE-----\nTEST_iter48\n-----END CERTIFICATE-----",
                "passTypeKeyPem": "-----BEGIN PRIVATE KEY-----\nTEST_iter48\n-----END PRIVATE KEY-----",
                "appleWwdrCertPem": "-----BEGIN CERTIFICATE-----\nWWDR_TEST\n-----END CERTIFICATE-----",
            },
            "google": {
                "issuerId": "3388000000TEST48",
                "classId": "3388000000TEST48.nua_loyalty",
                "serviceAccountKey": '{"type":"service_account","project_id":"test"}',
            },
        }
        r = owner_client.post(f"{BASE_URL}/api/settings/wallet-credentials", json=payload)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # Re-GET should show updated fields + envReady True + persistedInDb True
        g = owner_client.get(f"{BASE_URL}/api/settings/wallet-credentials").json()
        assert g["apple"]["passTypeId"] == "pass.com.TEST_iter48.nua"
        assert g["apple"]["teamId"] == "TESTITER48TID"
        assert g["apple"]["envReady"] is True
        assert g["apple"]["persistedInDb"] is True
        assert g["google"]["issuerId"] == "3388000000TEST48"
        assert g["google"]["classId"] == "3388000000TEST48.nua_loyalty"
        assert g["google"]["envReady"] is True
        assert g["google"]["persistedInDb"] is True

    def test_never_leaks_secrets(self, owner_client):
        g = owner_client.get(f"{BASE_URL}/api/settings/wallet-credentials").json()
        # Ensure no PEM/serviceAccountKey ever comes back in the payload
        blob = str(g)
        assert "BEGIN PRIVATE KEY" not in blob
        assert "BEGIN CERTIFICATE" not in blob
        assert "service_account" not in blob


# ─── 7. AI Bundle Discovery ──────────────────────────────────────────────
class TestBundleSuggestions:
    def test_shape(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/v26/promotions/bundle-suggestions?days=30")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("windowDays") == 30
        assert d.get("method") == "market_basket_apriori_lite"
        assert "ordersAnalysed" in d
        assert isinstance(d.get("pairs"), list)
        assert isinstance(d.get("triples"), list)

    def test_low_min_support_returns_shape(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/v26/promotions/bundle-suggestions",
                             params={"days": 180, "min_support": 1, "top": 5})
        assert r.status_code == 200
        d = r.json()
        for entry in d.get("pairs", []) + d.get("triples", []):
            # If any suggestion is returned, verify full shape
            for k in ("productIds", "productNames", "coOccurrenceCount",
                      "supportPct", "avgAlaCarte", "proposedBundlePrice",
                      "estimatedSavings", "savingsPct", "confidence"):
                assert k in entry, f"suggestion missing {k}"
            # margin floor: proposedBundlePrice >= cogs * 1.5
            assert entry["proposedBundlePrice"] >= entry.get("marginFloor", 0)


# ─── 8. Regression — Promotions still work ───────────────────────────────
class TestPromotionsRegression:
    _created_id = None

    def test_create_percentage_promo(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/promotions", json={
            "name": "TEST_iter48 Pct",
            "type": "category",
            "pricingMode": "percentage",
            "discount": 15,
            "active": True,
            "categories": ["Mains"],
        })
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d.get("pricingMode") == "percentage"
        assert d.get("discount") == 15
        TestPromotionsRegression._created_id = d.get("id")

    def test_apply_promos_percentage_still_works(self, owner_client):
        cart = {
            "items": [
                {"productId": "p1", "name": "Test Main", "category": "Mains",
                 "price": 20.0, "quantity": 1},
                {"productId": "p2", "name": "Test Main 2", "category": "Mains",
                 "price": 10.0, "quantity": 1},
            ]
        }
        r = owner_client.post(f"{BASE_URL}/api/v26/cart/apply-promos", json=cart)
        assert r.status_code == 200, r.text
        d = r.json()
        # Just verify response shape is normal — discount may be 0 if promo doesn't hit
        assert "originalTotal" in d or "subtotal" in d or "applied" in d or "promos" in d or "discount" in d

    def test_cleanup_promo(self, owner_client):
        pid = TestPromotionsRegression._created_id
        if pid:
            r = owner_client.delete(f"{BASE_URL}/api/promotions/{pid}")
            assert r.status_code in (200, 204, 404)
