"""Booking Analytics — a real reporting layer over reservations, not just the
handful of numbers get_booking_analytics() in reservation_features.py used to
return. Reuses the existing Reservation data model, the existing floor/table
service, and the existing tenant-scoping helper; adds no new database model.

Data-honesty note (see Item 14 of the audit brief this was built against):
there is no field anywhere linking a Reservation to the Transaction it
generated — POS checks are opened by table number, not by reservation id.
Rather than fabricate a booking-level revenue figure, financial numbers here
are computed two ways and kept clearly labelled:
  - "actual": real data stored on the reservation itself (deposits collected).
  - "estimated": a Transaction on the same table, same calendar date as a
    reservation, only when that table had exactly ONE booking that day (an
    unambiguous match). Two or more bookings sharing a table/day would make
    a per-booking split pure guesswork, so that revenue is bucketed as
    "unknown" instead of being divided up as if it were known.
Every totals block below carries all three figures side by side so nothing
implies more precision than the data actually supports.
"""
from fastapi import APIRouter, Depends, Response
from typing import Optional
from datetime import datetime, date as date_cls, timedelta
from collections import defaultdict
import csv
import io

from database import db
from deps import require_owner_or_manager
from middleware.actor_context import tenant_scope_filter
from services import floor_tables

router = APIRouter(prefix="/booking-analytics")

# Documented assumption used for table utilisation — no operating-hours
# config exists anywhere in NUA today (checked: no field on the business
# settings model), so a fixed service window is the only way to produce a
# utilisation percentage at all. Disclosed in every report's dataNotes
# rather than left as an invisible constant.
ASSUMED_SERVICE_MINUTES_PER_DAY = 720  # 12h/day — e.g. two lunch+dinner seatings

PARTY_SIZE_BUCKETS = [
    ("1", lambda n: n == 1),
    ("2", lambda n: n == 2),
    ("3-4", lambda n: 3 <= n <= 4),
    ("5-6", lambda n: 5 <= n <= 6),
    ("7-10", lambda n: 7 <= n <= 10),
    ("10+", lambda n: n > 10),
]

NON_REVENUE_STATUSES = {"cancelled", "no_show"}


def _parse_date(s: Optional[str], fallback: date_cls) -> date_cls:
    if not s:
        return fallback
    try:
        return date_cls.fromisoformat(s)
    except ValueError:
        return fallback


def _day_name(iso_date: str) -> Optional[str]:
    try:
        return date_cls.fromisoformat(iso_date).strftime("%A")
    except (ValueError, TypeError):
        return None


def _guest_name(r: dict) -> Optional[str]:
    """Some reservations predate the guestName field (see Reservation's own
    _legacy_aliases validator) and only have customerName/name in the raw
    document — this endpoint reads dicts straight from Mongo rather than
    through that model, so it needs the same fallback to avoid showing a
    blank guest name for perfectly real, older bookings."""
    return r.get("guestName") or r.get("customerName") or r.get("name")


def _hour(time_str: str) -> Optional[int]:
    try:
        return int((time_str or "")[:2])
    except ValueError:
        return None


def _pct(numerator: float, denominator: float) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


async def _fetch_reservations(business_id, start: date_cls, end: date_cls, filters: dict):
    query = tenant_scope_filter(business_id)
    query["date"] = {"$gte": start.isoformat(), "$lte": end.isoformat()}
    if filters.get("status"):
        query["status"] = filters["status"]
    if filters.get("source"):
        query["source"] = filters["source"]
    if filters.get("floorPlanId"):
        query["floorPlanId"] = filters["floorPlanId"]
    if filters.get("tableId"):
        query["tableId"] = filters["tableId"]
    if filters.get("section"):
        query["section"] = filters["section"]
    if filters.get("customerId"):
        query["customerId"] = filters["customerId"]
    rows = await db.reservations.find(query, {"_id": 0}).to_list(50000)
    min_p, max_p = filters.get("minPartySize"), filters.get("maxPartySize")
    if min_p is not None:
        rows = [r for r in rows if r.get("partySize", 0) >= min_p]
    if max_p is not None:
        rows = [r for r in rows if r.get("partySize", 0) <= max_p]
    return rows


