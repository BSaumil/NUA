# NUA brand assets

Sourced from the "Chrome × Brand Identity × Signature × Geometric Pulse"
digital identity package delivered against `BRAND-SPEC.md` (Pulse Grid icon,
Bricolage Grotesque gradient wordmark, Caveat signature flourish). This
supersedes an earlier hand-built approximation of the same spec that used
Instrument Serif before the real asset package arrived.

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
direct import into the app (use the React components). `wordmark-nua-gradient.svg`
and `lockup-horizontal.svg` reference Bricolage Grotesque **by name**; the
`-outlined` siblings are true vector outlines with no font dependency — use
those for any vendor who can't guarantee the font is loaded.

## Not generated

`site.webmanifest` and `favicon-links.html` from the spec's file tree are
omitted deliberately — this app already has `manifest.json` and an
`index.html` `<head>`, both updated in place rather than duplicated.
