from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from database import db
from models.product import Product, ProductCreate, ProductUpdate
from models.category import Category, CategoryCreate
from models.modifier import Modifier, ModifierCreate
from pydantic import BaseModel

router = APIRouter()

async def _require_owner_or_manager(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    return user

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
    update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
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


# ============ BULK PRODUCT EDIT ============
class BulkProductEdit(BaseModel):
    productIds: List[str]
    # Optional fields — only fields present (non-None) are applied
    category: Optional[str] = None
    categoryId: Optional[str] = None
    pricePercentDelta: Optional[float] = None  # e.g. +10 = +10%, -5 = -5%
    cost: Optional[float] = None
    gstRate: Optional[float] = None
    image: Optional[str] = None
    eightySixed: Optional[bool] = None
    active: Optional[bool] = None
    addModifierIds: Optional[List[str]] = None      # union into existing
    removeModifierIds: Optional[List[str]] = None   # subtract from existing
    replaceModifierIds: Optional[List[str]] = None  # overwrite entirely
    onlineChannels: Optional[List[str]] = None

@router.post("/products/bulk-edit")
async def bulk_edit_products(payload: BulkProductEdit, request: Request):
    await _require_owner_or_manager(request)
    if not payload.productIds:
        raise HTTPException(status_code=400, detail="productIds is required")
    now_iso = datetime.now(timezone.utc).isoformat()

    # ---- Fast path: when no per-row math (pricePercentDelta) AND no modifier
    # add/remove (which require per-row union/difference), apply update_many.
    needs_per_row = (
        payload.pricePercentDelta is not None
        or bool(payload.addModifierIds)
        or bool(payload.removeModifierIds)
    )
    common: dict = {"updatedAt": now_iso}
    if payload.category is not None:
        common["category"] = payload.category
    if payload.categoryId is not None:
        common["categoryId"] = payload.categoryId
    if payload.cost is not None:
        common["cost"] = payload.cost
    if payload.gstRate is not None:
        common["gstRate"] = payload.gstRate
    if payload.image is not None:
        common["image"] = payload.image
    if payload.eightySixed is not None:
        common["eightySixed"] = payload.eightySixed
        common["eightySixedAt"] = now_iso if payload.eightySixed else None
    if payload.active is not None:
        common["active"] = payload.active
    if payload.onlineChannels is not None:
        common["onlineChannels"] = payload.onlineChannels
    if payload.replaceModifierIds is not None:
        common["modifierIds"] = list(payload.replaceModifierIds)

    if not needs_per_row:
        res = await db.products.update_many(
            {"id": {"$in": payload.productIds}},
            {"$set": common},
        )
        return {"updated": res.modified_count, "failed": [], "mode": "update_many"}

    # ---- Slow path: per-row math
    updated = 0
    failed: List[str] = []
    for pid in payload.productIds:
        prod = await db.products.find_one({"id": pid})
        if not prod:
            failed.append(pid)
            continue
        patch: dict = dict(common)
        if payload.pricePercentDelta is not None:
            # Clamp to avoid driving prices below zero (a -100% would zero them;
            # anything < -99 is almost certainly a typo).
            delta = max(-99.0, float(payload.pricePercentDelta))
            base_price = float(prod.get("price", 0) or 0)
            patch["price"] = round(max(0.0, base_price * (1 + delta / 100.0)), 2)
        # Modifier ops
        if payload.replaceModifierIds is None and (payload.addModifierIds or payload.removeModifierIds):
            existing_mods = list(prod.get("modifierIds", []) or [])
            if payload.addModifierIds:
                existing_mods = list({*existing_mods, *payload.addModifierIds})
            if payload.removeModifierIds:
                existing_mods = [m for m in existing_mods if m not in payload.removeModifierIds]
            patch["modifierIds"] = existing_mods
        await db.products.update_one({"id": pid}, {"$set": patch})
        updated += 1
    return {"updated": updated, "failed": failed, "mode": "per_row"}


# ============ PRODUCT IMAGE LIBRARY ============
class ImageLibraryEntry(BaseModel):
    id: str
    name: str
    contentType: str
    dataUrl: str         # full data URL (data:image/png;base64,XXX)
    tags: List[str] = []
    createdAt: str
    createdBy: Optional[str] = None
    sizeBytes: int = 0

class ImageUploadBody(BaseModel):
    name: str
    contentType: str
    dataUrl: str
    tags: List[str] = []
    createdBy: Optional[str] = None

MAX_IMAGE_BYTES = 1_500_000  # ~1.5MB after base64 — keep db lean

@router.get("/product-images", response_model=List[ImageLibraryEntry])
async def list_images(request: Request, search: Optional[str] = None, tag: Optional[str] = None, limit: int = 100):
    # Any signed-in staff can browse the library (cashiers need to see images);
    # owner/manager required for mutations below.
    from routes.auth import get_current_user
    await get_current_user(request)
    # Cap list size — each entry can carry ~1.5MB base64 so a large list quickly
    # exhausts response bandwidth. Default 100 is plenty for a hand-curated library.
    limit = max(1, min(500, limit))
    query: dict = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if tag:
        query["tags"] = tag
    rows = await db.product_images.find(query).sort("createdAt", -1).to_list(limit)
    out = []
    for r in rows:
        out.append(ImageLibraryEntry(
            id=r.get("id"), name=r.get("name", ""), contentType=r.get("contentType", "image/png"),
            dataUrl=r.get("dataUrl", ""), tags=r.get("tags", []), createdAt=r.get("createdAt", ""),
            createdBy=r.get("createdBy"), sizeBytes=r.get("sizeBytes", 0),
        ))
    return out

@router.post("/product-images", response_model=ImageLibraryEntry)
async def upload_image(body: ImageUploadBody, request: Request):
    user = await _require_owner_or_manager(request)
    if not body.dataUrl.startswith("data:"):
        raise HTTPException(status_code=400, detail="dataUrl must be a data: URL")
    size = len(body.dataUrl)
    if size > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"Image too large ({size} > {MAX_IMAGE_BYTES})")
    entry = ImageLibraryEntry(
        id=str(uuid.uuid4()),
        name=body.name,
        contentType=body.contentType,
        dataUrl=body.dataUrl,
        tags=body.tags,
        createdAt=datetime.now(timezone.utc).isoformat(),
        createdBy=body.createdBy or user.get("name"),
        sizeBytes=size,
    )
    await db.product_images.insert_one(entry.dict())
    return entry

@router.delete("/product-images/{image_id}")
async def delete_image(image_id: str, request: Request):
    await _require_owner_or_manager(request)
    res = await db.product_images.delete_one({"id": image_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"deleted": True}


# Categories & Modifiers moved to routes/items_system.py
