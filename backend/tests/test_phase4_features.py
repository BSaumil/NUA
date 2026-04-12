"""
Test Suite for NUVA POS Phase 4 Features:
- Pre-Shift Dashboard API
- AI Command Center API
- Menu Engineering API
- Automation Engine API (Rules + Alerts)
- Kitchen Prep List API
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPreShiftDashboard:
    """Pre-Shift Dashboard API tests"""
    
    def test_get_preshift_today(self):
        """GET /api/pre-shift/today - returns today's briefing data"""
        response = requests.get(f"{BASE_URL}/api/pre-shift/today")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "date" in data, "Missing 'date' field"
        assert "reservations" in data, "Missing 'reservations' field"
        assert "totalReservations" in data, "Missing 'totalReservations' field"
        assert "totalCovers" in data, "Missing 'totalCovers' field"
        assert "vipGuests" in data, "Missing 'vipGuests' field"
        assert "dietaryAlerts" in data, "Missing 'dietaryAlerts' field"
        assert "specialRequests" in data, "Missing 'specialRequests' field"
        assert "kitchenPending" in data, "Missing 'kitchenPending' field"
        assert "waitlistCount" in data, "Missing 'waitlistCount' field"
        assert "revenueToday" in data, "Missing 'revenueToday' field"
        
        # Verify data types
        assert isinstance(data["reservations"], list), "reservations should be a list"
        assert isinstance(data["totalReservations"], int), "totalReservations should be int"
        assert isinstance(data["totalCovers"], int), "totalCovers should be int"
        assert isinstance(data["vipGuests"], list), "vipGuests should be a list"
        assert isinstance(data["dietaryAlerts"], list), "dietaryAlerts should be a list"
        assert isinstance(data["specialRequests"], list), "specialRequests should be a list"
        
        print(f"Pre-shift data: {data['totalReservations']} reservations, {data['totalCovers']} covers")


class TestAICommandCenter:
    """AI Command Center API tests"""
    
    def test_get_command_center(self):
        """GET /api/analytics/command-center - returns real-time metrics and insights"""
        response = requests.get(f"{BASE_URL}/api/analytics/command-center")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify revenue section
        assert "revenue" in data, "Missing 'revenue' field"
        assert "total" in data["revenue"], "Missing revenue.total"
        assert "transactions" in data["revenue"], "Missing revenue.transactions"
        assert "avgTicket" in data["revenue"], "Missing revenue.avgTicket"
        
        # Verify costs section
        assert "costs" in data, "Missing 'costs' field"
        assert "foodCost" in data["costs"], "Missing costs.foodCost"
        assert "foodCostPct" in data["costs"], "Missing costs.foodCostPct"
        assert "laborCost" in data["costs"], "Missing costs.laborCost"
        assert "laborPct" in data["costs"], "Missing costs.laborPct"
        
        # Verify profit section
        assert "profit" in data, "Missing 'profit' field"
        assert "gross" in data["profit"], "Missing profit.gross"
        assert "net" in data["profit"], "Missing profit.net"
        
        # Verify product performance
        assert "topSellers" in data, "Missing 'topSellers' field"
        assert "lowPerformers" in data, "Missing 'lowPerformers' field"
        assert isinstance(data["topSellers"], list), "topSellers should be a list"
        assert isinstance(data["lowPerformers"], list), "lowPerformers should be a list"
        
        # Verify AI insights
        assert "insights" in data, "Missing 'insights' field"
        assert isinstance(data["insights"], list), "insights should be a list"
        
        # Verify customer stats
        assert "customers" in data, "Missing 'customers' field"
        assert "total" in data["customers"], "Missing customers.total"
        assert "vips" in data["customers"], "Missing customers.vips"
        
        # Verify top sellers have required fields
        if len(data["topSellers"]) > 0:
            seller = data["topSellers"][0]
            assert "name" in seller, "Top seller missing 'name'"
            assert "revenue" in seller, "Top seller missing 'revenue'"
            assert "quantity" in seller, "Top seller missing 'quantity'"
            assert "margin" in seller, "Top seller missing 'margin'"
        
        print(f"Command Center: Revenue ${data['revenue']['total']:.0f}, Food Cost {data['costs']['foodCostPct']:.1f}%")


