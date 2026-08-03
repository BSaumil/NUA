// Offline-first queue for POS sales. Regional AU connectivity drop-outs mean
// a till losing its connection mid-service is a real, expected event — not
// an edge case. When a sale can't reach the server because the network
// itself failed (not because the server rejected it), the sale is queued
// locally in IndexedDB instead of being lost, and flushed automatically the
// moment connectivity returns.
//
// Scope: transaction creation only (the standard cash/card checkout path).
// Payment methods that inherently require a live gateway round-trip
// (QR/UPI confirmation, Stripe redirect, split payments) can't complete
// offline regardless of this queue and are left as-is.
import { transactionsAPI } from '../services/api';

const DB_NAME = 'nua-offline';
const DB_VERSION = 2;   // v2 adds the coursing action store
const STORE = 'pending_transactions';

function openDB() {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in window)) { reject(new Error('IndexedDB unavailable')); return; }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('pending_course_actions')) {
        db.createObjectStore('pending_course_actions', { keyPath: 'id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore(mode, fn) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const store = tx.objectStore(STORE);
    const result = fn(store);
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
  });
}

function genId() {
  return (typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : `q-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export async function enqueueTransaction(payload) {
  const record = { id: genId(), payload, queuedAt: new Date().toISOString() };
  await withStore('readwrite', (store) => store.add(record));
  return record;
}

export async function getQueued() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const store = tx.objectStore(STORE);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

export async function removeQueued(id) {
  await withStore('readwrite', (store) => store.delete(id));
}

export async function countQueued() {
  try { const rows = await getQueued(); return rows.length; }
  catch { return 0; }
}

// A network-level failure (no response reached the client at all) vs. a
// real server rejection (validation error, 409, etc.) — only the former
// should be queued; the latter must still surface to the cashier.
function isNetworkFailure(error) {
  return !error.response && !!error.request;
}

/**
 * Wraps transactionsAPI.create with offline fallback. On a genuine network
 * failure, queues the sale and returns a synthetic response shaped like the
 * real one so existing calling code (which reads res.data.id/.total) keeps
 * working unchanged. Throws through any real server-side rejection as-is.
 */
export async function createTransactionResilient(payload) {
  try {
    return await transactionsAPI.create(payload);
  } catch (error) {
    if (!isNetworkFailure(error)) throw error;
    const record = await enqueueTransaction(payload);
    return {
      data: {
        id: `OFFLINE-${record.id.slice(0, 8)}`,
        total: (payload.items || []).reduce((s, i) => s + (i.price || 0) * (i.quantity || 1), 0),
        queuedOffline: true,
      },
    };
  }
}

// ── Coursing actions ──────────────────────────────────────────────────────
// A till that loses its connection mid-service still has to be able to send
// food and fire courses; those calls used to fail hard while the sale beside
// them queued happily. Same queue, same rules: only network-level failures
// are held, real rejections still surface.
const COURSE_STORE = 'pending_course_actions';

async function withCourseStore(mode, fn) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    if (!db.objectStoreNames.contains(COURSE_STORE)) { resolve(null); return; }
    const tx = db.transaction(COURSE_STORE, mode);
    const result = fn(tx.objectStore(COURSE_STORE));
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
  });
}

export async function getQueuedCourseActions() {
  const db = await openDB();
  return new Promise((resolve) => {
    if (!db.objectStoreNames.contains(COURSE_STORE)) { resolve([]); return; }
    const req = db.transaction(COURSE_STORE, 'readonly').objectStore(COURSE_STORE).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => resolve([]);
  });
}

/**
 * Run a coursing call, queueing it if the network (not the server) failed.
 *
 * `kind` names the action so the flush knows how to replay it. Replay order
 * matters — firing a course before the ticket it belongs to exists would
 * fail — so the queue is strictly FIFO and stops at the first still-offline
 * error rather than skipping ahead.
 */
export async function courseActionResilient(kind, args, run) {
  try {
    return await run();
  } catch (error) {
    if (!isNetworkFailure(error)) throw error;
    const record = { id: genId(), kind, args, queuedAt: new Date().toISOString() };
    await withCourseStore('readwrite', (store) => store.add(record));
    return { data: null, queuedOffline: true, queuedKind: kind };
  }
}

async function replayCourseAction(row) {
  const { coursingAPI, kitchenAPI } = await import('../services/api');
  const a = row.args || {};
  switch (row.kind) {
    case 'sendToKitchen': return coursingAPI.sendToKitchen(a.payload);
    case 'addRound':      return coursingAPI.addRound(a.orderId, a.payload);
    case 'fire':          return kitchenAPI.fireCourse(a.orderId, a.course);
    case 'hold':          return kitchenAPI.holdCourse(a.orderId, a.course);
    case 'serve':         return kitchenAPI.serveCourse(a.orderId, a.course);
    case 'void':          return coursingAPI.voidItems(a.orderId, a.payload);
    case 'settle':        return coursingAPI.settle(a.payload);
    default: return null;   // unknown kind — drop rather than block the queue
  }
}

export async function flushCourseActions(onProgress) {
  const rows = await getQueuedCourseActions();
  for (const row of rows) {
    try {
      await replayCourseAction(row);
      await withCourseStore('readwrite', (store) => store.delete(row.id));
      onProgress?.((await getQueuedCourseActions()).length);
    } catch (error) {
      if (isNetworkFailure(error)) break;   // still offline — keep the rest
      // A real rejection on replay (the ticket was closed while we were away,
      // the course already fired) — drop it. Retrying forever would wedge
      // every later action behind one that can never succeed.
      await withCourseStore('readwrite', (store) => store.delete(row.id));
    }
  }
}

let syncing = false;
export async function flushQueue(onProgress) {
  if (syncing) return;
  syncing = true;
  try {
    const rows = await getQueued();
    for (const row of rows) {
      try {
        await transactionsAPI.create(row.payload);
        await removeQueued(row.id);
        onProgress?.(await countQueued());
      } catch (error) {
        if (isNetworkFailure(error)) break; // still offline — stop, retry later
        // A real rejection on retry (e.g. stale data) — drop it rather than
        // block the queue forever; nothing silently retries an invalid sale.
        await removeQueued(row.id);
      }
    }
    // Sales first: a queued fire refers to a ticket a queued send created.
    await flushCourseActions(onProgress);
  } finally { syncing = false; }
}
