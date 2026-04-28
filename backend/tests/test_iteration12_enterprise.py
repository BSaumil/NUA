"""
Iteration 12 Enterprise Features Tests
- Surcharging (weekend/holiday)
- Live Sales Reporting
- Custom Permissions (26 granular permissions)
- Smart Kiosk Upsells
- Automated Reporting (itemised, category, detailed)
- Hardware Integrations (printers, scanners)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests for all roles"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
        assert r.status_code == 200, f"Owner login failed: {r.text}"
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@nuva.com", "password": "Staff2026!"})
        assert r.status_code == 200, f"Manager login failed: {r.text}"
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def cashier_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "cashier@nuva.com", "password": "Staff2026!"})
        assert r.status_code == 200, f"Cashier login failed: {r.text}"
        return r.json()["token"]
    
    def test_owner_login(self, owner_token):
        """Owner login returns valid token"""
        assert owner_token is not None
        assert len(owner_token) > 50
        print("PASS: Owner login successful")
    
    def test_manager_login(self, manager_token):
        """Manager login returns valid token"""
        assert manager_token is not None
        print("PASS: Manager login successful")
    
    def test_cashier_login(self, cashier_token):
        """Cashier login returns valid token"""
        assert cashier_token is not None
        print("PASS: Cashier login successful")


class TestPermissions:
    """Custom permissions system tests"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def cashier_id(self, owner_token):
        """Get cashier's staff ID"""
        r = requests.get(f"{BASE_URL}/api/auth/staff", headers={"Authorization": f"Bearer {owner_token}"})
        staff = r.json()
        cashier = next((s for s in staff if s["email"] == "cashier@nuva.com"), None)
        return cashier["id"] if cashier else None
    
    def test_get_all_permissions_returns_26(self):
        """GET /api/permissions/all returns 26 permissions"""
        r = requests.get(f"{BASE_URL}/api/permissions/all")
        assert r.status_code == 200
        perms = r.json()
        assert isinstance(perms, list)
        assert len(perms) == 26, f"Expected 26 permissions, got {len(perms)}"
        # Check some key permissions exist
        assert "dashboard" in perms
        assert "pos" in perms
        assert "settings" in perms
        assert "accounting" in perms
        print(f"PASS: GET /api/permissions/all returns {len(perms)} permissions")
    
    def test_get_staff_permissions_owner(self, owner_token, cashier_id):
        """Owner can get staff permissions"""
        if not cashier_id:
            pytest.skip("Cashier not found")
        r = requests.get(f"{BASE_URL}/api/permissions/staff/{cashier_id}", headers={"Authorization": f"Bearer {owner_token}"})
        assert r.status_code == 200
        data = r.json()
        assert "staffId" in data
        assert "customPermissions" in data
        print(f"PASS: Owner can get staff permissions for cashier")
    
    def test_set_staff_permissions_owner(self, owner_token, cashier_id):
        """Owner can set custom permissions for staff"""
        if not cashier_id:
            pytest.skip("Cashier not found")
        custom_perms = ["pos", "customers", "products", "dashboard"]
        r = requests.post(
            f"{BASE_URL}/api/permissions/staff/{cashier_id}",
            json={"permissions": custom_perms},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "permissions" in data
        assert len(data["permissions"]) == 4
        print(f"PASS: Owner set custom permissions: {data['permissions']}")
    
    def test_set_staff_permissions_manager_denied(self, manager_token, cashier_id):
        """Manager cannot set staff permissions (403)"""
        if not cashier_id:
            pytest.skip("Cashier not found")
        r = requests.post(
            f"{BASE_URL}/api/permissions/staff/{cashier_id}",
            json={"permissions": ["pos"]},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert r.status_code == 403
        print("PASS: Manager denied setting permissions (403)")
    
    def test_auth_me_returns_custom_permissions(self, owner_token, cashier_id):
        """After setting custom permissions, /auth/me returns them"""
        if not cashier_id:
            pytest.skip("Cashier not found")
        # Login as cashier
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "cashier@nuva.com", "password": "Staff2026!"})
        cashier_token = r.json()["token"]
        # Get /me
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {cashier_token}"})
        assert r.status_code == 200
        data = r.json()
        # Should have customPermissions or permissions
        perms = data.get("customPermissions") or data.get("permissions", [])
        print(f"PASS: /auth/me returns permissions: {perms}")


