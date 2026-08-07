"""ENTITY_TYPE_TO_COLLECTION (routes/audit.py) is a manually maintained map
from the entity_type string a stamped_insert/stamped_update call declares
to the real Mongo collection it writes into — that's what let the audit
restore UI work with no ?collection= param for the common cases. It's
hand-maintained, which means it silently regresses the moment someone
adds a new stamped entity_type and forgets to add the matching map entry
— exactly the class of bug the map itself was built to fix (see
test_audit_restore.py). This scans the actual call sites so that
regression can't sneak back in unnoticed.
"""
import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CALL_PATTERN = re.compile(
    r'stamped_(?:insert|update)\s*\([^)]*?entity_type\s*=\s*"([a-z_]+)"',
    re.DOTALL,
)


def _stamped_entity_types() -> set:
    found = set()
    for py_file in (BACKEND_ROOT / "routes").glob("*.py"):
        text = py_file.read_text()
        found.update(CALL_PATTERN.findall(text))
    for py_file in (BACKEND_ROOT / "services").glob("*.py"):
        text = py_file.read_text()
        found.update(CALL_PATTERN.findall(text))
    return found


def test_every_stamped_entity_type_has_a_collection_map_entry():
    from routes.audit import ENTITY_TYPE_TO_COLLECTION

    stamped_types = _stamped_entity_types()
    assert stamped_types, "the scan itself found nothing — the regex probably broke, not that there's nothing stamped"

    missing = sorted(t for t in stamped_types if t not in ENTITY_TYPE_TO_COLLECTION)
    assert not missing, (
        f"entity_type(s) {missing} are used in a stamped_insert/stamped_update call "
        f"but have no ENTITY_TYPE_TO_COLLECTION entry in routes/audit.py — restoring "
        f"a version of one of these would 400 with 'pass ?collection= explicitly' "
        f"instead of the generic restore button just working. Add the mapping."
    )
