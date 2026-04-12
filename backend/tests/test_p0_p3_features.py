"""
Test P0-P3 Features for NUVA POS
- Loyalty & Events (Tiers, Rewards, Events)
- Forecasting (Demand, Table Turns, Smart Roster)
- What-If Simulator
- Predictive Customer Matching
- QR Menu Data
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestLoyaltyTiers:
    """Test Loyalty Tiers API - GET /api/loyalty/tiers"""
    
    def test_get_loyalty_tiers(self):
        """Should return 4 membership tiers with perks"""
        response = requests.get(f"{BASE_URL}/api/loyalty/tiers")
        assert response.status_code == 200
        
        tiers = response.json()
        assert isinstance(tiers, list)
        assert len(tiers) == 4
        
        # Verify tier names
        tier_names = [t["name"] for t in tiers]
        assert "Bronze" in tier_names
        assert "Silver" in tier_names
        assert "Gold" in tier_names
        assert "Platinum" in tier_names
        
        # Verify Bronze tier structure
        bronze = next(t for t in tiers if t["name"] == "Bronze")
        assert bronze["minPoints"] == 0
        assert bronze["multiplier"] == 1.0
        assert isinstance(bronze["perks"], list)
        
        # Verify Platinum tier has highest multiplier
        platinum = next(t for t in tiers if t["name"] == "Platinum")
        assert platinum["multiplier"] == 2.0
        assert platinum["minPoints"] == 5000


class TestLoyaltyRewards:
    """Test Loyalty Rewards CRUD - GET/POST/DELETE /api/loyalty/rewards"""
    
    def test_get_loyalty_rewards(self):
        """Should return list of rewards"""
        response = requests.get(f"{BASE_URL}/api/loyalty/rewards")
        assert response.status_code == 200
        
        rewards = response.json()
        assert isinstance(rewards, list)
        # Should have seeded rewards
        print(f"Found {len(rewards)} rewards")
    
    def test_create_and_delete_reward(self):
        """Should create and delete a reward"""
        # Create reward
        reward_data = {
            "name": "TEST_Free Appetizer",
            "description": "Get a free appetizer",
            "pointsCost": 200,
            "rewardType": "free_item"
        }
        create_response = requests.post(f"{BASE_URL}/api/loyalty/rewards", json=reward_data)
        assert create_response.status_code == 200
        
        created = create_response.json()
        assert created["name"] == "TEST_Free Appetizer"
        assert created["pointsCost"] == 200
        assert "id" in created
        
        reward_id = created["id"]
        
        # Verify it exists
        get_response = requests.get(f"{BASE_URL}/api/loyalty/rewards")
        rewards = get_response.json()
        assert any(r["id"] == reward_id for r in rewards)
        
        # Delete reward
        delete_response = requests.delete(f"{BASE_URL}/api/loyalty/rewards/{reward_id}")
        assert delete_response.status_code == 200
        
        # Verify deleted
        get_response2 = requests.get(f"{BASE_URL}/api/loyalty/rewards")
        rewards2 = get_response2.json()
        assert not any(r["id"] == reward_id for r in rewards2)


class TestEvents:
    """Test Events API - GET/POST /api/events, POST /api/events/{id}/book"""
    
    def test_get_events(self):
        """Should return list of events"""
        response = requests.get(f"{BASE_URL}/api/events")
        assert response.status_code == 200
        
        events = response.json()
        assert isinstance(events, list)
        print(f"Found {len(events)} events")
        
        # Verify event structure if events exist
        if events:
            event = events[0]
            assert "id" in event
            assert "name" in event
            assert "date" in event
            assert "capacity" in event
            assert "ticketsBooked" in event
    
    def test_create_event(self):
        """Should create a new event"""
        event_data = {
            "name": "TEST_Wine Tasting Night",
            "description": "Sample premium wines",
            "date": "2026-02-15",
            "time": "19:00",
            "duration": 180,
            "capacity": 30,
            "ticketPrice": 75.00,
            "eventType": "wine_pairing"
        }
        response = requests.post(f"{BASE_URL}/api/events", json=event_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created["name"] == "TEST_Wine Tasting Night"
        assert created["capacity"] == 30
        assert created["ticketPrice"] == 75.00
        assert "id" in created
        
        # Store for booking test
        self.__class__.test_event_id = created["id"]
    
    def test_book_event_ticket(self):
        """Should book tickets for an event"""
        # Get an event to book
        events_response = requests.get(f"{BASE_URL}/api/events")
        events = events_response.json()
        
        if not events:
            pytest.skip("No events available to book")
        
        event = events[0]
        event_id = event["id"]
        initial_booked = event.get("ticketsBooked", 0)
        
        # Book 2 tickets
        book_response = requests.post(
            f"{BASE_URL}/api/events/{event_id}/book",
            params={"quantity": 2}
        )
        assert book_response.status_code == 200
        
        result = book_response.json()
        assert "message" in result
        assert "2 ticket(s) booked" in result["message"]


class TestDemandForecast:
    """Test Demand Forecast API - GET /api/analytics/demand-forecast"""
    
    def test_get_demand_forecast(self):
        """Should return 7-day demand forecast"""
        response = requests.get(f"{BASE_URL}/api/analytics/demand-forecast")
        assert response.status_code == 200
        
        data = response.json()
        assert "forecast" in data
        assert "basedOnDataPoints" in data
        
        forecast = data["forecast"]
        assert isinstance(forecast, list)
        assert len(forecast) == 7  # 7 days
        
        # Verify forecast day structure
        day = forecast[0]
        assert "date" in day
        assert "dayName" in day
        assert "predictedRevenue" in day
        assert "predictedCovers" in day
        assert "confidence" in day
        assert "busyLevel" in day
        assert "staffRecommendation" in day
        
        # Verify busyLevel is valid
        assert day["busyLevel"] in ["low", "medium", "high"]
        
        print(f"7-day forecast generated based on {data['basedOnDataPoints']} data points")


class TestTableTurns:
    """Test Table Turn-Time API - GET /api/analytics/table-turns"""
    
    def test_get_table_turns(self):
        """Should return table turn time analysis"""
        response = requests.get(f"{BASE_URL}/api/analytics/table-turns")
        assert response.status_code == 200
        
        data = response.json()
        assert "turnTimeAnalysis" in data
        assert "totalTables" in data
        assert "revenuePerTable" in data
        assert "optimizationTips" in data
        
        # Verify optimization tips
        tips = data["optimizationTips"]
        assert isinstance(tips, list)
        assert len(tips) > 0
        
        # Verify turn time analysis structure if data exists
        analysis = data["turnTimeAnalysis"]
        if analysis:
            item = analysis[0]
            assert "partySize" in item
            assert "avgTurnTime" in item
            assert "recommendedSlot" in item
            assert "turnsPerShift" in item
        
        print(f"Total tables: {data['totalTables']}, Revenue per table: ${data['revenuePerTable']}")


class TestSmartRoster:
    """Test Smart Rostering API - GET /api/staff/smart-roster"""
    
    def test_get_smart_roster(self):
        """Should return 7-day roster suggestions"""
        response = requests.get(f"{BASE_URL}/api/staff/smart-roster")
        assert response.status_code == 200
        
        data = response.json()
        assert "rosterSuggestions" in data
        assert "currentStaffCount" in data
        
        suggestions = data["rosterSuggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) == 7  # 7 days
        
        # Verify roster suggestion structure
        day = suggestions[0]
        assert "date" in day
        assert "dayName" in day
        assert "busyLevel" in day
        assert "predictedCovers" in day
        assert "staffNeeded" in day
        assert "laborCostEstimate" in day
        assert "laborPctTarget" in day
        
        # Verify staffNeeded breakdown
        staff = day["staffNeeded"]
        assert "front_of_house" in staff
        assert "kitchen" in staff
        assert "bar" in staff
        assert "total" in staff
        
        print(f"Roster suggestions for 7 days, current staff: {data['currentStaffCount']}")


class TestWhatIfSimulator:
    """Test What-If Simulator API - POST /api/analytics/what-if"""
    
    def test_what_if_simulation(self):
        """Should simulate price/cost changes and return profit impact"""
        # First get a product to simulate
        products_response = requests.get(f"{BASE_URL}/api/products")
        products = products_response.json()
        
        if not products:
            pytest.skip("No products available for simulation")
        
        product = products[0]
        
        # Simulate price increase
        changes = [{
            "productId": product["id"],
            "newPrice": product["price"] * 1.1,  # 10% price increase
            "newCost": product.get("cost", 0)
        }]
        
        response = requests.post(f"{BASE_URL}/api/analytics/what-if", json=changes)
        assert response.status_code == 200
        
        data = response.json()
        assert "simulations" in data
        assert "totalCurrentProfit" in data
        assert "totalProjectedProfit" in data
        assert "netImpact" in data
        
        # Verify simulation result structure
        simulations = data["simulations"]
        assert len(simulations) == 1
        
        sim = simulations[0]
        assert "productId" in sim
        assert "productName" in sim
        assert "currentPrice" in sim
        assert "projectedPrice" in sim
        assert "currentProfit" in sim
        assert "projectedProfit" in sim
        assert "profitChange" in sim
        assert "profitChangePct" in sim
        
        print(f"Simulation: Net impact ${data['netImpact']}")
    
    def test_what_if_multiple_products(self):
        """Should simulate changes for multiple products"""
        products_response = requests.get(f"{BASE_URL}/api/products")
        products = products_response.json()
        
        if len(products) < 2:
            pytest.skip("Need at least 2 products for multi-product simulation")
        
        changes = [
            {"productId": products[0]["id"], "newPrice": products[0]["price"] * 1.05, "newCost": products[0].get("cost", 0)},
            {"productId": products[1]["id"], "newPrice": products[1]["price"] * 0.95, "newCost": products[1].get("cost", 0)}
        ]
        
        response = requests.post(f"{BASE_URL}/api/analytics/what-if", json=changes)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["simulations"]) == 2


class TestPredictiveCustomerMatching:
    """Test Predictive Customer Matching - POST /api/orders/predict-customer"""
    
    def test_predict_customer_empty_items(self):
        """Should handle empty items list"""
        response = requests.post(f"{BASE_URL}/api/orders/predict-customer", json=[])
        assert response.status_code == 200
        
        data = response.json()
        assert data["matched"] == False
        assert "message" in data
    
    def test_predict_customer_with_items(self):
        """Should attempt to match customer based on order items"""
        # Get some products to use as order items
        products_response = requests.get(f"{BASE_URL}/api/products")
        products = products_response.json()
        
        if not products:
            pytest.skip("No products available")
        
        order_items = [{"productName": products[0]["name"]}]
        
        response = requests.post(f"{BASE_URL}/api/orders/predict-customer", json=order_items)
        assert response.status_code == 200
        
        data = response.json()
        # Either matched or not matched is valid
        assert "matched" in data
        
        if data["matched"]:
            assert "predictions" in data
            assert "topMatch" in data
            
            top = data["topMatch"]
            assert "customerId" in top
            assert "customerName" in top
            assert "similarity" in top
            print(f"Top match: {top['customerName']} with {top['similarity']}% similarity")
        else:
            print("No matching customer patterns found")


class TestQRMenuData:
    """Test QR Menu Data API - GET /api/menu/qr-data"""
    
    def test_get_qr_menu_data(self):
        """Should return full menu grouped by category"""
        response = requests.get(f"{BASE_URL}/api/menu/qr-data")
        assert response.status_code == 200
        
        data = response.json()
        assert "restaurantName" in data
        assert "categories" in data
        assert "totalItems" in data
        
        assert data["restaurantName"] == "NUVA"
        
        categories = data["categories"]
        assert isinstance(categories, list)
        
        # Verify category structure
        if categories:
            cat = categories[0]
            assert "name" in cat
            assert "items" in cat
            
            # Verify item structure
            if cat["items"]:
                item = cat["items"][0]
                assert "id" in item
                assert "name" in item
                assert "price" in item
        
        print(f"QR Menu: {len(categories)} categories, {data['totalItems']} total items")


class TestSidebarNavigation:
    """Test that all 19 navigation routes are accessible"""
    
    @pytest.mark.parametrize("route,expected_status", [
        ("/api/", 200),  # Root API
        ("/api/products", 200),
        ("/api/customers", 200),
        ("/api/transactions", 200),
        ("/api/reservations", 200),
        ("/api/floor-plans", 200),
        ("/api/waitlist", 200),
        ("/api/kitchen/orders", 200),
        ("/api/pre-shift/today", 200),
        ("/api/analytics/command-center", 200),
        ("/api/analytics/menu-engineering", 200),
        ("/api/automation/rules", 200),
        ("/api/loyalty/rewards", 200),
        ("/api/loyalty/tiers", 200),
        ("/api/events", 200),
        ("/api/analytics/demand-forecast", 200),
        ("/api/analytics/table-turns", 200),
        ("/api/staff/smart-roster", 200),
        ("/api/menu/qr-data", 200),
    ])
    def test_api_endpoint_accessible(self, route, expected_status):
        """All API endpoints should be accessible"""
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code == expected_status, f"Route {route} returned {response.status_code}"


class TestRegressionPhase1to3:
    """Regression tests for Phase 1-3 features"""
    
    def test_pre_shift_dashboard(self):
        """Pre-Shift Dashboard should work"""
        response = requests.get(f"{BASE_URL}/api/pre-shift/today")
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "reservations" in data
        assert "vipGuests" in data
    
    def test_command_center(self):
        """AI Command Center should work"""
        response = requests.get(f"{BASE_URL}/api/analytics/command-center")
        assert response.status_code == 200
        data = response.json()
        assert "revenue" in data
        assert "costs" in data
        assert "topSellers" in data
    
    def test_menu_engineering(self):
        """Menu Engineering should work"""
        response = requests.get(f"{BASE_URL}/api/analytics/menu-engineering")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "categories" in data
        assert "summary" in data
    
    def test_automation_rules(self):
        """Automation Rules should work"""
        response = requests.get(f"{BASE_URL}/api/automation/rules")
        assert response.status_code == 200
        rules = response.json()
        assert isinstance(rules, list)
    
    def test_reservations(self):
        """Reservations should work"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        reservations = response.json()
        assert isinstance(reservations, list)
    
    def test_floor_plans(self):
        """Floor Plans should work"""
        response = requests.get(f"{BASE_URL}/api/floor-plans")
        assert response.status_code == 200
        plans = response.json()
        assert isinstance(plans, list)
    
    def test_waitlist(self):
        """Waitlist should work"""
        response = requests.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 200
        entries = response.json()
        assert isinstance(entries, list)
    
    def test_kitchen_orders(self):
        """Kitchen KDS should work"""
        response = requests.get(f"{BASE_URL}/api/kitchen/orders")
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
    
    def test_customers_crm(self):
        """Guest CRM should work"""
        response = requests.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        customers = response.json()
        assert isinstance(customers, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
