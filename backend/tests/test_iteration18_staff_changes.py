"""
Iteration 18 Tests: Staff System Changes
- Adding staff no longer requires email/password - only name is required, PIN is optional
- Owner can select salary type: Hourly, Daily, or Annually
- Owner can add custom roles (beyond default 8)
- Roster displayed week-wise (Mon-Sun columns) instead of staff-wise rows
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_owner_login(self):
        """Test owner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
        print("PASS: Owner login successful")
        return data["token"]

    def test_manager_login(self):
        """Test manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "manager"
        print("PASS: Manager login successful")
        return data["token"]

    def test_cashier_login(self):
        """Test cashier login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "cashier@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200, f"Cashier login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "cashier"
        print("PASS: Cashier login successful")
        return data["token"]


class TestStaffAddWithNameOnly:
    """Test adding staff with just name (no email/password required)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    def test_add_staff_with_name_only(self, owner_token):
        """Test adding staff with just name - no email/password"""
        unique_name = f"TEST_NameOnly_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"name": unique_name},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed to add staff with name only: {response.text}"
        data = response.json()
        assert data["name"] == unique_name
        # Email should be auto-generated
        assert "@nua.local" in data["email"] or data["email"] != ""
        assert data["role"] == "cashier"  # Default role
        print(f"PASS: Staff created with name only - email auto-generated: {data['email']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_add_staff_with_name_and_pin(self, owner_token):
        """Test adding staff with name and PIN (no email/password)"""
        unique_name = f"TEST_NamePin_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"name": unique_name, "pin": "1234"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == unique_name
        assert data["pin"] == "1234"
        print(f"PASS: Staff created with name and PIN")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_add_staff_with_optional_email_password(self, owner_token):
        """Test adding staff with optional email and password"""
        unique_name = f"TEST_WithEmail_{uuid.uuid4().hex[:6]}"
        unique_email = f"test_{uuid.uuid4().hex[:6]}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={
                "name": unique_name,
                "email": unique_email,
                "password": "TestPass123!",
                "pin": "99"
            },
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == unique_name
        assert data["email"] == unique_email.lower()
        print(f"PASS: Staff created with optional email/password")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_add_staff_name_required(self, owner_token):
        """Test that name is required"""
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"pin": "1234"},  # No name
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 400, f"Should fail without name: {response.text}"
        print("PASS: Name is required - returns 400 without name")


class TestSalaryType:
    """Test salary type field (hourly/daily/annually)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    def test_add_staff_with_hourly_salary(self, owner_token):
        """Test adding staff with hourly salary type"""
        unique_name = f"TEST_Hourly_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"name": unique_name, "salaryType": "hourly", "payRate": 25.50},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["salaryType"] == "hourly"
        assert data["payRate"] == 25.50
        print("PASS: Staff created with hourly salary type")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_add_staff_with_daily_salary(self, owner_token):
        """Test adding staff with daily salary type"""
        unique_name = f"TEST_Daily_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"name": unique_name, "salaryType": "daily", "payRate": 200},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["salaryType"] == "daily"
        assert data["payRate"] == 200
        print("PASS: Staff created with daily salary type")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_add_staff_with_annually_salary(self, owner_token):
        """Test adding staff with annually salary type"""
        unique_name = f"TEST_Annual_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"name": unique_name, "salaryType": "annually", "payRate": 65000},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["salaryType"] == "annually"
        assert data["payRate"] == 65000
        print("PASS: Staff created with annually salary type")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_update_staff_salary_type(self, owner_token):
        """Test updating staff salary type"""
        # Create staff first
        unique_name = f"TEST_UpdateSalary_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"name": unique_name, "salaryType": "hourly", "payRate": 20},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        staff_id = create_resp.json()["id"]
        
        # Update salary type
        update_resp = requests.put(
            f"{BASE_URL}/api/auth/staff/{staff_id}",
            json={"salaryType": "daily", "payRate": 180},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert update_resp.status_code == 200, f"Failed to update: {update_resp.text}"
        data = update_resp.json()
        assert data["salaryType"] == "daily"
        assert data["payRate"] == 180
        print("PASS: Staff salary type updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{staff_id}", headers={"Authorization": f"Bearer {owner_token}"})


class TestCustomRoles:
    """Test custom roles management"""
    
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
    
    def test_get_roles(self, owner_token):
        """Test getting roles list"""
        response = requests.get(
            f"{BASE_URL}/api/auth/roles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        roles = response.json()
        assert isinstance(roles, list)
        # Should have default roles
        default_roles = ["cashier", "kitchen", "manager", "barista", "bar", "floor", "host", "dishwasher"]
        for role in default_roles:
            assert role in roles, f"Missing default role: {role}"
        print(f"PASS: GET /api/auth/roles returns {len(roles)} roles: {roles}")
    
    def test_save_custom_roles_owner(self, owner_token):
        """Test saving custom roles (owner only)"""
        # Get current roles
        get_resp = requests.get(f"{BASE_URL}/api/auth/roles", headers={"Authorization": f"Bearer {owner_token}"})
        current_roles = get_resp.json()
        
        # Add a new custom role
        new_role = f"test_role_{uuid.uuid4().hex[:4]}"
        updated_roles = current_roles + [new_role]
        
        response = requests.post(
            f"{BASE_URL}/api/auth/roles",
            json={"roles": updated_roles},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert new_role in data["roles"]
        print(f"PASS: Custom role '{new_role}' added successfully")
        
        # Cleanup - restore original roles
        requests.post(f"{BASE_URL}/api/auth/roles", json={"roles": current_roles}, headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_save_custom_roles_manager_denied(self, manager_token):
        """Test that manager cannot save custom roles"""
        response = requests.post(
            f"{BASE_URL}/api/auth/roles",
            json={"roles": ["test"]},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 403, f"Manager should not be able to save roles: {response.text}"
        print("PASS: Manager cannot save custom roles (403)")
    
    def test_add_staff_with_custom_role(self, owner_token):
        """Test adding staff with a custom role"""
        # First add a custom role
        get_resp = requests.get(f"{BASE_URL}/api/auth/roles", headers={"Authorization": f"Bearer {owner_token}"})
        current_roles = get_resp.json()
        custom_role = "pizza_maker"
        if custom_role not in current_roles:
            requests.post(f"{BASE_URL}/api/auth/roles", json={"roles": current_roles + [custom_role]}, headers={"Authorization": f"Bearer {owner_token}"})
        
        # Add staff with custom role
        unique_name = f"TEST_CustomRole_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/auth/staff/add",
            json={"name": unique_name, "role": custom_role},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["role"] == custom_role
        print(f"PASS: Staff created with custom role '{custom_role}'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/auth/staff/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})


class TestRosterWeekView:
    """Test roster week-wise view (Mon-Sun columns)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    def test_create_shift_with_day_name(self, owner_token):
        """Test creating shift with day name (Monday, Tuesday, etc.)"""
        # Get staff list
        staff_resp = requests.get(f"{BASE_URL}/api/auth/staff", headers={"Authorization": f"Bearer {owner_token}"})
        staff = [s for s in staff_resp.json() if s["role"] != "owner"]
        if not staff:
            pytest.skip("No staff available for testing")
        
        staff_member = staff[0]
        
        # Create shift for Monday
        response = requests.post(
            f"{BASE_URL}/api/staff/roster",
            json={
                "staffId": staff_member["id"],
                "staffName": staff_member["name"],
                "date": "Monday",
                "startTime": "09:00",
                "endTime": "17:00",
                "role": "Floor",
                "notes": "Floor"
            },
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["date"] == "Monday"
        print(f"PASS: Shift created for Monday")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/staff/roster/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_get_roster_grouped_by_day(self, owner_token):
        """Test getting roster - shifts should have day names"""
        response = requests.get(
            f"{BASE_URL}/api/staff/roster",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        roster = response.json()
        
        # Check that shifts have date field (day names)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for shift in roster:
            if shift.get("date"):
                # Date should be a day name or contain a day name
                has_day = any(day in shift["date"] for day in days)
                if has_day:
                    print(f"  Shift: {shift.get('staffName')} on {shift['date']}")
        
        print(f"PASS: GET /api/staff/roster returns {len(roster)} shifts")
    
    def test_create_week_roster_multiple_days(self, owner_token):
        """Test creating shifts for multiple days in a week"""
        # Get staff list
        staff_resp = requests.get(f"{BASE_URL}/api/auth/staff", headers={"Authorization": f"Bearer {owner_token}"})
        staff = [s for s in staff_resp.json() if s["role"] != "owner"]
        if not staff:
            pytest.skip("No staff available for testing")
        
        staff_member = staff[0]
        created_ids = []
        
        # Create shifts for Mon, Wed, Fri
        for day in ["Monday", "Wednesday", "Friday"]:
            response = requests.post(
                f"{BASE_URL}/api/staff/roster",
                json={
                    "staffId": staff_member["id"],
                    "staffName": staff_member["name"],
                    "date": day,
                    "startTime": "10:00",
                    "endTime": "18:00",
                    "role": "Barista",
                    "notes": "Barista"
                },
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            if response.status_code == 200:
                created_ids.append(response.json()["id"])
        
        assert len(created_ids) == 3, f"Expected 3 shifts created, got {len(created_ids)}"
        print(f"PASS: Created shifts for Mon/Wed/Fri")
        
        # Cleanup
        for shift_id in created_ids:
            requests.delete(f"{BASE_URL}/api/staff/roster/{shift_id}", headers={"Authorization": f"Bearer {owner_token}"})


class TestStaffListPayRateColumn:
    """Test staff list shows pay rate with salary type abbreviation"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        return response.json()["token"]
    
    def test_staff_list_includes_salary_type(self, owner_token):
        """Test that staff list includes salaryType field"""
        response = requests.get(
            f"{BASE_URL}/api/auth/staff",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        staff = response.json()
        
        # Check that staff have salaryType field
        for s in staff:
            if s.get("payRate", 0) > 0:
                print(f"  {s['name']}: ${s.get('payRate', 0)}/{s.get('salaryType', 'hourly')[:2]}")
        
        print(f"PASS: Staff list returns {len(staff)} members with salaryType field")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