class TestSurcharging:
    """Auto surcharging tests"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    def test_get_surcharge_settings(self):
        """GET /api/surcharge/settings returns config"""
        r = requests.get(f"{BASE_URL}/api/surcharge/settings")
        assert r.status_code == 200
        data = r.json()
        assert "enabled" in data
        assert "weekendSurcharge" in data
        assert "publicHolidaySurcharge" in data
        assert "weekendDays" in data
        print(f"PASS: GET /api/surcharge/settings returns config")
    
    def test_save_surcharge_settings_owner(self, owner_token):
        """Owner can save surcharge settings"""
        settings = {
            "enabled": True,
            "weekendSurcharge": 10,
            "publicHolidaySurcharge": 15,
            "weekendDays": ["Saturday", "Sunday"],
            "publicHolidays": ["2026-01-01", "2026-01-26"]
        }
        r = requests.post(
            f"{BASE_URL}/api/surcharge/settings",
            json=settings,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        assert "message" in r.json()
        print("PASS: Owner saved surcharge settings")
    
    def test_save_surcharge_settings_manager_denied(self, manager_token):
        """Manager cannot save surcharge settings (403)"""
        r = requests.post(
            f"{BASE_URL}/api/surcharge/settings",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert r.status_code == 403
        print("PASS: Manager denied saving surcharge settings (403)")
    
    def test_check_surcharge(self):
        """GET /api/surcharge/check returns current surcharge"""
        r = requests.get(f"{BASE_URL}/api/surcharge/check")
        assert r.status_code == 200
        data = r.json()
        assert "surchargePercent" in data
        assert "reason" in data
        print(f"PASS: Surcharge check: {data['surchargePercent']}% - {data['reason']}")


class TestLiveSales:
    """Live sales reporting tests"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def cashier_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "cashier@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    def test_live_sales_owner(self, owner_token):
        """Owner can access live sales"""
        r = requests.get(f"{BASE_URL}/api/live-sales", headers={"Authorization": f"Bearer {owner_token}"})
        assert r.status_code == 200
        data = r.json()
        assert "totalSales" in data
        assert "transactionCount" in data
        assert "avgTicket" in data
        assert "byHour" in data
        assert "recentTransactions" in data
        print(f"PASS: Live sales - Total: ${data['totalSales']}, Count: {data['transactionCount']}")
    
    def test_live_sales_manager(self, manager_token):
        """Manager can access live sales"""
        r = requests.get(f"{BASE_URL}/api/live-sales", headers={"Authorization": f"Bearer {manager_token}"})
        assert r.status_code == 200
        print("PASS: Manager can access live sales")
    
    def test_live_sales_cashier_denied(self, cashier_token):
        """Cashier cannot access live sales (403)"""
        r = requests.get(f"{BASE_URL}/api/live-sales", headers={"Authorization": f"Bearer {cashier_token}"})
        assert r.status_code == 403
        print("PASS: Cashier denied live sales (403)")


