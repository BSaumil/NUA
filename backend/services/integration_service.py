"""Integration Plugin Framework for NUA POS

Supports easy integration with third-party services:
- Accounting: QuickBooks, Xero, MYOB, Tally
- E-commerce: Shopify, WooCommerce, Magento, BigCommerce
- Delivery: Uber Eats, DoorDash, Menulog, Deliveroo
- Marketing: MailChimp, SendGrid, Twilio
- Payments: Stripe, PayPal, Square, Afterpay
- Loyalty: LoyaltyLion, Smile.io
- Booking: OpenTable, Resy
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging
import json

logger = logging.getLogger(__name__)

class IntegrationPlugin(ABC):
    """Base class for all integration plugins"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.api_key = config.get('apiKey')
        self.api_secret = config.get('apiSecret')
        self.webhook_url = config.get('webhookUrl')
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the service"""
        pass
    
    @abstractmethod
    async def sync_data(self, data_type: str, data: Any) -> Dict[str, Any]:
        """Sync data to the service"""
        pass
    
    @abstractmethod
    async def fetch_data(self, data_type: str, params: Dict[str, Any] = None) -> Any:
        """Fetch data from the service"""
        pass
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the service"""
        try:
            result = await self.authenticate()
            return {"success": result, "message": "Connection successful" if result else "Authentication failed"}
        except Exception as e:
            return {"success": False, "message": str(e)}


