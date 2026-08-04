"""
Backend API Tests for NUA POS - Reservations, Floor Plans, and Waitlist
Tests all CRUD operations and special actions for Phase 1 features
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============ RESERVATIONS API TESTS ============
class TestReservationsAPI:
    """Tests for /api/reservations endpoints"""
    
    created_reservation_id = None
    
    def test_get_reservations(self):
        """GET /api/reservations - should return list of reservations"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/reservations - Found {len(data)} reservations")
    
    def test_get_reservations_with_date_filter(self):
        """GET /api/reservations?date=YYYY-MM-DD - filter by date"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/reservations", params={"date": today})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned reservations should have the filtered date
        for res in data:
            assert res.get("date") == today, f"Reservation date {res.get('date')} doesn't match filter {today}"
        print(f"✓ GET /api/reservations?date={today} - Found {len(data)} reservations for today")
    
    def test_get_reservations_with_status_filter(self):
        """GET /api/reservations?status=confirmed - filter by status"""
        response = requests.get(f"{BASE_URL}/api/reservations", params={"status": "confirmed"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for res in data:
            assert res.get("status") == "confirmed"
        print(f"✓ GET /api/reservations?status=confirmed - Found {len(data)} confirmed reservations")
    
    def test_create_reservation(self):
        """POST /api/reservations - create new reservation"""
        today = datetime.now().strftime('%Y-%m-%d')
        payload = {
            "guestName": "TEST_John Smith",
            "guestPhone": "+61 400 123 456",
            "guestEmail": "test@example.com",
            "partySize": 4,
            "date": today,
            "time": "19:00",
            "duration": 90,
            "specialRequests": "Window seat preferred",
            "notes": "VIP guest",
            "source": "phone",
            "depositRequired": 50.0
        }
        response = requests.post(f"{BASE_URL}/api/reservations", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data, "Response should contain id"
        assert data["guestName"] == payload["guestName"]
        assert data["partySize"] == payload["partySize"]
        assert data["date"] == payload["date"]
        assert data["time"] == payload["time"]
        assert data["status"] == "confirmed", "New reservation should be confirmed"
        
        TestReservationsAPI.created_reservation_id = data["id"]
        print(f"✓ POST /api/reservations - Created reservation {data['id']}")
    
    def test_get_single_reservation(self):
        """GET /api/reservations/{id} - get specific reservation"""
        if not TestReservationsAPI.created_reservation_id:
            pytest.skip("No reservation created to fetch")
        
        res_id = TestReservationsAPI.created_reservation_id
        response = requests.get(f"{BASE_URL}/api/reservations/{res_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == res_id
        assert data["guestName"] == "TEST_John Smith"
        print(f"✓ GET /api/reservations/{res_id} - Retrieved reservation successfully")
    
    def test_update_reservation(self):
        """PUT /api/reservations/{id} - update reservation"""
        if not TestReservationsAPI.created_reservation_id:
            pytest.skip("No reservation created to update")
        
        res_id = TestReservationsAPI.created_reservation_id
        update_payload = {
            "partySize": 6,
            "specialRequests": "Updated: Need high chair"
        }
        response = requests.put(f"{BASE_URL}/api/reservations/{res_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["partySize"] == 6
        assert data["specialRequests"] == "Updated: Need high chair"
        
        # Verify persistence with GET
        get_response = requests.get(f"{BASE_URL}/api/reservations/{res_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["partySize"] == 6
        print(f"✓ PUT /api/reservations/{res_id} - Updated and verified")
    
    def test_seat_reservation(self):
        """POST /api/reservations/{id}/seat - seat a guest"""
        if not TestReservationsAPI.created_reservation_id:
            pytest.skip("No reservation created to seat")
        
        res_id = TestReservationsAPI.created_reservation_id
        response = requests.post(f"{BASE_URL}/api/reservations/{res_id}/seat")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify status changed to seated
        get_response = requests.get(f"{BASE_URL}/api/reservations/{res_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["status"] == "seated"
        print(f"✓ POST /api/reservations/{res_id}/seat - Guest seated")
    
    def test_complete_reservation(self):
        """POST /api/reservations/{id}/complete - complete a reservation"""
        if not TestReservationsAPI.created_reservation_id:
            pytest.skip("No reservation created to complete")
        
        res_id = TestReservationsAPI.created_reservation_id
        response = requests.post(f"{BASE_URL}/api/reservations/{res_id}/complete")
        assert response.status_code == 200
        
        # Verify status changed to completed
        get_response = requests.get(f"{BASE_URL}/api/reservations/{res_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["status"] == "completed"
        print(f"✓ POST /api/reservations/{res_id}/complete - Reservation completed")
    
    def test_create_and_mark_no_show(self):
        """POST /api/reservations/{id}/no-show - mark as no-show"""
        today = datetime.now().strftime('%Y-%m-%d')
        # Create a new reservation for no-show test
        payload = {
            "guestName": "TEST_NoShow Guest",
            "partySize": 2,
            "date": today,
            "time": "20:00",
            "source": "online"
        }
        create_response = requests.post(f"{BASE_URL}/api/reservations", json=payload)
        assert create_response.status_code == 200
        res_id = create_response.json()["id"]
        
        # Mark as no-show
        response = requests.post(f"{BASE_URL}/api/reservations/{res_id}/no-show", params={"fee": 25.0})
        assert response.status_code == 200
        
        # Verify status
        get_response = requests.get(f"{BASE_URL}/api/reservations/{res_id}")
        fetched = get_response.json()
        assert fetched["status"] == "no_show"
        print(f"✓ POST /api/reservations/{res_id}/no-show - Marked as no-show")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reservations/{res_id}")
    
    def test_auto_assign_table(self):
        """GET /api/reservations/auto-assign/{id} - auto-assign table"""
        today = datetime.now().strftime('%Y-%m-%d')
        # Create a reservation without table
        payload = {
            "guestName": "TEST_AutoAssign Guest",
            "partySize": 2,
            "date": today,
            "time": "18:00",
            "source": "phone"
        }
        create_response = requests.post(f"{BASE_URL}/api/reservations", json=payload)
        assert create_response.status_code == 200
        res_id = create_response.json()["id"]
        
        # Try auto-assign
        response = requests.get(f"{BASE_URL}/api/reservations/auto-assign/{res_id}")
        assert response.status_code == 200
        data = response.json()
        # Response should have assigned field (true/false)
        assert "assigned" in data
        print(f"✓ GET /api/reservations/auto-assign/{res_id} - Auto-assign result: {data.get('assigned')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reservations/{res_id}")
    
    def test_delete_reservation(self):
        """DELETE /api/reservations/{id} - delete reservation"""
        if not TestReservationsAPI.created_reservation_id:
            pytest.skip("No reservation created to delete")
        
        res_id = TestReservationsAPI.created_reservation_id
        response = requests.delete(f"{BASE_URL}/api/reservations/{res_id}")
        assert response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/reservations/{res_id}")
        assert get_response.status_code == 404
        print(f"✓ DELETE /api/reservations/{res_id} - Deleted and verified")
    
    def test_get_nonexistent_reservation(self):
        """GET /api/reservations/{id} - should return 404 for non-existent"""
        response = requests.get(f"{BASE_URL}/api/reservations/NONEXISTENT-ID")
        assert response.status_code == 404
        print("✓ GET /api/reservations/NONEXISTENT-ID - Returns 404 as expected")


# ============ FLOOR PLANS API TESTS ============
class TestFloorPlansAPI:
    """Tests for /api/floor-plans endpoints"""
    
    created_plan_id = None
    
    def test_get_floor_plans(self):
        """GET /api/floor-plans - should return list of floor plans"""
        response = requests.get(f"{BASE_URL}/api/floor-plans")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/floor-plans - Found {len(data)} floor plans")
        
        # Check structure of first plan if exists
        if len(data) > 0:
            plan = data[0]
            assert "id" in plan
            assert "name" in plan
            assert "tables" in plan
            print(f"  First plan: {plan['name']} with {len(plan.get('tables', []))} tables")
    
    def test_create_floor_plan(self):
        """POST /api/floor-plans - create new floor plan"""
        payload = {
            "name": "TEST_Outdoor Patio",
            "tables": [
                {
                    "id": "TBL-TEST-001",
                    "number": "P1",
                    "capacity": 4,
                    "shape": "circle",
                    "x": 100,
                    "y": 100,
                    "width": 80,
                    "height": 80,
                    "section": "patio",
                    "status": "available",
                    "minCovers": 2,
                    "maxCovers": 4,
                    "isActive": True
                }
            ],
            "sections": [
                {"id": "SEC-TEST-001", "name": "patio", "color": "#10B981"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/floor-plans", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["name"] == "TEST_Outdoor Patio"
        assert len(data["tables"]) == 1
        
        TestFloorPlansAPI.created_plan_id = data["id"]
        print(f"✓ POST /api/floor-plans - Created floor plan {data['id']}")
    
    def test_get_single_floor_plan(self):
        """GET /api/floor-plans/{id} - get specific floor plan"""
        if not TestFloorPlansAPI.created_plan_id:
            pytest.skip("No floor plan created to fetch")
        
        plan_id = TestFloorPlansAPI.created_plan_id
        response = requests.get(f"{BASE_URL}/api/floor-plans/{plan_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == plan_id
        print(f"✓ GET /api/floor-plans/{plan_id} - Retrieved successfully")
    
    def test_update_floor_plan(self):
        """PUT /api/floor-plans/{id} - update floor plan"""
        if not TestFloorPlansAPI.created_plan_id:
            pytest.skip("No floor plan created to update")
        
        plan_id = TestFloorPlansAPI.created_plan_id
        update_payload = {
            "name": "TEST_Updated Patio",
            "tables": [
                {
                    "id": "TBL-TEST-001",
                    "number": "P1",
                    "capacity": 6,
                    "shape": "rectangle",
                    "x": 150,
                    "y": 150,
                    "width": 100,
                    "height": 60,
                    "section": "patio",
                    "status": "available",
                    "minCovers": 2,
                    "maxCovers": 6,
                    "isActive": True
                },
                {
                    "id": "TBL-TEST-002",
                    "number": "P2",
                    "capacity": 2,
                    "shape": "square",
                    "x": 300,
                    "y": 150,
                    "width": 60,
                    "height": 60,
                    "section": "patio",
                    "status": "available",
                    "minCovers": 1,
                    "maxCovers": 2,
                    "isActive": True
                }
            ]
        }
        response = requests.put(f"{BASE_URL}/api/floor-plans/{plan_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Updated Patio"
        assert len(data["tables"]) == 2
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/floor-plans/{plan_id}")
        fetched = get_response.json()
        assert fetched["name"] == "TEST_Updated Patio"
        assert len(fetched["tables"]) == 2
        print(f"✓ PUT /api/floor-plans/{plan_id} - Updated and verified")
    
    def test_update_table_status(self):
        """POST /api/floor-plans/tables/{table_id}/status - update table status"""
        if not TestFloorPlansAPI.created_plan_id:
            pytest.skip("No floor plan created")
        
        plan_id = TestFloorPlansAPI.created_plan_id
        table_id = "TBL-TEST-001"
        
        response = requests.post(
            f"{BASE_URL}/api/floor-plans/tables/{table_id}/status",
            params={"status": "occupied", "plan_id": plan_id}
        )
        assert response.status_code == 200
        print(f"✓ POST /api/floor-plans/tables/{table_id}/status - Status updated to occupied")
    
    def test_delete_floor_plan(self):
        """DELETE /api/floor-plans/{id} - delete floor plan"""
        if not TestFloorPlansAPI.created_plan_id:
            pytest.skip("No floor plan created to delete")
        
        plan_id = TestFloorPlansAPI.created_plan_id
        response = requests.delete(f"{BASE_URL}/api/floor-plans/{plan_id}")
        assert response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/floor-plans/{plan_id}")
        assert get_response.status_code == 404
        print(f"✓ DELETE /api/floor-plans/{plan_id} - Deleted and verified")


# ============ WAITLIST API TESTS ============
class TestWaitlistAPI:
    """Tests for /api/waitlist endpoints"""
    
    created_entry_id = None
    
    def test_get_waitlist(self):
        """GET /api/waitlist - should return list of waitlist entries"""
        response = requests.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/waitlist - Found {len(data)} entries")
    
    def test_add_to_waitlist(self):
        """POST /api/waitlist - add guest to waitlist"""
        payload = {
            "guestName": "TEST_Waiting Guest",
            "guestPhone": "+61 400 999 888",
            "partySize": 3,
            "quotedWait": 20,
            "notes": "Birthday celebration",
            "preferences": "outdoor"
        }
        response = requests.post(f"{BASE_URL}/api/waitlist", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["guestName"] == "TEST_Waiting Guest"
        assert data["partySize"] == 3
        assert data["quotedWait"] == 20
        assert data["status"] == "waiting"
        assert "position" in data
        
        TestWaitlistAPI.created_entry_id = data["id"]
        print(f"✓ POST /api/waitlist - Added {data['id']} at position {data['position']}")
    
    def test_update_waitlist_entry(self):
        """PUT /api/waitlist/{id} - update waitlist entry"""
        if not TestWaitlistAPI.created_entry_id:
            pytest.skip("No waitlist entry created")
        
        entry_id = TestWaitlistAPI.created_entry_id
        update_payload = {
            "status": "notified",
            "notes": "Updated: Called twice"
        }
        response = requests.put(f"{BASE_URL}/api/waitlist/{entry_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "notified"
        print(f"✓ PUT /api/waitlist/{entry_id} - Updated to notified")
    
    def test_seat_waitlist_guest(self):
        """POST /api/waitlist/{id}/seat - seat guest from waitlist"""
        # Create a new entry to seat
        payload = {
            "guestName": "TEST_ToSeat Guest",
            "partySize": 2,
            "quotedWait": 10
        }
        create_response = requests.post(f"{BASE_URL}/api/waitlist", json=payload)
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        
        # Seat the guest
        response = requests.post(f"{BASE_URL}/api/waitlist/{entry_id}/seat")
        assert response.status_code == 200
        print(f"✓ POST /api/waitlist/{entry_id}/seat - Guest seated from waitlist")
        
        # Note: Entry should now have status 'seated' - won't appear in default waitlist query
    
    def test_remove_from_waitlist(self):
        """DELETE /api/waitlist/{id} - remove from waitlist"""
        if not TestWaitlistAPI.created_entry_id:
            pytest.skip("No waitlist entry created")
        
        entry_id = TestWaitlistAPI.created_entry_id
        response = requests.delete(f"{BASE_URL}/api/waitlist/{entry_id}")
        assert response.status_code == 200
        print(f"✓ DELETE /api/waitlist/{entry_id} - Removed from waitlist")
    
    def test_remove_nonexistent_entry(self):
        """DELETE /api/waitlist/{id} - should return 404 for non-existent"""
        response = requests.delete(f"{BASE_URL}/api/waitlist/NONEXISTENT-ID")
        assert response.status_code == 404
        print("✓ DELETE /api/waitlist/NONEXISTENT-ID - Returns 404 as expected")


# ============ API ROOT TEST ============
class TestAPIRoot:
    """Test API root endpoint"""
    
    def test_api_root(self):
        """GET /api/ - should return API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        print(f"✓ GET /api/ - API: {data.get('name')} v{data.get('version')}")


# ============ CLEANUP ============
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed data after all tests"""
    yield
    # Cleanup reservations
    try:
        res = requests.get(f"{BASE_URL}/api/reservations")
        if res.status_code == 200:
            for r in res.json():
                if r.get("guestName", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/reservations/{r['id']}")
    except:
        pass
    
    # Cleanup floor plans
    try:
        res = requests.get(f"{BASE_URL}/api/floor-plans")
        if res.status_code == 200:
            for fp in res.json():
                if fp.get("name", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/floor-plans/{fp['id']}")
    except:
        pass
    
    # Cleanup waitlist
    try:
        res = requests.get(f"{BASE_URL}/api/waitlist")
        if res.status_code == 200:
            for w in res.json():
                if w.get("guestName", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/waitlist/{w['id']}")
    except:
        pass
    
    print("\n✓ Test data cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
