"""
Iteration 8 Backend Tests - NUA POS Endgame Features
Tests: Email Marketing, End-of-Day Reports, Tip Management, Training Mode
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pos-checkout-16.preview.emergentagent.com')

# Test credentials
OWNER_CREDS = {"email": "owner@nua.com", "password": "NuaOwner2026!"}
MANAGER_CREDS = {"email": "manager@nua.com", "password": "Staff2026!"}
CASHIER_CREDS = {"email": "cashier@nua.com", "password": "Staff2026!"}
KITCHEN_CREDS = {"email": "kitchen@nua.com", "password": "Staff2026!"}


@pytest.fixture(scope="module")
def owner_token():
    """Get owner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    assert data["user"]["role"] == "owner", "User is not owner"
    return data["token"]


@pytest.fixture(scope="module")
def manager_token():
    """Get manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def cashier_token():
    """Get cashier auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
    assert response.status_code == 200, f"Cashier login failed: {response.text}"
    return response.json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ============ AUTH TESTS ============
class TestAuth:
    """Authentication endpoint tests"""
    
    def test_owner_login_success(self):
        """Owner can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "owner@nua.com"
        assert data["user"]["role"] == "owner"
    
    def test_manager_login_success(self):
        """Manager can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "manager"
    
    def test_cashier_login_success(self):
        """Cashier can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "cashier"
    
    def test_invalid_credentials_rejected(self):
        """Invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@nua.com", "password": "wrongpass"
        })
        assert response.status_code == 401


