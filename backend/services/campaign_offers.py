"""Redeemable offers for marketing campaigns.

A campaign that just says "15% off this week" is unredeemable and
unmeasurable — the guest has nothing to present and the venue can't tell
which sale came from which campaign. This issues each recipient their own
voucher off the existing Universal Voucher Engine, so the same offer is
simultaneously:

  * a short CODE the guest can read out or the cashier can type,
  * a QR/barcode the POS camera can scan (the engine's signed qrPayload),
  * an entry in that guest's wallet, because engine vouchers carry
    customerId and the wallet reads by customerId.

One voucher per recipient (not one shared code) so redemptions attribute to
a person, single-use limits actually hold, and a leaked code can be revoked
without killing the whole campaign.
"""
import base64
import io
import logging
from typing import Optional

log = logging.getLogger("campaign_offers")

# Keep QR small enough to inline in an email without bloating it.
QR_BOX_SIZE = 6
QR_BORDER = 2


def qr_data_uri(payload: str) -> Optional[str]:
    """PNG data-URI for a voucher's QR. Emails can't run JS, so the code has
    to arrive as an image. Returns None if QR rendering isn't available —
    the code text is always present as a fallback, so a missing image
    degrades the email rather than breaking the campaign."""
    try:
        import qrcode
        img = qrcode.make(payload, box_size=QR_BOX_SIZE, border=QR_BORDER)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log.warning("qr-render-failed: %s", e)
        return None


async def issue_campaign_voucher(customer: dict, campaign: dict) -> Optional[dict]:
    """Issue one campaign voucher for one customer, linked both ways."""
    from routes.commerce_v29 import _issue_voucher
    offer = campaign.get("offer") or {}
    try:
        return await _issue_voucher({
            "sourceType": "campaign",
            "sourceRef": campaign.get("id"),
            "label": offer.get("label") or campaign.get("emailSubject") or "Campaign offer",
            "description": offer.get("description"),
            "valueType": offer.get("valueType", "percentage"),
            "value": float(offer.get("value") or 15),
            "usageType": "one_time",
            "maxRedemptions": 1,
            "customerId": customer.get("id"),
            "codePrefix": offer.get("codePrefix", "NUA"),
            "expiresAt": offer.get("expiresAt"),
            "metadata": {"campaignId": campaign.get("id"), "audience": campaign.get("audience")},
        })
    except Exception as e:
        log.warning("campaign-voucher-failed for %s: %s", customer.get("id"), e)
        return None


def render_offer_email(customer: dict, campaign: dict, voucher: dict) -> str:
    """Campaign body + the guest's personal code and scannable QR."""
    body = campaign.get("emailBody") or ""
    code = voucher.get("code", "")
    qr = qr_data_uri(voucher.get("qrPayload") or code)
    value = voucher.get("value")
    value_txt = (f"{value:g}% off" if voucher.get("valueType") == "percentage"
                 else f"${value:g} off") if value else "your offer"
    qr_block = (f'<img src="{qr}" alt="Scan at the counter" '
                f'style="width:160px;height:160px;display:block;margin:12px auto" />') if qr else ""
    expiry = voucher.get("expiresAt")
    expiry_txt = f'<p style="color:#888;font-size:12px">Valid until {str(expiry)[:10]}</p>' if expiry else ""
    return f"""<div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto">
  <p>Hi {customer.get('name', 'there')},</p>
  <p>{body}</p>
  <div style="border:2px dashed #f58c14;border-radius:12px;padding:16px;text-align:center;margin:20px 0">
    <p style="margin:0;font-size:13px;color:#666;text-transform:uppercase;letter-spacing:1px">{value_txt}</p>
    <p style="margin:6px 0;font-size:26px;font-weight:700;letter-spacing:3px">{code}</p>
    {qr_block}
    <p style="margin:0;font-size:12px;color:#666">Show this code or scan at the counter.</p>
    {expiry_txt}
  </div>
  <p style="color:#888;font-size:12px">It's also saved in your NUA wallet.</p>
</div>"""
