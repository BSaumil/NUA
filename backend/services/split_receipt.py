"""Digital receipt for a guest's own share of a split bill.

Fires right after services/bill_split.mark_lines_paid records a guest's
payment — reuses the same SendGrid/Twilio abstraction
(utils/notifications.py) every other guest-facing message in this codebase
goes through, so it's a no-op-but-logged send in a sandbox with no
provider keys configured, exactly like OTP delivery.
"""
from __future__ import annotations
from typing import List, Optional

from utils.notifications import send_email, send_sms


def _paid_items_and_amount(split: dict, line_ids: Optional[List[str]], slot_index: Optional[int]) -> tuple:
    if slot_index is not None:
        slot = next((p for p in split.get("equalParts") or [] if p["index"] == slot_index), None)
        if not slot:
            return [], 0.0
        label = "Equal share" if split.get("mode") == "equal" else "Custom share"
        return [(label, slot["amount"])], slot["amount"]

    lines = [l for l in split.get("lines") or [] if l["id"] in (line_ids or [])]
    amount = round(sum(l["unitPrice"] for l in lines), 2)
    return [(l["productName"], l["unitPrice"]) for l in lines], amount


def _receipt_text(split: dict, items: list, amount: float, transaction_id: str) -> str:
    lines = [f"Table {split['tableNumber']} — payment receipt", ""]
    for name, price in items:
        lines.append(f"  {name} — ${price:.2f}")
    lines.append("")
    lines.append(f"Total paid: ${amount:.2f}")
    lines.append(f"Reference: {transaction_id}")
    return "\n".join(lines)


def _receipt_html(split: dict, items: list, amount: float, transaction_id: str) -> str:
    rows = "".join(
        f"<tr><td style='padding:4px 8px'>{name}</td>"
        f"<td style='padding:4px 8px;text-align:right'>${price:.2f}</td></tr>"
        for name, price in items
    )
    return f"""
    <div style="font-family:sans-serif;max-width:420px">
      <h2 style="margin-bottom:4px">Table {split['tableNumber']} — Receipt</h2>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
      <p style="font-weight:bold;margin-top:12px">Total paid: ${amount:.2f}</p>
      <p style="color:#999;font-size:12px">Reference: {transaction_id}</p>
    </div>
    """


async def send_payment_receipt(split: dict, line_ids: Optional[List[str]], slot_index: Optional[int],
                                 transaction_id: str, guest_email: Optional[str] = None) -> dict:
    """Send the paying guest an itemized receipt for exactly what they
    covered — not the whole table's bill. Phone always gets an SMS (a
    verified phone is the one identity guaranteed to exist here); email is
    best-effort and only sent if the guest supplied one at checkout."""
    items, amount = _paid_items_and_amount(split, line_ids, slot_index)
    if not items:
        return {"sent": False, "reason": "no_items"}

    phone = None
    for l in split.get("lines") or []:
        if l["id"] in (line_ids or []) and l.get("claimedByPhone"):
            phone = l["claimedByPhone"]
            break
    if phone is None and slot_index is not None:
        slot = next((p for p in split.get("equalParts") or [] if p["index"] == slot_index), None)
        phone = (slot or {}).get("claimedByPhone")

    receipts = []
    if phone:
        receipts.append(await send_sms(phone, _receipt_text(split, items, amount, transaction_id)[:320]))
    if guest_email:
        receipts.append(await send_email(
            guest_email, f"Your receipt — Table {split['tableNumber']}",
            _receipt_html(split, items, amount, transaction_id),
        ))
    return {"sent": True, "amount": amount, "receipts": receipts}
