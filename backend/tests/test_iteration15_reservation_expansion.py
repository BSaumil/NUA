"""
Iteration 15 Tests: NUVA POS Reservation System Expansion
- Table Layout & Combinations
- Booking Settings (Rules + Schedule)
- Booking Experiences
- Clubmember Offers (EatClub-style)
- Staff redirect to POS (cashier/kitchen)
- Role-based access control
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OWNER_CREDS = {"email": "owner@nuva.com", "password": "NuvaOwner2026!"}
MANAGER_CREDS = {"email": "manager@nuva.com", "password": "Staff2026!"}
CASHIER_CREDS = {"email": "cashier@nuva.com", "password": "Staff2026!"}


class TestAuth:
    """Authentication tests for all roles"""
    
    def test_owner_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
        print(f"✓ Owner login successful, role: {data['user']['role']}")
    
    def test_manager_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "manager"
        print(f"✓ Manager login successful, role: {data['user']['role']}")
    
    def test_cashier_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "cashier"
        print(f"✓ Cashier login successful, role: {data['user']['role']}")


@pytest.fixture
def owner_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Owner auth failed")


@pytest.fixture
def manager_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Manager auth failed")


@pytest.fixture
def cashier_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CASHIER_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Cashier auth failed")


class TestTableCombinations:
    """Table Layout & Combinations CRUD"""
    
    def test_get_table_combinations(self, owner_token):
        """GET /api/tables/combinations returns list"""
        response = requests.get(
            f"{BASE_URL}/api/tables/combinations",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/tables/combinations returned {len(data)} combinations")
    
    def test_create_table_combination_owner(self, owner_token):
        """POST /api/tables/combinations creates combo (owner)"""
        payload = {
            "name": "TEST_Combo_A",
            "tableIds": ["1", "2"],
            "maxCovers": 8
        }
        response = requests.post(
            f"{BASE_URL}/api/tables/combinations",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "TEST_Combo_A"
        assert data["tableIds"] == ["1", "2"]
        assert data["maxCovers"] == 8
        print(f"✓ Created table combination: {data['id']}")
        return data["id"]
    
    def test_create_table_combination_manager(self, manager_token):
        """POST /api/tables/combinations creates combo (manager allowed)"""
        payload = {
            "name": "TEST_Combo_Manager",
            "tableIds": ["3", "4"],
            "maxCovers": 10
        }
        response = requests.post(
            f"{BASE_URL}/api/tables/combinations",
            json=payload,
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Manager created table combination: {data['id']}")
    
    def test_create_table_combination_cashier_denied(self, cashier_token):
        """POST /api/tables/combinations denied for cashier (403)"""
        payload = {
            "name": "TEST_Combo_Cashier",
            "tableIds": ["5", "6"],
            "maxCovers": 6
        }
        response = requests.post(
            f"{BASE_URL}/api/tables/combinations",
            json=payload,
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403
        print("✓ Cashier denied creating table combination (403)")


class TestBookingRules:
    """Booking Rules CRUD"""
    
    def test_get_booking_rules(self, owner_token):
        """GET /api/booking/rules returns rules with maxOnlinePartySize"""
        response = requests.get(
            f"{BASE_URL}/api/booking/rules",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "maxOnlinePartySize" in data
        assert "bookingWindowMinutes" in data
        print(f"✓ GET /api/booking/rules: maxOnlinePartySize={data['maxOnlinePartySize']}, bookingWindow={data['bookingWindowMinutes']}min")
    
    def test_save_booking_rules_owner(self, owner_token):
        """POST /api/booking/rules saves rules (owner only)"""
        payload = {
            "maxOnlinePartySize": 12,
            "maxAdvanceDays": 90,
            "bookingWindowMinutes": 60,
            "autoConfirm": False,
            "requireDeposit": True,
            "depositAmount": 25.00,
            "noShowFee": 50.00,
            "cancellationHours": 4
        }
        response = requests.post(
            f"{BASE_URL}/api/booking/rules",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        print("✓ Owner saved booking rules")
        
        # Verify persistence
        get_response = requests.get(
            f"{BASE_URL}/api/booking/rules",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert get_response.status_code == 200
        saved = get_response.json()
        assert saved["maxOnlinePartySize"] == 12
        assert saved["bookingWindowMinutes"] == 60
        print("✓ Booking rules persisted correctly")
    
    def test_save_booking_rules_manager_denied(self, manager_token):
        """POST /api/booking/rules denied for manager (403)"""
        payload = {"maxOnlinePartySize": 15}
        response = requests.post(
            f"{BASE_URL}/api/booking/rules",
            json=payload,
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 403
        print("✓ Manager denied saving booking rules (403)")
    
    def test_save_booking_rules_cashier_denied(self, cashier_token):
        """POST /api/booking/rules denied for cashier (403)"""
        payload = {"maxOnlinePartySize": 15}
        response = requests.post(
            f"{BASE_URL}/api/booking/rules",
            json=payload,
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403
        print("✓ Cashier denied saving booking rules (403)")


class TestBookingSchedule:
    """Booking Schedule (Shifts) CRUD"""
    
    def test_get_booking_schedule_default_shifts(self, owner_token):
        """GET /api/booking/schedule returns 3 default shifts"""
        response = requests.get(
            f"{BASE_URL}/api/booking/schedule",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least 3 default shifts (Breakfast, Lunch, Dinner)
        shift_names = [s.get("name", "") for s in data]
        print(f"✓ GET /api/booking/schedule returned {len(data)} shifts: {shift_names}")
        # Check for default shifts
        assert any("Breakfast" in name for name in shift_names) or len(data) >= 3
    
    def test_save_booking_schedule_owner(self, owner_token):
        """POST /api/booking/schedule saves shifts (owner)"""
        payload = {
            "shifts": [
                {"id": "shift-breakfast", "name": "Breakfast", "startTime": "07:00", "endTime": "11:00", "interval": 30, "enabled": True},
                {"id": "shift-lunch", "name": "Lunch", "startTime": "11:30", "endTime": "15:00", "interval": 30, "enabled": True},
                {"id": "shift-dinner", "name": "Dinner", "startTime": "17:00", "endTime": "22:00", "interval": 60, "enabled": True},
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/booking/schedule",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        print("✓ Owner saved booking schedule")


class TestBookingExperiences:
    """Booking Experiences CRUD"""
    
    def test_get_experiences(self, owner_token):
        """GET /api/booking/experiences returns list"""
        response = requests.get(
            f"{BASE_URL}/api/booking/experiences",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/booking/experiences returned {len(data)} experiences")
    
    def test_create_experience_owner(self, owner_token):
        """POST /api/booking/experiences creates experience (owner)"""
        payload = {
            "name": "TEST_Wine_Tasting",
            "description": "Premium wine tasting experience",
            "days": ["Friday", "Saturday"],
            "startDate": "2026-02-01",
            "endDate": "2026-03-31",
            "pricePerPerson": 75.00,
            "maxBookings": 20,
            "active": True
        }
        response = requests.post(
            f"{BASE_URL}/api/booking/experiences",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "TEST_Wine_Tasting"
        assert data["pricePerPerson"] == 75.00
        assert data["days"] == ["Friday", "Saturday"]
        print(f"✓ Created experience: {data['id']}")
        return data["id"]
    
    def test_create_experience_manager(self, manager_token):
        """POST /api/booking/experiences creates experience (manager allowed)"""
        payload = {
            "name": "TEST_Chef_Table",
            "description": "Exclusive chef's table experience",
            "days": ["Saturday"],
            "pricePerPerson": 150.00,
            "maxBookings": 8,
            "active": True
        }
        response = requests.post(
            f"{BASE_URL}/api/booking/experiences",
            json=payload,
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Manager created experience: {data['id']}")
    
    def test_create_experience_cashier_denied(self, cashier_token):
        """POST /api/booking/experiences denied for cashier (403)"""
        payload = {
            "name": "TEST_Cashier_Exp",
            "description": "Should fail",
            "pricePerPerson": 50.00
        }
        response = requests.post(
            f"{BASE_URL}/api/booking/experiences",
            json=payload,
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403
        print("✓ Cashier denied creating experience (403)")


class TestClubmemberOffers:
    """Clubmember Offers (EatClub-style) CRUD"""
    
    def test_get_club_offers(self, owner_token):
        """GET /api/clubmember/offers returns list"""
        response = requests.get(
            f"{BASE_URL}/api/clubmember/offers",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/clubmember/offers returned {len(data)} offers")
    
    def test_create_club_offer_owner(self, owner_token):
        """POST /api/clubmember/offers creates offer (owner only)"""
        payload = {
            "title": "TEST_Happy_Hour_Deal",
            "description": "Social media exclusive discount",
            "discount": 30,
            "startDate": "2026-02-01",
            "startTime": "17:00",
            "endDate": "2026-02-28",
            "endTime": "19:00",
            "totalSlots": 15,
            "active": True,
            "socialPlatforms": ["instagram", "facebook", "tiktok"]
        }
        response = requests.post(
            f"{BASE_URL}/api/clubmember/offers",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "TEST_Happy_Hour_Deal"
        assert data["discount"] == 30
        assert data["totalSlots"] == 15
        assert "instagram" in data["socialPlatforms"]
        print(f"✓ Created club offer: {data['id']}")
        return data["id"]
    
    def test_create_club_offer_discount_validation_min(self, owner_token):
        """POST /api/clubmember/offers validates discount >= 20%"""
        payload = {
            "title": "TEST_Low_Discount",
            "discount": 10,  # Below minimum 20%
            "totalSlots": 5
        }
        response = requests.post(
            f"{BASE_URL}/api/clubmember/offers",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 400
        assert "20%" in response.json().get("detail", "") or "20" in response.json().get("detail", "")
        print("✓ Discount < 20% rejected (400)")
    
    def test_create_club_offer_discount_validation_max(self, owner_token):
        """POST /api/clubmember/offers validates discount <= 50%"""
        payload = {
            "title": "TEST_High_Discount",
            "discount": 60,  # Above maximum 50%
            "totalSlots": 5
        }
        response = requests.post(
            f"{BASE_URL}/api/clubmember/offers",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 400
        assert "50%" in response.json().get("detail", "") or "50" in response.json().get("detail", "")
        print("✓ Discount > 50% rejected (400)")
    
    def test_create_club_offer_manager_denied(self, manager_token):
        """POST /api/clubmember/offers denied for manager (403)"""
        payload = {
            "title": "TEST_Manager_Offer",
            "discount": 25,
            "totalSlots": 10
        }
        response = requests.post(
            f"{BASE_URL}/api/clubmember/offers",
            json=payload,
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 403
        print("✓ Manager denied creating club offer (403)")
    
    def test_create_club_offer_cashier_denied(self, cashier_token):
        """POST /api/clubmember/offers denied for cashier (403)"""
        payload = {
            "title": "TEST_Cashier_Offer",
            "discount": 25,
            "totalSlots": 10
        }
        response = requests.post(
            f"{BASE_URL}/api/clubmember/offers",
            json=payload,
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert response.status_code == 403
        print("✓ Cashier denied creating club offer (403)")


class TestClubmemberClaim:
    """Clubmember Offer Claim (Public endpoint)"""
    
    def test_claim_club_offer(self, owner_token):
        """POST /api/clubmember/offers/{id}/claim claims slot (public)"""
        # First create an offer
        create_payload = {
            "title": "TEST_Claimable_Offer",
            "discount": 25,
            "totalSlots": 5,
            "active": True
        }
        create_response = requests.post(
            f"{BASE_URL}/api/clubmember/offers",
            json=create_payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert create_response.status_code == 200
        offer_id = create_response.json()["id"]
        
        # Claim without auth (public endpoint)
        claim_payload = {
            "name": "Test Customer",
            "email": "test@example.com"
        }
        claim_response = requests.post(
            f"{BASE_URL}/api/clubmember/offers/{offer_id}/claim",
            json=claim_payload
        )
        assert claim_response.status_code == 200
        claim_data = claim_response.json()
        assert "id" in claim_data
        assert claim_data["offerId"] == offer_id
        assert claim_data["discount"] == 25
        print(f"✓ Claimed offer {offer_id}, claim ID: {claim_data['id']}")
    
    def test_claim_nonexistent_offer(self):
        """POST /api/clubmember/offers/{id}/claim returns 404 for invalid offer"""
        claim_payload = {"name": "Test", "email": "test@example.com"}
        response = requests.post(
            f"{BASE_URL}/api/clubmember/offers/INVALID-ID/claim",
            json=claim_payload
        )
        assert response.status_code == 404
        print("✓ Claim nonexistent offer returns 404")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, owner_token):
        """Delete TEST_ prefixed data"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        
        # Cleanup table combinations
        combos = requests.get(f"{BASE_URL}/api/tables/combinations", headers=headers).json()
        for combo in combos:
            if combo.get("name", "").startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/tables/combinations/{combo['id']}", headers=headers)
                print(f"  Deleted combo: {combo['id']}")
        
        # Cleanup experiences
        exps = requests.get(f"{BASE_URL}/api/booking/experiences", headers=headers).json()
        for exp in exps:
            if exp.get("name", "").startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/booking/experiences/{exp['id']}", headers=headers)
                print(f"  Deleted experience: {exp['id']}")
        
        # Cleanup club offers
        offers = requests.get(f"{BASE_URL}/api/clubmember/offers", headers=headers).json()
        for offer in offers:
            if offer.get("title", "").startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/clubmember/offers/{offer['id']}", headers=headers)
                print(f"  Deleted offer: {offer['id']}")
        
        print("✓ Test data cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
