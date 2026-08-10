/**
 * Reports uncaught browser errors back to the backend so an owner has some
 * way to know the POS threw a white screen mid-shift, instead of finding out
 * because a staff member mentioned it after the fact. Before this, a JS
 * error just vanished the moment that tab closed or refreshed.
 *
 * Deliberately dumb: window.onerror and unhandledrejection only, no source
 * maps, no session replay. That's a reasonable "who do I call" signal for a
 * restaurant POS, not a full error-tracking product.
 */
import { opsAPI } from '../services/api';

// A bad deploy that errors on every render could otherwise fire hundreds of
// reports a second from one tab — cap it so this can't turn a crash into a
// second, self-inflicted flood.
const MAX_REPORTS_PER_SESSION = 20;
let reportCount = 0;

function report(message, stack) {
  if (reportCount >= MAX_REPORTS_PER_SESSION) return;
  reportCount++;
  opsAPI.reportClientError({
    message: String(message || '').slice(0, 500),
    stack: String(stack || '').slice(0, 4000),
    url: window.location.href,
    userAgent: navigator.userAgent,
  }).catch(() => { /* nothing further to do if the report itself fails */ });
}

let installed = false;

export function installErrorReporting() {
  if (installed) return;
  installed = true;

  window.addEventListener('error', (event) => {
    report(event.message, event.error?.stack);
  });

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    report(reason?.message || String(reason), reason?.stack);
  });
}
