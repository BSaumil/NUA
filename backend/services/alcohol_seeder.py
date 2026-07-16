"""
Seeder — Alcoholic categories & products.

Idempotent: runs once, second run is a no-op.
Auto-links Measured Stock (StockUnit + SellVariant) for anything that's
poured, so the beverage-margin math is real from day one.

Called at server startup (see server.py) and also exposed via
POST /api/settings/seed-alcohol for manual re-runs.
"""
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime, timezone
from database import db
from services.entity_service import stamped_insert
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Category tree ────────────────────────────────────────────────────────
CATEGORIES: List[Dict[str, Any]] = [
    # Existing food kept intact — these are the alcoholic + non-alcoholic drink families
    {"name": "Beer",              "group": "Alcohol",      "icon": "beer",       "color": "#f59e0b"},
    {"name": "Wine — Red",        "group": "Alcohol",      "icon": "wine",       "color": "#7f1d1d"},
    {"name": "Wine — White",      "group": "Alcohol",      "icon": "wine",       "color": "#d4d4aa"},
    {"name": "Wine — Sparkling",  "group": "Alcohol",      "icon": "wine",       "color": "#fef3c7"},
    {"name": "Wine — Rosé",       "group": "Alcohol",      "icon": "wine",       "color": "#fbcfe8"},
    {"name": "Cocktails",         "group": "Alcohol",      "icon": "martini",    "color": "#ec4899"},
    {"name": "Spirits — Whisky",  "group": "Alcohol",      "icon": "glass",      "color": "#a16207"},
    {"name": "Spirits — Gin",     "group": "Alcohol",      "icon": "glass",      "color": "#0ea5e9"},
    {"name": "Spirits — Vodka",   "group": "Alcohol",      "icon": "glass",      "color": "#e5e7eb"},
    {"name": "Spirits — Rum",     "group": "Alcohol",      "icon": "glass",      "color": "#78350f"},
    {"name": "Spirits — Tequila", "group": "Alcohol",      "icon": "glass",      "color": "#84cc16"},
    {"name": "Liqueurs",          "group": "Alcohol",      "icon": "glass",      "color": "#a855f7"},
    {"name": "Non-Alcoholic",     "group": "Drinks",       "icon": "cup-soda",   "color": "#22c55e"},
    {"name": "Coffee & Tea",      "group": "Drinks",       "icon": "coffee",     "color": "#78350f"},
]

# ─── Products ─────────────────────────────────────────────────────────────
# Each entry:  (categoryName, productName, price, taxRate, measuredStock?)
# `measured` dict — if present, seed a StockUnit + SellVariant:
#   { bottle: {uom, totalMeasure, cost}, pour: {uom, amount, label} }
PRODUCTS: List[Dict[str, Any]] = [
    # Beer
    {"cat": "Beer", "name": "Craft Lager (Draft)", "price": 9.5, "measured": {
        "bottle": {"uom": "l", "totalMeasure": 50, "cost": 220},
        "pour":   {"uom": "ml", "amount": 425, "label": "Schooner 425ml"},
    }},
    {"cat": "Beer", "name": "IPA (Draft)", "price": 10.5, "measured": {
        "bottle": {"uom": "l", "totalMeasure": 50, "cost": 260},
        "pour":   {"uom": "ml", "amount": 425, "label": "Schooner 425ml"},
    }},
    {"cat": "Beer", "name": "Bottled Pale Ale 330ml", "price": 8.5},
    {"cat": "Beer", "name": "Cider (Draft)", "price": 9.5, "measured": {
        "bottle": {"uom": "l", "totalMeasure": 20, "cost": 130},
        "pour":   {"uom": "ml", "amount": 425, "label": "Schooner 425ml"},
    }},

    # Wine — Red
    {"cat": "Wine — Red", "name": "House Shiraz — Glass", "price": 12, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 750, "cost": 22},
        "pour":   {"uom": "ml", "amount": 150, "label": "Standard glass 150ml"},
    }},
    {"cat": "Wine — Red", "name": "Cabernet Sauvignon — Glass", "price": 14, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 750, "cost": 28},
        "pour":   {"uom": "ml", "amount": 150, "label": "Standard glass 150ml"},
    }},
    {"cat": "Wine — Red", "name": "Pinot Noir — Bottle", "price": 68},

    # Wine — White
    {"cat": "Wine — White", "name": "Sauvignon Blanc — Glass", "price": 12, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 750, "cost": 20},
        "pour":   {"uom": "ml", "amount": 150, "label": "Standard glass 150ml"},
    }},
    {"cat": "Wine — White", "name": "Chardonnay — Glass", "price": 13, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 750, "cost": 24},
        "pour":   {"uom": "ml", "amount": 150, "label": "Standard glass 150ml"},
    }},

    # Wine — Sparkling
    {"cat": "Wine — Sparkling", "name": "Prosecco — Glass", "price": 12, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 750, "cost": 18},
        "pour":   {"uom": "ml", "amount": 120, "label": "Flute 120ml"},
    }},
    {"cat": "Wine — Sparkling", "name": "Champagne — Bottle", "price": 120},

    # Wine — Rosé
    {"cat": "Wine — Rosé", "name": "Rosé — Glass", "price": 12, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 750, "cost": 20},
        "pour":   {"uom": "ml", "amount": 150, "label": "Standard glass 150ml"},
    }},

    # Cocktails (recipes not measured at ingredient level yet, price only)
    {"cat": "Cocktails", "name": "Espresso Martini", "price": 22},
    {"cat": "Cocktails", "name": "Negroni", "price": 20},
    {"cat": "Cocktails", "name": "Old Fashioned", "price": 22},
    {"cat": "Cocktails", "name": "Margarita", "price": 20},
    {"cat": "Cocktails", "name": "Aperol Spritz", "price": 18},
    {"cat": "Cocktails", "name": "Whisky Sour", "price": 20},
    {"cat": "Cocktails", "name": "Mojito", "price": 19},

    # Spirits — Whisky
    {"cat": "Spirits — Whisky", "name": "Scotch Single Malt — 30ml", "price": 16, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 95},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},
    {"cat": "Spirits — Whisky", "name": "Bourbon — 30ml", "price": 12, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 55},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},

    # Spirits — Gin
    {"cat": "Spirits — Gin", "name": "London Dry Gin — 30ml", "price": 11, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 45},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},
    {"cat": "Spirits — Gin", "name": "Botanical Gin — 30ml", "price": 14, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 65},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},

    # Spirits — Vodka
    {"cat": "Spirits — Vodka", "name": "Premium Vodka — 30ml", "price": 11, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 42},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},

    # Spirits — Rum
    {"cat": "Spirits — Rum", "name": "Aged Rum — 30ml", "price": 12, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 50},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},

    # Spirits — Tequila
    {"cat": "Spirits — Tequila", "name": "Reposado Tequila — 30ml", "price": 13, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 55},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},

    # Liqueurs
    {"cat": "Liqueurs", "name": "Amaretto — 30ml", "price": 10, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 38},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},
    {"cat": "Liqueurs", "name": "Baileys — 30ml", "price": 10, "measured": {
        "bottle": {"uom": "ml", "totalMeasure": 700, "cost": 32},
        "pour":   {"uom": "ml", "amount": 30, "label": "Standard 30ml"},
    }},

    # Non-Alcoholic
    {"cat": "Non-Alcoholic", "name": "Sparkling Water 500ml", "price": 5},
    {"cat": "Non-Alcoholic", "name": "Still Water 500ml", "price": 4},
    {"cat": "Non-Alcoholic", "name": "Soft Drink 330ml", "price": 5.5},
    {"cat": "Non-Alcoholic", "name": "Fresh Juice", "price": 8},
    {"cat": "Non-Alcoholic", "name": "Iced Tea", "price": 6},
    {"cat": "Non-Alcoholic", "name": "Kombucha", "price": 7},

    # Coffee & Tea
    {"cat": "Coffee & Tea", "name": "Flat White", "price": 5.5},
    {"cat": "Coffee & Tea", "name": "Latte", "price": 5.5},
    {"cat": "Coffee & Tea", "name": "Long Black", "price": 5.0},
    {"cat": "Coffee & Tea", "name": "Cappuccino", "price": 5.5},
    {"cat": "Coffee & Tea", "name": "Espresso", "price": 4.5},
    {"cat": "Coffee & Tea", "name": "Pot of Tea", "price": 6},
    {"cat": "Coffee & Tea", "name": "Chai Latte", "price": 6},
]


