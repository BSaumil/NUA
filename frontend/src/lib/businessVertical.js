// Coarse "which kind of NUA is this" bucket, derived from the free-text
// business.type field set at business creation/edit. Restaurant-flavored
// types (restaurant/cafe/bar/catering) plus anything unset or unrecognized
// — nearly every business created before this field mattered — all fall
// back to 'hospitality', so no existing deployment's nav changes by
// surprise the moment this ships.
export const BUSINESS_TYPE_OPTIONS = [
  { value: 'restaurant', label: 'Restaurant', vertical: 'hospitality' },
  { value: 'cafe', label: 'Cafe', vertical: 'hospitality' },
  { value: 'bar', label: 'Bar', vertical: 'hospitality' },
  { value: 'catering', label: 'Catering', vertical: 'hospitality' },
  { value: 'retail', label: 'Retail Store', vertical: 'retail' },
  { value: 'salon', label: 'Salon & Beauty', vertical: 'beauty' },
  { value: 'services', label: 'Professional Services', vertical: 'services' },
];

const VERTICAL_BY_TYPE = Object.fromEntries(BUSINESS_TYPE_OPTIONS.map(o => [o.value, o.vertical]));

export function getVertical(type) {
  return VERTICAL_BY_TYPE[type] || 'hospitality';
}

export const VERTICAL_LABELS = {
  hospitality: 'Hospitality',
  retail: 'Retail',
  beauty: 'Beauty & Wellness',
  services: 'Professional Services',
};

// What the product-catalog nav entry calls itself per vertical — a
// restaurant has a "Menu," a retail shop has "Products," a salon has
// "Services." Same underlying item-library page in every case (Phase 2/4
// give retail and beauty/services their own real catalog features).
export const MENU_LABELS = {
  hospitality: { group: 'Menu & Items', itemLabel: 'Item Library' },
  retail: { group: 'Products & Stock', itemLabel: 'Product Library' },
  beauty: { group: 'Services & Catalog', itemLabel: 'Service Library' },
  services: { group: 'Services & Catalog', itemLabel: 'Service Library' },
};

export function getMenuLabels(vertical) {
  return MENU_LABELS[vertical] || MENU_LABELS.hospitality;
}
