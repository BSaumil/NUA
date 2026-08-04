/**
 * One live ticket stream per browser, shared by everything that needs it.
 *
 * The first version opened an EventSource per POS *per table*, so a floor view
 * watching twelve tables would hold twelve connections open. This opens a
 * single un-filtered stream and fans it out to subscribers, who filter to the
 * table they care about. Browsers cap concurrent connections per origin (six
 * on HTTP/1.1), so "one per table" doesn't just waste sockets — past six it
 * silently stops delivering.
 */
import { coursingAPI } from '../services/api';

let source = null;
let subscribers = new Set();
let lastTickets = [];
let healthy = false;

function ensureOpen() {
  if (source || typeof EventSource === 'undefined') return;
  try {
    source = new EventSource(coursingAPI.streamUrl());   // no table = every table
    source.addEventListener('tickets', (ev) => {
      healthy = true;
      try {
        lastTickets = JSON.parse(ev.data) || [];
      } catch { return; }
      subscribers.forEach(fn => { try { fn(lastTickets); } catch {} });
    });
    source.onerror = () => {
      healthy = false;
      // EventSource reconnects on its own; the server also recycles streams on
      // a timer, so an error here is usually that planned recycle.
    };
  } catch {
    source = null;
  }
}

// Don't tear the connection down the instant the last subscriber leaves.
// Switching tables unsubscribes and resubscribes within the same tick, and
// reconnecting each time throws away the buffered ticket state and costs a
// round trip on every switch — during a service that's constant churn.
const IDLE_GRACE_MS = 30000;
let idleTimer = null;

function closeIfIdle() {
  if (subscribers.size > 0) return;
  if (idleTimer) clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    idleTimer = null;
    if (subscribers.size === 0 && source) {
      source.close();
      source = null;
      healthy = false;
    }
  }, IDLE_GRACE_MS);
}

/**
 * Subscribe to live tickets. Returns an unsubscribe function.
 * The callback receives the full ticket array; filter it yourself.
 */
export function subscribeTickets(fn) {
  // A new subscriber cancels any pending idle close.
  if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
  subscribers.add(fn);
  ensureOpen();
  if (lastTickets.length) { try { fn(lastTickets); } catch {} }
  return () => { subscribers.delete(fn); closeIfIdle(); };
}

/** Is the stream currently delivering? Callers poll as a fallback when not. */
export function streamHealthy() {
  return healthy;
}

/** Drop the connection — used when the token changes (log out / log in). */
export function resetTicketStream() {
  if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
  subscribers = new Set();
  lastTickets = [];
  if (source) { source.close(); source = null; }
  healthy = false;
}
