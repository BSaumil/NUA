/**
 * WCAG contrast helpers.
 *
 * Category colors are owner-configurable — any hex an owner picks becomes a
 * button background on the POS category bar. A hardcoded `text-white` on top
 * of an arbitrary color is a coin flip: fine on a dark teal, unreadable on a
 * pale yellow. This picks black or white by the actual relative luminance of
 * whatever color was chosen, so the text stays legible regardless of what
 * the owner picks — the same reasoning that led to fixing the dark-theme
 * `--primary-foreground` token (see index.css), generalised to arbitrary
 * per-category colors that a CSS variable can't cover.
 */

function hexToRgb(hex) {
  const clean = (hex || '').replace('#', '');
  const full = clean.length === 3 ? clean.split('').map(c => c + c).join('') : clean;
  const num = parseInt(full, 16);
  if (full.length !== 6 || Number.isNaN(num)) return null;
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

function channelLuminance(c) {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(hex) {
  const rgb = hexToRgb(hex);
  if (!rgb) return 1;   // unparseable → assume light, so callers fall back to dark text
  return 0.2126 * channelLuminance(rgb.r) + 0.7152 * channelLuminance(rgb.g) + 0.0722 * channelLuminance(rgb.b);
}

export function contrastRatio(hexA, hexB) {
  const a = relativeLuminance(hexA);
  const b = relativeLuminance(hexB);
  const lighter = Math.max(a, b);
  const darker = Math.min(a, b);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Black or white — whichever reads better against `bgHex` — using the same
 * relative-luminance math WCAG's contrast formula is built on. Comparing
 * against black directly rather than a fixed luminance threshold means this
 * agrees with the actual contrast ratio, not an approximation of it.
 */
export function readableTextColor(bgHex, { dark = '#111827', light = '#ffffff' } = {}) {
  const contrastWithDark = contrastRatio(bgHex, dark);
  const contrastWithLight = contrastRatio(bgHex, light);
  return contrastWithDark >= contrastWithLight ? dark : light;
}