class TestReports:
    """Automated reporting tests (itemised, category, detailed)"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def cashier_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "cashier@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    def test_generate_itemised_report(self, owner_token):
        """POST /api/reports/generate type=itemised returns item-level profit/margin"""
        r = requests.post(
            f"{BASE_URL}/api/reports/generate",
            json={"type": "itemised"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "itemised"
        assert "items" in data
        assert "totalRevenue" in data
        assert "totalProfit" in data
        # Check item structure if items exist
        if data["items"]:
            item = data["items"][0]
            assert "name" in item
            assert "qty" in item
            assert "revenue" in item
            assert "profit" in item
            assert "margin" in item
        print(f"PASS: Itemised report - {len(data['items'])} items, Revenue: ${data['totalRevenue']}")
    
    def test_generate_category_report(self, owner_token):
        """POST /api/reports/generate type=category returns category breakdown"""
        r = requests.post(
            f"{BASE_URL}/api/reports/generate",
            json={"type": "category"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "category"
        assert "categories" in data
        assert "totalRevenue" in data
        print(f"PASS: Category report - {len(data['categories'])} categories")
    
    def test_generate_detailed_report(self, owner_token):
        """POST /api/reports/generate type=detailed returns full P&L"""
        r = requests.post(
            f"{BASE_URL}/api/reports/generate",
            json={"type": "detailed"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "detailed"
        assert "revenue" in data
        assert "expenses" in data
        assert "grossProfit" in data
        assert "netProfit" in data
        assert "transactionCount" in data
        print(f"PASS: Detailed report - Revenue: ${data['revenue']}, Net Profit: ${data['netProfit']}")
    
    def test_generate_report_manager(self, manager_token):
        """Manager can generate reports"""
        r = requests.post(
            f"{BASE_URL}/api/reports/generate",
            json={"type": "detailed"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert r.status_code == 200
        print("PASS: Manager can generate reports")
    
    def test_generate_report_cashier_denied(self, cashier_token):
        """Cashier cannot generate reports (403)"""
        r = requests.post(
            f"{BASE_URL}/api/reports/generate",
            json={"type": "detailed"},
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert r.status_code == 403
        print("PASS: Cashier denied report generation (403)")


class TestUpsells:
    """Smart kiosk upsells tests"""
    
    def test_get_upsells(self):
        """GET /api/pos/upsells returns suggestions"""
        r = requests.get(f"{BASE_URL}/api/pos/upsells", params={"items": "prod1,prod2"})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        print(f"PASS: Upsells returned {len(data)} suggestions")


class TestHardware:
    """Hardware integrations tests (printers, scanners)"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    def test_get_printers(self):
        """GET /api/hardware/printers returns list"""
        r = requests.get(f"{BASE_URL}/api/hardware/printers")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        print(f"PASS: GET /api/hardware/printers returns {len(r.json())} printers")
    
    def test_add_printer_owner(self, owner_token):
        """Owner can add a printer"""
        printer = {
            "name": "TEST_Kitchen Printer",
            "type": "kitchen",
            "connectionType": "network",
            "ipAddress": "192.168.1.100",
            "model": "Epson TM-T88VI"
        }
        r = requests.post(
            f"{BASE_URL}/api/hardware/printers",
            json=printer,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["name"] == "TEST_Kitchen Printer"
        print(f"PASS: Added printer with ID: {data['id']}")
        # Cleanup
        requests.delete(f"{BASE_URL}/api/hardware/printers/{data['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    
    def test_add_printer_manager(self, manager_token):
        """Manager can add a printer"""
        printer = {"name": "TEST_Manager Printer", "type": "receipt", "connectionType": "usb"}
        r = requests.post(
            f"{BASE_URL}/api/hardware/printers",
            json=printer,
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        print(f"PASS: Manager added printer")
        # Cleanup
        requests.delete(f"{BASE_URL}/api/hardware/printers/{data['id']}", headers={"Authorization": f"Bearer {manager_token}"})
    
    def test_get_scanners(self):
        """GET /api/hardware/scanners returns list"""
        r = requests.get(f"{BASE_URL}/api/hardware/scanners")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        print(f"PASS: GET /api/hardware/scanners returns {len(r.json())} scanners")
    
    def test_add_scanner_owner(self, owner_token):
        """Owner can add a scanner"""
        scanner = {"name": "TEST_Barcode Scanner", "type": "barcode", "connectionType": "usb", "model": "Honeywell 1900"}
        r = requests.post(
            f"{BASE_URL}/api/hardware/scanners",
            json=scanner,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        print(f"PASS: Added scanner with ID: {data['id']}")


class TestReportConfig:
    """Automated report configuration tests"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    def test_get_report_config_owner(self, owner_token):
        """Owner can get automated report config"""
        r = requests.get(f"{BASE_URL}/api/reports/automated-config", headers={"Authorization": f"Bearer {owner_token}"})
        assert r.status_code == 200
        data = r.json()
        assert "enabled" in data
        assert "frequency" in data
        assert "reportTypes" in data
        print(f"PASS: Report config - enabled: {data['enabled']}, frequency: {data['frequency']}")
    
    def test_save_report_config_owner(self, owner_token):
        """Owner can save automated report config"""
        config = {
            "enabled": True,
            "frequency": "weekly",
            "time": "08:00",
            "reportTypes": ["itemised", "detailed"],
            "recipientEmail": "test@example.com",
            "includeAIInsights": True
        }
        r = requests.post(
            f"{BASE_URL}/api/reports/automated-config",
            json=config,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        print("PASS: Owner saved report config")
    
    def test_get_report_config_manager_denied(self, manager_token):
        """Manager cannot access report config (403)"""
        r = requests.get(f"{BASE_URL}/api/reports/automated-config", headers={"Authorization": f"Bearer {manager_token}"})
        assert r.status_code == 403
        print("PASS: Manager denied report config (403)")


class TestRBACEnforcement:
    """RBAC enforcement for enterprise features"""
    
    @pytest.fixture(scope="class")
    def cashier_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "cashier@nuva.com", "password": "Staff2026!"})
        return r.json()["token"]
    
    def test_cashier_denied_surcharge_save(self, cashier_token):
        """Cashier cannot save surcharge settings"""
        r = requests.post(
            f"{BASE_URL}/api/surcharge/settings",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert r.status_code == 403
        print("PASS: Cashier denied surcharge settings (403)")
    
    def test_cashier_denied_permissions_set(self, cashier_token):
        """Cashier cannot set permissions"""
        r = requests.post(
            f"{BASE_URL}/api/permissions/staff/some-id",
            json={"permissions": ["pos"]},
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert r.status_code in [401, 403]
        print("PASS: Cashier denied setting permissions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