async def _upsert_category(cat: Dict[str, Any]) -> Dict[str, Any]:
    existing = await db.categories.find_one({"name": cat["name"]}, {"_id": 0})
    if existing:
        return existing
    doc = {
        "id": str(uuid.uuid4()),
        "name": cat["name"],
        "group": cat.get("group"),
        "icon": cat.get("icon"),
        "color": cat.get("color"),
    }
    return await stamped_insert("categories", doc, entity_type="category")


async def _upsert_product(name: str, category: Dict[str, Any], price: float,
                            measured: Dict[str, Any] | None = None) -> Dict[str, Any]:
    existing = await db.products.find_one({"name": name}, {"_id": 0})
    if existing:
        return existing
    prod = {
        "id": str(uuid.uuid4()),
        "name": name,
        "category": category["name"],
        "categoryId": category["id"],
        "price": price,
        "stock": 0 if measured else 20,   # measured items don't use scalar stock
        "parLevel": 3,
        "taxRate": 0.10,
        "isMeasured": bool(measured),
    }
    saved = await stamped_insert("products", prod, entity_type="product")

    if measured:
        # Seed a stock unit (bought container) + sell variant (poured serve)
        su = await stamped_insert("stock_units", {
            "id": str(uuid.uuid4()),
            "productId": saved["id"],
            "uom": measured["bottle"]["uom"],
            "totalMeasure": measured["bottle"]["totalMeasure"],
            "costPerUnit": measured["bottle"]["cost"],
            "label": f"{measured['bottle']['totalMeasure']}{measured['bottle']['uom']} bottle",
        }, entity_type="stock_unit")
        await stamped_insert("sell_variants", {
            "id": str(uuid.uuid4()),
            "productId": saved["id"],
            "stockUnitId": su["id"],
            "uom": measured["pour"]["uom"],
            "deductAmount": measured["pour"]["amount"],
            "label": measured["pour"]["label"],
        }, entity_type="sell_variant")
    return saved


async def seed_alcohol_catalog() -> Dict[str, Any]:
    """Idempotent. Reports how many rows were newly created."""
    stats = {"categoriesInserted": 0, "productsInserted": 0, "stockUnitsInserted": 0}
    cat_map: Dict[str, Dict[str, Any]] = {}
    for cat in CATEGORIES:
        before = await db.categories.find_one({"name": cat["name"]}, {"_id": 0})
        got = await _upsert_category(cat)
        cat_map[cat["name"]] = got
        if not before:
            stats["categoriesInserted"] += 1

    for p in PRODUCTS:
        cat = cat_map.get(p["cat"])
        if not cat:
            continue
        existing = await db.products.find_one({"name": p["name"]}, {"_id": 0})
        await _upsert_product(p["name"], cat, p["price"], p.get("measured"))
        if not existing:
            stats["productsInserted"] += 1
            if p.get("measured"):
                stats["stockUnitsInserted"] += 1

    return {"seededAt": _now(), **stats}
