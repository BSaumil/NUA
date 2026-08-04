"""
Backend API Tests for NUA POS - Phase 2 (Guest CRM, Feedback) and Phase 3 (KDS)
Tests cover:
- Customer 360° Profile API
- Feedback API (CRUD + respond)
- Kitchen Display System (KDS) API (CRUD + workflow actions)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCustomerProfile:
    """Customer 360° Profile API tests"""
    
    def test_get_customers_list(self):
        """GET /api/customers - list all customers"""
        response = requests.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} customers")
        
    def test_get_customer_profile_full(self):
        """GET /api/customers/{id}/profile - full 360° profile"""
        # First get a customer
        customers_res = requests.get(f"{BASE_URL}/api/customers")
        assert customers_res.status_code == 200
        customers = customers_res.json()
        
        if len(customers) == 0:
            pytest.skip("No customers in database")
        
        customer_id = customers[0]['id']
        response = requests.get(f"{BASE_URL}/api/customers/{customer_id}/profile")
        assert response.status_code == 200
        
        profile = response.json()
        # Verify profile structure
        assert 'id' in profile
        assert 'name' in profile
        assert 'email' in profile
        assert 'reservationHistory' in profile
        assert 'feedbackHistory' in profile
        assert 'transactionHistory' in profile
        assert isinstance(profile['reservationHistory'], list)
        assert isinstance(profile['feedbackHistory'], list)
        assert isinstance(profile['transactionHistory'], list)
        print(f"Profile for {profile['name']}: {len(profile['reservationHistory'])} reservations, {len(profile['feedbackHistory'])} feedback, {len(profile['transactionHistory'])} transactions")
        
    def test_get_customer_profile_not_found(self):
        """GET /api/customers/{id}/profile - 404 for non-existent customer"""
        response = requests.get(f"{BASE_URL}/api/customers/nonexistent-id/profile")
        assert response.status_code == 404
        
    def test_create_customer(self):
        """POST /api/customers - create new customer"""
        customer_data = {
            "name": f"TEST_Customer_{uuid.uuid4().hex[:6]}",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "0412345678",
            "membershipTier": "Gold",
            "isVip": True,
            "dietaryRestrictions": ["Gluten-Free", "Vegan"],
            "allergies": ["Peanuts"],
            "tags": ["VIP", "Corporate"],
            "seatingPreference": "window",
            "notes": "Test customer for automated testing"
        }
        response = requests.post(f"{BASE_URL}/api/customers", json=customer_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created['name'] == customer_data['name']
        assert created['email'] == customer_data['email']
        assert created['membershipTier'] == 'Gold'
        assert created['isVip'] == True
        assert 'Gluten-Free' in created.get('dietaryRestrictions', [])
        print(f"Created customer: {created['id']}")
        
        # Verify via GET profile
        profile_res = requests.get(f"{BASE_URL}/api/customers/{created['id']}/profile")
        assert profile_res.status_code == 200
        profile = profile_res.json()
        assert profile['name'] == customer_data['name']
        
    def test_update_customer(self):
        """PUT /api/customers/{id} - update customer"""
        # Create a customer first
        customer_data = {
            "name": f"TEST_Update_{uuid.uuid4().hex[:6]}",
            "email": f"update_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "0400000000"
        }
        create_res = requests.post(f"{BASE_URL}/api/customers", json=customer_data)
        assert create_res.status_code == 200
        customer_id = create_res.json()['id']
        
        # Update
        update_data = {
            "name": "TEST_Updated Name",
            "membershipTier": "Platinum",
            "isVip": True
        }
        update_res = requests.put(f"{BASE_URL}/api/customers/{customer_id}", json=update_data)
        assert update_res.status_code == 200
        
        updated = update_res.json()
        assert updated['name'] == "TEST_Updated Name"
        assert updated['membershipTier'] == "Platinum"
        print(f"Updated customer {customer_id}")
        
    def test_search_customers(self):
        """GET /api/customers?search= - search customers"""
        response = requests.get(f"{BASE_URL}/api/customers", params={"search": "TEST"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Search found {len(data)} customers matching 'TEST'")


class TestFeedbackAPI:
    """Feedback API tests"""
    
    def test_get_all_feedback(self):
        """GET /api/feedback - list all feedback"""
        response = requests.get(f"{BASE_URL}/api/feedback")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} feedback entries")
        
    def test_get_feedback_by_customer(self):
        """GET /api/feedback?customer_id= - filter by customer"""
        # Get a customer first
        customers_res = requests.get(f"{BASE_URL}/api/customers")
        if customers_res.status_code == 200 and len(customers_res.json()) > 0:
            customer_id = customers_res.json()[0]['id']
            response = requests.get(f"{BASE_URL}/api/feedback", params={"customer_id": customer_id})
            assert response.status_code == 200
            assert isinstance(response.json(), list)
            
    def test_create_feedback(self):
        """POST /api/feedback - create new feedback"""
        # Get a customer
        customers_res = requests.get(f"{BASE_URL}/api/customers")
        assert customers_res.status_code == 200
        customers = customers_res.json()
        
        if len(customers) == 0:
            pytest.skip("No customers to add feedback for")
            
        customer_id = customers[0]['id']
        feedback_data = {
            "customerId": customer_id,
            "guestName": customers[0]['name'],
            "rating": 4,
            "foodRating": 5,
            "serviceRating": 4,
            "ambienceRating": 4,
            "comment": "TEST_Feedback - Great food and service!"
        }
        response = requests.post(f"{BASE_URL}/api/feedback", json=feedback_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created['customerId'] == customer_id
        assert created['rating'] == 4
        assert created['foodRating'] == 5
        assert 'id' in created
        print(f"Created feedback: {created['id']}")
        
        # Verify feedback appears in customer profile
        profile_res = requests.get(f"{BASE_URL}/api/customers/{customer_id}/profile")
        assert profile_res.status_code == 200
        profile = profile_res.json()
        feedback_ids = [f['id'] for f in profile.get('feedbackHistory', [])]
        assert created['id'] in feedback_ids, "Feedback should appear in customer profile"
        
    def test_respond_to_feedback(self):
        """PUT /api/feedback/{id}/respond - respond to feedback"""
        # Get existing feedback
        feedback_res = requests.get(f"{BASE_URL}/api/feedback")
        assert feedback_res.status_code == 200
        feedbacks = feedback_res.json()
        
        if len(feedbacks) == 0:
            pytest.skip("No feedback to respond to")
            
        feedback_id = feedbacks[0]['id']
        response = requests.put(
            f"{BASE_URL}/api/feedback/{feedback_id}/respond",
            params={"response": "Thank you for your feedback! We appreciate it."}
        )
        assert response.status_code == 200
        
        updated = response.json()
        assert updated['status'] == 'responded'
        assert updated['response'] == "Thank you for your feedback! We appreciate it."
        print(f"Responded to feedback {feedback_id}")
        
    def test_respond_to_nonexistent_feedback(self):
        """PUT /api/feedback/{id}/respond - 404 for non-existent"""
        response = requests.put(
            f"{BASE_URL}/api/feedback/nonexistent-id/respond",
            params={"response": "Test"}
        )
        assert response.status_code == 404


class TestKitchenDisplayAPI:
    """Kitchen Display System (KDS) API tests"""
    
    def test_get_kitchen_orders(self):
        """GET /api/kitchen/orders - list active orders"""
        response = requests.get(f"{BASE_URL}/api/kitchen/orders")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} active kitchen orders")
        
    def test_get_kitchen_orders_by_status(self):
        """GET /api/kitchen/orders?status= - filter by status"""
        for status in ['new', 'preparing', 'ready']:
            response = requests.get(f"{BASE_URL}/api/kitchen/orders", params={"status": status})
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # All returned orders should have the requested status
            for order in data:
                assert order['status'] == status
            print(f"Status '{status}': {len(data)} orders")
            
    def test_create_kitchen_order(self):
        """POST /api/kitchen/orders - create new order"""
        order_data = {
            "tableNumber": "T99",
            "orderType": "dine_in",
            "items": [
                {"productId": "test-prod-1", "productName": "TEST_Burger", "quantity": 2, "course": 1, "status": "pending"},
                {"productId": "test-prod-2", "productName": "TEST_Fries", "quantity": 1, "course": 1, "status": "pending"}
            ],
            "notes": "TEST_Order - No onions please",
            "priority": "normal"
        }
        response = requests.post(f"{BASE_URL}/api/kitchen/orders", json=order_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created['tableNumber'] == "T99"
        assert created['status'] == 'new'
        assert len(created['items']) == 2
        assert 'id' in created
        print(f"Created kitchen order: {created['id']}")
        return created['id']
        
    def test_kitchen_order_workflow_start(self):
        """POST /api/kitchen/orders/{id}/start - start preparing order"""
        # Create an order first
        order_data = {
            "tableNumber": "T100",
            "orderType": "dine_in",
            "items": [{"productId": "p1", "productName": "TEST_Item", "quantity": 1, "course": 1, "status": "pending"}],
            "priority": "normal"
        }
        create_res = requests.post(f"{BASE_URL}/api/kitchen/orders", json=order_data)
        assert create_res.status_code == 200
        order_id = create_res.json()['id']
        
        # Start the order
        response = requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/start")
        assert response.status_code == 200
        
        started = response.json()
        assert started['status'] == 'preparing'
        assert 'startedAt' in started
        print(f"Started order {order_id}")
        return order_id
        
    def test_kitchen_order_workflow_ready(self):
        """POST /api/kitchen/orders/{id}/ready - mark order ready"""
        # Create and start an order
        order_data = {
            "tableNumber": "T101",
            "orderType": "dine_in",
            "items": [{"productId": "p1", "productName": "TEST_Item", "quantity": 1, "course": 1, "status": "pending"}],
            "priority": "normal"
        }
        create_res = requests.post(f"{BASE_URL}/api/kitchen/orders", json=order_data)
        order_id = create_res.json()['id']
        requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/start")
        
        # Mark ready
        response = requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/ready")
        assert response.status_code == 200
        
        ready = response.json()
        assert ready['status'] == 'ready'
        assert 'readyAt' in ready
        print(f"Order {order_id} marked ready")
        return order_id
        
    def test_kitchen_order_workflow_served(self):
        """POST /api/kitchen/orders/{id}/served - mark order served"""
        # Create, start, and ready an order
        order_data = {
            "tableNumber": "T102",
            "orderType": "dine_in",
            "items": [{"productId": "p1", "productName": "TEST_Item", "quantity": 1, "course": 1, "status": "pending"}],
            "priority": "normal"
        }
        create_res = requests.post(f"{BASE_URL}/api/kitchen/orders", json=order_data)
        order_id = create_res.json()['id']
        requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/start")
        requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/ready")
        
        # Mark served
        response = requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/served")
        assert response.status_code == 200
        
        served = response.json()
        assert served['status'] == 'served'
        assert 'servedAt' in served
        print(f"Order {order_id} marked served")
        
    def test_kitchen_order_cancel(self):
        """POST /api/kitchen/orders/{id}/cancel - cancel order"""
        # Create an order
        order_data = {
            "tableNumber": "T103",
            "orderType": "dine_in",
            "items": [{"productId": "p1", "productName": "TEST_Cancel", "quantity": 1, "course": 1, "status": "pending"}],
            "priority": "normal"
        }
        create_res = requests.post(f"{BASE_URL}/api/kitchen/orders", json=order_data)
        order_id = create_res.json()['id']
        
        # Cancel
        response = requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/cancel")
        assert response.status_code == 200
        
        cancelled = response.json()
        assert cancelled['status'] == 'cancelled'
        print(f"Order {order_id} cancelled")
        
    def test_kitchen_order_priority_rush(self):
        """POST /api/kitchen/orders/{id}/priority - set rush priority"""
        # Create an order
        order_data = {
            "tableNumber": "T104",
            "orderType": "dine_in",
            "items": [{"productId": "p1", "productName": "TEST_Rush", "quantity": 1, "course": 1, "status": "pending"}],
            "priority": "normal"
        }
        create_res = requests.post(f"{BASE_URL}/api/kitchen/orders", json=order_data)
        order_id = create_res.json()['id']
        
        # Set rush priority
        response = requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/priority", params={"priority": "rush"})
        assert response.status_code == 200
        
        updated = response.json()
        assert updated['priority'] == 'rush'
        print(f"Order {order_id} set to rush priority")
        
    def test_kitchen_order_fire_course(self):
        """POST /api/kitchen/orders/{id}/fire-course - fire next course"""
        # Create and start an order
        order_data = {
            "tableNumber": "T105",
            "orderType": "dine_in",
            "items": [
                {"productId": "p1", "productName": "TEST_Course1", "quantity": 1, "course": 1, "status": "pending"},
                {"productId": "p2", "productName": "TEST_Course2", "quantity": 1, "course": 2, "status": "pending"}
            ],
            "priority": "normal"
        }
        create_res = requests.post(f"{BASE_URL}/api/kitchen/orders", json=order_data)
        order_id = create_res.json()['id']
        requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/start")
        
        # Fire course 2
        response = requests.post(f"{BASE_URL}/api/kitchen/orders/{order_id}/fire-course", params={"course": 2})
        assert response.status_code == 200
        
        updated = response.json()
        assert updated['currentCourse'] == 2
        print(f"Order {order_id} fired course 2")
        
    def test_kitchen_order_not_found(self):
        """POST /api/kitchen/orders/{id}/start - 404 for non-existent"""
        response = requests.post(f"{BASE_URL}/api/kitchen/orders/nonexistent-id/start")
        assert response.status_code == 404


class TestPhase1Regression:
    """Regression tests for Phase 1 features (Reservations, Floor Plan, Waitlist)"""
    
    def test_reservations_list(self):
        """GET /api/reservations - list reservations"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"Reservations: {len(response.json())} found")
        
    def test_floor_plans_list(self):
        """GET /api/floor-plans - list floor plans"""
        response = requests.get(f"{BASE_URL}/api/floor-plans")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"Floor plans: {len(response.json())} found")
        
    def test_waitlist_list(self):
        """GET /api/waitlist - list waitlist entries"""
        response = requests.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"Waitlist: {len(response.json())} entries")
        
    def test_api_root(self):
        """GET /api/ - API root info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'NUA POS API'
        assert 'features' in data
        print(f"API: {data['name']} v{data['version']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