async def _fetch_transactions_by_table_date(business_id, start: date_cls, end: date_cls):
    """{(tableNumber, 'YYYY-MM-DD'): total_of_all_transactions_that_day}."""
    query = tenant_scope_filter(business_id)
    txns = await db.transactions.find(query, {"_id": 0, "tableNumber": 1, "timestamp": 1, "total": 1, "status": 1}).to_list(200000)
    out = defaultdict(float)
    for t in txns:
        if t.get("status") == "refunded":
            continue
        table = t.get("tableNumber")
        ts = t.get("timestamp")
        if not table or not ts:
            continue
        try:
            d = (ts if isinstance(ts, str) else ts.isoformat())[:10]
        except Exception:
            continue
        if not (start.isoformat() <= d <= end.isoformat()):
            continue
        out[(str(table), d)] += float(t.get("total") or 0)
    return out


def _financials(reservations: list, txn_by_table_date: dict):
    """Returns (actualDeposits, estimatedRevenue, unknownRevenue, per-reservation map)."""
    revenue_relevant = [r for r in reservations if r.get("status") not in NON_REVENUE_STATUSES]

    # How many revenue-relevant bookings share each (table, date) — only a
    # count of 1 is an unambiguous match to that day's transaction total.
    key_counts = defaultdict(int)
    for r in revenue_relevant:
        if r.get("tableNumber"):
            key_counts[(str(r["tableNumber"]), r.get("date"))] += 1

    actual_deposits = sum(r.get("depositRequired", 0) for r in reservations if r.get("depositPaid"))

    per_reservation = {}
    estimated_total = 0.0
    unknown_total = 0.0
    matched_keys_seen = set()
    for r in revenue_relevant:
        key = (str(r.get("tableNumber")), r.get("date")) if r.get("tableNumber") else None
        day_total = txn_by_table_date.get(key, 0.0) if key else 0.0
        if key and key_counts.get(key) == 1 and day_total > 0:
            per_reservation[r["id"]] = {"amount": round(day_total, 2), "confidence": "estimated"}
            if key not in matched_keys_seen:
                estimated_total += day_total
                matched_keys_seen.add(key)
        else:
            per_reservation[r["id"]] = {"amount": None, "confidence": "unknown"}
    # Table/days with 2+ bookings: that day's transaction total genuinely
    # happened, it just can't be safely split — count it once as "unknown"
    # rather than silently dropping it or guessing a split.
    counted_unknown_keys = set()
    for r in revenue_relevant:
        key = (str(r.get("tableNumber")), r.get("date")) if r.get("tableNumber") else None
        if key and key_counts.get(key, 0) > 1 and key not in counted_unknown_keys:
            unknown_total += txn_by_table_date.get(key, 0.0)
            counted_unknown_keys.add(key)

    return round(actual_deposits, 2), round(estimated_total, 2), round(unknown_total, 2), per_reservation


