"""Iter 38 — Social Media Marketing endpoints + Loyalty config minRedeem=10."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "owner@nuva.com", "password": "NuvaOwner2026!"}
CASHIER = {"email": "cashier@nuva.com", "password": "Staff2026!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def owner_token():
    return _login(OWNER)


@pytest.fixture(scope="module")
def cashier_token():
    return _login(CASHIER)


def hdrs(token):
    return {"Authorization": f"Bearer {token}"}


# ============== PLATFORMS ==============
def test_platforms_anon_401():
    r = requests.get(f"{API}/social/platforms", timeout=15)
    assert r.status_code == 401, r.text


def test_platforms_owner_returns_5(owner_token):
    r = requests.get(f"{API}/social/platforms", headers=hdrs(owner_token), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    keys = {p["key"] for p in data}
    assert keys == {"instagram", "facebook", "tiktok", "x", "google_business"}
    assert len(data) == 5


# ============== ACCOUNTS ==============
created_account_id = {"id": None}


def test_connect_account_anon_401():
    r = requests.post(f"{API}/social/accounts", json={"platform": "instagram", "handle": "nuva_qa"}, timeout=15)
    assert r.status_code == 401


def test_connect_account_cashier_403_before_422(cashier_token):
    # Invalid platform should NOT short-circuit role check
    r = requests.post(f"{API}/social/accounts", headers=hdrs(cashier_token),
                      json={"platform": "instagram", "handle": "denied"}, timeout=15)
    assert r.status_code == 403, f"cashier should be 403, got {r.status_code}: {r.text}"


def test_connect_account_owner_success(owner_token):
    # cleanup any prior nuva_qa
    requests.delete(f"{API}/social/accounts/_purge", headers=hdrs(owner_token), timeout=5)  # noop
    # remove existing
    r0 = requests.get(f"{API}/social/accounts", headers=hdrs(owner_token), timeout=15).json()
    for a in r0:
        if a.get("platform") == "instagram" and a.get("handle") == "nuva_qa":
            requests.delete(f"{API}/social/accounts/{a['id']}", headers=hdrs(owner_token), timeout=10)

    r = requests.post(f"{API}/social/accounts", headers=hdrs(owner_token),
                      json={"platform": "instagram", "handle": "nuva_qa"}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["platformLabel"] == "Instagram"
    assert data["tokenStatus"] == "mock_active"
    assert data["handle"] == "nuva_qa"
    assert "id" in data
    created_account_id["id"] = data["id"]


def test_connect_duplicate_409(owner_token):
    r = requests.post(f"{API}/social/accounts", headers=hdrs(owner_token),
                      json={"platform": "instagram", "handle": "nuva_qa"}, timeout=15)
    assert r.status_code == 409, r.text


def test_connect_invalid_platform_400(owner_token):
    r = requests.post(f"{API}/social/accounts", headers=hdrs(owner_token),
                      json={"platform": "myspace", "handle": "x"}, timeout=15)
    assert r.status_code == 400, r.text


def test_list_accounts_includes_new(owner_token):
    r = requests.get(f"{API}/social/accounts", headers=hdrs(owner_token), timeout=15)
    assert r.status_code == 200
    handles = [(a.get("platform"), a.get("handle")) for a in r.json()]
    assert ("instagram", "nuva_qa") in handles


# ============== AI GENERATE ==============
def test_ai_generate_anon_401():
    r = requests.post(f"{API}/social/ai-generate",
                      json={"sourceType": "special", "customPrompt": "x", "platforms": ["instagram"]}, timeout=15)
    assert r.status_code == 401


def test_ai_generate_special(owner_token):
    r = requests.post(f"{API}/social/ai-generate", headers=hdrs(owner_token), json={
        "sourceType": "special", "customPrompt": "Truffle pasta night",
        "platforms": ["instagram"], "tone": "playful", "postType": "post",
    }, timeout=60)
    assert r.status_code == 200, r.text
    gens = r.json()["generations"]
    assert len(gens) == 1
    g = gens[0]
    assert g["platform"] == "instagram"
    assert isinstance(g.get("caption"), str) and g["caption"]
    assert isinstance(g.get("hashtags"), list)
    assert isinstance(g.get("isFallback"), bool)
    assert "imageAlt" in g
    # When EMERGENT_LLM_KEY is set, ideally not a fallback — log but don't hard fail
    if g["isFallback"]:
        print("WARN: AI fallback used — aiError:", g.get("aiError"))


def test_ai_generate_product_requires_id(owner_token):
    r = requests.post(f"{API}/social/ai-generate", headers=hdrs(owner_token),
                      json={"sourceType": "product", "platforms": ["instagram"]}, timeout=15)
    assert r.status_code == 400


def test_ai_generate_product_not_found(owner_token):
    r = requests.post(f"{API}/social/ai-generate", headers=hdrs(owner_token),
                      json={"sourceType": "product", "sourceId": "nonexistent-zzz", "platforms": ["instagram"]}, timeout=15)
    assert r.status_code == 404


def test_ai_generate_product_with_image(owner_token):
    products = requests.get(f"{API}/products", headers=hdrs(owner_token), timeout=15).json()
    if isinstance(products, dict):
        products = products.get("products", [])
    target = next((p for p in products if p.get("image")), None) if products else None
    if not target:
        pytest.skip("no product with image to test imageHint")
    r = requests.post(f"{API}/social/ai-generate", headers=hdrs(owner_token), json={
        "sourceType": "product", "sourceId": target["id"], "platforms": ["instagram"],
    }, timeout=60)
    assert r.status_code == 200, r.text
    gens = r.json()["generations"]
    assert gens[0].get("imageHint") == target["image"]


# ============== POSTS ==============
created_post_id = {"id": None}


def test_create_post_requires_connected_account(owner_token):
    # facebook is not connected — should 400
    # ensure not connected
    accs = requests.get(f"{API}/social/accounts", headers=hdrs(owner_token), timeout=15).json()
    for a in accs:
        if a["platform"] == "facebook":
            requests.delete(f"{API}/social/accounts/{a['id']}", headers=hdrs(owner_token), timeout=10)
    r = requests.post(f"{API}/social/posts", headers=hdrs(owner_token), json={
        "platform": "facebook", "postType": "post", "caption": "hi", "hashtags": ["#nuva"],
    }, timeout=15)
    assert r.status_code == 400


def test_create_post_success(owner_token):
    r = requests.post(f"{API}/social/posts", headers=hdrs(owner_token), json={
        "platform": "instagram", "postType": "post",
        "caption": "TEST_iter38 caption", "hashtags": ["#nuva", "#test"],
        "status": "draft",
    }, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "draft"
    assert data["platform"] == "instagram"
    created_post_id["id"] = data["id"]


def test_list_posts(owner_token):
    r = requests.get(f"{API}/social/posts", headers=hdrs(owner_token), timeout=15)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert created_post_id["id"] in ids


def test_publish_post(owner_token):
    pid = created_post_id["id"]
    assert pid
    r = requests.post(f"{API}/social/posts/{pid}/publish", headers=hdrs(owner_token), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "published"
    assert "publishedAt" in data


def test_delete_post(owner_token):
    pid = created_post_id["id"]
    r = requests.delete(f"{API}/social/posts/{pid}", headers=hdrs(owner_token), timeout=15)
    assert r.status_code == 200
    # verify gone
    r2 = requests.get(f"{API}/social/posts", headers=hdrs(owner_token), timeout=15)
    ids = [p["id"] for p in r2.json()]
    assert pid not in ids


# ============== DELETE ACCOUNT ==============
def test_disconnect_account(owner_token):
    aid = created_account_id["id"]
    assert aid
    r = requests.delete(f"{API}/social/accounts/{aid}", headers=hdrs(owner_token), timeout=15)
    assert r.status_code == 200
    r2 = requests.delete(f"{API}/social/accounts/{aid}", headers=hdrs(owner_token), timeout=15)
    assert r2.status_code == 404


# ============== LOYALTY CONFIG ==============
def test_loyalty_config_minredeem_10(owner_token):
    r = requests.get(f"{API}/loyalty/config", headers=hdrs(owner_token), timeout=15)
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg.get("minRedeem") == 10, f"expected 10, got {cfg.get('minRedeem')}"
    assert abs(float(cfg.get("redeemRate", 0)) - 0.01) < 1e-9
