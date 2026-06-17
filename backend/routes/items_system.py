from fastapi import APIRouter, HTTPException, Request
from database import db
from datetime import datetime, timezone
import uuid

router = APIRouter()

# ============ CATEGORIES ============
@router.get("/categories")
async def get_categories():
    cats = await db.categories.find({}, {"_id": 0}).to_list(200)
    if not cats:
        defaults = [
            {"id": "cat-beverages", "name": "Beverages", "sortOrder": 0, "active": True, "icon": "Coffee", "color": "#8b5cf6"},
            {"id": "cat-food", "name": "Food", "sortOrder": 1, "active": True, "icon": "UtensilsCrossed", "color": "#f97316"},
            {"id": "cat-bakery", "name": "Bakery", "sortOrder": 2, "active": True, "icon": "Croissant", "color": "#ec4899"},
            {"id": "cat-alcohol", "name": "Alcohol", "sortOrder": 3, "active": True, "icon": "Wine", "color": "#ef4444"},
            {"id": "cat-desserts", "name": "Desserts", "sortOrder": 4, "active": True, "icon": "Cake", "color": "#f59e0b"},
        ]
        for d in defaults:
            await db.categories.insert_one(d)
        return defaults
    return cats

@router.post("/categories")
async def create_category(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    cat = {
        "id": f"cat-{str(uuid.uuid4())[:8]}",
        "name": data.get("name", ""), "sortOrder": data.get("sortOrder", 99),
        "active": data.get("active", True),
        "icon": data.get("icon", "Tag"),          # lucide-react icon name
        "color": data.get("color", "#6366f1"),    # tile accent
        # Online-ordering: how long this category takes to prep (mins) and which
        # channels it's available on.
        "prepTime": int(data.get("prepTime", 8)),
        "channels": data.get("channels", ["dine-in", "pickup", "delivery"]),
    }
    await db.categories.insert_one(cat)
    cat.pop("_id", None)
    return cat

@router.put("/categories/{cat_id}")
async def update_category(cat_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    allowed = {"name", "sortOrder", "active", "icon", "color", "prepTime", "channels"}
    update = {k: v for k, v in data.items() if k in allowed}
    if "prepTime" in update: update["prepTime"] = int(update["prepTime"] or 0)
    result = await db.categories.find_one_and_update({"id": cat_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result


@router.post("/categories/cleanup-legacy")
async def cleanup_legacy_categories(request: Request):
    """Owner one-click: removes ANY category that has zero products attached
    AND is not in the canonical seed-catalog set (Coffee/Burgers/Mains/
    Cakes & Slices/Pasta). Safe — products are unaffected."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner only")
    canonical = {c["name"] for c in SEED_CATEGORIES}
    all_cats = await db.categories.find({}, {"_id": 0}).to_list(200)
    removed, kept = [], []
    for cat in all_cats:
        if cat["name"] in canonical:
            continue
        product_count = await db.products.count_documents({"category": cat["name"]})
        if product_count == 0:
            await db.categories.delete_one({"id": cat["id"]})
            removed.append(cat["name"])
        else:
            kept.append({"name": cat["name"], "productCount": product_count})
    return {"removed": removed, "keptWithProducts": kept}

@router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    await db.categories.delete_one({"id": cat_id})
    return {"message": "Category deleted"}


# ============ SEED CATALOG (60 products + 10 modifiers) ============
SEED_CATEGORIES = [
    {"id": "cat-coffee", "name": "Coffee", "sortOrder": 0, "active": True, "icon": "Coffee", "color": "#92400e", "prepTime": 4, "channels": ["dine-in", "pickup", "delivery"]},
    {"id": "cat-burgers", "name": "Burgers", "sortOrder": 1, "active": True, "icon": "Beef", "color": "#dc2626", "prepTime": 12, "channels": ["dine-in", "pickup", "delivery"]},
    {"id": "cat-mains", "name": "Mains", "sortOrder": 2, "active": True, "icon": "UtensilsCrossed", "color": "#16a34a", "prepTime": 18, "channels": ["dine-in", "pickup"]},
    {"id": "cat-cakes", "name": "Cakes & Slices", "sortOrder": 3, "active": True, "icon": "Cake", "color": "#db2777", "prepTime": 2, "channels": ["dine-in", "pickup", "delivery"]},
    {"id": "cat-pasta", "name": "Pasta", "sortOrder": 4, "active": True, "icon": "Soup", "color": "#ea580c", "prepTime": 14, "channels": ["dine-in", "pickup", "delivery"]},
]

SEED_PRODUCTS = [
    # === 20 COFFEES ===
    *[{"name": n, "category": "Coffee", "price": p, "cost": round(p*0.35, 2), "stock": 200,
       "image": img}
      for n, p, img in [
        ("Espresso", 4.50, "https://images.unsplash.com/photo-1510707577719-ae7c14805e3a?w=400"),
        ("Double Espresso", 5.00, "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=400"),
        ("Long Black", 4.80, "https://images.unsplash.com/photo-1497935586351-b67a49e012bf?w=400"),
        ("Americano", 4.60, "https://images.unsplash.com/photo-1551030173-122aabc4489c?w=400"),
        ("Flat White", 5.20, "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=400"),
        ("Cappuccino", 5.20, "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400"),
        ("Latte", 5.40, "https://images.unsplash.com/photo-1561882468-9110e03e0f78?w=400"),
        ("Mocha", 5.80, "https://images.unsplash.com/photo-1578314675229-c1f3a9b5dbe6?w=400"),
        ("Macchiato", 4.90, "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=400"),
        ("Piccolo Latte", 4.80, "https://images.unsplash.com/photo-1599506539953-a48aafa3c197?w=400"),
        ("Cortado", 5.00, "https://images.unsplash.com/photo-1568649929103-28ffbefaca1e?w=400"),
        ("Affogato", 7.50, "https://images.unsplash.com/photo-1497636577773-f1231844b336?w=400"),
        ("Iced Latte", 6.00, "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=400"),
        ("Iced Long Black", 5.50, "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=400"),
        ("Cold Brew", 6.50, "https://images.unsplash.com/photo-1517959105821-eaf2591984ca?w=400"),
        ("Nitro Cold Brew", 7.20, "https://images.unsplash.com/photo-1559496417-e7f25cb247f3?w=400"),
        ("Chai Latte", 5.40, "https://images.unsplash.com/photo-1571934811356-5cc061b6821f?w=400"),
        ("Matcha Latte", 6.20, "https://images.unsplash.com/photo-1545518514-ce8448f542b3?w=400"),
        ("Dirty Chai", 6.00, "https://images.unsplash.com/photo-1518882570151-d3f5337d3ade?w=400"),
        ("Hot Chocolate", 5.40, "https://images.unsplash.com/photo-1542990253-0d0f5be5f0ed?w=400"),
      ]],
    # === 10 BURGERS ===
    *[{"name": n, "category": "Burgers", "price": p, "cost": round(p*0.32, 2), "stock": 80,
       "image": img}
      for n, p, img in [
        ("Classic Cheeseburger", 16.50, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400"),
        ("Double Bacon Burger", 19.50, "https://images.unsplash.com/photo-1572802419224-296b0aeee0d9?w=400"),
        ("BBQ Brisket Burger", 21.00, "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=400"),
        ("Crispy Chicken Burger", 17.80, "https://images.unsplash.com/photo-1606755962773-d324e0a13086?w=400"),
        ("Mushroom Swiss Burger", 18.50, "https://images.unsplash.com/photo-1550317138-10000687a72b?w=400"),
        ("Vegan Beetroot Burger", 17.00, "https://images.unsplash.com/photo-1525059696034-4967a729002e?w=400"),
        ("Wagyu Burger", 26.00, "https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=400"),
        ("Lamb Burger", 19.80, "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=400"),
        ("Smash Burger", 15.50, "https://images.unsplash.com/photo-1572448862527-d3c904757de6?w=400"),
        ("Spicy Halloumi Burger", 18.00, "https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=400"),
      ]],
    # === 10 MAINS ===
    *[{"name": n, "category": "Mains", "price": p, "cost": round(p*0.30, 2), "stock": 50,
       "image": img}
      for n, p, img in [
        ("Eye Fillet Steak 250g", 38.00, "https://images.unsplash.com/photo-1546964124-0cce460f38ef?w=400"),
        ("Atlantic Salmon", 32.50, "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400"),
        ("Crispy Pork Belly", 28.00, "https://images.unsplash.com/photo-1432139509613-5c4255815697?w=400"),
        ("Roast Lamb Rump", 33.00, "https://images.unsplash.com/photo-1544025162-d76694265947?w=400"),
        ("Chicken Schnitzel", 24.50, "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=400"),
        ("Fish & Chips", 22.00, "https://images.unsplash.com/photo-1580217593608-61931cefc821?w=400"),
        ("Duck Confit", 34.00, "https://images.unsplash.com/photo-1547573854-74d2a71d0826?w=400"),
        ("Beef Brisket Plate", 29.50, "https://images.unsplash.com/photo-1529694157872-4e0c0f3b238b?w=400"),
        ("Vegetarian Buddha Bowl", 19.50, "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400"),
        ("Slow-Cooked Lamb Shank", 31.00, "https://images.unsplash.com/photo-1544025162-d76694265947?w=400"),
      ]],
    # === 10 CAKES & SLICES ===
    *[{"name": n, "category": "Cakes & Slices", "price": p, "cost": round(p*0.28, 2), "stock": 30,
       "image": img}
      for n, p, img in [
        ("Flourless Chocolate Cake", 8.50, "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400"),
        ("Carrot Cake Slice", 7.80, "https://images.unsplash.com/photo-1621303837174-89787a7d4729?w=400"),
        ("New York Cheesecake", 8.90, "https://images.unsplash.com/photo-1567171466295-4afa63d45416?w=400"),
        ("Red Velvet Slice", 7.50, "https://images.unsplash.com/photo-1586788680434-30d324b2d46f?w=400"),
        ("Lemon Tart", 7.80, "https://images.unsplash.com/photo-1519915028121-7d3463d20b13?w=400"),
        ("Vanilla Slice", 6.80, "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400"),
        ("Caramel Slice", 6.50, "https://images.unsplash.com/photo-1551404973-761c83cf8c11?w=400"),
        ("Tiramisu Slice", 8.20, "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400"),
        ("Pavlova Slice", 7.20, "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=400"),
        ("Pistachio Brownie", 6.90, "https://images.unsplash.com/photo-1606312619070-d48b4c652a52?w=400"),
      ]],
    # === 10 PASTA ===
    *[{"name": n, "category": "Pasta", "price": p, "cost": round(p*0.27, 2), "stock": 60,
       "image": img}
      for n, p, img in [
        ("Spaghetti Carbonara", 21.00, "https://images.unsplash.com/photo-1612874742237-6526221588e3?w=400"),
        ("Penne Arrabbiata", 18.50, "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=400"),
        ("Fettuccine Alfredo", 19.80, "https://images.unsplash.com/photo-1645112411341-6c4fd023714a?w=400"),
        ("Lasagna Bolognese", 22.50, "https://images.unsplash.com/photo-1619895092538-128f4d0a4e0f?w=400"),
        ("Pesto Linguine", 20.00, "https://images.unsplash.com/photo-1473093226795-af9932fe5856?w=400"),
        ("Mushroom Tagliatelle", 21.80, "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=400"),
        ("Prawn Aglio e Olio", 24.50, "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=400"),
        ("Ravioli Ricotta & Spinach", 22.00, "https://images.unsplash.com/photo-1587740908075-9e245311cf67?w=400"),
        ("Gnocchi Sorrentina", 21.50, "https://images.unsplash.com/photo-1633436374961-09b92742047b?w=400"),
        ("Truffle Mac & Cheese", 24.00, "https://images.unsplash.com/photo-1612464962427-ed4d8b8b6f87?w=400"),
      ]],
]

SEED_MODIFIERS = [
    {"name": "Milk Choice", "type": "list", "mandatory": True, "multiSelect": False, "maxSelections": 1,
     "assignedCategories": ["Coffee"],
     "options": [{"name": "Full Cream", "price": 0}, {"name": "Skim", "price": 0}, {"name": "Oat", "price": 0.80},
                 {"name": "Almond", "price": 0.80}, {"name": "Soy", "price": 0.60}, {"name": "Lactose Free", "price": 0.60}]},
    {"name": "Extra Shot", "type": "list", "mandatory": False, "multiSelect": True, "maxSelections": 3,
     "assignedCategories": ["Coffee"],
     "options": [{"name": "Single Shot", "price": 0.80}, {"name": "Double Shot", "price": 1.50}]},
    {"name": "Coffee Strength", "type": "dropdown", "mandatory": False, "multiSelect": False, "maxSelections": 1,
     "assignedCategories": ["Coffee"],
     "options": [{"name": "Mild", "price": 0}, {"name": "Regular", "price": 0}, {"name": "Strong", "price": 0}, {"name": "Extra Strong", "price": 0.50}]},
    {"name": "Syrup", "type": "list", "mandatory": False, "multiSelect": True, "maxSelections": 2,
     "assignedCategories": ["Coffee"],
     "options": [{"name": "Vanilla", "price": 0.80}, {"name": "Caramel", "price": 0.80}, {"name": "Hazelnut", "price": 0.80}, {"name": "Sugar-Free Vanilla", "price": 0.80}]},
    {"name": "Burger Cheese", "type": "list", "mandatory": False, "multiSelect": True, "maxSelections": 2,
     "assignedCategories": ["Burgers"],
     "options": [{"name": "Cheddar", "price": 1.50}, {"name": "Blue Cheese", "price": 2.00}, {"name": "Swiss", "price": 1.80}, {"name": "Vegan Cheese", "price": 2.00}]},
    {"name": "Burger Add-ons", "type": "list", "mandatory": False, "multiSelect": True, "maxSelections": 5,
     "assignedCategories": ["Burgers"],
     "options": [{"name": "Bacon", "price": 3.00}, {"name": "Avocado", "price": 2.50}, {"name": "Pineapple", "price": 1.50},
                 {"name": "Fried Egg", "price": 2.00}, {"name": "Jalapeños", "price": 1.00}]},
    {"name": "Cooking Preference", "type": "dropdown", "mandatory": True, "multiSelect": False, "maxSelections": 1,
     "assignedCategories": ["Mains", "Burgers"],
     "options": [{"name": "Rare", "price": 0}, {"name": "Medium Rare", "price": 0}, {"name": "Medium", "price": 0},
                 {"name": "Medium Well", "price": 0}, {"name": "Well Done", "price": 0}]},
    {"name": "Side Choice", "type": "list", "mandatory": False, "multiSelect": False, "maxSelections": 1,
     "assignedCategories": ["Mains", "Burgers"],
     "options": [{"name": "Fries", "price": 0}, {"name": "Sweet Potato Fries", "price": 2.00},
                 {"name": "Garden Salad", "price": 1.50}, {"name": "Mashed Potato", "price": 1.50}]},
    {"name": "Pasta Style", "type": "list", "mandatory": False, "multiSelect": False, "maxSelections": 1,
     "assignedCategories": ["Pasta"],
     "options": [{"name": "Gluten Free", "price": 2.00}, {"name": "Wholemeal", "price": 1.00}, {"name": "Regular", "price": 0}]},
    {"name": "Sauce Add-on", "type": "list", "mandatory": False, "multiSelect": True, "maxSelections": 3,
     "assignedCategories": ["Pasta", "Mains", "Burgers"],
     "options": [{"name": "Garlic Aioli", "price": 1.00}, {"name": "BBQ", "price": 0.50},
                 {"name": "Sriracha", "price": 0.50}, {"name": "Truffle Mayo", "price": 1.50}]},
]


@router.post("/seed/catalog")
async def seed_catalog(request: Request):
    """Owner-only: seed 5 categories, 60 products, 10 modifiers. Idempotent —
    skips items that already exist by name+category."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner only")
    # Categories
    cat_added = 0
    for c in SEED_CATEGORIES:
        existing = await db.categories.find_one({"name": c["name"]})
        if existing:
            await db.categories.update_one(
                {"name": c["name"]},
                {"$set": {"icon": c["icon"], "color": c["color"],
                          "prepTime": c["prepTime"], "channels": c["channels"]}},
            )
        else:
            await db.categories.insert_one({**c})
            cat_added += 1
    # Products
    prod_added = 0
    for i, p in enumerate(SEED_PRODUCTS):
        existing = await db.products.find_one({"name": p["name"], "category": p["category"]})
        if existing:
            continue
        sku = f"SEED-{p['category'][:3].upper()}-{i:03d}"
        product = {
            "id": str(uuid.uuid4()),
            "name": p["name"], "category": p["category"],
            "price": float(p["price"]), "cost": float(p["cost"]),
            "stock": int(p["stock"]),
            "sku": sku, "image": p["image"],
            "gstRate": 10.0, "modifiers": [], "locations": ["Main"],
            "onlineChannels": [], "seoDescription": "", "description": "",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        await db.products.insert_one(product)
        prod_added += 1
    # Modifiers
    mod_added = 0
    for m in SEED_MODIFIERS:
        existing = await db.modifiers.find_one({"name": m["name"]})
        if existing:
            continue
        mod = {
            "id": f"mod-{str(uuid.uuid4())[:8]}",
            "printWithItem": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            **m,
        }
        await db.modifiers.insert_one(mod)
        mod_added += 1
    return {
        "categoriesAdded": cat_added, "categoriesTotal": len(SEED_CATEGORIES),
        "productsAdded": prod_added, "productsTotal": len(SEED_PRODUCTS),
        "modifiersAdded": mod_added, "modifiersTotal": len(SEED_MODIFIERS),
    }

# ============ MODIFIERS (Universal) ============
@router.get("/modifiers")
async def get_modifiers():
    mods = await db.modifiers.find({}, {"_id": 0}).to_list(500)
    return mods

@router.post("/modifiers")
async def create_modifier(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    mod = {
        "id": f"mod-{str(uuid.uuid4())[:8]}",
        "name": data.get("name", ""),
        "type": data.get("type", "list"),
        "mandatory": data.get("mandatory", False),
        "multiSelect": data.get("multiSelect", False),
        "maxSelections": data.get("maxSelections", 1),
        "options": data.get("options", []),
        "assignedCategories": data.get("assignedCategories", []),
        # Where this modifier is offered + when it's available on each channel.
        # channels = ["dine-in","pickup","delivery","uber-eats","doordash","online"]
        "channels": data.get("channels", ["dine-in", "pickup", "delivery"]),
        "availableFrom": data.get("availableFrom"),   # "HH:MM"
        "availableTo": data.get("availableTo"),       # "HH:MM"
        "activeDays": data.get("activeDays", []),     # ["Mon",...,"Sun"] empty=all
        "printWithItem": data.get("printWithItem", True),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.modifiers.insert_one(mod)
    mod.pop("_id", None)
    return mod

@router.put("/modifiers/{mod_id}")
async def update_modifier(mod_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    allowed = {"name", "type", "mandatory", "multiSelect", "maxSelections", "options",
               "assignedCategories", "printWithItem",
               "channels", "availableFrom", "availableTo", "activeDays"}
    update = {k: v for k, v in data.items() if k in allowed}
    update["updatedAt"] = datetime.now(timezone.utc).isoformat()
    result = await db.modifiers.find_one_and_update({"id": mod_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result

@router.delete("/modifiers/{mod_id}")
async def delete_modifier(mod_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    await db.modifiers.delete_one({"id": mod_id})
    return {"message": "Modifier deleted"}

# ============ DISCOUNTS & OFFERS ============
@router.get("/discounts")
async def get_discounts():
    discounts = await db.discounts.find({}, {"_id": 0}).to_list(200)
    return discounts

@router.post("/discounts")
async def create_discount(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    disc = {
        "id": f"DISC-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", ""),
        "type": data.get("type", "percentage"),  # percentage, fixed, bundle, bogo, half_price
        "value": data.get("value", 0),  # % or $ amount
        "conditions": data.get("conditions", {}),  # e.g. {minQty: 2, productId: "..."}
        "active": data.get("active", True),
        "startDate": data.get("startDate"), "endDate": data.get("endDate"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.discounts.insert_one(disc)
    disc.pop("_id", None)
    return disc

@router.put("/discounts/{disc_id}")
async def update_discount(disc_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    allowed = {"name", "type", "value", "conditions", "active", "startDate", "endDate"}
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db.discounts.find_one_and_update({"id": disc_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result

@router.delete("/discounts/{disc_id}")
async def delete_discount(disc_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    await db.discounts.delete_one({"id": disc_id})
    return {"message": "Discount deleted"}

# ============ COMP / VOID ============
@router.post("/comp-void")
async def create_comp_void(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    record = {
        "id": f"CV-{str(uuid.uuid4())[:8].upper()}",
        "type": data.get("type", "comp"),  # comp or void
        "transactionId": data.get("transactionId"),
        "items": data.get("items", []),
        "reason": data.get("reason", ""),
        "amount": data.get("amount", 0),
        "printVoid": data.get("printVoid", False),
        "processedBy": user["id"],
        "processedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.comp_voids.insert_one(record)
    record.pop("_id", None)
    return record

@router.get("/comp-void")
async def get_comp_voids(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    records = await db.comp_voids.find({}, {"_id": 0}).sort("processedAt", -1).to_list(500)
    return records

# ============ PAYMENT LINKS ============
@router.post("/payment-links")
async def create_payment_link(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    link = {
        "id": f"PLINK-{str(uuid.uuid4())[:8].upper()}",
        "productId": data.get("productId"),
        "productName": data.get("productName", ""),
        "price": data.get("price", 0),
        "url": f"https://pay.nua.pos/{str(uuid.uuid4())[:12]}",
        "active": True,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.payment_links.insert_one(link)
    link.pop("_id", None)
    return link

@router.get("/payment-links")
async def get_payment_links():
    links = await db.payment_links.find({}, {"_id": 0}).to_list(500)
    return links

@router.delete("/payment-links/{link_id}")
async def delete_payment_link(link_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    await db.payment_links.delete_one({"id": link_id})
    return {"message": "Payment link deleted"}
