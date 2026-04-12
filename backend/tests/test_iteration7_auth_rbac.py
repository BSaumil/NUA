"""
Iteration 7 Tests: Auth/RBAC, Staff Management, AI Pantry, Member Portal, Multi-Business
Tests for new features added in NUVA POS v4.0
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OWNER_CREDS = {"email": "owner@nuva.com", "password": "NUVAOwner2026!"}
MANAGER_CREDS = {"email": "manager@nuva.com", "password": "Staff2026!"}
CASHIER_CREDS = {"email": "cashier@nuva.com", "password": "Staff2026!"}
KITCHEN_CREDS = {"email": "kitchen@nuva.com", "password": "Staff2026!"}


class TestAuthLogin:
    """Test authentication login endpoint"""
    
    def test_owner_login_success(self):
        """Owner login returns user and token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["user"]["email"] == "owner@nuva.com"
        assert data["user"]["role"] == "owner"
        assert len(data["token"]) > 0
        print(f"PASS: Owner login successful, role={data['user']['role']}")
    
    def test_manager_login_success(self):
        """Manager login returns user and token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "manager"
        print(f"PASS: Manager login successful")
    
    def test_cashier_login_success(self):
        """Cashier login returns user and token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "cashier"
        print(f"PASS: Cashier login successful")
    
    def test_kitchen_login_success(self):
        """Kitchen login returns user and token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=KITCHEN_CREDS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "kitchen"
        print(f"PASS: Kitchen login successful")
    
    def test_invalid_credentials_rejected(self):
        """Invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "wrong@test.com", "password": "wrong"})
        assert response.status_code == 401
        print(f"PASS: Invalid credentials rejected with 401")


class TestAuthMe:
    """Test /auth/me endpoint with permissions"""
    
    def test_owner_me_returns_all_permissions(self):
        """Owner /me returns user with all permissions"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "owner"
        assert "permissions" in data
        assert "*" in data["permissions"]  # Owner has all permissions
        print(f"PASS: Owner /me returns permissions: {data['permissions']}")
    
    def test_cashier_me_returns_limited_permissions(self):
        """Cashier /me returns limited permissions"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "cashier"
        assert "permissions" in data
        # Cashier should have limited permissions
        assert "pos" in data["permissions"]
        assert "tables" in data["permissions"] or "customers" in data["permissions"]
        # Cashier should NOT have accounting
        assert "accounting" not in data["permissions"]
        print(f"PASS: Cashier /me returns limited permissions: {data['permissions']}")
    
    def test_kitchen_me_returns_kitchen_permissions(self):
        """Kitchen /me returns kitchen-only permissions"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=KITCHEN_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "kitchen"
        assert "permissions" in data
        assert "kitchen" in data["permissions"]
        assert "pre-shift" in data["permissions"]
        print(f"PASS: Kitchen /me returns permissions: {data['permissions']}")
    
    def test_me_without_token_returns_401(self):
        """Accessing /me without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print(f"PASS: /me without token returns 401")


class TestStaffManagement:
    """Test staff management endpoints"""
    
    def test_owner_can_get_staff_with_payrate(self):
        """Owner can see all staff with payRate"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/staff", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        staff = response.json()
        assert isinstance(staff, list)
        assert len(staff) >= 4  # At least owner, manager, cashier, kitchen
        
        # Owner should see payRate
        for s in staff:
            if s["role"] != "owner":
                assert "payRate" in s, f"Staff {s['email']} missing payRate"
        print(f"PASS: Owner sees {len(staff)} staff members with payRate")
    
    def test_manager_can_get_staff_without_payrate(self):
        """Manager can see staff but WITHOUT payRate"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/staff", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        staff = response.json()
        
        # Manager should NOT see payRate
        for s in staff:
            assert "payRate" not in s, f"Manager should not see payRate for {s['email']}"
        print(f"PASS: Manager sees staff WITHOUT payRate")
    
    def test_cashier_cannot_access_staff(self):
        """Cashier cannot access staff endpoint"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/staff", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        print(f"PASS: Cashier gets 403 on staff endpoint")


class TestLaborCostReport:
    """Test owner-only labor cost report"""
    
    def test_owner_can_access_labor_cost_report(self):
        """Owner can access labor cost report with financial data"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/reports/labor-cost", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "totalRevenue" in data
        assert "cogs" in data
        assert "totalRosterCost" in data
        assert "netProfit" in data
        assert "staff" in data
        assert isinstance(data["staff"], list)
        print(f"PASS: Owner sees labor report - Revenue: ${data['totalRevenue']}, Net Profit: ${data['netProfit']}")
    
    def test_cashier_cannot_access_labor_cost_report(self):
        """Cashier gets 403 on labor cost report"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/reports/labor-cost", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        print(f"PASS: Cashier gets 403 on labor cost report")
    
    def test_manager_cannot_access_labor_cost_report(self):
        """Manager gets 403 on labor cost report (owner only)"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/auth/reports/labor-cost", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        print(f"PASS: Manager gets 403 on labor cost report")