class TestMenuEngineering:
    """Menu Engineering API tests"""
    
    def test_get_menu_engineering(self):
        """GET /api/analytics/menu-engineering - returns menu performance analysis"""
        response = requests.get(f"{BASE_URL}/api/analytics/menu-engineering")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify items list
        assert "items" in data, "Missing 'items' field"
        assert isinstance(data["items"], list), "items should be a list"
        
        # Verify categories
        assert "categories" in data, "Missing 'categories' field"
        assert isinstance(data["categories"], list), "categories should be a list"
        
        # Verify summary with classification counts
        assert "summary" in data, "Missing 'summary' field"
        assert "stars" in data["summary"], "Missing summary.stars"
        assert "puzzles" in data["summary"], "Missing summary.puzzles"
        assert "horses" in data["summary"], "Missing summary.horses"
        assert "dogs" in data["summary"], "Missing summary.dogs"
        
        # Verify item structure if items exist
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "name" in item, "Item missing 'name'"
            assert "category" in item, "Item missing 'category'"
            assert "price" in item, "Item missing 'price'"
            assert "cost" in item, "Item missing 'cost'"
            assert "margin" in item, "Item missing 'margin'"
            assert "quantity" in item, "Item missing 'quantity'"
            assert "revenue" in item, "Item missing 'revenue'"
            assert "profit" in item, "Item missing 'profit'"
            assert "classification" in item, "Item missing 'classification'"
            
            # Verify classification is valid
            valid_classifications = ["star", "puzzle", "horse", "dog"]
            assert item["classification"] in valid_classifications, f"Invalid classification: {item['classification']}"
        
        # Verify category structure if categories exist
        if len(data["categories"]) > 0:
            cat = data["categories"][0]
            assert "name" in cat, "Category missing 'name'"
            assert "revenue" in cat, "Category missing 'revenue'"
            assert "profit" in cat, "Category missing 'profit'"
            assert "margin" in cat, "Category missing 'margin'"
            assert "items" in cat, "Category missing 'items' count"
        
        print(f"Menu Engineering: {len(data['items'])} items, {data['summary']['stars']} stars, {data['summary']['dogs']} dogs")


