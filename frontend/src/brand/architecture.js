/**
 * NUA brand architecture — the naming source of truth.
 *
 * One company, one platform, many industry verticals. Import from here rather
 * than hard-coding product names in UI, so a rename lands in one place.
 *
 * The distinction that matters: these are PRODUCT names. Features inside a
 * product keep plain descriptive names ("Payment Links", "Finance Suite",
 * "Item Library") — promoting a feature to a product name is what makes brand
 * architectures rot.
 */

export const COMPANY = {
  name: 'NUA AUS',
  legalName: 'NUA AUS PTY LTD',
  abn: '54 299 131 653',
};

/** The shared platform every vertical is built on. */
export const PLATFORM = { name: 'NUA OS', tagline: 'Operating system' };

/** The AI agent, consistent across every vertical. */
export const AI = { name: 'NUA AI' };

/**
 * Industry verticals. `status: 'live'` means it ships today; 'planned' names
 * are reserved so nothing else claims them, and so that domain/app naming is
 * decided once rather than improvised per launch.
 */
export const VERTICALS = {
  hospitality:   { name: 'NUA POS',       domain: 'nuapos.com.au', status: 'live' },
  retail:        { name: 'NUA Retail',    status: 'planned' },
  healthcare:    { name: 'NUA Health',    status: 'planned' },
  pharmacy:      { name: 'NUA Pharmacy',  status: 'planned' },
  education:     { name: 'NUA Education', status: 'planned' },
  manufacturing: { name: 'NUA Factory',   status: 'planned' },
  logistics:     { name: 'NUA Logistics', status: 'planned' },
  // The finance INDUSTRY vertical — not the accounting module inside NUA POS,
  // which stays "Finance Suite" precisely so it can't collide with this.
  finance:       { name: 'NUA Finance',   status: 'planned' },
};

/** Cross-vertical services — shared by every industry product. */
export const SERVICES = {
  wallet:   { name: 'NUA Wallet', status: 'live', note: 'Customer-held value: credit, points, vouchers' },
  payments: { name: 'NUA Pay',    status: 'planned', note: 'Payment processing' },
};

/** This build's vertical. Everything below derives from it. */
export const CURRENT_VERTICAL = VERTICALS.hospitality;

/** Product name for titles, manifests and in-product chrome. */
export const PRODUCT_NAME = CURRENT_VERTICAL.name;

/** Long form for meta descriptions and about screens. */
export const PRODUCT_FULL_NAME = `${PRODUCT_NAME} — hospitality on ${PLATFORM.name}`;

export default {
  COMPANY, PLATFORM, AI, VERTICALS, SERVICES,
  CURRENT_VERTICAL, PRODUCT_NAME, PRODUCT_FULL_NAME,
};