async def _build_report(business_id, filters: dict):
    today = date_cls.today()
    start = _parse_date(filters.get("start"), today - timedelta(days=30))
    end = _parse_date(filters.get("end"), today)
    if end < start:
        start, end = end, start
    days_in_range = max((end - start).days + 1, 1)

    reservations = await _fetch_reservations(business_id, start, end, filters)
    txn_by_table_date = await _fetch_transactions_by_table_date(business_id, start, end)
    actual_deposits, estimated_revenue, unknown_revenue, per_res_revenue = _financials(reservations, txn_by_table_date)

    total = len(reservations)
    revenue_relevant = [r for r in reservations if r.get("status") not in NON_REVENUE_STATUSES]
    covers = sum(r.get("partySize", 0) for r in revenue_relevant)
    no_shows = len([r for r in reservations if r.get("status") == "no_show"])
    cancellations = len([r for r in reservations if r.get("status") == "cancelled"])
    completed_or_seated = [r for r in reservations if r.get("status") in ("completed", "seated")]

    known_revenue_bookings = len([r for r in revenue_relevant if per_res_revenue.get(r["id"], {}).get("amount")])
    avg_spend = round(estimated_revenue / known_revenue_bookings, 2) if known_revenue_bookings else None
    spend_per_guest_covers = sum(r.get("partySize", 0) for r in revenue_relevant
                                  if per_res_revenue.get(r["id"], {}).get("amount"))
    spend_per_guest = round(estimated_revenue / spend_per_guest_covers, 2) if spend_per_guest_covers else None

    # Table utilisation — booked minutes (seated/completed only, real
    # `duration` field) over an assumed service window per table per day.
    tables = await floor_tables.list_tables()
    table_by_number = {str(t.get("number")): t for t in tables}
    minutes_by_table = defaultdict(int)
    covers_by_table = defaultdict(int)
    bookings_by_table = defaultdict(int)
    revenue_by_table = defaultdict(float)
    for r in reservations:
        tn = r.get("tableNumber")
        if not tn:
            continue
        bookings_by_table[tn] += 1
        if r.get("status") in ("completed", "seated"):
            minutes_by_table[tn] += r.get("duration", 90)
            covers_by_table[tn] += r.get("partySize", 0)
        amt = per_res_revenue.get(r["id"], {}).get("amount")
        if amt:
            revenue_by_table[tn] += amt

    table_rows = []
    all_table_numbers = set(bookings_by_table) | set(minutes_by_table)
    for tn in sorted(all_table_numbers, key=str):
        capacity = 0
        meta = table_by_number.get(str(tn))
        if meta:
            capacity = meta.get("maxCovers") or meta.get("capacity") or 0
        possible_minutes = days_in_range * ASSUMED_SERVICE_MINUTES_PER_DAY
        util = _pct(minutes_by_table.get(tn, 0), possible_minutes)
        table_rows.append({
            "table": tn,
            "floor": meta.get("planName") if meta else None,
            "section": meta.get("section") if meta else None,
            "capacity": capacity or None,
            "bookings": bookings_by_table.get(tn, 0),
            "covers": covers_by_table.get(tn, 0),
            "revenueEstimate": round(revenue_by_table.get(tn, 0), 2) or None,
            "avgDurationMinutes": round(minutes_by_table.get(tn, 0) / max(bookings_by_table.get(tn, 1), 1)) if minutes_by_table.get(tn) else None,
            "utilisationPct": util,
        })
    overall_utilisation = _pct(sum(minutes_by_table.values()), len(all_table_numbers) * days_in_range * ASSUMED_SERVICE_MINUTES_PER_DAY) if all_table_numbers else 0.0

    # Channels — grouped by whatever `source` values actually exist in the
    # data, not a hard-coded list, so a new channel added later shows up
    # automatically.
    channel_groups = defaultdict(list)
    for r in reservations:
        channel_groups[r.get("source") or "unknown"].append(r)
    channels = []
    for source, rows in sorted(channel_groups.items(), key=lambda kv: -len(kv[1])):
        c_relevant = [r for r in rows if r.get("status") not in NON_REVENUE_STATUSES]
        c_revenue = sum(per_res_revenue.get(r["id"], {}).get("amount") or 0 for r in c_relevant)
        c_known = len([r for r in c_relevant if per_res_revenue.get(r["id"], {}).get("amount")])
        channels.append({
            "source": source,
            "bookings": len(rows),
            "guests": sum(r.get("partySize", 0) for r in c_relevant),
            "revenueEstimate": round(c_revenue, 2) if c_known else None,
            "avgSpend": round(c_revenue / c_known, 2) if c_known else None,
            "avgPartySize": round(sum(r.get("partySize", 0) for r in rows) / len(rows), 1) if rows else 0,
            "noShowRate": _pct(len([r for r in rows if r.get("status") == "no_show"]), len(rows)),
            "cancellationRate": _pct(len([r for r in rows if r.get("status") == "cancelled"]), len(rows)),
        })

    # Day-of-week
    by_day = defaultdict(lambda: {"bookings": 0, "covers": 0})
    for r in reservations:
        dn = _day_name(r.get("date", ""))
        if dn:
            by_day[dn]["bookings"] += 1
            by_day[dn]["covers"] += r.get("partySize", 0)
    week_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_of_week = [{"day": d, **by_day.get(d, {"bookings": 0, "covers": 0})} for d in week_order]

    # Hour-of-day
    by_hour = defaultdict(int)
    for r in reservations:
        h = _hour(r.get("time", ""))
        if h is not None:
            by_hour[h] += 1
    hour_of_day = [{"hour": h, "bookings": by_hour.get(h, 0)} for h in range(24)]
    peak_hours = sorted(by_hour.items(), key=lambda kv: -kv[1])[:3]
    quiet_hours = sorted(((h, c) for h, c in by_hour.items() if c > 0), key=lambda kv: kv[1])[:3]

    # Party size buckets
    party_buckets = []
    for label, pred in PARTY_SIZE_BUCKETS:
        rows = [r for r in reservations if pred(r.get("partySize", 0))]
        party_buckets.append({
            "bucket": label,
            "bookings": len(rows),
            "guests": sum(r.get("partySize", 0) for r in rows),
        })

    # Customer behaviour — "new" means this is the earliest reservation on
    # record for that customerId across ALL time, not just this range; best
    # effort, since it depends entirely on customerId being set.
    customer_ids = {r["customerId"] for r in reservations if r.get("customerId")}
    new_count = returning_count = 0
    if customer_ids:
        all_for_customers = await db.reservations.find(
            {"customerId": {"$in": list(customer_ids)}, **tenant_scope_filter(business_id)},
            {"_id": 0, "customerId": 1, "date": 1}
        ).to_list(200000)
        earliest = {}
        for r in all_for_customers:
            cid = r.get("customerId")
            d = r.get("date", "")
            if cid and (cid not in earliest or d < earliest[cid]):
                earliest[cid] = d
        counted = set()
        for r in reservations:
            cid = r.get("customerId")
            if not cid or cid in counted:
                continue
            counted.add(cid)
            if earliest.get(cid) and earliest[cid] >= start.isoformat():
                new_count += 1
            else:
                returning_count += 1
    unattributed_bookings = len([r for r in reservations if not r.get("customerId")])

    detailed = []
    for r in reservations:
        rev = per_res_revenue.get(r["id"], {})
        detailed.append({
            "id": r["id"], "guestName": _guest_name(r), "date": r.get("date"), "time": r.get("time"),
            "status": r.get("status"), "source": r.get("source"), "partySize": r.get("partySize"),
            "tableNumber": r.get("tableNumber"), "section": r.get("section"), "duration": r.get("duration"),
            "customerId": r.get("customerId"), "createdAt": r.get("createdAt"),
            "revenueEstimate": rev.get("amount"), "revenueConfidence": rev.get("confidence"),
            "notes": r.get("notes"),
        })

    data_notes = [
        "Revenue has no direct link between a booking and a POS transaction in NUA today — checks are opened by "
        "table number, not by reservation id. \"Estimated\" revenue below is a same-table, same-day transaction "
        "match, used only when exactly one booking occupied that table that day. When two or more bookings shared "
        "a table on the same day, that day's revenue is real but cannot be safely split between them — it is "
        "counted once under \"unknown\" rather than divided up as a guess.",
        "\"Actual\" revenue is deposits collected — the one booking-level financial figure stored directly on the "
        "reservation record.",
        f"Table utilisation assumes a {ASSUMED_SERVICE_MINUTES_PER_DAY // 60}-hour service window per table per "
        "day (no operating-hours configuration exists in NUA to derive this from) — booked minutes come from each "
        "booking's real `duration` field on seated/completed bookings only.",
        "New vs returning customers only covers bookings with a customerId attached" +
        (f" ({unattributed_bookings} of {total} booking(s) in range had none)." if unattributed_bookings else "."),
    ]

    return {
        "meta": {
            "start": start.isoformat(), "end": end.isoformat(), "daysInRange": days_in_range,
            "generatedAt": datetime.utcnow().isoformat(), "filtersApplied": {k: v for k, v in filters.items() if v not in (None, "")},
        },
        "kpis": {
            "bookings": total, "covers": covers,
            "revenueActual": actual_deposits, "revenueEstimated": estimated_revenue, "revenueUnknown": unknown_revenue,
            "avgSpend": avg_spend, "spendPerGuest": spend_per_guest,
            "noShowRate": _pct(no_shows, total), "cancellationRate": _pct(cancellations, total),
            "tableUtilisationPct": overall_utilisation,
            "completedBookings": len(completed_or_seated),
        },
        "channels": channels,
        "dayOfWeek": day_of_week,
        "hourOfDay": hour_of_day,
        "peakHours": [{"hour": h, "bookings": c} for h, c in peak_hours],
        "quietHours": [{"hour": h, "bookings": c} for h, c in quiet_hours],
        "partySizeBuckets": party_buckets,
        "tables": table_rows,
        "customers": {
            "new": new_count, "returning": returning_count, "unattributedBookings": unattributed_bookings,
        },
        "detailed": detailed,
        "dataNotes": data_notes,
    }