class TestMemberPortal:
    """Test member signup, login, vouchers"""
    
    def test_member_signup_creates_account_with_bonus(self):
        """Member signup creates account with 50 points and welcome voucher"""
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/members/signup", json={
            "name": "Test Member",
            "email": test_email,
            "phone": "0400000000",
            "password": "TestPass123!"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "member" in data
        assert "token" in data
        member = data["member"]
        assert member["points"] == 50, f"Expected 50 bonus points, got {member['points']}"
        assert member["tier"] == "Bronze"
        assert len(member["vouchers"]) >= 1, "Expected welcome voucher"
        assert "Welcome" in member["vouchers"][0]["name"]
        assert member["referralCode"] is not None
        print(f"PASS: Member signup - 50 points, welcome voucher, referral code: {member['referralCode']}")
        
        return test_email, "TestPass123!"
    
    def test_member_login_works(self):
        """Member login works after signup"""
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        
        # First signup
        signup_res = requests.post(f"{BASE_URL}/api/members/signup", json={
            "name": "Login Test",
            "email": test_email,
            "phone": "0400000001",
            "password": "LoginTest123!"
        })
        assert signup_res.status_code == 200
        
        # Then login
        login_res = requests.post(f"{BASE_URL}/api/members/login", json={
            "email": test_email,
            "password": "LoginTest123!"
        })
        assert login_res.status_code == 200
        data = login_res.json()
        assert "member" in data
        assert "token" in data
        print(f"PASS: Member login works after signup")
    
    def test_member_duplicate_email_rejected(self):
        """Duplicate member email is rejected"""
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        
        # First signup
        requests.post(f"{BASE_URL}/api/members/signup", json={
            "name": "First",
            "email": test_email,
            "phone": "0400000002",
            "password": "Test123!"
        })
        
        # Second signup with same email
        response = requests.post(f"{BASE_URL}/api/members/signup", json={
            "name": "Second",
            "email": test_email,
            "phone": "0400000003",
            "password": "Test123!"
        })
        assert response.status_code == 400
        print(f"PASS: Duplicate member email rejected")


class TestVouchers:
    """Test voucher creation and management"""
    
    def test_create_voucher(self):
        """Create voucher endpoint works"""
        response = requests.post(f"{BASE_URL}/api/vouchers/create", json={
            "name": "Test Promo 20% Off",
            "type": "percentage",
            "value": 20,
            "minSpend": 50,
            "maxUses": 100
        })
        assert response.status_code == 200
        voucher = response.json()
        assert voucher["name"] == "Test Promo 20% Off"
        assert voucher["value"] == 20
        assert voucher["type"] == "percentage"
        assert "code" in voucher
        print(f"PASS: Voucher created with code: {voucher['code']}")
    
    def test_get_all_vouchers(self):
        """Get all vouchers endpoint works"""
        response = requests.get(f"{BASE_URL}/api/vouchers")
        assert response.status_code == 200
        vouchers = response.json()
        assert isinstance(vouchers, list)
        print(f"PASS: Got {len(vouchers)} vouchers")


class TestMultiBusiness:
    """Test multi-business management"""
    
    def test_owner_can_create_business(self):
        """Owner can create a new business"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        token = login.json()["token"]
        
        import uuid
        biz_name = f"Test Cafe {uuid.uuid4().hex[:6]}"
        
        response = requests.post(f"{BASE_URL}/api/business/create", 
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": biz_name,
                "type": "cafe",
                "abn": "12345678901",
                "address": "123 Test St",
                "phone": "0400000000",
                "email": "test@cafe.com"
            })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        business = response.json()
        assert business["name"] == biz_name
        assert business["type"] == "cafe"
        assert "id" in business
        print(f"PASS: Business created: {business['id']}")
        return business["id"]
    
    def test_owner_can_list_businesses(self):
        """Owner can list their businesses"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/business/list", 
            headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        businesses = response.json()
        assert isinstance(businesses, list)
        print(f"PASS: Owner has {len(businesses)} businesses")
    
    def test_cashier_cannot_create_business(self):
        """Cashier cannot create business"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        token = login.json()["token"]
        
        response = requests.post(f"{BASE_URL}/api/business/create", 
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Unauthorized Biz"})
        assert response.status_code == 403
        print(f"PASS: Cashier gets 403 on business create")


class TestAIPantry:
    """Test AI Smart Pantry endpoints"""
    
    def test_owner_can_access_pantry_history(self):
        """Owner can access pantry history"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/ai-pantry/history", 
            headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        print(f"PASS: Pantry history accessible, {len(history)} entries")
    
    def test_cashier_cannot_access_pantry(self):
        """Cashier cannot access AI pantry"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        token = login.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/ai-pantry/history", 
            headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        print(f"PASS: Cashier gets 403 on AI pantry")
    
    def test_ai_pantry_generate_endpoint_exists(self):
        """AI pantry generate endpoint exists (may take time due to GPT call)"""
        login = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        token = login.json()["token"]
        
        # Just check endpoint exists - actual generation takes time
        response = requests.get(f"{BASE_URL}/api/ai-pantry/generate", 
            headers={"Authorization": f"Bearer {token}"},
            timeout=60)  # Allow 60s for GPT response
        # Should be 200 or 500 (if AI not configured), not 404
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        print(f"PASS: AI pantry generate endpoint exists, status: {response.status_code}")


class TestRegressionChecks:
    """Regression tests for existing features"""
    
    def test_api_root(self):
        """API root returns v4.0.0"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "4.0.0"
        print(f"PASS: API version {data['version']}")
    
    def test_products_endpoint(self):
        """Products endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        print(f"PASS: Products endpoint returns {len(products)} items")
    
    def test_customers_endpoint(self):
        """Customers endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        customers = response.json()
        assert isinstance(customers, list)
        print(f"PASS: Customers endpoint returns {len(customers)} items")
    
    def test_reservations_endpoint(self):
        """Reservations endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        reservations = response.json()
        assert isinstance(reservations, list)
        print(f"PASS: Reservations endpoint returns {len(reservations)} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