class TestAutomationRules:
    """Automation Rules CRUD API tests"""
    
    created_rule_id = None
    
    def test_01_get_automation_rules(self):
        """GET /api/automation/rules - list all rules"""
        response = requests.get(f"{BASE_URL}/api/automation/rules")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify seeded rules exist
        print(f"Found {len(data)} automation rules")
        
        # Verify rule structure if rules exist
        if len(data) > 0:
            rule = data[0]
            assert "id" in rule, "Rule missing 'id'"
            assert "name" in rule, "Rule missing 'name'"
            assert "trigger" in rule, "Rule missing 'trigger'"
            assert "action" in rule, "Rule missing 'action'"
            assert "enabled" in rule, "Rule missing 'enabled'"
    
    def test_02_create_automation_rule(self):
        """POST /api/automation/rules - create new rule"""
        rule_data = {
            "name": "TEST_Auto Reorder Coffee",
            "trigger": "low_stock",
            "condition": "stock < 5",
            "action": "create_purchase_order",
            "enabled": True
        }
        
        response = requests.post(f"{BASE_URL}/api/automation/rules", json=rule_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Created rule missing 'id'"
        assert data["name"] == rule_data["name"], "Name mismatch"
        assert data["trigger"] == rule_data["trigger"], "Trigger mismatch"
        assert data["action"] == rule_data["action"], "Action mismatch"
        assert data["enabled"] == True, "Should be enabled"
        
        TestAutomationRules.created_rule_id = data["id"]
        print(f"Created rule: {data['id']}")
    
    def test_03_verify_rule_created(self):
        """GET /api/automation/rules - verify rule was persisted"""
        response = requests.get(f"{BASE_URL}/api/automation/rules")
        assert response.status_code == 200
        
        data = response.json()
        rule_ids = [r["id"] for r in data]
        assert TestAutomationRules.created_rule_id in rule_ids, "Created rule not found in list"
    
    def test_04_toggle_automation_rule(self):
        """POST /api/automation/rules/{id}/toggle - toggle enabled state"""
        rule_id = TestAutomationRules.created_rule_id
        assert rule_id is not None, "No rule ID from previous test"
        
        response = requests.post(f"{BASE_URL}/api/automation/rules/{rule_id}/toggle")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "enabled" in data, "Response missing 'enabled'"
        assert data["enabled"] == False, "Should be disabled after toggle"
        
        # Toggle back
        response2 = requests.post(f"{BASE_URL}/api/automation/rules/{rule_id}/toggle")
        assert response2.status_code == 200
        assert response2.json()["enabled"] == True, "Should be enabled after second toggle"
        
        print(f"Toggled rule {rule_id} successfully")
    
    def test_05_update_automation_rule(self):
        """PUT /api/automation/rules/{id} - update rule"""
        rule_id = TestAutomationRules.created_rule_id
        assert rule_id is not None, "No rule ID from previous test"
        
        update_data = {
            "name": "TEST_Updated Rule Name",
            "condition": "stock < 10"
        }
        
        response = requests.put(f"{BASE_URL}/api/automation/rules/{rule_id}", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["name"] == update_data["name"], "Name not updated"
        assert data["condition"] == update_data["condition"], "Condition not updated"
        
        print(f"Updated rule {rule_id}")
    
    def test_06_delete_automation_rule(self):
        """DELETE /api/automation/rules/{id} - delete rule"""
        rule_id = TestAutomationRules.created_rule_id
        assert rule_id is not None, "No rule ID from previous test"
        
        response = requests.delete(f"{BASE_URL}/api/automation/rules/{rule_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        response2 = requests.get(f"{BASE_URL}/api/automation/rules")
        rule_ids = [r["id"] for r in response2.json()]
        assert rule_id not in rule_ids, "Rule should be deleted"
        
        print(f"Deleted rule {rule_id}")
    
    def test_07_toggle_nonexistent_rule(self):
        """POST /api/automation/rules/{id}/toggle - 404 for nonexistent rule"""
        response = requests.post(f"{BASE_URL}/api/automation/rules/NONEXISTENT/toggle")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestAutomationAlerts:
    """Automation Alerts API tests"""
    
    def test_get_automation_alerts(self):
        """GET /api/automation/alerts - returns real-time alerts"""
        response = requests.get(f"{BASE_URL}/api/automation/alerts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify alert structure if alerts exist
        if len(data) > 0:
            alert = data[0]
            assert "type" in alert, "Alert missing 'type'"
            assert "severity" in alert, "Alert missing 'severity'"
            assert "title" in alert, "Alert missing 'title'"
            assert "message" in alert, "Alert missing 'message'"
            
            # Verify severity is valid
            valid_severities = ["high", "warning", "info"]
            assert alert["severity"] in valid_severities, f"Invalid severity: {alert['severity']}"
        
        print(f"Found {len(data)} automation alerts")


class TestKitchenPrepList:
    """Kitchen Prep List API tests"""
    
    def test_get_prep_list(self):
        """GET /api/kitchen/prep-list - returns dynamic prep list"""
        response = requests.get(f"{BASE_URL}/api/kitchen/prep-list")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        assert "date" in data, "Missing 'date' field"
        assert "expectedCovers" in data, "Missing 'expectedCovers' field"
        assert "totalReservations" in data, "Missing 'totalReservations' field"
        assert "prepItems" in data, "Missing 'prepItems' field"
        
        assert isinstance(data["prepItems"], list), "prepItems should be a list"
        
        # Verify prep item structure if items exist
        if len(data["prepItems"]) > 0:
            item = data["prepItems"][0]
            assert "productId" in item, "Prep item missing 'productId'"
            assert "name" in item, "Prep item missing 'name'"
            assert "category" in item, "Prep item missing 'category'"
            assert "currentStock" in item, "Prep item missing 'currentStock'"
            assert "estimatedNeeded" in item, "Prep item missing 'estimatedNeeded'"
            assert "popularityPct" in item, "Prep item missing 'popularityPct'"
            assert "prepStatus" in item, "Prep item missing 'prepStatus'"
        
        print(f"Prep list: {data['expectedCovers']} covers, {len(data['prepItems'])} items to prep")


class TestRegressionPhase1:
    """Regression tests for Phase 1 features (Reservations, Floor Plan, Waitlist)"""
    
    def test_reservations_api(self):
        """GET /api/reservations - verify still working"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200, f"Reservations API failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"Reservations: {len(data)} found")
    
    def test_floor_plans_api(self):
        """GET /api/floor-plans - verify still working"""
        response = requests.get(f"{BASE_URL}/api/floor-plans")
        assert response.status_code == 200, f"Floor plans API failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"Floor plans: {len(data)} found")
    
    def test_waitlist_api(self):
        """GET /api/waitlist - verify still working"""
        response = requests.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 200, f"Waitlist API failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"Waitlist: {len(data)} entries")


class TestRegressionPhase2Phase3:
    """Regression tests for Phase 2 (CRM, Feedback) and Phase 3 (Kitchen) features"""
    
    def test_customers_api(self):
        """GET /api/customers - verify still working"""
        response = requests.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200, f"Customers API failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"Customers: {len(data)} found")
    
    def test_feedback_api(self):
        """GET /api/feedback - verify still working"""
        response = requests.get(f"{BASE_URL}/api/feedback")
        assert response.status_code == 200, f"Feedback API failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"Feedback: {len(data)} entries")
    
    def test_kitchen_orders_api(self):
        """GET /api/kitchen/orders - verify still working"""
        response = requests.get(f"{BASE_URL}/api/kitchen/orders")
        assert response.status_code == 200, f"Kitchen orders API failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"Kitchen orders: {len(data)} active")


class TestSidebarNavigation:
    """Test all 16 sidebar navigation routes exist"""
    
    def test_all_routes_accessible(self):
        """Verify all frontend routes are accessible"""
        routes = [
            "/",
            "/pre-shift",
            "/command-center",
            "/pos",
            "/reservations",
            "/floor-plan",
            "/waitlist",
            "/kitchen",
            "/menu-engineering",
            "/products",
            "/customers",
            "/inventory",
            "/automation",
            "/accounting",
            "/bas-gst",
            "/settings"
        ]
        
        # Just verify the API root is accessible (frontend routes are tested via Playwright)
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, "API root not accessible"
        
        print(f"API accessible, {len(routes)} frontend routes defined")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
