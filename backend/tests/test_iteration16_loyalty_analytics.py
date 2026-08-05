"""
Iteration 16 Tests: Loyalty Editable Tiers/Rewards, Booking Analytics, Social Accounts, Email Settings
- Loyalty Tiers: GET, PUT (editable)
- Loyalty Rewards: GET, POST, PUT (with dates), DELETE
- Events: GET, POST, PUT
- Booking Analytics: GET (owner/manager only)
- Social Accounts: GET, POST, DELETE (owner only)
- Email Test: POST (owner/manager)
- Email Settings: GET, POST (owner only)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_owner_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@nua.com",
            "password": "NuaOwner2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
    
    def test_manager_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "manager"
    
    def test_cashier_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "cashier@nua.com",
            "password": "Staff2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "cashier"


@pytest.fixture
def owner_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "owner@nua.com",
        "password": "NuaOwner2026!"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Owner auth failed")

@pytest.fixture
def manager_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "manager@nua.com",
        "password": "Staff2026!"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Manager auth failed")

@pytest.fixture
def cashier_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "cashier@nua.com",
        "password": "Staff2026!"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Cashier auth failed")


class TestLoyaltyTiers:
    """Loyalty Tiers - GET and PUT (editable)"""
    
    def test_get_loyalty_tiers(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/loyalty/tiers", 
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 4  # Bronze, Silver, Gold, Platinum
        tier_names = [t["name"] for t in data]
        assert "Bronze" in tier_names or any("bronze" in t["id"].lower() for t in data)
    
    def test_update_loyalty_tier_owner(self, owner_token):
        # First get tiers to find one to update
        response = requests.get(f"{BASE_URL}/api/loyalty/tiers",
            headers={"Authorization": f"Bearer {owner_token}"})
        tiers = response.json()
        tier_id = tiers[0]["id"]  # Get first tier
        
        # Update the tier
        update_data = {
            "name": tiers[0]["name"],  # Keep same name
            "minPoints": tiers[0].get("minPoints", 0),
            "multiplier": 1.15,  # Change multiplier
            "perks": tiers[0].get("perks", []) + ["TEST_perk"]
        }
        response = requests.put(f"{BASE_URL}/api/loyalty/tiers/{tier_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["multiplier"] == 1.15
        assert "TEST_perk" in data["perks"]
        
        # Cleanup - remove test perk
        update_data["perks"] = [p for p in data["perks"] if p != "TEST_perk"]
        update_data["multiplier"] = tiers[0].get("multiplier", 1.0)
        requests.put(f"{BASE_URL}/api/loyalty/tiers/{tier_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=update_data)
    
    def test_update_nonexistent_tier(self, owner_token):
        response = requests.put(f"{BASE_URL}/api/loyalty/tiers/nonexistent-tier",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": "Test"})
        assert response.status_code == 404


class TestLoyaltyRewards:
    """Loyalty Rewards - CRUD with dates"""
    
    def test_get_loyalty_rewards(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/loyalty/rewards",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_reward_with_dates(self, owner_token):
        reward_data = {
            "name": "TEST_Weekend Special",
            "description": "Test reward with dates",
            "pointsCost": 200,
            "rewardType": "discount",
            "discountAmount": 15,
            "startDate": "2026-01-10",
            "startTime": "09:00",
            "endDate": "2026-01-20",
            "endTime": "21:00"
        }
        response = requests.post(f"{BASE_URL}/api/loyalty/rewards",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=reward_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Weekend Special"
        assert "id" in data
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/loyalty/rewards/{data['id']}",
            headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_update_reward_with_dates(self, owner_token):
        # Create a reward first
        create_response = requests.post(f"{BASE_URL}/api/loyalty/rewards",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": "TEST_Update Reward", "pointsCost": 100, "rewardType": "free_item"})
        reward_id = create_response.json()["id"]
        
        # Update with dates
        update_data = {
            "name": "TEST_Updated Reward",
            "pointsCost": 150,
            "startDate": "2026-02-01",
            "endDate": "2026-02-28"
        }
        response = requests.put(f"{BASE_URL}/api/loyalty/rewards/{reward_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Updated Reward"
        assert data["pointsCost"] == 150
        assert data["startDate"] == "2026-02-01"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/loyalty/rewards/{reward_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_delete_reward(self, owner_token):
        # Create then delete
        create_response = requests.post(f"{BASE_URL}/api/loyalty/rewards",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": "TEST_Delete Me", "pointsCost": 50, "rewardType": "discount"})
        reward_id = create_response.json()["id"]
        
        response = requests.delete(f"{BASE_URL}/api/loyalty/rewards/{reward_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200


class TestEvents:
    """Events - CRUD"""
    
    def test_get_events(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/events",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_event(self, owner_token):
        event_data = {
            "name": "TEST_Wine Tasting",
            "description": "Test event",
            "date": "2026-02-15",
            "time": "19:00",
            "duration": 120,
            "capacity": 30,
            "ticketPrice": 75,
            "eventType": "wine_pairing"
        }
        response = requests.post(f"{BASE_URL}/api/events",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=event_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Wine Tasting"
        assert "id" in data
        return data["id"]
    
    def test_update_event(self, owner_token):
        # Create event first (time is required)
        create_response = requests.post(f"{BASE_URL}/api/events",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": "TEST_Update Event", "date": "2026-03-01", "time": "18:00", "capacity": 20, "ticketPrice": 50, "eventType": "dining"})
        assert create_response.status_code == 200, f"Event creation failed: {create_response.text}"
        event_id = create_response.json()["id"]
        
        # Update
        update_data = {
            "name": "TEST_Updated Event",
            "capacity": 40,
            "ticketPrice": 65
        }
        response = requests.put(f"{BASE_URL}/api/events/{event_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Updated Event"
        assert data["capacity"] == 40


class TestBookingAnalytics:
    """Booking Analytics - owner/manager only"""
    
    def test_get_booking_analytics_owner(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/booking/analytics",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "totalBookings" in data
        assert "noShowRate" in data
        assert "avgPartySize" in data
        assert "byShift" in data
        assert "peakDays" in data
    
    def test_get_booking_analytics_manager(self, manager_token):
        response = requests.get(f"{BASE_URL}/api/booking/analytics",
            headers={"Authorization": f"Bearer {manager_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "totalBookings" in data
    
    def test_get_booking_analytics_cashier_denied(self, cashier_token):
        response = requests.get(f"{BASE_URL}/api/booking/analytics",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403


class TestSocialAccounts:
    """Social Media Accounts - owner only"""
    
    def test_get_social_accounts_owner(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/clubmember/social-accounts",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_social_accounts_manager_denied(self, manager_token):
        response = requests.get(f"{BASE_URL}/api/clubmember/social-accounts",
            headers={"Authorization": f"Bearer {manager_token}"})
        assert response.status_code == 403
    
    def test_add_social_account_owner(self, owner_token):
        account_data = {
            "platform": "instagram",
            "accountName": "TEST_nuatest",
            "accessToken": "test_token_123"
        }
        response = requests.post(f"{BASE_URL}/api/clubmember/social-accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=account_data)
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "instagram"
        assert data["accountName"] == "TEST_nuatest"
        assert data["connected"] == True
        assert "id" in data
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/clubmember/social-accounts/{data['id']}",
            headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_remove_social_account_owner(self, owner_token):
        # Create then remove
        create_response = requests.post(f"{BASE_URL}/api/clubmember/social-accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"platform": "tiktok", "accountName": "TEST_delete_me"})
        account_id = create_response.json()["id"]
        
        response = requests.delete(f"{BASE_URL}/api/clubmember/social-accounts/{account_id}",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
    
    def test_add_social_account_cashier_denied(self, cashier_token):
        response = requests.post(f"{BASE_URL}/api/clubmember/social-accounts",
            headers={"Authorization": f"Bearer {cashier_token}"},
            json={"platform": "facebook", "accountName": "test"})
        assert response.status_code == 403


class TestEmailFeatures:
    """Email Test and Settings - owner/manager for test, owner only for settings"""
    
    def test_send_test_email_owner(self, owner_token):
        response = requests.post(f"{BASE_URL}/api/email/test",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"subject": "TEST_Email", "body": "Test body"})
        assert response.status_code == 200
        data = response.json()
        assert "emailId" in data
        # Default recipient should be sambhatt7@gmail.com
        assert "sambhatt7@gmail.com" in data.get("message", "")
    
    def test_send_test_email_manager(self, manager_token):
        response = requests.post(f"{BASE_URL}/api/email/test",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"subject": "TEST_Manager Email"})
        assert response.status_code == 200
    
    def test_send_test_email_cashier_denied(self, cashier_token):
        response = requests.post(f"{BASE_URL}/api/email/test",
            headers={"Authorization": f"Bearer {cashier_token}"},
            json={"subject": "TEST"})
        assert response.status_code == 403
    
    def test_get_email_settings_owner(self, owner_token):
        response = requests.get(f"{BASE_URL}/api/email/settings",
            headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "testEmail" in data
        assert data["testEmail"] == "sambhatt7@gmail.com"
    
    def test_get_email_settings_manager_denied(self, manager_token):
        response = requests.get(f"{BASE_URL}/api/email/settings",
            headers={"Authorization": f"Bearer {manager_token}"})
        assert response.status_code == 403
    
    def test_save_email_settings_owner(self, owner_token):
        settings_data = {
            "testEmail": "sambhatt7@gmail.com",
            "senderName": "NUA POS Test",
            "senderEmail": "noreply@nua.com"
        }
        response = requests.post(f"{BASE_URL}/api/email/settings",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=settings_data)
        assert response.status_code == 200


class TestCashierRestrictions:
    """Verify cashier cannot access booking analytics or edit tiers"""
    
    def test_cashier_cannot_access_booking_analytics(self, cashier_token):
        response = requests.get(f"{BASE_URL}/api/booking/analytics",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403
    
    def test_cashier_cannot_access_social_accounts(self, cashier_token):
        response = requests.get(f"{BASE_URL}/api/clubmember/social-accounts",
            headers={"Authorization": f"Bearer {cashier_token}"})
        assert response.status_code == 403
    
    def test_cashier_cannot_send_test_email(self, cashier_token):
        response = requests.post(f"{BASE_URL}/api/email/test",
            headers={"Authorization": f"Bearer {cashier_token}"},
            json={"subject": "Test"})
        assert response.status_code == 403
