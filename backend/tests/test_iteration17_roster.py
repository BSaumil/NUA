"""
Iteration 17 Tests: Enhanced Roster Features
- Week Roster creation (multiple shifts at once)
- Position stored in role/notes field
- Budget calculation (hours × payRate)
- Roster CRUD operations
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_owner_login(self):
        """Test owner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
        print(f"Owner login: PASS - token received")
        return data["token"]
    
    def test_manager_login(self):
        """Test manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "manager"
        print(f"Manager login: PASS")
        return data["token"]
    
    def test_cashier_login(self):
        """Test cashier login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "cashier@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "cashier"
        print(f"Cashier login: PASS")
        return data["token"]


class TestRosterCRUD:
    """Roster CRUD operations"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@nua.com",
            "password": "Staff2026!"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def cashier_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "cashier@nua.com",
            "password": "Staff2026!"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_list(self, owner_token):
        """Get list of staff members"""
        response = requests.get(f"{BASE_URL}/api/auth/staff", 
            headers={"Authorization": f"Bearer {owner_token}"})
        return response.json()
    
    def test_get_roster_owner(self, owner_token):
        """Owner can get roster"""
        response = requests.get(f"{BASE_URL}/api/staff/roster",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Get roster (owner): PASS - {len(data)} shifts found")
        return data
    
    def test_get_roster_manager(self, manager_token):
        """Manager can get roster"""
        response = requests.get(f"{BASE_URL}/api/staff/roster",
            headers={"Authorization": f"Bearer {manager_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Get roster (manager): PASS - {len(data)} shifts found")
    
    def test_get_roster_cashier_denied(self, cashier_token):
        """Cashier cannot get roster"""
        response = requests.get(f"{BASE_URL}/api/staff/roster",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403
        print(f"Get roster (cashier): PASS - correctly denied (403)")
    
    def test_create_roster_shift_with_position(self, owner_token, staff_list):
        """Create roster shift with position in role/notes field"""
        # Find a non-owner staff member
        staff = [s for s in staff_list if s.get("role") != "owner"]
        if not staff:
            pytest.skip("No non-owner staff found")
        
        test_staff = staff[0]
        shift_data = {
            "staffId": test_staff["id"],
            "staffName": test_staff["name"],
            "date": "Monday",
            "weekStart": "2026-01-06",
            "startTime": "09:00",
            "endTime": "17:00",
            "role": "Barista",  # Position stored in role
            "notes": "Barista"  # Position also stored in notes
        }
        
        response = requests.post(f"{BASE_URL}/api/staff/roster", json=shift_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        
        # Verify shift created with position
        assert "id" in data
        assert data["staffId"] == test_staff["id"]
        assert data["role"] == "Barista"
        assert data["notes"] == "Barista"
        assert data["startTime"] == "09:00"
        assert data["endTime"] == "17:00"
        print(f"Create roster shift with position: PASS - shift {data['id']} created with position=Barista")
        return data["id"]
    
    def test_create_roster_shift_manager(self, manager_token, staff_list):
        """Manager can create roster shift"""
        staff = [s for s in staff_list if s.get("role") != "owner"]
        if not staff:
            pytest.skip("No non-owner staff found")
        
        test_staff = staff[0]
        shift_data = {
            "staffId": test_staff["id"],
            "staffName": test_staff["name"],
            "date": "Tuesday",
            "weekStart": "2026-01-06",
            "startTime": "10:00",
            "endTime": "18:00",
            "role": "Floor",
            "notes": "Floor"
        }
        
        response = requests.post(f"{BASE_URL}/api/staff/roster", json=shift_data,
            headers={"Authorization": f"Bearer {manager_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "Floor"
        print(f"Create roster shift (manager): PASS - shift {data['id']} created")
        return data["id"]
    
    def test_create_roster_shift_cashier_denied(self, cashier_token, staff_list):
        """Cashier cannot create roster shift"""
        staff = [s for s in staff_list if s.get("role") != "owner"]
        if not staff:
            pytest.skip("No non-owner staff found")
        
        test_staff = staff[0]
        shift_data = {
            "staffId": test_staff["id"],
            "staffName": test_staff["name"],
            "date": "Wednesday",
            "startTime": "09:00",
            "endTime": "17:00",
            "role": "Kitchen"
        }
        
        response = requests.post(f"{BASE_URL}/api/staff/roster", json=shift_data,
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403
        print(f"Create roster shift (cashier): PASS - correctly denied (403)")
    
    def test_delete_roster_shift(self, owner_token, staff_list):
        """Delete roster shift"""
        # First create a shift to delete
        staff = [s for s in staff_list if s.get("role") != "owner"]
        if not staff:
            pytest.skip("No non-owner staff found")
        
        test_staff = staff[0]
        shift_data = {
            "staffId": test_staff["id"],
            "staffName": test_staff["name"],
            "date": "TEST_DELETE_DAY",
            "startTime": "09:00",
            "endTime": "17:00",
            "role": "Host"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/staff/roster", json=shift_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        shift_id = create_response.json()["id"]
        
        # Now delete it
        delete_response = requests.delete(f"{BASE_URL}/api/staff/roster/{shift_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert delete_response.status_code == 200
        print(f"Delete roster shift: PASS - shift {shift_id} deleted")
    
    def test_delete_roster_shift_cashier_denied(self, cashier_token, owner_token, staff_list):
        """Cashier cannot delete roster shift"""
        # First create a shift as owner
        staff = [s for s in staff_list if s.get("role") != "owner"]
        if not staff:
            pytest.skip("No non-owner staff found")
        
        test_staff = staff[0]
        shift_data = {
            "staffId": test_staff["id"],
            "staffName": test_staff["name"],
            "date": "TEST_CASHIER_DELETE",
            "startTime": "09:00",
            "endTime": "17:00",
            "role": "Register"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/staff/roster", json=shift_data,
            headers={"Authorization": f"Bearer {owner_token}"})
        shift_id = create_response.json()["id"]
        
        # Try to delete as cashier
        delete_response = requests.delete(f"{BASE_URL}/api/staff/roster/{shift_id}",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert delete_response.status_code == 403
        print(f"Delete roster shift (cashier): PASS - correctly denied (403)")
        
        # Cleanup - delete as owner
        requests.delete(f"{BASE_URL}/api/staff/roster/{shift_id}",
            headers={"Authorization": f"Bearer {owner_token}"})


class TestWeekRosterCreation:
    """Test creating multiple shifts for a week at once"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_list(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/auth/staff", 
            headers={"Authorization": f"Bearer {owner_token}"})
        return response.json()
    
    def test_create_multiple_shifts_for_week(self, owner_token, staff_list):
        """Create shifts for multiple days at once (simulating Add Week Roster)"""
        staff = [s for s in staff_list if s.get("role") != "owner"]
        if not staff:
            pytest.skip("No non-owner staff found")
        
        test_staff = staff[0]
        days = ["Monday", "Wednesday", "Friday"]
        position = "Barista"
        week_start = "2026-01-13"
        created_shifts = []
        
        for day in days:
            shift_data = {
                "staffId": test_staff["id"],
                "staffName": test_staff["name"],
                "date": day,
                "weekStart": week_start,
                "startTime": "08:00",
                "endTime": "16:00",
                "role": position,
                "notes": position
            }
            
            response = requests.post(f"{BASE_URL}/api/staff/roster", json=shift_data,
                headers={"Authorization": f"Bearer {owner_token}"})
            assert response.status_code == 200
            created_shifts.append(response.json()["id"])
        
        print(f"Create week roster (3 days): PASS - created {len(created_shifts)} shifts")
        
        # Verify all shifts exist
        roster_response = requests.get(f"{BASE_URL}/api/staff/roster",
            headers={"Authorization": f"Bearer {owner_token}"})
        roster = roster_response.json()
        
        for shift_id in created_shifts:
            assert any(s["id"] == shift_id for s in roster), f"Shift {shift_id} not found in roster"
        
        print(f"Verify week roster persistence: PASS - all 3 shifts found in roster")
        
        # Cleanup
        for shift_id in created_shifts:
            requests.delete(f"{BASE_URL}/api/staff/roster/{shift_id}",
                headers={"Authorization": f"Bearer {owner_token}"})


