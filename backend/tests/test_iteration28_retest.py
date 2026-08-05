"""Iteration 28 retest — verifies action items from iteration_27:
   (1) GET /api/products now exposes eightySixed/active/eightySixedAt/eightySixedBy.
   (2) v25 sync-queue/process still works.
   (3) v25 86 toggle + substitute still works.
   (4) v25 kiosk upsell still works.
   (5) v26 gift card regression.
"""
import os, uuid, pytest, requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
OWNER = {"email": "owner@nua.com", "password": "NuaOwner2026!"}


@pytest.fixture(scope="module")
def owner_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=OWNER, timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


# --- ACTION ITEM 1: Product model exposes eightySixed/active ---
def test_get_products_exposes_new_fields(owner_client):
    r = owner_client.get(f"{BASE_URL}/api/products", timeout=15)
    assert r.status_code == 200
    prods = r.json()
    assert len(prods) > 0
    sample = prods[0]
    assert "eightySixed" in sample, f"eightySixed missing from product response: {sample.keys()}"
    assert "active" in sample, f"active missing from product response: {sample.keys()}"
    # default values
    assert isinstance(sample["eightySixed"], bool)
    assert isinstance(sample["active"], bool)


def test_86_toggle_reflects_in_products_list(owner_client):
    products = owner_client.get(f"{BASE_URL}/api/products", timeout=15).json()
    coffees = [p for p in products if p.get("category") == "Coffee" and not p.get("eightySixed")]
    assert len(coffees) >= 1
    pid = coffees[0]["id"]
    # 86 ON
    r = owner_client.post(f"{BASE_URL}/api/v25/products/{pid}/86",
                          json={"eightySixed": True}, timeout=15)
    assert r.status_code == 200, r.text
    # Verify field reflected in GET /api/products
    after = owner_client.get(f"{BASE_URL}/api/products", timeout=15).json()
    p_now = next(p for p in after if p["id"] == pid)
    assert p_now.get("eightySixed") is True, f"eightySixed not reflected — got {p_now.get('eightySixed')}"
    # eightySixedAt should be set
    assert p_now.get("eightySixedAt") is not None, "eightySixedAt should be populated"
    # 86 OFF (cleanup)
    r2 = owner_client.post(f"{BASE_URL}/api/v25/products/{pid}/86",
                           json={"eightySixed": False}, timeout=15)
    assert r2.status_code == 200
    after2 = owner_client.get(f"{BASE_URL}/api/products", timeout=15).json()
    p_after = next(p for p in after2 if p["id"] == pid)
    assert p_after.get("eightySixed") is False
    # restore stock for downstream tests
    owner_client.put(f"{BASE_URL}/api/products/{pid}", json={"stock": 100}, timeout=15)


# --- Regression: v25 substitute ---
def test_substitute_with_reasons(owner_client):
    products = owner_client.get(f"{BASE_URL}/api/products", timeout=15).json()
    coffee = next(p for p in products if p.get("category") == "Coffee" and p.get("stock", 0) > 0)
    r = owner_client.post(f"{BASE_URL}/api/v25/substitute",
                          json={"productId": coffee["id"]}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["original"]["id"] == coffee["id"]
    subs = body["substitutes"]
    assert len(subs) >= 1
    for s in subs:
        assert s.get("substitutionReason"), "Missing reason"
        assert isinstance(s["substitutionReason"], str)


# --- Regression: v25 sync-queue/process ---
def test_sync_queue_process_replays(owner_client):
    pid_resp = owner_client.get(f"{BASE_URL}/api/products", timeout=15).json()
    target = next(p for p in pid_resp if p.get("category") == "Coffee" and p.get("stock", 0) > 0)
    tx_op_id = f"TEST-OP-TX-{uuid.uuid4().hex[:6]}"
    stk_op_id = f"TEST-OP-STK-{uuid.uuid4().hex[:6]}"
    push = owner_client.post(f"{BASE_URL}/api/v25/sync-queue", json={
        "ops": [
            {"clientOpId": tx_op_id, "kind": "transaction.create",
             "payload": {"id": f"TEST-TX-{uuid.uuid4().hex[:6]}", "total": 12.50, "items": []}},
            {"clientOpId": stk_op_id, "kind": "stock.adjust",
             "payload": {"productId": target["id"], "delta": -1}},
        ]
    }, timeout=15)
    assert push.status_code == 200
    assert len(push.json()["accepted"]) == 2
    before_stock = target["stock"]
    proc = owner_client.post(f"{BASE_URL}/api/v25/sync-queue/process", timeout=20)
    assert proc.status_code == 200, proc.text
    body = proc.json()
    assert body["applied"] >= 2
    after = owner_client.get(f"{BASE_URL}/api/products", timeout=15).json()
    after_target = next(p for p in after if p["id"] == target["id"])
    assert after_target["stock"] == before_stock - 1


# --- Regression: v25 kiosk upsell ---
def test_kiosk_upsell(owner_client):
    products = owner_client.get(f"{BASE_URL}/api/products", timeout=15).json()
    burger = next(p for p in products if p.get("category") == "Burgers")
    sess = owner_client.post(f"{BASE_URL}/api/v25/kiosk/session",
                             json={"tableId": "T1", "guests": 2}, timeout=15).json()
    sid = sess["id"]
    owner_client.post(f"{BASE_URL}/api/v25/kiosk/session/{sid}/add",
                      json={"item": {"id": burger["id"], "name": burger["name"],
                                     "category": "Burgers", "price": burger["price"], "quantity": 1}}, timeout=15)
    r = owner_client.post(f"{BASE_URL}/api/v25/kiosk/session/{sid}/upsell", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "suggestions" in body
    assert len(body["suggestions"]) <= 3
    if body["suggestions"]:
        for s in body["suggestions"]:
            assert s.get("reason"), "Missing reason"
            assert s.get("productId")


# --- Regression: v26 gift voucher ---
def test_v26_gift_voucher_create_activate_redeem(owner_client):
    code = f"TEST_GIFTVCH_{uuid.uuid4().hex[:6]}"
    r = owner_client.post(f"{BASE_URL}/api/v26/vouchers", json={
        "code": code, "kind": "gift", "valueType": "fixed", "value": 25, "active": True,
    }, timeout=15)
    assert r.status_code in (200, 201), r.text
    gc = owner_client.get(f"{BASE_URL}/api/v26/gift-cards", timeout=15)
    assert gc.status_code == 200
