from fastapi import APIRouter, HTTPException
from typing import List, Optional
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

# ============ CATEGORIES API ============
@router.get("/categories", response_model=List[Category])
async def get_categories():
    categories = await db.categories.find().to_list(1000)
    return [Category(**c) for c in categories]

@router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate):
    cat_obj = Category(**category.dict())
    await db.categories.insert_one(cat_obj.dict())
    return cat_obj

# ============ MODIFIERS API ============
@router.get("/modifiers", response_model=List[Modifier])
async def get_modifiers():
    modifiers = await db.modifiers.find().to_list(1000)
    return [Modifier(**m) for m in modifiers]

@router.post("/modifiers", response_model=Modifier)
async def create_modifier(modifier: ModifierCreate):
    mod_obj = Modifier(**modifier.dict())
    await db.modifiers.insert_one(mod_obj.dict())
    return mod_obj
