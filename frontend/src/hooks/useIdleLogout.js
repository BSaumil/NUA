import { useEffect, useRef } from 'react';
import { staffMgmtAPI } from '../services/api';

const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'touchstart', 'pointerdown'];

// Owner-configurable auto-logout for the POS screen (Settings → POS Session).
// 0 = stay logged in (the hook simply never arms a timer). Any user
// interaction — a click, a keypress, a tap while taking an order — resets
// the clock; only real inactivity ever triggers it.
export default function useIdleLogout(enabled, logout) {
  const timeoutMinutesRef = useRef(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    staffMgmtAPI.getPosSessionSettings()
      .then(r => { if (!cancelled) timeoutMinutesRef.current = r.data.timeoutMinutes || 0; })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;

    const arm = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      const minutes = timeoutMinutesRef.current;
      if (!minutes) return; // "stay logged in"
      timerRef.current = setTimeout(() => { logout(); }, minutes * 60 * 1000);
    };

    arm();
    ACTIVITY_EVENTS.forEach(evt => window.addEventListener(evt, arm));
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      ACTIVITY_EVENTS.forEach(evt => window.removeEventListener(evt, arm));
    };
  }, [enabled, logout]);
}
