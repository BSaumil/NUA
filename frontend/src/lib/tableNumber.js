/**
 * Typed-table matching for POS dine-in.
 *
 * Mirrors `backend/services/floor_tables.py` exactly — if the two drift, the
 * POS will accept a table the server then rejects (or worse, the reverse), so
 * keep `normalizeTableNumber` in step with `normalize_table_number` there.
 */

// Leading words people type before the actual identifier: "Table 12", "t12".
const PREFIX_RE = /^(?:table|tbl|tab|t)?\s*[#\-.]?\s*/i;

/** Fold a typed table reference to a comparable key. "Table 12" -> "12". */
export function normalizeTableNumber(raw) {
  const s = String(raw ?? '').trim();
  if (!s) return '';
  return s.replace(PREFIX_RE, '').replace(/[\s\-_.#]+/g, '').toUpperCase();
}

/** Find the configured table a typed value refers to, or null. */
export function findTable(raw, tables) {
  const key = normalizeTableNumber(raw);
  if (!key) return null;
  return (tables || []).find(t =>
    normalizeTableNumber(t.number) === key ||
    (t.name && normalizeTableNumber(t.name) === key)
  ) || null;
}

/**
 * Validate a typed table against the floor plan.
 *
 * `configured` false means the venue has drawn no floor plan, so free text is
 * legitimate and we must not block the sale — a POS that refuses to ring up an
 * order because setup is incomplete is worse than one that trusts the typing.
 */
export function validateTable(raw, tables, configured) {
  const trimmed = String(raw ?? '').trim();
  if (!trimmed) return { status: 'empty', table: null, message: '' };
  if (!configured) return { status: 'unchecked', table: null, message: '' };
  const table = findTable(trimmed, tables);
  if (table) return { status: 'ok', table, message: '' };
  return {
    status: 'unknown',
    table: null,
    message: `Table "${trimmed}" is not on the floor plan`,
  };
}

/** Nearby table numbers to offer when a typed one doesn't exist. */
export function suggestTables(raw, tables, limit = 6) {
  const key = normalizeTableNumber(raw);
  const numbers = (tables || []).map(t => String(t.number ?? '')).filter(Boolean);
  if (!key) return numbers.slice(0, limit);
  const starts = numbers.filter(n => normalizeTableNumber(n).startsWith(key));
  const contains = numbers.filter(n => normalizeTableNumber(n).includes(key) && !starts.includes(n));
  const hits = [...starts, ...contains].slice(0, limit);
  return hits.length ? hits : numbers.slice(0, limit);
}