def _filters_from_params(start, end, status, source, floorPlanId, tableId, section,
                          minPartySize, maxPartySize, customerId):
    return {
        "start": start, "end": end, "status": status, "source": source,
        "floorPlanId": floorPlanId, "tableId": tableId, "section": section,
        "minPartySize": minPartySize, "maxPartySize": maxPartySize, "customerId": customerId,
    }


# NUA brand orange (matches frontend/src/contexts/ThemeContext.jsx's default
# theme.primary) — used for section headers so the PDF reads as NUA-branded
# without embedding a logo image, which the minimal PDF-1.4 assembler below
# (same technique as finalize.py's _pdf_from_lines, reused rather than
# adding reportlab/weasyprint as a new dependency) doesn't support.
_NUA_ORANGE = (0.961, 0.549, 0.078)  # #f58c14


def _build_report_pdf(report: dict, business_name: str) -> bytes:
    """NUA-branded PDF for a booking report — a real layout with sections,
    not a screenshot of the dashboard. Charts stay on-screen (Recharts-free
    SVG bars already exist there); this is the detailed data + methodology
    companion, per the report's own dataNotes on what is actual vs
    estimated vs unknown.
    """
    TOP_Y = 800
    BOTTOM_MARGIN = 50
    pages: list = [[]]
    y = TOP_Y

    def esc(text):
        return (str(text) if text is not None else "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def add(text, size=10, color=None, gap=None):
        nonlocal y
        if y < BOTTOM_MARGIN:
            pages.append([])
            y = TOP_Y
        ops = []
        if color:
            ops.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
        ops.append(f"BT /F1 {size} Tf 40 {y} Td ({esc(text)}) Tj ET")
        if color:
            ops.append("0 0 0 rg")
        pages[-1].append(" ".join(ops))
        y -= gap if gap is not None else size + 5

    def heading(text):
        nonlocal y
        y -= 8
        add(text, size=14, color=_NUA_ORANGE, gap=20)

    def row(cols, widths, size=9):
        nonlocal y
        if y < BOTTOM_MARGIN:
            pages.append([])
            y = TOP_Y
        x = 40
        parts = []
        for col, w in zip(cols, widths):
            parts.append(f"BT /F1 {size} Tf {x} {y} Td ({esc(col)}) Tj ET")
            x += w
        pages[-1].append(" ".join(parts))
        y -= size + 4

    meta, kpis = report["meta"], report["kpis"]
    add(business_name or "NUA POS", size=20, color=_NUA_ORANGE, gap=26)
    add("Booking Analytics Report", size=13, gap=18)
    add(f"Reporting period: {meta['start']} to {meta['end']} ({meta['daysInRange']} day(s))", size=10)
    add(f"Generated: {meta['generatedAt'][:19].replace('T', ' ')} UTC", size=9)
    if meta.get("filtersApplied"):
        add(f"Filters: {meta['filtersApplied']}", size=9)

    heading("Executive Summary")
    add(f"Total bookings: {kpis['bookings']}    Total covers: {kpis['covers']}    Completed: {kpis['completedBookings']}")
    add(f"No-show rate: {kpis['noShowRate']}%    Cancellation rate: {kpis['cancellationRate']}%    Table utilisation: {kpis['tableUtilisationPct']}%")

    heading("Revenue (see Methodology for what each figure means)")
    add(f"Actual (deposits collected): ${kpis['revenueActual']:.2f}")
    add(f"Estimated (matched transactions): ${kpis['revenueEstimated']:.2f}"
        + (f"  |  Avg spend: ${kpis['avgSpend']:.2f}  |  Spend/guest: ${kpis['spendPerGuest']:.2f}" if kpis.get("avgSpend") else ""))
    add(f"Unknown (ambiguous table/day matches): ${kpis['revenueUnknown']:.2f}")

    heading("Channel Performance")
    row(["Source", "Bookings", "Guests", "Revenue Est.", "Avg Spend", "No-show %", "Cancel %"],
        [90, 60, 55, 70, 65, 65, 60], size=8)
    for c in report["channels"]:
        row([c["source"], c["bookings"], c["guests"],
             f"${c['revenueEstimate']:.2f}" if c["revenueEstimate"] else "—",
             f"${c['avgSpend']:.2f}" if c["avgSpend"] else "—",
             f"{c['noShowRate']}%", f"{c['cancellationRate']}%"],
            [90, 60, 55, 70, 65, 65, 60])

    heading("Time Analysis")
    add("By day of week:")
    for d in report["dayOfWeek"]:
        if d["bookings"]:
            add(f"  {d['day']}: {d['bookings']} bookings, {d['covers']} covers", size=9)
    if report["peakHours"]:
        add("Peak hours: " + ", ".join(f"{h['hour']:02d}:00 ({h['bookings']})" for h in report["peakHours"]))
    if report["quietHours"]:
        add("Quiet hours: " + ", ".join(f"{h['hour']:02d}:00 ({h['bookings']})" for h in report["quietHours"]))
    add("By party size:")
    for b in report["partySizeBuckets"]:
        if b["bookings"]:
            add(f"  {b['bucket']} guests: {b['bookings']} bookings, {b['guests']} total guests", size=9)

    heading("Table Performance")
    row(["Table", "Floor", "Bookings", "Covers", "Revenue Est.", "Avg Duration", "Utilisation"],
        [50, 90, 60, 55, 70, 75, 60], size=8)
    for t in report["tables"]:
        row([t["table"], t.get("floor") or "—", t["bookings"], t["covers"],
             f"${t['revenueEstimate']:.2f}" if t["revenueEstimate"] else "—",
             f"{t['avgDurationMinutes']}m" if t["avgDurationMinutes"] else "—",
             f"{t['utilisationPct']}%"],
            [50, 90, 60, 55, 70, 75, 60])

    heading("Guest Behaviour")
    cust = report["customers"]
    add(f"New customers: {cust['new']}    Returning customers: {cust['returning']}")
    if cust["unattributedBookings"]:
        add(f"Bookings without a linked customer profile: {cust['unattributedBookings']}", size=9)

    heading("Booking Status Breakdown")
    status_counts = defaultdict(int)
    for d in report["detailed"]:
        status_counts[d["status"]] += 1
    for s, c in sorted(status_counts.items(), key=lambda kv: -kv[1]):
        add(f"  {s}: {c}", size=9)

    heading(f"Detailed Bookings ({len(report['detailed'])})")
    row(["Guest", "Date", "Time", "Status", "Source", "Party", "Table", "Revenue"],
        [95, 60, 40, 55, 55, 35, 40, 55], size=8)
    for d in report["detailed"]:
        row([d["guestName"] or "—", d["date"], d["time"], d["status"], d["source"] or "—",
             d["partySize"], d["tableNumber"] or "—",
             f"${d['revenueEstimate']:.2f}" if d["revenueEstimate"] else "—"],
            [95, 60, 40, 55, 55, 35, 40, 55])

    heading("Methodology & Data Notes")
    for note in report["dataNotes"]:
        add(note, size=8, gap=11)
        y -= 4

    header_bytes = b"%PDF-1.4\n"
    n_pages = len(pages)
    page_obj_nums = [3 + 2 * i for i in range(n_pages)]
    font_obj_num = 3 + 2 * n_pages
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objs.append(f"<< /Type /Pages /Count {n_pages} /Kids [{kids}] >>".encode())
    for i, page_lines in enumerate(pages):
        stream_body = "\n".join(page_lines).encode("latin-1", errors="ignore")
        content_obj_num = page_obj_nums[i] + 1
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_obj_num} 0 R "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> >>".encode()
        )
        objs.append(f"<< /Length {len(stream_body)} >>\nstream\n".encode() + stream_body + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    body = bytearray()
    body += header_bytes
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(body))
        body += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_off = len(body)
    body += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        body += f"{off:010d} 00000 n \n".encode()
    body += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_off}\n%%EOF".encode()
    return bytes(body)


