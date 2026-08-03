# NUA brand assets

Generated from `BRAND-SPEC.md`. The spec arrived without its asset package,
so the icon, wordmark, flourish, favicons and tokens here were built to match
its description (Pulse Grid icon, Instrument Serif gradient wordmark, Caveat
signature flourish) and its colour/type tables.

## What's wired into the app already

| Asset | Wired as |
|---|---|
| `assets/favicon/*` | copied to `frontend/public/`, linked from `index.html` + `manifest.json` |
| `assets/icons/icon-pulse-grid.svg` | `frontend/public/nua-icon.svg` (SVG favicon) |
| `tokens/colors.css`, `tokens/typography.css` | copied to `frontend/src/`, imported at the top of `index.css` |
| `tokens/tailwind.tokens.js` | merged into `frontend/tailwind.config.js` (`theme.extend`) |
| React components | `frontend/src/components/brand/{Icon,Logo}.jsx` |

Usage: `<Logo variant="product" />` in app chrome, `<Logo variant="marketing" />`
on login/hero, `<Icon variant="mono" />` below ~24px.

## Files here are the source of truth for handoff

`assets/wordmark/*.svg` are for print vendors, signage and merch — not for
direct import into the app (use the React components). They reference
Instrument Serif **by name**: convert text to outlines before sending to any
vendor who can't guarantee the font is loaded.

## Not generated

`site.webmanifest` and `favicon-links.html` from the spec's file tree are
omitted deliberately — this app already has `manifest.json` and an
`index.html` `<head>`, both updated in place rather than duplicated.
