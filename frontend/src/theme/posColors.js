// NUA POS colour tokens — data & semantic layer.
// Source of truth: NUA_POS_DESIGN_TOKENS.md. Chrome tokens (nav, buttons,
// links) live in tailwind.config.js / colors.css as `nua.burgundy` etc；
// this file is for the DATA layer: floor plans, kitchen tickets, order
// states, charts, stock levels, agent activity. Don't use these for chrome,
// and don't use chrome burgundy for any of these — the two layers exist so
// a glance can tell "brand" from "information".

/** Tier 1 — true icon hues. Marks that carry NO text: bars, dots, blocks, washes. */
export const NUA_DATA = {
  orange: '#f58c14',
  purple: '#8b5cf6',
  pink:   '#ec4899',
  ink:    '#1c1917',
};

/** Tier 2 — fills with a label, number or icon on top. `on` is the ink that passes. */
export const NUA_DATA_SOLID = {
  orange: { bg: '#f58c14', on: '#29241E', ratio: 6.33 },
  purple: { bg: '#7c3aed', on: '#FFFFFF', ratio: 5.70 },
  pink:   { bg: '#db2777', on: '#FFFFFF', ratio: 4.60 },
  ink:    { bg: '#1c1917', on: '#FFFFFF', ratio: 17.49 },
};

/** Tier 3 — 1-2px strokes: sparklines, chart lines, thin rules. */
export const NUA_DATA_LINE = {
  orange: '#b45309',
  purple: '#7c3aed',
  pink:   '#be185d',
  ink:    '#29241E',
};

/** The four meanings a POS needs constantly. `ink` = text/icons on a light
 *  surface; `fill` = solid chip background; `on` = text colour on that fill. */
export const NUA_SEMANTIC = {
  success: { ink: '#046C4E', fill: '#047857', on: '#FFFFFF', wash: 'rgba(16,185,129,0.12)', dot: '#059669' },
  warning: { ink: '#8a4a00', fill: '#d97706', on: '#29241E', wash: 'rgba(245,140,20,0.14)', dot: '#d97706' },
  danger:  { ink: '#B01B1B', fill: '#B01B1B', on: '#FFFFFF', wash: 'rgba(176,27,27,0.10)',  dot: '#B01B1B' },
  // Purple always means NUA Agent — not "info", not "primary", not decorative.
  agent:   { ink: '#6d28d9', fill: '#7c3aed', on: '#FFFFFF', wash: 'rgba(139,92,246,0.12)', dot: '#7c3aed' },
};

/** Floor plan / table states. */
export const TABLE_STATE_COLORS = {
  open:     { fill: '#FFFFFF', stroke: '#D9CFC5', ink: '#29241E', label: 'Open' },
  reserved: { fill: '#7c3aed', stroke: '#6d28d9', ink: '#FFFFFF', label: 'Reserved' },
  seated:   { fill: '#1c1917', stroke: '#1c1917', ink: '#FFFFFF', label: 'Seated' },
  vip:      { fill: '#db2777', stroke: '#be185d', ink: '#FFFFFF', label: 'VIP' },
  overdue:  { fill: '#f58c14', stroke: '#b45309', ink: '#29241E', label: 'Overdue' },
};

/** Kitchen display — ticket age escalates by itself, so pair with a visible
 *  timer number; never signal lateness with colour alone. */
export const KDS_COLUMN_COLORS = {
  new:       { accent: '#7c3aed', label: 'New', ageUnderMin: 5 },
  preparing: { accent: '#b45309', label: 'Preparing', ageUnderMin: 10 },
  ready:     { accent: '#047857', label: 'Ready' },
};
export const KDS_AGE_COLORS = {
  fresh:   '#7c3aed', // under 5 min
  aging:   '#b45309', // 5–10 min
  overdue: '#B01B1B', // over 10 min
};

/** Order / payment states. */
export const ORDER_STATE_COLORS = {
  openTab:  { ink: '#750D28', wash: '#F5ECEA', label: 'Open tab' },
  paid:     { fill: '#047857', on: '#FFFFFF', label: 'Paid' },
  partPaid: { fill: '#d97706', on: '#29241E', label: 'Part-paid' },
  refunded: { fill: '#B01B1B', on: '#FFFFFF', strikethrough: true, label: 'Refunded / void' },
  offlineQueued: { ink: '#8a4a00', wash: 'rgba(245,140,20,0.14)', label: 'Offline, queued' },
};

/** Stock levels. */
export const STOCK_LEVEL_COLORS = {
  inStock: '#046C4E',
  low:     '#8a4a00',
  out:     '#B01B1B',
};

/** NUA Agent activity tiers — always purple-family; never reused for non-agent state. */
export const AGENT_TIER_COLORS = {
  executed:         { wash: 'rgba(16,185,129,0.12)', text: '#046C4E', dot: '#059669' },
  approvedPending:  { wash: 'rgba(139,92,246,0.12)', text: '#6d28d9', dot: '#7c3aed' },
  suggested:        { wash: 'rgba(245,140,20,0.14)', text: '#8a4a00', dot: '#d97706' },
};
