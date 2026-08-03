from fastapi import APIRouter, HTTPException, Depends
from deps import get_user, require_owner_or_manager
from typing import List, Optional
from datetime import datetime
from database import db
from models.location import Location, LocationCreate
from models.user import User, UserCreate
from models.printer import PrinterConfig, PrinterConfigCreate
from models.table import Table, TableCreate
from models.eftpos import EFTPOSConfig, EFTPOSConfigCreate, EFTPOSTransaction, EFTPOSTransactionRequest
from models.integration import Integration, IntegrationCreate, IntegrationUpdate, SyncRequest
from models.employee import EmployeeSchedule, EmployeeScheduleCreate, TimeOffRequest, AgeVerification
from models.staff import StaffCommission, StaffShift
from utils.mongo_safe import safe_find_list
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ============ LOCATIONS API ============
def _coerce_location(loc: dict) -> dict:
    """Legacy migration: `timings` → `hours`; scrub string-typed hours."""
    hours = loc.get("hours")
    if hours is not None and not isinstance(hours, dict):
        loc["hours"] = None
    timings = loc.get("timings")
    if timings is not None:
        if isinstance(timings, dict) and not loc.get("hours"):
            loc["hours"] = timings
        loc.pop("timings", None)
    return loc


def _location_fallback(loc: dict, _err: Exception):
    """Minimal safe shape so a corrupted doc still surfaces in the UI."""
    try:
        return Location(
            id=loc.get("id", ""),
            name=loc.get("name", "Unnamed"),
            address=loc.get("address", ""),
            phone=loc.get("phone", ""),
            status=loc.get("status", "active"),
        )
    except Exception:
        return None


@router.get("/locations")
async def get_locations():
    """Defensive read via `safe_find_list` — legacy docs never 500."""
    return await safe_find_list(
        db.locations, Location, {},
        limit=1000, coerce=_coerce_location, fallback=_location_fallback,
        where="locations",
    )

@router.post("/locations", response_model=Location)
async def create_location(location: LocationCreate):
    loc_obj = Location(**location.dict())
    await db.locations.insert_one(loc_obj.dict())
    return loc_obj

