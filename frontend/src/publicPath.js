/**
 * Must be the very first import in index.js — before anything that might
 * trigger a lazy `import()`.
 *
 * package.json sets "homepage": "./" (required for the Capacitor mobile
 * build, which serves from a scheme with no fixed absolute root). CRA turns
 * that into a *relative* webpack publicPath ("./"), which is fine for the
 * scripts in index.html — the browser resolves those against the page's URL
 * at initial load, which is correct.
 *
 * It is NOT fine for lazy-loaded route chunks (every page in App.js is
 * `lazy(() => import(...))`). A relative publicPath is re-resolved by the
 * browser against `document.baseURI` at the moment each chunk is actually
 * requested — and for a single-page app, baseURI tracks whatever route
 * `history.pushState` last navigated to, not the page's original load URL.
 * Client-side-navigate to /track/ORD-XXX before that chunk has ever loaded
 * (e.g. straight after placing a guest order) and the browser requests
 * "/track/static/js/1234.chunk.js" instead of "/static/js/1234.chunk.js" —
 * a 404, and a blank page with no visible error.
 *
 * Pinning __webpack_public_path__ once, here, from the *initial* script's
 * own src (which is only ever evaluated once, synchronously, at first load)
 * makes every later chunk request use that fixed, correct origin instead —
 * web and Capacitor both, since this reads wherever the script actually was
 * served from rather than assuming any particular scheme.
 */
if (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) {
  // The initial script sits at ".../static/js/main.<hash>.js" — chunk
  // filenames (e.g. "static/js/1234.<hash>.chunk.js") are themselves
  // relative to the build ROOT, not to the js/ folder, so the public path
  // has to be the root, not this script's own parent directory.
  const src = document.currentScript.src;
  const staticIdx = src.indexOf('/static/');
  // eslint-disable-next-line no-undef, camelcase
  __webpack_public_path__ = staticIdx === -1 ? src.replace(/[^/]*$/, '') : src.slice(0, staticIdx + 1);
}
