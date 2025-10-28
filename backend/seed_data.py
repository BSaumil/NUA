import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def seed_database():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Clear existing data
    print("Clearing existing data...")
    await db.products.delete_many({})
    await db.promotions.delete_many({})
    await db.customers.delete_many({})
    await db.transactions.delete_many({})
    await db.bas_reports.delete_many({})
    await db.locations.delete_many({})
    await db.users.delete_many({})
    await db.categories.delete_many({})
    await db.modifiers.delete_many({})
    await db.printers.delete_many({})
    
    # Seed Products
    print("Seeding products...")
    products = [
        {
            "id": "1",
            "name": "Espresso",
            "category": "Beverages",
            "price": 4.50,
            "cost": 1.20,
            "stock": 150,
            "sku": "BEV-ESP-001",
            "image": "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=200",
            "gstRate": 10,
            "modifiers": [
                {
                    "id": "mod-size",
                    "name": "Size",
                    "type": "single",
                    "required": True,
                    "options": [
                        {"id": "size-small", "name": "Small", "price": 0.0},
                        {"id": "size-medium", "name": "Medium", "price": 1.0},
                        {"id": "size-large", "name": "Large", "price": 2.0}
                    ]
                },
                {
                    "id": "mod-extras",
                    "name": "Extras",
                    "type": "multiple",
                    "required": False,
                    "options": [
                        {"id": "extra-shot", "name": "Extra Shot", "price": 1.5},
                        {"id": "extra-milk", "name": "Extra Milk", "price": 0.5}
                    ]
                }
            ],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "id": "2",
            "name": "Cappuccino",
            "category": "Beverages",
            "price": 5.00,
            "cost": 1.50,
            "stock": 200,
            "sku": "BEV-CAP-001",
            "image": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=200",
            "gstRate": 10,
            "modifiers": [
                {
                    "id": "mod-size",
                    "name": "Size",
                    "type": "single",
                    "required": True,
                    "options": [
                        {"id": "size-small", "name": "Small", "price": 0.0},
                        {"id": "size-medium", "name": "Medium", "price": 1.0},
                        {"id": "size-large", "name": "Large", "price": 2.0}
                    ]
                }
            ],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "id": "3",
            "name": "Chocolate Cake",
            "category": "Bakery",
            "price": 6.50,
            "cost": 2.00,
            "stock": 50,
            "sku": "BAK-CHO-001",
            "image": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=200",
            "gstRate": 10,
            "modifiers": [],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "id": "4",
            "name": "Beef Burger",
            "category": "Food",
            "price": 12.00,
            "cost": 4.50,
            "stock": 80,
            "sku": "FOD-BUR-001",
            "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=200",
            "gstRate": 10,
            "modifiers": [
                {
                    "id": "mod-cooking",
                    "name": "Cooking Level",
                    "type": "single",
                    "required": True,
                    "options": [
                        {"id": "rare", "name": "Rare", "price": 0.0},
                        {"id": "medium", "name": "Medium", "price": 0.0},
                        {"id": "well-done", "name": "Well Done", "price": 0.0}
                    ]
                },
                {
                    "id": "mod-add-ons",
                    "name": "Add-ons",
                    "type": "multiple",
                    "required": False,
                    "options": [
                        {"id": "extra-cheese", "name": "Extra Cheese", "price": 2.0},
                        {"id": "bacon", "name": "Bacon", "price": 3.0},
                        {"id": "avocado", "name": "Avocado", "price": 2.5}
                    ]
                },
                {
                    "id": "mod-remove",
                    "name": "Remove",
                    "type": "multiple",
                    "required": False,
                    "options": [
                        {"id": "no-onions", "name": "No Onions", "price": 0.0},
                        {"id": "no-pickles", "name": "No Pickles", "price": 0.0},
                        {"id": "no-tomato", "name": "No Tomato", "price": 0.0}
                    ]
                }
            ],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "id": "5",
            "name": "Soft Drink",
            "category": "Beverages",
            "price": 3.50,
            "cost": 0.80,
            "stock": 300,
            "sku": "BEV-SOD-001",
            "image": "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=200",
            "gstRate": 10,
            "modifiers": [],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "id": "6",
            "name": "Caesar Salad",
            "category": "Food",
            "price": 10.00,
            "cost": 3.50,
            "stock": 60,
            "sku": "FOD-SAL-001",
            "image": "https://images.unsplash.com/photo-1546793665-c74683f339c1?w=200",
            "gstRate": 10,
            "modifiers": [],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
    ]
    await db.products.insert_many(products)
    
    # Seed Promotions
    print("Seeding promotions...")
    promotions = [
        {
            "id": "promo-1",
            "name": "Coffee & Cake Deal",
            "type": "bundle",
            "products": ["1", "3"],
            "originalPrice": 11.00,
            "discountedPrice": 9.00,
            "discount": 18,
            "active": True,
            "schedule": "All Day",
            "createdAt": datetime.utcnow()
        },
        {
            "id": "promo-2",
            "name": "Burger & Drink Combo",
            "type": "bundle",
            "products": ["4", "5"],
            "originalPrice": 15.50,
            "discountedPrice": 13.00,
            "discount": 16,
            "active": True,
            "schedule": "All Day",
            "createdAt": datetime.utcnow()
        },
        {
            "id": "promo-3",
            "name": "Happy Hour - 20% Off Beverages",
            "type": "category",
            "category": "Beverages",
            "discount": 20,
            "active": True,
            "schedule": "3:00 PM - 6:00 PM",
            "createdAt": datetime.utcnow()
        }
    ]
    await db.promotions.insert_many(promotions)
    
    # Seed Customers
    print("Seeding customers...")
    customers = [
        {
            "id": "cust-1",
            "name": "Sarah Johnson",
            "email": "sarah.j@email.com",
            "phone": "+61 412 345 678",
            "membershipTier": "Gold",
            "totalSpent": 2450.00,
            "visits": 87,
            "joinDate": datetime(2023, 6, 15),
            "points": 2450
        },
        {
            "id": "cust-2",
            "name": "Michael Chen",
            "email": "mchen@email.com",
            "phone": "+61 423 456 789",
            "membershipTier": "Platinum",
            "totalSpent": 5680.00,
            "visits": 156,
            "joinDate": datetime(2023, 1, 20),
            "points": 5680
        },
        {
            "id": "cust-3",
            "name": "Emma Wilson",
            "email": "emma.w@email.com",
            "phone": "+61 434 567 890",
            "membershipTier": "Silver",
            "totalSpent": 890.00,
            "visits": 34,
            "joinDate": datetime(2024, 3, 10),
            "points": 890
        },
        {
            "id": "cust-4",
            "name": "James Brown",
            "email": "jbrown@email.com",
            "phone": "+61 445 678 901",
            "membershipTier": "Bronze",
            "totalSpent": 245.00,
            "visits": 12,
            "joinDate": datetime(2024, 10, 5),
            "points": 245
        }
    ]
    await db.customers.insert_many(customers)
    
    # Seed Transactions
    print("Seeding transactions...")
    transactions = [
        {
            "id": "TXN-20250115-001",
            "timestamp": datetime(2025, 1, 15, 9, 15, 32),
            "items": [
                {"productId": "1", "productName": "Espresso", "quantity": 2, "price": 4.50},
                {"productId": "3", "productName": "Chocolate Cake", "quantity": 1, "price": 6.50}
            ],
            "subtotal": 15.50,
            "gst": 1.55,
            "total": 17.05,
            "paymentMethod": "Card",
            "customerId": "cust-1",
            "customerName": "Sarah Johnson",
            "location": "Main Street",
            "cashier": "John Doe",
            "status": "completed"
        },
        {
            "id": "TXN-20250115-002",
            "timestamp": datetime(2025, 1, 15, 9, 23, 18),
            "items": [
                {"productId": "4", "productName": "Beef Burger", "quantity": 1, "price": 12.00},
                {"productId": "5", "productName": "Soft Drink", "quantity": 1, "price": 3.50}
            ],
            "subtotal": 15.50,
            "gst": 1.55,
            "total": 17.05,
            "paymentMethod": "Cash",
            "customerId": None,
            "customerName": None,
            "location": "Main Street",
            "cashier": "John Doe",
            "status": "completed"
        },
        {
            "id": "TXN-20250115-003",
            "timestamp": datetime(2025, 1, 15, 9, 45, 7),
            "items": [
                {"productId": "2", "productName": "Cappuccino", "quantity": 3, "price": 5.00}
            ],
            "subtotal": 15.00,
            "gst": 1.50,
            "total": 16.50,
            "paymentMethod": "Digital Wallet",
            "customerId": "cust-2",
            "customerName": "Michael Chen",
            "location": "Mall Branch",
            "cashier": "Jane Smith",
            "status": "completed"
        }
    ]
    await db.transactions.insert_many(transactions)
    
    # Seed Locations
    print("Seeding locations...")
    locations = [
        {
            "id": "loc-1",
            "name": "Main Street",
            "address": "123 Main St, Sydney NSW 2000",
            "phone": "+61 2 9876 5432",
            "status": "active"
        },
        {
            "id": "loc-2",
            "name": "Mall Branch",
            "address": "456 Shopping Mall, Sydney NSW 2001",
            "phone": "+61 2 9876 5433",
            "status": "active"
        }
    ]
    await db.locations.insert_many(locations)
    
    # Seed Users
    print("Seeding users...")
    users = [
        {
            "id": "user-1",
            "name": "John Doe",
            "email": "john@company.com",
            "role": "Admin",
            "locations": ["loc-1", "loc-2"],
            "status": "active"
        },
        {
            "id": "user-2",
            "name": "Jane Smith",
            "email": "jane@company.com",
            "role": "Cashier",
            "locations": ["loc-2"],
            "status": "active"
        },
        {
            "id": "user-3",
            "name": "Robert Wilson",
            "email": "robert@company.com",
            "role": "Accountant",
            "locations": ["loc-1", "loc-2"],
            "status": "active"
        }
    ]
    await db.users.insert_many(users)
    
    # Seed BAS Reports
    print("Seeding BAS reports...")
    bas_reports = [
        {
            "id": "bas-q4-2024",
            "quarter": "Q4 2024",
            "period": "Oct - Dec 2024",
            "totalSales": 145680.00,
            "gstCollected": 14568.00,
            "gstPaid": 3240.00,
            "netGst": 11328.00,
            "status": "submitted",
            "submittedDate": datetime(2025, 1, 28),
            "dueDate": datetime(2025, 2, 28),
            "transactionIds": [],
            "createdAt": datetime.utcnow()
        },
        {
            "id": "bas-q1-2025",
            "quarter": "Q1 2025",
            "period": "Jan - Mar 2025",
            "totalSales": 48920.00,
            "gstCollected": 4892.00,
            "gstPaid": 1120.00,
            "netGst": 3772.00,
            "status": "draft",
            "submittedDate": None,
            "dueDate": datetime(2025, 4, 28),
            "transactionIds": [],
            "createdAt": datetime.utcnow()
        }
    ]
    await db.bas_reports.insert_many(bas_reports)
    
    # Seed Categories
    print("Seeding categories...")
    categories = [
        {
            "id": "cat-1",
            "name": "Beverages",
            "description": "Hot and cold drinks",
            "color": "#3b82f6",
            "icon": "coffee",
            "sortOrder": 1,
            "active": True,
            "createdAt": datetime.utcnow()
        },
        {
            "id": "cat-2",
            "name": "Food",
            "description": "Main meals and snacks",
            "color": "#10b981",
            "icon": "utensils",
            "sortOrder": 2,
            "active": True,
            "createdAt": datetime.utcnow()
        },
        {
            "id": "cat-3",
            "name": "Bakery",
            "description": "Fresh baked goods",
            "color": "#f59e0b",
            "icon": "cake",
            "sortOrder": 3,
            "active": True,
            "createdAt": datetime.utcnow()
        }
    ]
    await db.categories.insert_many(categories)
    
    # Seed Printer Configurations
    print("Seeding printer configurations...")
    printers = [
        {
            "id": "printer-1",
            "name": "Main Counter Printer",
            "type": "network",
            "ipAddress": "192.168.1.100",
            "port": 9100,
            "paperWidth": 80,
            "autoprint": True,
            "location": "Main Street",
            "status": "active"
        },
        {
            "id": "printer-2",
            "name": "Mall Branch Printer",
            "type": "network",
            "ipAddress": "192.168.1.101",
            "port": 9100,
            "paperWidth": 80,
            "autoprint": False,
            "location": "Mall Branch",
            "status": "active"
        }
    ]
    await db.printers.insert_many(printers)
    
    print("✅ Database seeded successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