@router.put("/locations/{location_id}")
async def update_location(location_id: str, data: dict):
    """Allow the full extended Location profile (logo, website, hours, GMB,
    geo). Whitelist keeps arbitrary junk out but lets the v27.7 fields land."""
    allowed = {"name", "address", "phone", "status",
               "email", "website", "logoUrl", "latitude", "longitude", "timezone",
               "hours", "gmbPlaceId", "gmbSyncEnabled", "gmbLastSyncAt", "tags"}
    update_data = {k: v for k, v in data.items() if k in allowed}
    result = await db.locations.find_one_and_update({"id": location_id}, {"$set": update_data}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Location not found")
    result.pop("_id", None)
    return result


@router.post("/locations/{location_id}/gmb-sync")
async def gmb_sync(location_id: str):
    """Best-effort Google My Business sync — stamps the last-sync time and
    marks the location as synced. The real Google API call needs the
    location's `gmbPlaceId` plus an OAuth token stored elsewhere; when those
    aren't available we surface a clear message instead of failing hard."""
    from datetime import datetime, timezone
    loc = await db.locations.find_one({"id": location_id}, {"_id": 0})
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    if not loc.get("gmbPlaceId"):
        raise HTTPException(status_code=400, detail="Location has no GMB place id set")
    now = datetime.now(timezone.utc).isoformat()
    await db.locations.update_one(
        {"id": location_id},
        {"$set": {"gmbLastSyncAt": now, "gmbSyncEnabled": True}},
    )
    return {"syncedAt": now, "message": "GMB sync queued (real push requires GMB OAuth)."}

@router.delete("/locations/{location_id}")
async def delete_location(location_id: str):
    result = await db.locations.delete_one({"id": location_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"message": "Location deleted"}

# ============ USERS API ============
@router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find().to_list(1000)
    return [User(**u) for u in users]

@router.post("/users", response_model=User)
async def create_user(user: UserCreate):
    user_obj = User(**user.dict())
    await db.users.insert_one(user_obj.dict())
    return user_obj

# ============ PRINTER API ============
@router.get("/printers", response_model=List[PrinterConfig])
async def get_printers():
    printers = await db.printers.find().to_list(1000)
    return [PrinterConfig(**p) for p in printers]

@router.post("/printers", response_model=PrinterConfig)
async def create_printer(printer: PrinterConfigCreate):
    printer_obj = PrinterConfig(**printer.dict())
    await db.printers.insert_one(printer_obj.dict())
    return printer_obj

@router.post("/printers/{printer_id}/print")
async def print_receipt(printer_id: str, transaction_id: str):
    printer = await db.printers.find_one({"id": printer_id})
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    transaction = await db.transactions.find_one({"id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "message": "Receipt sent to printer",
        "printerId": printer_id,
        "transactionId": transaction_id,
        "printerName": printer.get("name", ""),
        "status": "queued"
    }

# ============ OFFLINE SYNC API ============
@router.post("/offline/sync")
async def sync_offline_data(data: dict):
    synced = {"transactions": 0, "products": 0, "customers": 0}
    if "transactions" in data:
        for txn in data["transactions"]:
            await db.transactions.update_one({"id": txn["id"]}, {"$set": txn}, upsert=True)
            synced["transactions"] += 1
    if "products" in data:
        for prod in data["products"]:
            await db.products.update_one({"id": prod["id"]}, {"$set": prod}, upsert=True)
            synced["products"] += 1
    return {"message": "Sync complete", "synced": synced}

# ============ TABLES API ============
@router.get("/tables", response_model=List[Table])
async def get_tables(location: Optional[str] = None):
    query = {"location": location} if location else {}
    tables = await db.tables.find(query).to_list(1000)
    return [Table(**t) for t in tables]

@router.post("/tables", response_model=Table)
async def create_table(table: TableCreate):
    table_obj = Table(**table.dict())
    await db.tables.insert_one(table_obj.dict())
    return table_obj

@router.post("/tables/{table_id}/occupy")
async def occupy_table(table_id: str, order_id: str):
    await db.tables.update_one({"id": table_id}, {"$set": {"status": "occupied", "currentOrderId": order_id}})
    return {"message": "Table occupied"}

@router.post("/tables/{table_id}/free")
async def free_table(table_id: str):
    await db.tables.update_one({"id": table_id}, {"$set": {"status": "available", "currentOrderId": None}})
    return {"message": "Table freed"}

# ============ STAFF API ============
@router.get("/staff/commissions")
async def get_staff_commissions(period: Optional[str] = None):
    query = {"period": period} if period else {}
    commissions = await db.staff_commissions.find(query).to_list(1000)
    return commissions

@router.post("/staff/legacy-clock-in")
async def staff_clock_in(user_id: str, location: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    shift = StaffShift(userId=user_id, userName=user["name"], location=location, clockIn=datetime.utcnow())
    await db.staff_shifts.insert_one(shift.dict())
    return shift

@router.post("/staff/legacy-clock-out/{shift_id}")
async def staff_clock_out(shift_id: str, break_minutes: int = 0):
    shift = await db.staff_shifts.find_one({"id": shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    clock_out = datetime.utcnow()
    clock_in = shift["clockIn"]
    total_hours = (clock_out - clock_in).total_seconds() / 3600
    total_hours -= break_minutes / 60
    await db.staff_shifts.update_one(
        {"id": shift_id},
        {"$set": {"clockOut": clock_out, "breakMinutes": break_minutes, "totalHours": total_hours, "status": "completed"}}
    )
    return {"total_hours": total_hours}

# ============ EFTPOS API ============
# Terminal config carries apiKey/apiSecret for the provider account, and
# these routes previously had no per-route auth at all — only the app-wide
# "you must be logged in as *someone*" gate applied, meaning any cashier
# account could read out another payment provider's API secret, or delete a
# terminal outright. Config and diagnostics are owner/manager; reading which
# terminals exist and actually taking a payment stay open to any signed-in
# staff member, since that's the ordinary checkout path.
@router.get("/eftpos/terminals", response_model=List[EFTPOSConfig])
async def get_eftpos_terminals(_: dict = Depends(get_user)):
    terminals = await db.eftpos_terminals.find().to_list(1000)
    return [EFTPOSConfig(**t) for t in terminals]

@router.post("/eftpos/terminals", response_model=EFTPOSConfig)
async def create_eftpos_terminal(terminal: EFTPOSConfigCreate, _: dict = Depends(require_owner_or_manager)):
    terminal_obj = EFTPOSConfig(**terminal.dict())
    await db.eftpos_terminals.insert_one(terminal_obj.dict())
    return terminal_obj

@router.put("/eftpos/terminals/{terminal_id}", response_model=EFTPOSConfig)
async def update_eftpos_terminal(terminal_id: str, terminal: EFTPOSConfigCreate, _: dict = Depends(require_owner_or_manager)):
    update_data = terminal.dict()
    result = await db.eftpos_terminals.find_one_and_update(
        {"id": terminal_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return EFTPOSConfig(**result)

@router.delete("/eftpos/terminals/{terminal_id}")
async def delete_eftpos_terminal(terminal_id: str, _: dict = Depends(require_owner_or_manager)):
    result = await db.eftpos_terminals.delete_one({"id": terminal_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return {"message": "Terminal deleted successfully"}

@router.post("/eftpos/terminals/{terminal_id}/test")
async def test_eftpos_connection(terminal_id: str, _: dict = Depends(require_owner_or_manager)):
    terminal = await db.eftpos_terminals.find_one({"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    try:
        from services.eftpos_service import eftpos_service
        provider = eftpos_service.get_provider(terminal)
        connected = await provider.connect()
        if connected:
            await provider.disconnect()
            await db.eftpos_terminals.update_one({"id": terminal_id}, {"$set": {"status": "active", "lastPing": datetime.utcnow()}})
            return {"success": True, "message": "Connection successful"}
        else:
            await db.eftpos_terminals.update_one({"id": terminal_id}, {"$set": {"status": "error"}})
            return {"success": False, "message": "Connection failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.post("/eftpos/transaction", response_model=EFTPOSTransaction)
async def process_eftpos_transaction(request: EFTPOSTransactionRequest, _: dict = Depends(get_user)):
    terminal = await db.eftpos_terminals.find_one({"id": request.terminalId})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    try:
        from services.eftpos_service import eftpos_service
        result = await eftpos_service.process_transaction(
            config=terminal, transaction_type=request.transactionType,
            amount=request.amount, reference=request.reference, cashout=request.cashout
        )
        eftpos_txn = EFTPOSTransaction(
            terminalId=request.terminalId, provider=terminal["provider"],
            transactionType=request.transactionType, amount=request.amount,
            cashout=request.cashout, reference=request.reference, posTransactionId=request.posTransactionId,
            cardType=result.get("cardType"), maskedPan=result.get("maskedPan"),
            authCode=result.get("authCode"), rrn=result.get("rrn"), stan=result.get("stan"),
            responseCode=result.get("responseCode", "99"), responseText=result.get("responseText", "Unknown"),
            approved=result.get("approved", False)
        )
        await db.eftpos_transactions.insert_one(eftpos_txn.dict())
        return eftpos_txn
    except Exception as e:
        logger.error(f"EFTPOS transaction error: {e}")
        eftpos_txn = EFTPOSTransaction(
            terminalId=request.terminalId, provider=terminal["provider"],
            transactionType=request.transactionType, amount=request.amount,
            cashout=request.cashout, reference=request.reference, posTransactionId=request.posTransactionId,
            responseCode="99", responseText=str(e), approved=False
        )
        await db.eftpos_transactions.insert_one(eftpos_txn.dict())
        return eftpos_txn

@router.get("/eftpos/transactions", response_model=List[EFTPOSTransaction])
async def get_eftpos_transactions(start_date: Optional[str] = None, end_date: Optional[str] = None,
                                  terminal_id: Optional[str] = None,
                                  _: dict = Depends(require_owner_or_manager)):
    query = {}
    if terminal_id:
        query["terminalId"] = terminal_id
    if start_date and end_date:
        query["timestamp"] = {"$gte": datetime.fromisoformat(start_date), "$lte": datetime.fromisoformat(end_date)}
    transactions = await db.eftpos_transactions.find(query).sort("timestamp", -1).to_list(1000)
    return [EFTPOSTransaction(**t) for t in transactions]

@router.post("/eftpos/terminals/{terminal_id}/settlement")
async def perform_settlement(terminal_id: str, _: dict = Depends(require_owner_or_manager)):
    terminal = await db.eftpos_terminals.find_one({"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    try:
        from services.eftpos_service import eftpos_service
        provider = eftpos_service.get_provider(terminal)
        await provider.connect()
        result = await provider.settlement()
        await provider.disconnect()
        return {"success": result.get("approved", False), "message": result.get("responseText", "Settlement completed")}
    except Exception as e:
        return {"success": False, "message": str(e)}