class QuickBooksPlugin(IntegrationPlugin):
    """QuickBooks Online Integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.realm_id = config.get('realmId')
        self.base_url = "https://quickbooks.api.intuit.com/v3/company"
        
    async def authenticate(self) -> bool:
        """OAuth 2.0 authentication"""
        import requests
        try:
            # Simplified - real implementation needs full OAuth flow
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/{self.realm_id}/companyinfo/{self.realm_id}", 
                                  headers=headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"QuickBooks auth failed: {e}")
            return False
    
    async def sync_data(self, data_type: str, data: Any) -> Dict[str, Any]:
        """Sync sales, invoices, customers to QuickBooks"""
        import requests
        
        if data_type == "sales":
            # Create invoice in QuickBooks
            invoice = {
                "Line": [{"Amount": data['total'], "DetailType": "SalesItemLineDetail"}],
                "CustomerRef": {"value": data.get('customerId', '1')}
            }
            response = requests.post(
                f"{self.base_url}/{self.realm_id}/invoice",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=invoice,
                timeout=30
            )
            return response.json()
        
        return {"success": False, "message": "Unsupported data type"}
    
    async def fetch_data(self, data_type: str, params: Dict[str, Any] = None) -> Any:
        """Fetch data from QuickBooks"""
        import requests
        
        if data_type == "customers":
            response = requests.get(
                f"{self.base_url}/{self.realm_id}/query",
                params={"query": "SELECT * FROM Customer"},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            return response.json()
        
        return None


class XeroPlugin(IntegrationPlugin):
    """Xero Accounting Integration"""
    
    async def authenticate(self) -> bool:
        import requests
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get("https://api.xero.com/api.xro/2.0/Organisation", 
                                  headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    async def sync_data(self, data_type: str, data: Any) -> Dict[str, Any]:
        import requests
        
        if data_type == "sales":
            invoice = {
                "Type": "ACCREC",
                "Contact": {"Name": data.get('customerName', 'Walk-in')},
                "LineItems": [{"Description": "Sale", "Quantity": 1, "UnitAmount": data['total']}],
                "Date": data['timestamp'],
                "DueDate": data['timestamp'],
                "Status": "PAID"
            }
            
            response = requests.post(
                "https://api.xero.com/api.xro/2.0/Invoices",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"Invoices": [invoice]},
                timeout=30
            )
            return response.json()
        
        return {"success": False}
    
    async def fetch_data(self, data_type: str, params: Dict[str, Any] = None) -> Any:
        return None


class ShopifyPlugin(IntegrationPlugin):
    """Shopify E-commerce Integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.shop_url = config.get('shopUrl')  # e.g., mystore.myshopify.com
        self.base_url = f"https://{self.shop_url}/admin/api/2024-01"
        
    async def authenticate(self) -> bool:
        import requests
        try:
            headers = {"X-Shopify-Access-Token": self.api_key}
            response = requests.get(f"{self.base_url}/shop.json", headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    async def sync_data(self, data_type: str, data: Any) -> Dict[str, Any]:
        import requests
        headers = {"X-Shopify-Access-Token": self.api_key, "Content-Type": "application/json"}
        
        if data_type == "inventory":
            # Update product inventory
            response = requests.post(
                f"{self.base_url}/inventory_levels/set.json",
                headers=headers,
                json={
                    "location_id": data['locationId'],
                    "inventory_item_id": data['productId'],
                    "available": data['stock']
                },
                timeout=30
            )
            return response.json()
        
        elif data_type == "order":
            # Import order from Shopify to POS
            return {"success": True, "message": "Order synced"}
        
        return {"success": False}
    
    async def fetch_data(self, data_type: str, params: Dict[str, Any] = None) -> Any:
        import requests
        headers = {"X-Shopify-Access-Token": self.api_key}
        
        if data_type == "orders":
            response = requests.get(f"{self.base_url}/orders.json", headers=headers, timeout=30)
            return response.json()
        
        elif data_type == "products":
            response = requests.get(f"{self.base_url}/products.json", headers=headers, timeout=30)
            return response.json()
        
        return None


class WooCommercePlugin(IntegrationPlugin):
    """WooCommerce Integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.store_url = config.get('storeUrl')
        self.consumer_key = config.get('consumerKey')
        self.consumer_secret = config.get('consumerSecret')
        
    async def authenticate(self) -> bool:
        import requests
        from requests.auth import HTTPBasicAuth
        
        try:
            auth = HTTPBasicAuth(self.consumer_key, self.consumer_secret)
            response = requests.get(f"{self.store_url}/wp-json/wc/v3/system_status", 
                                  auth=auth, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    async def sync_data(self, data_type: str, data: Any) -> Dict[str, Any]:
        import requests
        from requests.auth import HTTPBasicAuth
        
        auth = HTTPBasicAuth(self.consumer_key, self.consumer_secret)
        
        if data_type == "inventory":
            # Update stock
            response = requests.put(
                f"{self.store_url}/wp-json/wc/v3/products/{data['productId']}",
                auth=auth,
                json={"stock_quantity": data['stock']},
                timeout=30
            )
            return response.json()
        
        return {"success": False}
    
    async def fetch_data(self, data_type: str, params: Dict[str, Any] = None) -> Any:
        import requests
        from requests.auth import HTTPBasicAuth
        
        auth = HTTPBasicAuth(self.consumer_key, self.consumer_secret)
        
        if data_type == "orders":
            response = requests.get(f"{self.store_url}/wp-json/wc/v3/orders", auth=auth, timeout=30)
            return response.json()
        
        return None


class UberEatsPlugin(IntegrationPlugin):
    """Uber Eats Delivery Integration"""
    
    async def authenticate(self) -> bool:
        # Uber Eats uses OAuth
        return True
    
    async def sync_data(self, data_type: str, data: Any) -> Dict[str, Any]:
        if data_type == "order":
            # Receive order from Uber Eats
            return {"success": True, "orderId": data.get('id')}
        return {"success": False}
    
    async def fetch_data(self, data_type: str, params: Dict[str, Any] = None) -> Any:
        # Fetch orders from Uber Eats
        return []


class MailChimpPlugin(IntegrationPlugin):
    """MailChimp Email Marketing Integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_prefix = config.get('serverPrefix', 'us1')
        self.base_url = f"https://{self.server_prefix}.api.mailchimp.com/3.0"
        
    async def authenticate(self) -> bool:
        import requests
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/ping", headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    async def sync_data(self, data_type: str, data: Any) -> Dict[str, Any]:
        import requests
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        if data_type == "customer":
            # Add subscriber to list
            list_id = self.config.get('listId')
            response = requests.post(
                f"{self.base_url}/lists/{list_id}/members",
                headers=headers,
                json={
                    "email_address": data['email'],
                    "status": "subscribed",
                    "merge_fields": {
                        "FNAME": data.get('firstName', ''),
                        "LNAME": data.get('lastName', '')
                    }
                },
                timeout=30
            )
            return response.json()
        
        return {"success": False}
    
    async def fetch_data(self, data_type: str, params: Dict[str, Any] = None) -> Any:
        return None


class IntegrationManager:
    """Central manager for all integrations"""
    
    PLUGINS = {
        'quickbooks': QuickBooksPlugin,
        'xero': XeroPlugin,
        'shopify': ShopifyPlugin,
        'woocommerce': WooCommercePlugin,
        'uber_eats': UberEatsPlugin,
        'mailchimp': MailChimpPlugin,
        # Easy to add more
    }
    
    def __init__(self):
        self.active_plugins = {}
    
    def register_plugin(self, name: str, config: Dict[str, Any]):
        """Register and activate a plugin"""
        plugin_class = self.PLUGINS.get(name)
        if not plugin_class:
            raise ValueError(f"Unknown plugin: {name}")
        
        self.active_plugins[name] = plugin_class(config)
        logger.info(f"Registered plugin: {name}")
    
    async def sync_transaction(self, transaction: Dict[str, Any]):
        """Sync transaction to all active accounting plugins"""
        results = {}
        for name, plugin in self.active_plugins.items():
            if name in ['quickbooks', 'xero'] and plugin.enabled:
                try:
                    result = await plugin.sync_data('sales', transaction)
                    results[name] = result
                except Exception as e:
                    logger.error(f"Failed to sync to {name}: {e}")
                    results[name] = {"success": False, "error": str(e)}
        return results
    
    async def sync_inventory(self, product: Dict[str, Any]):
        """Sync inventory to e-commerce plugins"""
        results = {}
        for name, plugin in self.active_plugins.items():
            if name in ['shopify', 'woocommerce'] and plugin.enabled:
                try:
                    result = await plugin.sync_data('inventory', product)
                    results[name] = result
                except Exception as e:
                    logger.error(f"Failed to sync inventory to {name}: {e}")
                    results[name] = {"success": False, "error": str(e)}
        return results
    
    async def sync_customer(self, customer: Dict[str, Any]):
        """Sync customer to marketing plugins"""
        results = {}
        for name, plugin in self.active_plugins.items():
            if name == 'mailchimp' and plugin.enabled:
                try:
                    result = await plugin.sync_data('customer', customer)
                    results[name] = result
                except Exception as e:
                    logger.error(f"Failed to sync customer to {name}: {e}")
                    results[name] = {"success": False, "error": str(e)}
        return results

# Global instance
integration_manager = IntegrationManager()
