"""Render a station docket as ESC/POS bytes and push it to a thermal printer.

The docket *content* has been right for a while; the transport was a browser
print dialog, which is fine for a demo and useless on a service line. This
turns a queued print job into the byte stream an 80mm thermal printer actually
speaks, and sends it over the network (ESC/POS raw, port 9100 — what Epson
TM-series, Star and most clones expose).

Kept deliberately dependency-free: ESC/POS is a handful of control codes, and
adding a driver library for this would be more surface than the codes are.

Printers that aren't reachable fall back to the browser path — a station
without a configured IP still prints the way it does today.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

ESC = b"\x1b"
GS = b"\x1d"

INIT = ESC + b"@"
BOLD_ON = ESC + b"E\x01"
BOLD_OFF = ESC + b"E\x00"
ALIGN_LEFT = ESC + b"a\x00"
ALIGN_CENTER = ESC + b"a\x01"
# GS ! n — width in the high nibble, height in the low nibble.
SIZE_NORMAL = GS + b"!\x00"
SIZE_DOUBLE = GS + b"!\x11"
SIZE_TALL = GS + b"!\x01"
CUT = GS + b"V\x42\x00"        # partial cut, feed first
FEED_3 = b"\n\n\n"

DEFAULT_PORT = 9100
DEFAULT_WIDTH = 48             # characters per line at font A on 80mm


def _line(char: str = "-", width: int = DEFAULT_WIDTH) -> bytes:
    return (char * width).encode("cp437", "replace") + b"\n"


def _text(s: str) -> bytes:
    # cp437 is the default codepage on virtually every thermal printer.
    # Anything outside it (— … é) is replaced rather than corrupting the stream.
    return str(s).encode("cp437", "replace")


def _wrap(text: str, width: int, indent: int = 0) -> List[str]:
    words, lines, cur = str(text).split(), [], ""
    pad = " " * indent
    for w in words:
        candidate = f"{cur} {w}".strip()
        if len(candidate) + (indent if lines else 0) > width:
            lines.append((pad if lines else "") + cur)
            cur = w
        else:
            cur = candidate
    if cur:
        lines.append((pad if lines else "") + cur)
    return lines or [""]


def _station_label(printer: str) -> str:
    import re
    return re.sub(r"\s*(printer|station)\s*$", "", str(printer or ""),
                  flags=re.IGNORECASE).strip().upper() or "KITCHEN"


def render(job: Dict[str, Any], width: int = DEFAULT_WIDTH) -> bytes:
    """A print job -> ESC/POS byte stream, mirroring the on-screen docket."""
    out = bytearray()
    out += INIT

    # Station banner — the biggest thing on the ticket, because a cook reads
    # it from arm's length across a hot line.
    out += ALIGN_CENTER + SIZE_DOUBLE + BOLD_ON
    out += _text(_station_label(job.get("printer"))) + b"\n"
    out += BOLD_OFF + SIZE_NORMAL

    if job.get("voidDocket"):
        out += SIZE_TALL + BOLD_ON + _text("*** VOID ***") + b"\n" + BOLD_OFF + SIZE_NORMAL
    elif job.get("courseLabel"):
        out += SIZE_TALL + BOLD_ON + _text(f"FIRE: {job['courseLabel']}") + b"\n"
        out += BOLD_OFF + SIZE_NORMAL

    out += ALIGN_LEFT + _line("=", width)
    table = job.get("tableNumber")
    header = f"TABLE {table}" if table else str(job.get("orderId") or "")
    out += BOLD_ON + _text(header.ljust(width - 6)) + _text(f"P{job.get('priority', 2)}") + b"\n" + BOLD_OFF
    if table and job.get("orderId"):
        out += _text(str(job["orderId"])) + b"\n"
    out += _line("=", width)

    # Own section first — that's what this station cooks.
    sections = job.get("orderSections") or [{"printer": job.get("printer"), "items": job.get("items") or []}]
    own = _station_label(job.get("printer"))
    own_items = next((s["items"] for s in sections if _station_label(s.get("printer")) == own),
                     job.get("items") or [])
    out += _render_items(own_items, width, dim=False)

    others = [s for s in sections if _station_label(s.get("printer")) != own]
    if others:
        out += _line("-", width)
        out += ALIGN_CENTER + _text("- ALSO ON THIS ORDER -") + b"\n" + ALIGN_LEFT
        for s in others:
            out += BOLD_ON + _text(_station_label(s.get("printer"))) + b"\n" + BOLD_OFF
            out += _render_items(s.get("items") or [], width, dim=True)

    stations = job.get("orderStations") or [job.get("printer")]
    out += _line("-", width)
    out += _text("SECTIONS: ") + _text(" | ".join(_station_label(p) for p in stations)) + b"\n"

    out += FEED_3 + CUT
    return bytes(out)


def _render_items(items: List[dict], width: int, dim: bool) -> bytes:
    out = bytearray()
    # Course above category, same order as the screen docket.
    by_course: Dict[Any, List[dict]] = {}
    for it in items or []:
        by_course.setdefault(it.get("course"), []).append(it)
    ordered = sorted(by_course.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))

    for course, rows in ordered:
        if course is not None and len(ordered) > 1:
            label = rows[0].get("courseLabel") or f"COURSE {course}"
            out += BOLD_ON + _text(f"-- {str(label).upper()} --") + b"\n" + BOLD_OFF
        seen_cat = None
        for it in rows:
            cat = (it.get("category") or "Other").upper()
            if cat != seen_cat:
                seen_cat = cat
                out += _text(cat) + b"\n"
            qty = f"{it.get('quantity', 1)}x "
            seat = f"[S{it['seat']}] " if it.get("seat") else ""
            name = f"{seat}{it.get('productName') or it.get('name') or ''}"
            lines = _wrap(name, width - len(qty))
            if not dim:
                out += BOLD_ON
            out += _text(qty + lines[0]) + b"\n"
            for extra in lines[1:]:
                out += _text(" " * len(qty) + extra) + b"\n"
            if not dim:
                out += BOLD_OFF
            if it.get("notes"):
                for nl in _wrap(f"> {it['notes']}", width - 2):
                    out += _text("  " + nl) + b"\n"
    return bytes(out)


async def send(host: str, payload: bytes, port: int = DEFAULT_PORT,
               timeout: float = 5.0) -> Dict[str, Any]:
    """Push bytes to a network thermal printer (raw ESC/POS, usually :9100)."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout)
    except (OSError, asyncio.TimeoutError) as e:
        return {"ok": False, "error": f"could not reach {host}:{port} — {e}"}
    try:
        writer.write(payload)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        return {"ok": True, "bytes": len(payload), "host": host, "port": port}
    except (OSError, asyncio.TimeoutError) as e:
        return {"ok": False, "error": f"write failed to {host}:{port} — {e}"}
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=timeout)
        except (OSError, asyncio.TimeoutError):
            pass


async def printer_target(printer_name: str) -> Optional[Dict[str, Any]]:
    """Look up a configured network address for a station printer."""
    from database import db
    row = await db.printer_targets.find_one({"printer": printer_name}, {"_id": 0})
    if row and row.get("host"):
        return row
    return None
