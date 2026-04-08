from fastapi import APIRouter, HTTPException
from datetime import datetime
from database import db
import uuid

router = APIRouter()

# ============ AUTOMATION RULES API ============
@router.get("/automation/rules")
async def get_automation_rules():
    rules = await db.automation_rules.find({}, {"_id": 0}).to_list(100)
    return rules

@router.post("/automation/rules")
async def create_automation_rule(rule: dict):
    rule_id = f"RULE-{str(uuid.uuid4())[:8].upper()}"
    rule_doc = {
        "id": rule_id, "name": rule.get("name", ""), "trigger": rule.get("trigger", ""),
        "condition": rule.get("condition", ""), "action": rule.get("action", ""),
        "enabled": rule.get("enabled", True), "lastTriggered": None,
        "triggerCount": 0, "createdAt": datetime.utcnow().isoformat(),
    }
    await db.automation_rules.insert_one(rule_doc)
    rule_doc.pop("_id", None)
    return rule_doc

@router.put("/automation/rules/{rule_id}")
async def update_automation_rule(rule_id: str, update: dict):
    update_data = {k: v for k, v in update.items() if k != "id"}
    result = await db.automation_rules.find_one_and_update(
        {"id": rule_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")
    result.pop("_id", None)
    return result

@router.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(rule_id: str):
    result = await db.automation_rules.delete_one({"id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted"}

@router.post("/automation/rules/{rule_id}/toggle")
async def toggle_automation_rule(rule_id: str):
    rule = await db.automation_rules.find_one({"id": rule_id}, {"_id": 0})
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    new_state = not rule.get("enabled", True)
    await db.automation_rules.update_one({"id": rule_id}, {"$set": {"enabled": new_state}})
    return {"enabled": new_state}

@router.get("/automation/alerts")
async def get_automation_alerts():
    alerts = []
    low_stock = await db.products.find({"stock": {"$lt": 10}}, {"_id": 0}).to_list(100)
    for p in low_stock:
        alerts.append({
            "type": "inventory", "severity": "warning",
            "title": f"Low Stock: {p['name']}",
            "message": f"Only {p.get('stock', 0)} units remaining.",
            "action": "create_purchase_order", "data": {"productId": p["id"]}
        })
    kitchen_new = await db.kitchen_orders.count_documents({"status": "new"})
    if kitchen_new > 5:
        alerts.append({
            "type": "kitchen", "severity": "high",
            "title": "Kitchen Backlog",
            "message": f"{kitchen_new} orders waiting.",
            "action": "notify_manager"
        })
    no_show_customers = await db.customers.find({"noShowCount": {"$gte": 3}}, {"_id": 0}).to_list(50)
    for c in no_show_customers:
        alerts.append({
            "type": "customer", "severity": "info",
            "title": f"Frequent No-Show: {c['name']}",
            "message": f"{c.get('noShowCount', 0)} no-shows recorded.",
            "action": "flag_customer"
        })
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    for p in products:
        if p.get("cost", 0) > 0 and p.get("price", 0) > 0:
            margin = ((p["price"] - p["cost"]) / p["price"]) * 100
            if margin < 15:
                alerts.append({
                    "type": "menu", "severity": "warning",
                    "title": f"Low Margin: {p['name']}",
                    "message": f"Only {margin:.0f}% margin. Price: ${p['price']}, Cost: ${p['cost']}",
                    "action": "review_pricing"
                })
    return alerts
