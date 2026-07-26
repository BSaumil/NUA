import { useEffect, useRef, useState } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

function wsUrl() {
  const token = localStorage.getItem('nuva_token') || '';
  const base = BACKEND_URL.replace(/^http/, 'ws');
  return `${base}/api/ws/live?token=${encodeURIComponent(token)}`;
}

/**
 * Live-sync for the Dashboard app. This is a nice-to-have, not a dependency —
 * regional connectivity drop-outs and proxies that block WS upgrades are
 * real, so callers must keep their own polling running regardless. All this
 * hook does is call `onEvent` a little sooner when the socket is up, with
 * capped exponential-backoff reconnects while it isn't.
 */
export default function useLiveFeed(onEvent) {
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!localStorage.getItem('nuva_token')) return undefined;
    let socket;
    let closedByCleanup = false;
    let retryDelay = 1000;
    let retryTimer;

    const connect = () => {
      try { socket = new WebSocket(wsUrl()); }
      catch { scheduleRetry(); return; }

      socket.onopen = () => { setConnected(true); retryDelay = 1000; };
      socket.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          if (data.type !== 'connected') onEventRef.current?.(data);
        } catch { /* ignore malformed frame */ }
      };
      socket.onclose = () => { setConnected(false); if (!closedByCleanup) scheduleRetry(); };
      socket.onerror = () => { try { socket.close(); } catch { /* noop */ } };
    };

    const scheduleRetry = () => {
      clearTimeout(retryTimer);
      retryTimer = setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 30000); // cap at 30s
    };

    connect();
    return () => {
      closedByCleanup = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return { connected };
}