# ============ TIP MANAGEMENT TESTS ============
class TestTipManagement:
    """Tip Management endpoint tests (Toast-style)"""
    
    def test_add_tip_success(self, owner_token):
        """Owner can add a tip"""
        tip_data = {
            "staffName": f"TEST_Staff_{uuid.uuid4().hex[:6]}",
            "amount": 15.50,
            "method": "card",
            "pooled": False,
            "staffId": "test-staff-id"
        }
        response = requests.post(
            f"{BASE_URL}/api/tips/add",
            json=tip_data,
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["id"].startswith("TIP-")
        assert data["amount"] == 15.50
        assert data["method"] == "card"
        assert data["pooled"] == False
    
    def test_add_pooled_tip(self, owner_token):
        """Can add a pooled tip"""
        tip_data = {
            "staffName": f"TEST_PoolStaff_{uuid.uuid4().hex[:6]}",
            "amount": 20.00,
            "method": "cash",
            "pooled": True
        }
        response = requests.post(
            f"{BASE_URL}/api/tips/add",
            json=tip_data,
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pooled"] == True
    
    def test_get_tips_owner_access(self, owner_token):
        """Owner can get all tips"""
        response = requests.get(
            f"{BASE_URL}/api/tips",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_tips_manager_access(self, manager_token):
        """Manager can get all tips"""
        response = requests.get(
            f"{BASE_URL}/api/tips",
            headers=auth_header(manager_token)
        )
        assert response.status_code == 200
    
    def test_get_tips_cashier_denied(self, cashier_token):
        """Cashier cannot get tips"""
        response = requests.get(
            f"{BASE_URL}/api/tips",
            headers=auth_header(cashier_token)
        )
        assert response.status_code == 403
    
    def test_get_tips_summary_owner_only(self, owner_token, manager_token):
        """Only owner can get tips summary"""
        # Owner can access
        response = requests.get(
            f"{BASE_URL}/api/tips/summary",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "totalTips" in data
        assert "pooledAmount" in data
        assert "byStaff" in data
        assert "tipCount" in data
        
        # Manager cannot access
        response = requests.get(
            f"{BASE_URL}/api/tips/summary",
            headers=auth_header(manager_token)
        )
        assert response.status_code == 403
    
    def test_distribute_tip_pool_owner_only(self, owner_token, manager_token):
        """Only owner can distribute tip pool"""
        # Owner can distribute
        response = requests.post(
            f"{BASE_URL}/api/tips/pool-distribute",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "distributed" in data
        assert "perPerson" in data
        
        # Manager cannot distribute
        response = requests.post(
            f"{BASE_URL}/api/tips/pool-distribute",
            headers=auth_header(manager_token)
        )
        assert response.status_code == 403


# ============ TRAINING MODE TESTS ============
class TestTrainingMode:
    """Training Mode endpoint tests (Clover-style)"""
    
    def test_get_training_mode(self, owner_token):
        """Can get training mode status"""
        response = requests.get(
            f"{BASE_URL}/api/settings/training-mode",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)
    
    def test_toggle_training_mode_owner(self, owner_token):
        """Owner can toggle training mode"""
        # Enable
        response = requests.post(
            f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": True},
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == True
        
        # Disable
        response = requests.post(
            f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": False},
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False
    
    def test_toggle_training_mode_manager(self, manager_token):
        """Manager can toggle training mode"""
        response = requests.post(
            f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": True},
            headers=auth_header(manager_token)
        )
        assert response.status_code == 200
        
        # Reset
        requests.post(
            f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": False},
            headers=auth_header(manager_token)
        )
    
    def test_toggle_training_mode_cashier_denied(self, cashier_token):
        """Cashier cannot toggle training mode"""
        response = requests.post(
            f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": True},
            headers=auth_header(cashier_token)
        )
        assert response.status_code == 403


# ============ END-OF-DAY REPORTS TESTS ============
class TestEndOfDayReports:
    """End-of-Day Reports endpoint tests (Square-style)"""
    
    def test_get_eod_report_owner(self, owner_token):
        """Owner can get EOD report"""
        response = requests.get(
            f"{BASE_URL}/api/reports/end-of-day",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "date" in data
        assert "summary" in data
        assert "byPaymentMethod" in data
        assert "byHour" in data
        assert "topItems" in data
        
        # Verify summary fields
        summary = data["summary"]
        assert "totalSales" in summary
        assert "totalTransactions" in summary
        assert "avgTicket" in summary
        assert "totalRefunds" in summary
        assert "totalTips" in summary
        assert "totalGST" in summary
        assert "netSales" in summary
    
    def test_get_eod_report_manager(self, manager_token):
        """Manager can get EOD report"""
        response = requests.get(
            f"{BASE_URL}/api/reports/end-of-day",
            headers=auth_header(manager_token)
        )
        assert response.status_code == 200
    
    def test_get_eod_report_cashier_denied(self, cashier_token):
        """Cashier cannot get EOD report"""
        response = requests.get(
            f"{BASE_URL}/api/reports/end-of-day",
            headers=auth_header(cashier_token)
        )
        assert response.status_code == 403


# ============ EMAIL MARKETING TESTS ============
class TestEmailMarketing:
    """Email Marketing Campaign endpoint tests"""
    
    @pytest.fixture
    def test_campaign_id(self, owner_token):
        """Create a test campaign and return its ID"""
        campaign_data = {
            "name": f"TEST_Campaign_{uuid.uuid4().hex[:6]}",
            "subject": "Test Subject Line",
            "body": "<p>Test email body content</p>",
            "targetTier": "Gold"
        }
        response = requests.post(
            f"{BASE_URL}/api/marketing/campaigns",
            json=campaign_data,
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_create_campaign_owner(self, owner_token):
        """Owner can create email campaign"""
        campaign_data = {
            "name": f"TEST_OwnerCampaign_{uuid.uuid4().hex[:6]}",
            "subject": "Special Offer for You!",
            "body": "<h1>Hello!</h1><p>Check out our new menu items.</p>",
            "targetTier": "Silver"
        }
        response = requests.post(
            f"{BASE_URL}/api/marketing/campaigns",
            json=campaign_data,
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"].startswith("CMP-")
        assert data["name"] == campaign_data["name"]
        assert data["subject"] == campaign_data["subject"]
        assert data["status"] == "draft"
        assert data["targetTier"] == "Silver"
    
    def test_create_campaign_manager(self, manager_token):
        """Manager can create email campaign"""
        campaign_data = {
            "name": f"TEST_ManagerCampaign_{uuid.uuid4().hex[:6]}",
            "subject": "Manager's Newsletter",
            "body": "Content here",
            "targetTier": ""  # All members
        }
        response = requests.post(
            f"{BASE_URL}/api/marketing/campaigns",
            json=campaign_data,
            headers=auth_header(manager_token)
        )
        assert response.status_code == 200
    
    def test_create_campaign_cashier_denied(self, cashier_token):
        """Cashier cannot create email campaign"""
        response = requests.post(
            f"{BASE_URL}/api/marketing/campaigns",
            json={"name": "Test", "subject": "Test", "body": "Test"},
            headers=auth_header(cashier_token)
        )
        assert response.status_code == 403
    
    def test_get_campaigns_owner(self, owner_token):
        """Owner can get all campaigns"""
        response = requests.get(
            f"{BASE_URL}/api/marketing/campaigns",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_campaigns_cashier_denied(self, cashier_token):
        """Cashier cannot get campaigns"""
        response = requests.get(
            f"{BASE_URL}/api/marketing/campaigns",
            headers=auth_header(cashier_token)
        )
        assert response.status_code == 403
    
    def test_send_campaign(self, owner_token, test_campaign_id):
        """Owner can send a campaign"""
        response = requests.post(
            f"{BASE_URL}/api/marketing/campaigns/{test_campaign_id}/send",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "recipientCount" in data
    
    def test_delete_campaign(self, owner_token):
        """Owner can delete a campaign"""
        # Create a campaign to delete
        campaign_data = {
            "name": f"TEST_ToDelete_{uuid.uuid4().hex[:6]}",
            "subject": "Delete Me",
            "body": "This will be deleted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/marketing/campaigns",
            json=campaign_data,
            headers=auth_header(owner_token)
        )
        campaign_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/marketing/campaigns/{campaign_id}",
            headers=auth_header(owner_token)
        )
        assert response.status_code == 200
        
        # Verify it's gone
        campaigns = requests.get(
            f"{BASE_URL}/api/marketing/campaigns",
            headers=auth_header(owner_token)
        ).json()
        assert not any(c["id"] == campaign_id for c in campaigns)


# ============ RBAC SIDEBAR ACCESS TESTS ============
class TestRBACAccess:
    """Test role-based access control for new features"""
    
    def test_owner_has_full_access(self, owner_token):
        """Owner can access all new endpoints"""
        endpoints = [
            ("GET", "/api/tips"),
            ("GET", "/api/tips/summary"),
            ("GET", "/api/settings/training-mode"),
            ("GET", "/api/reports/end-of-day"),
            ("GET", "/api/marketing/campaigns"),
        ]
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=auth_header(owner_token))
            assert response.status_code == 200, f"Owner denied access to {endpoint}"
    
    def test_cashier_denied_advanced_features(self, cashier_token):
        """Cashier cannot access advanced features"""
        endpoints = [
            ("GET", "/api/tips"),
            ("GET", "/api/tips/summary"),
            ("GET", "/api/reports/end-of-day"),
            ("GET", "/api/marketing/campaigns"),
        ]
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=auth_header(cashier_token))
            assert response.status_code == 403, f"Cashier should be denied access to {endpoint}"


# ============ REGRESSION TESTS ============
class TestRegression:
    """Regression tests for existing functionality"""
    
    def test_api_root(self):
        """API root returns version"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
    
    def test_products_endpoint(self, owner_token):
        """Products endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/products", headers=auth_header(owner_token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_customers_endpoint(self, owner_token):
        """Customers endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/customers", headers=auth_header(owner_token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
