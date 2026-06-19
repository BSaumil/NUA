import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, Cable, Activity, AlertTriangle, Printer, Monitor, Cpu } from 'lucide-react';
import { v25API } from '../../services/api';

/**
 * Compact status bar shown above the search / category strip in the POS.
 * Shows:
 *   • Live clock + date
 *   • Number of registered devices, with offline count flagged
 *   • Connection type (wifi vs ethernet) and online indicator
 *
 * Devices come from /api/v25/hardware (existing endpoint — returns
 * {id, name, kind, status: 'online'|'offline'} list). Polls every 30s.
 */
export default function POSHeaderBar({ themeColor = '#f58c14' }) {
  const [now, setNow] = useState(new Date());
  const [devices, setDevices] = useState([]);
  const [online, setOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [connType, setConnType] = useState('unknown'); // wifi | ethernet | unknown

  // Live clock
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  // Online / offline + connection type detection
  useEffect(() => {
    const updateOnline = () => setOnline(navigator.onLine);
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
    const updateConn = () => {
      const c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (c?.type === 'ethernet' || c?.effectiveType === 'ethernet') setConnType('ethernet');
      else if (c?.type === 'wifi' || ['4g', '3g', '2g', 'wifi'].includes(c?.effectiveType)) setConnType('wifi');
      else setConnType('unknown');
    };
    updateConn();
    const c = navigator.connection;
    c?.addEventListener?.('change', updateConn);
    return () => {
      window.removeEventListener('online', updateOnline);
      window.removeEventListener('offline', updateOnline);
      c?.removeEventListener?.('change', updateConn);
    };
  }, []);

  // Device list — poll every 30s
  useEffect(() => {
    let mounted = true;
    const tick = () => {
      v25API.hardware()
        .then(r => { if (mounted) setDevices(r.data || []); })
        .catch(() => { /* keep last-known list */ });
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  const offline = devices.filter(d => d.status !== 'online');
  const total = devices.length;

  const time = now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const date = now.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });

  const deviceIcon = (kind) => {
    if (!kind) return <Cpu size={11} />;
    const k = kind.toLowerCase();
    if (k.includes('printer')) return <Printer size={11} />;
    if (k.includes('display') || k.includes('cfd') || k.includes('kds')) return <Monitor size={11} />;
    return <Cpu size={11} />;
  };

  return (
    <div className="flex items-center justify-between gap-3 px-3 py-1.5 mb-2 rounded-md border bg-white text-xs"
      data-testid="pos-header-bar"
      style={{ borderColor: 'rgba(0,0,0,0.06)' }}>

      {/* LEFT: clock */}
      <div className="flex items-center gap-2 min-w-0">
        <Activity size={14} style={{ color: themeColor }} />
        <span className="font-mono font-bold tabular-nums" data-testid="pos-clock">{time}</span>
        <span className="text-gray-400 hidden sm:inline">·</span>
        <span className="text-gray-500 hidden sm:inline" data-testid="pos-date">{date}</span>
      </div>

      {/* MIDDLE: devices */}
      <div className="flex items-center gap-2 flex-1 justify-center min-w-0" data-testid="pos-devices">
        {total === 0 ? (
          <span className="text-gray-400">No devices registered</span>
        ) : (
          <>
            <span className={`font-medium ${offline.length > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
              {total - offline.length}/{total} devices online
            </span>
            {offline.length > 0 && (
              <span
                className="hidden md:flex items-center gap-1 text-red-600 truncate"
                title={offline.map(d => d.name).join(', ')}
                data-testid="pos-devices-offline"
              >
                <AlertTriangle size={11} />
                <span className="truncate">
                  {offline.slice(0, 2).map(d => (
                    <span key={d.id} className="inline-flex items-center gap-0.5 mr-1.5">
                      {deviceIcon(d.kind)} {d.name}
                    </span>
                  ))}
                  {offline.length > 2 && <span>+{offline.length - 2} more</span>}
                </span>
              </span>
            )}
          </>
        )}
      </div>

      {/* RIGHT: connection indicator */}
      <div className="flex items-center gap-1.5" data-testid="pos-connection">
        {!online ? (
          <span className="inline-flex items-center gap-1 text-red-600 font-medium" data-testid="pos-connection-offline">
            <WifiOff size={13} /> Offline
          </span>
        ) : connType === 'ethernet' ? (
          <span className="inline-flex items-center gap-1 text-emerald-700 font-medium" data-testid="pos-connection-ethernet" title="Wired connection">
            <Cable size={13} /> Ethernet
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-emerald-700 font-medium" data-testid="pos-connection-wifi" title="Wireless connection">
            <Wifi size={13} /> Wi-Fi
          </span>
        )}
      </div>
    </div>
  );
}
