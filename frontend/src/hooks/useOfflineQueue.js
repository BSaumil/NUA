import { useEffect, useState, useCallback } from 'react';
import { countQueued, flushQueue } from '../lib/offlineQueue';

/** Tracks how many sales are queued offline and keeps retrying to flush them. */
export default function useOfflineQueue() {
  const [queuedCount, setQueuedCount] = useState(0);

  const refresh = useCallback(async () => setQueuedCount(await countQueued()), []);
  const trySync = useCallback(async () => {
    await flushQueue(setQueuedCount);
    refresh();
  }, [refresh]);

  useEffect(() => {
    refresh();
    trySync(); // in case sales were queued in a previous session and we're back online now
    window.addEventListener('online', trySync);
    const id = setInterval(trySync, 30000); // safety net — 'online' doesn't always fire cleanly
    return () => { window.removeEventListener('online', trySync); clearInterval(id); };
  }, [refresh, trySync]);

  return { queuedCount, refresh };
}