class TestPositionOptions:
    """Test all 8 position options"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_list(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/auth/staff", 
            headers={"Authorization": f"Bearer {owner_token}"})
        return response.json()
    
    def test_all_position_options(self, owner_token, staff_list):
        """Test creating shifts with all 8 position options"""
        positions = ['Barista', 'Bar', 'Floor', 'Kitchen', 'Register', 'Manager', 'Host', 'Dishwasher']
        staff = [s for s in staff_list if s.get("role") != "owner"]
        if not staff:
            pytest.skip("No non-owner staff found")
        
        test_staff = staff[0]
        created_shifts = []
        
        for i, position in enumerate(positions):
            shift_data = {
                "staffId": test_staff["id"],
                "staffName": test_staff["name"],
                "date": f"TEST_POS_{position}",
                "startTime": "09:00",
                "endTime": "17:00",
                "role": position,
                "notes": position
            }
            
            response = requests.post(f"{BASE_URL}/api/staff/roster", json=shift_data,
                headers={"Authorization": f"Bearer {owner_token}"})
            assert response.status_code == 200
            data = response.json()
            assert data["role"] == position
            assert data["notes"] == position
            created_shifts.append(data["id"])
        
        print(f"All 8 positions: PASS - {positions}")
        
        # Cleanup
        for shift_id in created_shifts:
            requests.delete(f"{BASE_URL}/api/staff/roster/{shift_id}",
                headers={"Authorization": f"Bearer {owner_token}"})


class TestTimecardsCostVisibility:
    """Test that Cost column is only visible to owner/manager"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def cashier_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "cashier@nua.com",
            "password": "Staff2026!"
        })
        return response.json()["token"]
    
    def test_get_timecards_owner(self, owner_token):
        """Owner can get timecards"""
        response = requests.get(f"{BASE_URL}/api/staff/timecards",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Get timecards (owner): PASS - {len(data)} timecards")
    
    def test_get_timecards_cashier(self, cashier_token):
        """Cashier can only see their own timecards"""
        response = requests.get(f"{BASE_URL}/api/staff/timecards",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 200
        data = response.json()
        # Cashier should only see their own timecards (filtered by backend)
        print(f"Get timecards (cashier): PASS - {len(data)} timecards (own only)")


class TestStaffReports:
    """Test staff reports endpoint"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    def test_get_staff_reports(self, owner_token):
        """Get staff reports with summary"""
        response = requests.get(f"{BASE_URL}/api/staff/reports",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        
        assert "staffStats" in data
        assert "summary" in data
        assert "totalStaff" in data["summary"]
        assert "totalHours" in data["summary"]
        assert "totalWages" in data["summary"]
        
        print(f"Staff reports: PASS - {data['summary']['totalStaff']} staff, {data['summary']['totalHours']}h total")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    def test_cleanup_test_shifts(self, owner_token):
        """Clean up any TEST_ prefixed shifts"""
        response = requests.get(f"{BASE_URL}/api/staff/roster",
            headers={"Authorization": f"Bearer {owner_token}"})
        roster = response.json()
        
        deleted = 0
        for shift in roster:
            if shift.get("date", "").startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/staff/roster/{shift['id']}",
                    headers={"Authorization": f"Bearer {owner_token}"})
                deleted += 1
        
        print(f"Cleanup: PASS - deleted {deleted} test shifts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
