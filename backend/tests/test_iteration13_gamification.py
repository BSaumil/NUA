"""
Iteration 13 Tests: Gamification Features
- Staff Leaderboard with performance scores
- Smart Tip Distribution (hours + performance weighted)
- Quarterly Menu Review (top/worst sellers, underperformers)
- Category-wise Print Routing (Kitchen/Bar/Pizza printers)
- Print Queue management
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def owner_token():
    """Get owner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "owner@nuva.com",
        "password": "NuvaOwner2026!"
    })
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture(scope="module")
def manager_token():
    """Get manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "manager@nuva.com",
        "password": "Staff2026!"
    })
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture(scope="module")
def cashier_token():
    """Get cashier auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "cashier@nuva.com",
        "password": "Staff2026!"
    })
    assert response.status_code == 200, f"Cashier login failed: {response.text}"
    return response.json()["token"]


class TestStaffLeaderboard:
    """Staff Leaderboard endpoint tests"""
    
    def test_get_leaderboard_owner(self, owner_token):
        """Owner can access leaderboard"""
        response = requests.get(
            f"{BASE_URL}/api/staff/leaderboard",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert "generatedAt" in data
        # Verify leaderboard structure
        if len(data["leaderboard"]) > 0:
            staff = data["leaderboard"][0]
            assert "id" in staff
            assert "name" in staff
            assert "role" in staff
            assert "totalSales" in staff
            assert "totalTransactions" in staff
            assert "totalTips" in staff
            assert "totalHours" in staff
            assert "performanceScore" in staff
            assert "rank" in staff
    
    def test_get_leaderboard_manager(self, manager_token):
        """Manager can access leaderboard"""
        response = requests.get(
            f"{BASE_URL}/api/staff/leaderboard",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
    
    def test_get_leaderboard_cashier(self, cashier_token):
        """Cashier can access leaderboard (all staff can view)"""
        response = requests.get(
            f"{BASE_URL}/api/staff/leaderboard",
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
    
    def test_leaderboard_sorted_by_score(self, owner_token):
        """Leaderboard is sorted by performanceScore descending"""
        response = requests.get(
            f"{BASE_URL}/api/staff/leaderboard",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        leaderboard = data["leaderboard"]
        if len(leaderboard) > 1:
            for i in range(len(leaderboard) - 1):
                assert leaderboard[i]["performanceScore"] >= leaderboard[i+1]["performanceScore"]
    
    def test_leaderboard_ranks_sequential(self, owner_token):
        """Leaderboard ranks are sequential starting from 1"""
        response = requests.get(
            f"{BASE_URL}/api/staff/leaderboard",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        leaderboard = data["leaderboard"]
        for i, staff in enumerate(leaderboard):
            assert staff["rank"] == i + 1


class TestSmartTipDistribution:
    """Smart Tip Distribution endpoint tests"""
    
    def test_smart_distribute_owner(self, owner_token):
        """Owner can trigger smart tip distribution"""
        response = requests.post(
            f"{BASE_URL}/api/tips/smart-distribute",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Either has distributions or message about no pooled tips
        assert "message" in data or "distributions" in data
    
    def test_smart_distribute_manager_denied(self, manager_token):
        """Manager cannot trigger smart tip distribution (owner only)"""
        response = requests.post(
            f"{BASE_URL}/api/tips/smart-distribute",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 403
        assert "Owner access only" in response.json().get("detail", "")
    
    def test_smart_distribute_cashier_denied(self, cashier_token):
        """Cashier cannot trigger smart tip distribution"""
        response = requests.post(
            f"{BASE_URL}/api/tips/smart-distribute",
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403


class TestQuarterlyReview:
    """Quarterly Menu Review endpoint tests"""
    
    def test_quarterly_review_owner(self, owner_token):
        """Owner can access quarterly review"""
        response = requests.get(
            f"{BASE_URL}/api/reports/quarterly-review",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert data["period"] == "quarterly"
        assert "topSellers" in data
        assert "worstSellers" in data
        assert "underperformers" in data
        assert "totalItems" in data
        assert "generatedAt" in data
    
    def test_quarterly_review_manager(self, manager_token):
        """Manager can access quarterly review"""
        response = requests.get(
            f"{BASE_URL}/api/reports/quarterly-review",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "topSellers" in data
    
    def test_quarterly_review_cashier_denied(self, cashier_token):
        """Cashier cannot access quarterly review"""
        response = requests.get(
            f"{BASE_URL}/api/reports/quarterly-review",
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403
    
    def test_quarterly_review_top_sellers_structure(self, owner_token):
        """Top sellers have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/reports/quarterly-review",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        if len(data["topSellers"]) > 0:
            item = data["topSellers"][0]
            assert "id" in item
            assert "name" in item
            assert "category" in item
            assert "qtySold" in item
            assert "revenue" in item
            assert "profit" in item
            assert "margin" in item
    
    def test_ai_alternatives_owner(self, owner_token):
        """Owner can request AI alternatives for underperformers"""
        response = requests.post(
            f"{BASE_URL}/api/reports/quarterly-review/ai-alternatives",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"items": [{"name": "Test Item", "price": 10, "margin": 15, "qtySold": 5}]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "generatedAt" in data
    
    def test_ai_alternatives_manager_denied(self, manager_token):
        """Manager cannot request AI alternatives (owner only)"""
        response = requests.post(
            f"{BASE_URL}/api/reports/quarterly-review/ai-alternatives",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"items": []}
        )
        assert response.status_code == 403


class TestPrintRoutingConfig:
    """Print Routing Configuration endpoint tests"""
    
    DEFAULT_CONFIG = {
        "enabled": True,
        "routes": [
            {"category": "Beverages", "printer": "Bar Printer", "priority": 1},
            {"category": "Alcohol", "printer": "Bar Printer", "priority": 1},
            {"category": "Food", "printer": "Kitchen Printer", "priority": 2},
            {"category": "Mains", "printer": "Kitchen Printer", "priority": 2},
            {"category": "Appetizers", "printer": "Kitchen Printer", "priority": 1},
            {"category": "Bakery", "printer": "Kitchen Printer", "priority": 3},
            {"category": "Desserts", "printer": "Kitchen Printer", "priority": 3},
            {"category": "Pizza", "printer": "Pizza Station", "priority": 1}
        ],
        "defaultPrinter": "Kitchen Printer",
        "defaultPriority": 2
    }
    
    def _restore_default_config(self, token):
        """Helper to restore default config"""
        requests.post(
            f"{BASE_URL}/api/print-routing/config",
            headers={"Authorization": f"Bearer {token}"},
            json=self.DEFAULT_CONFIG
        )
    
    def test_get_print_routing_config(self, owner_token):
        """Get print routing configuration returns routes"""
        # First restore default config
        self._restore_default_config(owner_token)
        
        response = requests.get(
            f"{BASE_URL}/api/print-routing/config",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "routes" in data
        assert "defaultPrinter" in data
        assert "defaultPriority" in data
        # Verify 8 default routes
        assert len(data["routes"]) == 8
        # Verify route structure
        route = data["routes"][0]
        assert "category" in route
        assert "printer" in route
        assert "priority" in route
    
    def test_print_routing_categories(self, owner_token):
        """Verify correct category-to-printer mappings"""
        response = requests.get(
            f"{BASE_URL}/api/print-routing/config",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        routes = {r["category"]: r["printer"] for r in data["routes"]}
        # Verify key mappings
        assert routes.get("Beverages") == "Bar Printer"
        assert routes.get("Alcohol") == "Bar Printer"
        assert routes.get("Pizza") == "Pizza Station"
        assert routes.get("Mains") == "Kitchen Printer"
        assert routes.get("Food") == "Kitchen Printer"
    
    def test_save_print_routing_owner(self, owner_token):
        """Owner can save print routing config"""
        config = {
            "enabled": True,
            "routes": [
                {"category": "Beverages", "printer": "Bar Printer", "priority": 1},
                {"category": "Pizza", "printer": "Pizza Station", "priority": 1}
            ],
            "defaultPrinter": "Kitchen Printer",
            "defaultPriority": 2
        }
        response = requests.post(
            f"{BASE_URL}/api/print-routing/config",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=config
        )
        assert response.status_code == 200
        assert "message" in response.json()
        # Restore default config
        self._restore_default_config(owner_token)
    
    def test_save_print_routing_manager(self, manager_token, owner_token):
        """Manager can save print routing config"""
        config = {
            "enabled": True,
            "routes": [{"category": "Test", "printer": "Test Printer", "priority": 1}],
            "defaultPrinter": "Kitchen Printer",
            "defaultPriority": 2
        }
        response = requests.post(
            f"{BASE_URL}/api/print-routing/config",
            headers={"Authorization": f"Bearer {manager_token}"},
            json=config
        )
        assert response.status_code == 200
        # Restore default config
        self._restore_default_config(owner_token)
    
    def test_save_print_routing_cashier_denied(self, cashier_token):
        """Cashier cannot save print routing config"""
        response = requests.post(
            f"{BASE_URL}/api/print-routing/config",
            headers={"Authorization": f"Bearer {cashier_token}"},
            json={"enabled": True, "routes": []}
        )
        assert response.status_code == 403


class TestPrintRoutingSend:
    """Print Routing Send endpoint tests - routes items to correct printers"""
    
    def test_send_to_printers_creates_jobs(self, owner_token):
        """Sending items creates print jobs"""
        order_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(
            f"{BASE_URL}/api/print-routing/send",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "items": [
                    {"productName": "Espresso", "category": "Beverages", "quantity": 2}
                ],
                "orderId": order_id,
                "tableNumber": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "totalPrinters" in data
        assert len(data["jobs"]) >= 1
    
    def test_send_routes_beverages_to_bar(self, owner_token):
        """Beverages route to Bar Printer"""
        order_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(
            f"{BASE_URL}/api/print-routing/send",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "items": [
                    {"productName": "Latte", "category": "Beverages", "quantity": 1}
                ],
                "orderId": order_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        bar_job = next((j for j in data["jobs"] if j["printer"] == "Bar Printer"), None)
        assert bar_job is not None, "Beverages should route to Bar Printer"
        assert any(i["category"] == "Beverages" for i in bar_job["items"])
    
    def test_send_routes_pizza_to_pizza_station(self, owner_token):
        """Pizza routes to Pizza Station"""
        order_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(
            f"{BASE_URL}/api/print-routing/send",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "items": [
                    {"productName": "Margherita", "category": "Pizza", "quantity": 1}
                ],
                "orderId": order_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        pizza_job = next((j for j in data["jobs"] if j["printer"] == "Pizza Station"), None)
        assert pizza_job is not None, "Pizza should route to Pizza Station"
    
    def test_send_routes_mains_to_kitchen(self, owner_token):
        """Mains route to Kitchen Printer"""
        order_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(
            f"{BASE_URL}/api/print-routing/send",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "items": [
                    {"productName": "Steak", "category": "Mains", "quantity": 1}
                ],
                "orderId": order_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        kitchen_job = next((j for j in data["jobs"] if j["printer"] == "Kitchen Printer"), None)
        assert kitchen_job is not None, "Mains should route to Kitchen Printer"
    
    def test_send_mixed_order_creates_multiple_jobs(self, owner_token):
        """Mixed order creates separate jobs for each printer"""
        order_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(
            f"{BASE_URL}/api/print-routing/send",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "items": [
                    {"productName": "Espresso", "category": "Beverages", "quantity": 2},
                    {"productName": "Margherita", "category": "Pizza", "quantity": 1},
                    {"productName": "Beef Burger", "category": "Mains", "quantity": 1}
                ],
                "orderId": order_id,
                "tableNumber": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalPrinters"] == 3, "Should create 3 separate printer jobs"
        printers = [j["printer"] for j in data["jobs"]]
        assert "Bar Printer" in printers
        assert "Pizza Station" in printers
        assert "Kitchen Printer" in printers
    
    def test_print_job_structure(self, owner_token):
        """Print job has correct structure"""
        order_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(
            f"{BASE_URL}/api/print-routing/send",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "items": [{"productName": "Test", "category": "Beverages", "quantity": 1}],
                "orderId": order_id,
                "tableNumber": 10
            }
        )
        assert response.status_code == 200
        job = response.json()["jobs"][0]
        assert "id" in job
        assert job["id"].startswith("PRINT-")
        assert "orderId" in job
        assert "tableNumber" in job
        assert "printer" in job
        assert "priority" in job
        assert "items" in job
        assert "status" in job
        assert job["status"] == "queued"
        assert "createdAt" in job


class TestPrintQueue:
    """Print Queue endpoint tests"""
    
    def test_get_print_queue(self, owner_token):
        """Get print queue returns queued jobs"""
        response = requests.get(
            f"{BASE_URL}/api/print-routing/queue",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_print_queue_by_printer(self, owner_token):
        """Get print queue filtered by printer"""
        response = requests.get(
            f"{BASE_URL}/api/print-routing/queue",
            headers={"Authorization": f"Bearer {owner_token}"},
            params={"printer": "Bar Printer"}
        )
        assert response.status_code == 200
        data = response.json()
        # All jobs should be for Bar Printer
        for job in data:
            assert job["printer"] == "Bar Printer"
    
    def test_complete_print_job(self, owner_token):
        """Complete a print job marks it as printed"""
        # First create a job
        order_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        create_response = requests.post(
            f"{BASE_URL}/api/print-routing/send",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "items": [{"productName": "Test", "category": "Beverages", "quantity": 1}],
                "orderId": order_id
            }
        )
        assert create_response.status_code == 200
        job_id = create_response.json()["jobs"][0]["id"]
        
        # Complete the job
        complete_response = requests.post(
            f"{BASE_URL}/api/print-routing/complete/{job_id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert complete_response.status_code == 200
        assert "message" in complete_response.json()
        
        # Verify job is no longer in queue
        queue_response = requests.get(
            f"{BASE_URL}/api/print-routing/queue",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        queue_jobs = queue_response.json()
        assert not any(j["id"] == job_id for j in queue_jobs), "Completed job should not be in queue"


class TestRBACEnforcement:
    """RBAC enforcement tests for iteration 13 features"""
    
    def test_cashier_can_view_leaderboard(self, cashier_token):
        """Cashier can view leaderboard (all staff can view)"""
        response = requests.get(
            f"{BASE_URL}/api/staff/leaderboard",
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 200
    
    def test_cashier_cannot_smart_distribute(self, cashier_token):
        """Cashier cannot trigger smart tip distribution"""
        response = requests.post(
            f"{BASE_URL}/api/tips/smart-distribute",
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403
    
    def test_cashier_cannot_view_quarterly_review(self, cashier_token):
        """Cashier cannot view quarterly review"""
        response = requests.get(
            f"{BASE_URL}/api/reports/quarterly-review",
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403
    
    def test_cashier_cannot_save_print_routing(self, cashier_token):
        """Cashier cannot save print routing config"""
        response = requests.post(
            f"{BASE_URL}/api/print-routing/config",
            headers={"Authorization": f"Bearer {cashier_token}"},
            json={"enabled": True, "routes": []}
        )
        assert response.status_code == 403
