# NUA — Digital Identity Build Spec

**For:** Claude Code
**Company:** NUA AUS PTY LTD · ABN 54 299 131 653
**Product:** NUA — Restaurant OS
**Spec version:** 2026-08-03
**Source concept:** Mixed lockup — Pulse Grid icon (Brand Identity system) + Instrument Serif gradient wordmark (Instrument Gradient / Chrome Serif) + Caveat signature flourish (Script Signature)

This package contains every asset and token needed to wire NUA's digital identity into the codebase: favicons, app icons, logo components, color tokens, and typography tokens. Follow the tasks below in order.

---

## 1. File tree

```
nua-digital-identity/
├── BRAND-SPEC.md                 ← this file
├── assets/
│   ├── icons/
│   │   ├── icon-pulse-grid.svg        full-colour icon (app icon, avatar, large use)
│   │   └── icon-pulse-grid-mono.svg   single-tone icon (favicon, <24px use)
│   ├── wordmark/
│   │   ├── wordmark-nua-gradient.svg  "Nua" gradient wordmark alone
│   │   ├── flourish-signature.svg     signature flourish stroke alone
│   │   └── lockup-horizontal.svg      icon + wordmark + flourish, combined
│   └── favicon/
│       ├── favicon.ico                 16/32/48px, single-tone
│       ├── favicon-16x16.png
│       ├── favicon-32x32.png
│       ├── favicon-48x48.png
│       ├── apple-touch-icon-180x180.png
│       ├── android-chrome-192x192.png
│       ├── android-chrome-512x512.png
│       ├── site.webmanifest
│       └── favicon-links.html          <head> snippet, ready to paste
├── tokens/
│   ├── colors.css                      CSS custom properties
│   ├── colors.json                     same tokens, JSON
│   ├── typography.css                  font imports + font-role variables
│   └── tailwind.tokens.js              merge into tailwind.config.js
└── components/
    ├── Icon.jsx                        Pulse Grid icon component
    └── Logo.jsx                        full lockup component (marketing + product variants)
```

---

## 2. Tasks

1. **Favicons.** Copy everything in `assets/favicon/` (except `favicon-links.html`) into the app's static root (e.g. `public/` in Next.js, `static/` elsewhere). Paste the contents of `favicon-links.html` into the document `<head>`.

2. **Tokens.** Import `tokens/colors.css` and `tokens/typography.css` once, globally (root layout / `_app` / `index.css`). If the project uses Tailwind, merge `tokens/tailwind.tokens.js` into `theme.extend` in `tailwind.config.js` instead of hand-writing the CSS variables.

3. **Components.** Drop `components/Icon.jsx` and `components/Logo.jsx` into the project's component directory. Use:
   - `<Logo variant="product" />` — app headers, nav bars, in-product chrome. Plain Space Grotesk wordmark, no gradient, no flourish.
   - `<Logo variant="marketing" />` — landing page hero, investor decks rendered in-app, login/signup screens. Full gradient wordmark + flourish.
   - `<Icon size={n} variant="mono" />` — anywhere below ~24px.

4. **SVG source files** in `assets/wordmark/` are for design handoff, print vendors, or contexts outside the app (letterhead, merch, signage) — not for direct import into the app; use the React components for those instead. Note: `wordmark-nua-gradient.svg` and `lockup-horizontal.svg` reference the Instrument Serif web font by name. If a vendor or tool can't guarantee that font is loaded, convert the text to outlines before sending the file out (Figma/Illustrator: *Text → Outline*).

5. **Verify** the tab favicon, app manifest icon (install as PWA / add to home screen), and both `<Logo>` variants render correctly light and dark before marking this done.

---

## 3. Usage rules

- `--nua-purple` (`#8b5cf6`) is reserved for AI-surfaced features. Never use it decoratively elsewhere in product UI, including in the icon — the Pulse Grid's purple tile is the one fixed exception, since it *is* the AI-feature signal.
- The gradient wordmark (`variant="marketing"`) is for hero/marketing surfaces only. Never use it in functional UI — buttons, nav, in-app headers all use `variant="product"`.
- The Caveat signature flourish is a supporting accent only. Never set it as the primary wordmark or use it for body copy.
- Minimum size: 24px digital (full-colour icon), 14px digital (mono icon), 12mm print.
- Clear space around the icon: one grid-tile width on all sides, minimum.

## 4. Color reference

| Token | Hex | Role |
|---|---|---|
| `--nua-orange` | `#f58c14` | Primary / CTA |
| `--nua-purple` | `#8b5cf6` | AI features only |
| `--nua-pink` | `#ec4899` | Insights / alerts |
| `--nua-ink` | `#1c1917` | Dark mode / reversed |
| `--nua-paper` | `#fdfcfa` | Background |

## 5. Type reference

| Role | Face | Notes |
|---|---|---|
| Wordmark (marketing) | Instrument Serif, italic | Gradient-filled, hero contexts only |
| Display / product headings | Space Grotesk, 700 | In-app, functional UI |
| Body | Manrope | General copy |
| Tagline / data / receipts | IBM Plex Mono | Tracked +0.3–0.4em for taglines |
| Signature accent | Caveat, 600 | Flourish and sign-off line only |

---

❤️ NUA — Built iteratively. Tested rigorously. Themed boldly.
NUA AUS PTY LTD · ABN 54 299 131 653
