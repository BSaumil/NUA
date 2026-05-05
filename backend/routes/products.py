from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
from database import db
from models.product import Product, ProductCreate, ProductUpdate
from models.category import Category, CategoryCreate
from models.modifier import Modifier, ModifierCreate

router = APIRouter()

# ============ PRODUCTS API ============
@router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, search: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    products = await db.products.find(query).to_list(1000)
    return [Product(**p) for p in products]

@router.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    product_dict = product.dict()
    product_obj = Product(**product_dict)
    await db.products.insert_one(product_obj.dict())
    return product_obj

@router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_update: ProductUpdate):
    update_data = {k: v for k, v in product_update.dict().items() if v is not None}
    result = await db.products.find_one_and_update(
        {"id": product_id},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**result)

@router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}

@router.post("/products/{product_id}/adjust-stock")
async def adjust_stock(product_id: str, data: dict):
    adjustment = data.get("adjustment", 0)
    reason = data.get("reason", "Manual adjustment")
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    new_stock = product.get("stock", 0) + adjustment
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot go below zero")
    await db.products.update_one({"id": product_id}, {"$set": {"stock": new_stock}})
    await db.stock_adjustments.insert_one({
        "productId": product_id, "productName": product.get("name", ""),
        "previousStock": product.get("stock", 0), "adjustment": adjustment,
        "newStock": new_stock, "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": "Stock adjusted", "newStock": new_stock}



# Categories & Modifiers moved to routes/items_system.py
