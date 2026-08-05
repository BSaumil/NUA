"""
Iteration 9 Backend Tests - Major Bug Fixes
Tests for: Products CRUD, Inventory Stock Adjustment, Forecasting, Settings (Locations/Staff/Business),
Accounting (Transactions/Refunds), End of Day Reports with date ranges
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests for all roles"""
    
    def test_owner_login(self):
        """Owner login with full access"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data["user"]["role"] == "owner"
        print(f"PASS: Owner login - role={data['user']['role']}")
        return data["token"]
    
    def test_manager_login(self):
        """Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "manager"
        print(f"PASS: Manager login - role={data['user']['role']}")
        return data["token"]
    
    def test_cashier_login(self):
        """Cashier login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "cashier@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200, f"Cashier login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "cashier"
        print(f"PASS: Cashier login - role={data['user']['role']}")
        return data["token"]


@pytest.fixture(scope="module")
def owner_token():
    """Get owner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "owner@nua.com",
        "password": "NuaOwner2026!"
    })
    if response.status_code != 200:
        pytest.skip("Owner login failed")
    return response.json()["token"]


@pytest.fixture(scope="module")
def cashier_token():
    """Get cashier auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "cashier@nua.com",
        "password": "Staff2026!"
    })
    if response.status_code != 200:
        pytest.skip("Cashier login failed")
    return response.json()["token"]


class TestProductsCRUD:
    """Products page - Add/Edit/Delete products"""
    
    def test_get_products(self, owner_token):
        """GET /api/products returns list"""
        response = requests.get(f"{BASE_URL}/api/products", 
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/products - {len(data)} products")
    
    def test_create_product(self, owner_token):
        """POST /api/products creates new product"""
        product_data = {
            "name": "TEST_Espresso",
            "category": "Beverages",
            "price": 4.50,
            "cost": 1.20,
            "stock": 100,
            "sku": "TEST-ESP-001",
            "image": "https://example.com/espresso.jpg",
            "gstRate": 10
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Create product failed: {response.text}"
        data = response.json()
        assert data["name"] == "TEST_Espresso"
        assert data["price"] == 4.50
        assert "id" in data
        print(f"PASS: Create product - id={data['id']}")
        return data["id"]
    
    def test_update_product(self, owner_token):
        """PUT /api/products/{id} updates product"""
        # First create a product
        create_resp = requests.post(f"{BASE_URL}/api/products", json={
            "name": "TEST_UpdateMe",
            "category": "Food",
            "price": 10.00,
            "cost": 5.00,
            "stock": 50,
            "sku": "TEST-UPD-001",
            "image": "https://example.com/test.jpg",
            "gstRate": 10
        }, headers={"Authorization": f"Bearer {owner_token}"})
        product_id = create_resp.json()["id"]
        
        # Update it
        update_resp = requests.put(f"{BASE_URL}/api/products/{product_id}", json={
            "name": "TEST_Updated",
            "price": 12.00
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        data = update_resp.json()
        assert data["name"] == "TEST_Updated"
        assert data["price"] == 12.00
        print(f"PASS: Update product - name={data['name']}, price={data['price']}")
    
    def test_delete_product(self, owner_token):
        """DELETE /api/products/{id} deletes product"""
        # Create a product to delete
        create_resp = requests.post(f"{BASE_URL}/api/products", json={
            "name": "TEST_DeleteMe",
            "category": "Other",
            "price": 5.00,
            "cost": 2.00,
            "stock": 10,
            "sku": "TEST-DEL-001",
            "image": "https://example.com/test.jpg",
            "gstRate": 10
        }, headers={"Authorization": f"Bearer {owner_token}"})
        product_id = create_resp.json()["id"]
        
        # Delete it
        delete_resp = requests.delete(f"{BASE_URL}/api/products/{product_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
        
        # Verify it's gone
        get_resp = requests.get(f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {owner_token}"})
        products = get_resp.json()
        assert not any(p["id"] == product_id for p in products)
        print(f"PASS: Delete product - id={product_id} removed")


class TestPromotionsCRUD:
    """Promotions - Create/Edit/Delete"""
    
    def test_get_promotions(self, owner_token):
        """GET /api/promotions returns list"""
        response = requests.get(f"{BASE_URL}/api/promotions",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/promotions - {len(data)} promotions")
    
    def test_create_promotion(self, owner_token):
        """POST /api/promotions creates promotion"""
        promo_data = {
            "name": "TEST_Happy Hour",
            "type": "category",
            "discount": 15,
            "schedule": "Mon-Fri 4pm-6pm",
            "active": True,
            "category": "Beverages"
        }
        response = requests.post(f"{BASE_URL}/api/promotions", json=promo_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Create promo failed: {response.text}"
        data = response.json()
        assert data["name"] == "TEST_Happy Hour"
        assert data["discount"] == 15
        print(f"PASS: Create promotion - id={data['id']}")
        return data["id"]
    
    def test_update_promotion(self, owner_token):
        """PUT /api/promotions/{id} updates promotion"""
        # Create first
        create_resp = requests.post(f"{BASE_URL}/api/promotions", json={
            "name": "TEST_UpdatePromo",
            "type": "bundle",
            "discount": 10,
            "schedule": "Weekends",
            "active": True
        }, headers={"Authorization": f"Bearer {owner_token}"})
        promo_id = create_resp.json()["id"]
        
        # Update
        update_resp = requests.put(f"{BASE_URL}/api/promotions/{promo_id}", json={
            "discount": 20,
            "active": False
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert update_resp.status_code == 200, f"Update promo failed: {update_resp.text}"
        data = update_resp.json()
        assert data["discount"] == 20
        assert data["active"] == False
        print(f"PASS: Update promotion - discount={data['discount']}, active={data['active']}")
    
    def test_delete_promotion(self, owner_token):
        """DELETE /api/promotions/{id} deletes promotion"""
        # Create
        create_resp = requests.post(f"{BASE_URL}/api/promotions", json={
            "name": "TEST_DeletePromo",
            "type": "category",
            "discount": 5,
            "schedule": "Daily",
            "active": True
        }, headers={"Authorization": f"Bearer {owner_token}"})
        promo_id = create_resp.json()["id"]
        
        # Delete
        delete_resp = requests.delete(f"{BASE_URL}/api/promotions/{promo_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert delete_resp.status_code == 200
        print(f"PASS: Delete promotion - id={promo_id}")


class TestInventoryStockAdjustment:
    """Inventory page - Stock adjustment"""
    
    def test_adjust_stock_positive(self, owner_token):
        """POST /api/products/{id}/adjust-stock with positive adjustment"""
        # Get a product
        products_resp = requests.get(f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {owner_token}"})
        products = products_resp.json()
        if not products:
            pytest.skip("No products to test stock adjustment")
        
        product = products[0]
        original_stock = product["stock"]
        
        # Adjust stock +10
        adjust_resp = requests.post(f"{BASE_URL}/api/products/{product['id']}/adjust-stock",
            json={"adjustment": 10, "reason": "Received shipment"},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert adjust_resp.status_code == 200, f"Adjust stock failed: {adjust_resp.text}"
        data = adjust_resp.json()
        assert data["newStock"] == original_stock + 10
        print(f"PASS: Adjust stock +10 - {original_stock} -> {data['newStock']}")
    
    def test_adjust_stock_negative(self, owner_token):
        """POST /api/products/{id}/adjust-stock with negative adjustment"""
        # Get a product with enough stock
        products_resp = requests.get(f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {owner_token}"})
        products = [p for p in products_resp.json() if p["stock"] >= 5]
        if not products:
            pytest.skip("No products with enough stock")
        
        product = products[0]
        original_stock = product["stock"]
        
        # Adjust stock -5
        adjust_resp = requests.post(f"{BASE_URL}/api/products/{product['id']}/adjust-stock",
            json={"adjustment": -5, "reason": "Damaged / waste"},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert adjust_resp.status_code == 200, f"Adjust stock failed: {adjust_resp.text}"
        data = adjust_resp.json()
        assert data["newStock"] == original_stock - 5
        print(f"PASS: Adjust stock -5 - {original_stock} -> {data['newStock']}")
    
    def test_adjust_stock_below_zero_fails(self, owner_token):
        """Stock cannot go below zero"""
        # Create a product with low stock
        create_resp = requests.post(f"{BASE_URL}/api/products", json={
            "name": "TEST_LowStock",
            "category": "Other",
            "price": 1.00,
            "cost": 0.50,
            "stock": 2,
            "sku": "TEST-LOW-001",
            "image": "https://example.com/test.jpg",
            "gstRate": 10
        }, headers={"Authorization": f"Bearer {owner_token}"})
        product_id = create_resp.json()["id"]
        
        # Try to adjust -10 (should fail)
        adjust_resp = requests.post(f"{BASE_URL}/api/products/{product_id}/adjust-stock",
            json={"adjustment": -10, "reason": "Test"},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert adjust_resp.status_code == 400, "Should fail when stock goes below zero"
        print("PASS: Stock adjustment below zero correctly rejected")


class TestForecasting:
    """Forecasting page - demand, table turns, roster"""
    
    def test_demand_forecast(self, owner_token):
        """GET /api/analytics/demand-forecast"""
        response = requests.get(f"{BASE_URL}/api/analytics/demand-forecast",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Demand forecast failed: {response.text}"
        data = response.json()
        assert "forecast" in data
        assert isinstance(data["forecast"], list)
        if data["forecast"]:
            day = data["forecast"][0]
            # Check field names exist (fixed field name mismatches)
            assert any(k in day for k in ["totalEstimatedCovers", "predictedCovers", "busyLevel"])
        print(f"PASS: Demand forecast - {len(data['forecast'])} days")
    
    def test_table_turns(self, owner_token):
        """GET /api/analytics/table-turns"""
        response = requests.get(f"{BASE_URL}/api/analytics/table-turns",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Table turns failed: {response.text}"
        data = response.json()
        assert "avgTurnTime" in data
        assert "optimization" in data
        print(f"PASS: Table turns - avgTurnTime={data['avgTurnTime']}")
    
    def test_smart_roster(self, owner_token):
        """GET /api/staff/smart-roster"""
        response = requests.get(f"{BASE_URL}/api/staff/smart-roster",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Smart roster failed: {response.text}"
        data = response.json()
        assert any(k in data for k in ["roster", "rosterSuggestions"])
        print(f"PASS: Smart roster loaded")


class TestSettingsLocations:
    """Settings > Locations tab - CRUD"""
    
    def test_get_locations(self, owner_token):
        """GET /api/locations"""
        response = requests.get(f"{BASE_URL}/api/locations",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/locations - {len(data)} locations")
    
    def test_create_location(self, owner_token):
        """POST /api/locations"""
        loc_data = {
            "name": "TEST_Branch",
            "address": "123 Test St",
            "phone": "0400000000"
        }
        response = requests.post(f"{BASE_URL}/api/locations", json=loc_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Create location failed: {response.text}"
        data = response.json()
        assert data["name"] == "TEST_Branch"
        print(f"PASS: Create location - id={data['id']}")
        return data["id"]
    
    def test_update_location(self, owner_token):
        """PUT /api/locations/{id}"""
        # Create first
        create_resp = requests.post(f"{BASE_URL}/api/locations", json={
            "name": "TEST_UpdateLoc",
            "address": "Old Address",
            "phone": "0400000001"
        }, headers={"Authorization": f"Bearer {owner_token}"})
        loc_id = create_resp.json()["id"]
        
        # Update
        update_resp = requests.put(f"{BASE_URL}/api/locations/{loc_id}", json={
            "address": "New Address 456"
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert update_resp.status_code == 200, f"Update location failed: {update_resp.text}"
        data = update_resp.json()
        assert data["address"] == "New Address 456"
        print(f"PASS: Update location - address={data['address']}")
    
    def test_delete_location(self, owner_token):
        """DELETE /api/locations/{id}"""
        # Create
        create_resp = requests.post(f"{BASE_URL}/api/locations", json={
            "name": "TEST_DeleteLoc",
            "address": "Delete Me",
            "phone": "0400000002"
        }, headers={"Authorization": f"Bearer {owner_token}"})
        loc_id = create_resp.json()["id"]
        
        # Delete
        delete_resp = requests.delete(f"{BASE_URL}/api/locations/{loc_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert delete_resp.status_code == 200
        print(f"PASS: Delete location - id={loc_id}")


class TestSettingsStaff:
    """Settings > Staff tab - real API"""
    
    def test_get_staff(self, owner_token):
        """GET /api/auth/staff returns staff list"""
        response = requests.get(f"{BASE_URL}/api/auth/staff",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Get staff failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # Should have owner, manager, cashier, kitchen
        roles = [s["role"] for s in data]
        assert "owner" in roles, "Owner not in staff list"
        print(f"PASS: GET /api/auth/staff - {len(data)} staff members, roles: {set(roles)}")
    
    def test_update_staff(self, owner_token):
        """PUT /api/auth/staff/{id} updates staff"""
        # Get staff list
        staff_resp = requests.get(f"{BASE_URL}/api/auth/staff",
            headers={"Authorization": f"Bearer {owner_token}"})
        staff = staff_resp.json()
        # Find a non-owner to update
        target = next((s for s in staff if s["role"] != "owner"), None)
        if not target:
            pytest.skip("No non-owner staff to update")
        
        # Update pay rate
        update_resp = requests.put(f"{BASE_URL}/api/auth/staff/{target['id']}", json={
            "name": target["name"],
            "role": target["role"],
            "payRate": 30.00
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert update_resp.status_code == 200, f"Update staff failed: {update_resp.text}"
        print(f"PASS: Update staff - {target['name']} payRate set")


class TestSettingsBusiness:
    """Settings > Business Info - save to DB"""
    
    def test_get_business_settings(self, owner_token):
        """GET /api/business/settings"""
        response = requests.get(f"{BASE_URL}/api/business/settings",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Get business settings failed: {response.text}"
        data = response.json()
        assert "name" in data
        print(f"PASS: GET /api/business/settings - name={data.get('name')}")
    
    def test_save_business_settings(self, owner_token):
        """POST /api/business/settings saves data"""
        biz_data = {
            "name": "NUA POS Test",
            "abn": "12 345 678 901",
            "address": "100 Test Street, Sydney",
            "phone": "02 1234 5678",
            "email": "test@nua.com",
            "taxId": "TAX123"
        }
        response = requests.post(f"{BASE_URL}/api/business/settings", json=biz_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Save business settings failed: {response.text}"
        
        # Verify it persisted
        get_resp = requests.get(f"{BASE_URL}/api/business/settings",
            headers={"Authorization": f"Bearer {owner_token}"})
        data = get_resp.json()
        assert data["abn"] == "12 345 678 901"
        print(f"PASS: Save business settings - abn={data['abn']}")


class TestSettingsTrainingMode:
    """Settings > Training Mode toggle"""
    
    def test_get_training_mode(self, owner_token):
        """GET /api/settings/training-mode"""
        response = requests.get(f"{BASE_URL}/api/settings/training-mode",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        print(f"PASS: GET training mode - enabled={data['enabled']}")
    
    def test_toggle_training_mode(self, owner_token):
        """POST /api/settings/training-mode toggles"""
        # Get current state
        get_resp = requests.get(f"{BASE_URL}/api/settings/training-mode",
            headers={"Authorization": f"Bearer {owner_token}"})
        current = get_resp.json()["enabled"]
        
        # Toggle
        toggle_resp = requests.post(f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": not current},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert toggle_resp.status_code == 200
        data = toggle_resp.json()
        assert data["enabled"] == (not current)
        
        # Toggle back
        requests.post(f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": current},
            headers={"Authorization": f"Bearer {owner_token}"})
        print(f"PASS: Toggle training mode - {current} -> {not current} -> {current}")


class TestAccountingTransactions:
    """Accounting page - transactions, details, refunds"""
    
    def test_get_transactions(self, owner_token):
        """GET /api/transactions returns list"""
        response = requests.get(f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/transactions - {len(data)} transactions")
        return data
    
    def test_get_transaction_detail(self, owner_token):
        """GET /api/transactions/{id} returns detail with refunds array"""
        # Get transactions
        txns_resp = requests.get(f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {owner_token}"})
        txns = txns_resp.json()
        if not txns:
            pytest.skip("No transactions to test detail")
        
        txn_id = txns[0]["id"]
        detail_resp = requests.get(f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert detail_resp.status_code == 200, f"Get detail failed: {detail_resp.text}"
        data = detail_resp.json()
        assert "id" in data
        assert "refunds" in data, "refunds array missing from transaction detail"
        assert isinstance(data["refunds"], list)
        print(f"PASS: GET /api/transactions/{txn_id} - has refunds array")
    
    def test_create_refund(self, owner_token):
        """POST /api/refunds creates refund"""
        # Get a transaction
        txns_resp = requests.get(f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {owner_token}"})
        txns = txns_resp.json()
        if not txns:
            pytest.skip("No transactions for refund test")
        
        txn = txns[0]
        refund_data = {
            "originalTransactionId": txn["id"],
            "amount": 5.00,
            "reason": "TEST_Customer complaint",
            "refundMethod": "original_payment",
            "processedBy": "Owner",
            "customerId": txn.get("customerId")
        }
        response = requests.post(f"{BASE_URL}/api/refunds", json=refund_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Create refund failed: {response.text}"
        data = response.json()
        assert data["amount"] == 5.00
        assert data["reason"] == "TEST_Customer complaint"
        print(f"PASS: Create refund - id={data['id']}, amount=${data['amount']}")


class TestEndOfDayReports:
    """End of Day page - comprehensive reports with date ranges"""
    
    def test_eod_report_today(self, owner_token):
        """GET /api/reports/end-of-day?period=today"""
        response = requests.get(f"{BASE_URL}/api/reports/end-of-day",
            params={"period": "today"},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"EOD today failed: {response.text}"
        data = response.json()
        assert "summary" in data
        assert "totalSales" in data["summary"]
        assert "customerAnalytics" in data
        print(f"PASS: EOD today - totalSales=${data['summary']['totalSales']}")
    
    def test_eod_report_week(self, owner_token):
        """GET /api/reports/end-of-day?period=week"""
        response = requests.get(f"{BASE_URL}/api/reports/end-of-day",
            params={"period": "week"},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"
        print(f"PASS: EOD week - {data['summary']['totalTransactions']} transactions")
    
    def test_eod_report_month(self, owner_token):
        """GET /api/reports/end-of-day?period=month"""
        response = requests.get(f"{BASE_URL}/api/reports/end-of-day",
            params={"period": "month"},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "month"
        assert "byPaymentMethod" in data
        assert "byCategory" in data
        assert "topItems" in data
        print(f"PASS: EOD month - has byPaymentMethod, byCategory, topItems")
    
    def test_eod_report_quarter(self, owner_token):
        """GET /api/reports/end-of-day?period=quarter"""
        response = requests.get(f"{BASE_URL}/api/reports/end-of-day",
            params={"period": "quarter"},
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "quarter"
        print(f"PASS: EOD quarter - netSales=${data['summary']['netSales']}")
    
    def test_eod_customer_analytics(self, owner_token):
        """EOD report includes customer analytics"""
        response = requests.get(f"{BASE_URL}/api/reports/end-of-day",
            params={"period": "month"},
            headers={"Authorization": f"Bearer {owner_token}"})
        data = response.json()
        ca = data.get("customerAnalytics", {})
        assert "totalCovers" in ca
        assert "walkIns" in ca
        assert "newCustomers" in ca
        assert "returningCustomers" in ca
        assert "avgCustomerSpend" in ca
        assert "topSpenders" in ca
        print(f"PASS: EOD customer analytics - covers={ca['totalCovers']}, walkIns={ca['walkIns']}")
    
    def test_eod_hourly_breakdown(self, owner_token):
        """EOD report includes hourly breakdown"""
        response = requests.get(f"{BASE_URL}/api/reports/end-of-day",
            params={"period": "month"},
            headers={"Authorization": f"Bearer {owner_token}"})
        data = response.json()
        assert "byHour" in data
        assert isinstance(data["byHour"], list)
        print(f"PASS: EOD hourly breakdown - {len(data['byHour'])} hours with data")


class TestRBACRestrictions:
    """Cashier role cannot access restricted endpoints"""
    
    def test_cashier_denied_eod_report(self, cashier_token):
        """Cashier cannot access EOD reports"""
        response = requests.get(f"{BASE_URL}/api/reports/end-of-day",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403, f"Cashier should be denied EOD access, got {response.status_code}"
        print("PASS: Cashier denied EOD report access")
    
    def test_cashier_denied_tips_summary(self, cashier_token):
        """Cashier cannot access tips summary"""
        response = requests.get(f"{BASE_URL}/api/tips/summary",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403
        print("PASS: Cashier denied tips summary access")
    
    def test_cashier_denied_training_mode_toggle(self, cashier_token):
        """Cashier cannot toggle training mode"""
        response = requests.post(f"{BASE_URL}/api/settings/training-mode",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403
        print("PASS: Cashier denied training mode toggle")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_products(self, owner_token):
        """Remove TEST_ prefixed products"""
        products_resp = requests.get(f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {owner_token}"})
        products = products_resp.json()
        deleted = 0
        for p in products:
            if p["name"].startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/products/{p['id']}",
                    headers={"Authorization": f"Bearer {owner_token}"})
                deleted += 1
        print(f"CLEANUP: Deleted {deleted} test products")
    
    def test_cleanup_test_promotions(self, owner_token):
        """Remove TEST_ prefixed promotions"""
        promos_resp = requests.get(f"{BASE_URL}/api/promotions",
            headers={"Authorization": f"Bearer {owner_token}"})
        promos = promos_resp.json()
        deleted = 0
        for p in promos:
            if p["name"].startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/promotions/{p['id']}",
                    headers={"Authorization": f"Bearer {owner_token}"})
                deleted += 1
        print(f"CLEANUP: Deleted {deleted} test promotions")
    
    def test_cleanup_test_locations(self, owner_token):
        """Remove TEST_ prefixed locations"""
        locs_resp = requests.get(f"{BASE_URL}/api/locations",
            headers={"Authorization": f"Bearer {owner_token}"})
        locs = locs_resp.json()
        deleted = 0
        for loc in locs:
            if loc["name"].startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/locations/{loc['id']}",
                    headers={"Authorization": f"Bearer {owner_token}"})
                deleted += 1
        print(f"CLEANUP: Deleted {deleted} test locations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
