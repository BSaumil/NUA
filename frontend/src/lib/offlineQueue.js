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
const DB_VERSION = 1;
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
  } finally { syncing = false; }
}