@router.get("/report")
async def get_booking_analytics_report(
    start: Optional[str] = None, end: Optional[str] = None,
    status: Optional[str] = None, source: Optional[str] = None,
    floorPlanId: Optional[str] = None, tableId: Optional[str] = None, section: Optional[str] = None,
    minPartySize: Optional[int] = None, maxPartySize: Optional[int] = None, customerId: Optional[str] = None,
    user: dict = Depends(require_owner_or_manager),
):
    filters = _filters_from_params(start, end, status, source, floorPlanId, tableId, section,
                                    minPartySize, maxPartySize, customerId)
    return await _build_report(user.get("businessId"), filters)


@router.get("/report.csv")
async def get_booking_analytics_report_csv(
    start: Optional[str] = None, end: Optional[str] = None,
    status: Optional[str] = None, source: Optional[str] = None,
    floorPlanId: Optional[str] = None, tableId: Optional[str] = None, section: Optional[str] = None,
    minPartySize: Optional[int] = None, maxPartySize: Optional[int] = None, customerId: Optional[str] = None,
    user: dict = Depends(require_owner_or_manager),
):
    filters = _filters_from_params(start, end, status, source, floorPlanId, tableId, section,
                                    minPartySize, maxPartySize, customerId)
    report = await _build_report(user.get("businessId"), filters)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Booking ID", "Guest", "Date", "Time", "Status", "Source", "Party Size",
                      "Table", "Section", "Duration (min)", "Revenue Estimate", "Revenue Confidence", "Notes"])
    for row in report["detailed"]:
        writer.writerow([row["id"], row["guestName"], row["date"], row["time"], row["status"], row["source"],
                          row["partySize"], row["tableNumber"], row["section"], row["duration"],
                          row["revenueEstimate"], row["revenueConfidence"], row.get("notes")])

    range_label = f"{report['meta']['start']}_to_{report['meta']['end']}"
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="booking-report-{range_label}.csv"'})


@router.get("/report.pdf")
async def get_booking_analytics_report_pdf(
    start: Optional[str] = None, end: Optional[str] = None,
    status: Optional[str] = None, source: Optional[str] = None,
    floorPlanId: Optional[str] = None, tableId: Optional[str] = None, section: Optional[str] = None,
    minPartySize: Optional[int] = None, maxPartySize: Optional[int] = None, customerId: Optional[str] = None,
    user: dict = Depends(require_owner_or_manager),
):
    filters = _filters_from_params(start, end, status, source, floorPlanId, tableId, section,
                                    minPartySize, maxPartySize, customerId)
    report = await _build_report(user.get("businessId"), filters)
    business = await db.businesses.find_one({"id": user.get("businessId")}, {"_id": 0, "name": 1})
    pdf = _build_report_pdf(report, (business or {}).get("name") or "NUA POS")

    range_label = f"{report['meta']['start']}_to_{report['meta']['end']}"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="booking-report-{range_label}.pdf"'})
