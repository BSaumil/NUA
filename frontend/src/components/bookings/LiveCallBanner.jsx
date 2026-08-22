import React, { useEffect, useState, useRef } from 'react';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { PhoneCall, Users, CalendarDays, Clock, User, X } from 'lucide-react';
import api from '../../services/api';

/**
 * Floating banner shown at the top of the Bookings page whenever NUA is on
 * an inbound call. Polls every 2 seconds — small payload, negligible load.
 * Silently renders nothing when no call is active.
 */
export default function LiveCallBanner() {
  const [calls, setCalls] = useState([]);
  const [dismissed, setDismissed] = useState(new Set());
  const timerRef = useRef(null);

  const tick = async () => {
    try {
      const r = await api.get('/voice/inbound/active');
      setCalls(Array.isArray(r.data) ? r.data : []);
    } catch { /* silent — staff without permission just get nothing */ }
  };

  useEffect(() => {
    tick();
    timerRef.current = setInterval(tick, 2000);
    return () => clearInterval(timerRef.current);
  }, []);

  const active = calls.filter(c => !dismissed.has(c.id));
  if (active.length === 0) return null;

  return (
    <div className="fixed top-3 right-3 z-40 space-y-2 max-w-sm" data-testid="live-call-banner">
      {active.map(c => {
        const s = c.slots || {};
        const filled = Object.values(s).filter(Boolean).length;
        const lastLine = (c.transcript || [])[c.transcript.length - 1];
        return (
          <Card key={c.id} className="border-l-4 border-l-indigo-500 shadow-lg animate-in slide-in-from-right-4">
            <div className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-indigo-700 font-medium text-sm">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500" />
                  </span>
                  <PhoneCall size={13} />
                  NUA is on a call
                </div>
                <button
                  onClick={() => setDismissed(new Set([...dismissed, c.id]))}
                  className="text-gray-400 hover:text-gray-700"
                  data-testid={`live-call-dismiss-${c.id}`}
                >
                  <X size={14} />
                </button>
              </div>

              <div className="text-[11px] text-gray-500">
                From {c.phone || 'unknown'} · turn {c.turns} · {filled}/4 slots
              </div>

              {/* Slot progress chips — light up as NUA extracts them */}
              <div className="flex flex-wrap gap-1.5 text-[10px]" data-testid={`live-call-slots-${c.id}`}>
                <Chip filled={!!s.partySize} Icon={Users} label={s.partySize ? `${s.partySize} people` : 'Party size'} />
                <Chip filled={!!s.date} Icon={CalendarDays} label={s.date || 'Date'} />
                <Chip filled={!!s.time} Icon={Clock} label={s.time || 'Time'} />
                <Chip filled={!!s.name} Icon={User} label={s.name || 'Name'} />
              </div>

              {/* Rolling transcript — last 2 exchanges */}
              <div className="text-[11px] space-y-0.5 max-h-28 overflow-y-auto pr-1">
                {(c.transcript || []).slice(-4).map((t, i) => (
                  <div key={i} className={t.speaker === 'nua' ? 'text-indigo-700' : 'text-gray-700'}>
                    <span className="font-medium">{t.speaker === 'nua' ? 'NUA:' : 'Guest:'}</span>{' '}
                    {t.text || <em className="text-gray-400">(no speech)</em>}
                  </div>
                ))}
              </div>

              {lastLine?.speaker === 'nua' && (
                <div className="text-[10px] text-gray-500 italic">Waiting for guest reply…</div>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function Chip({ filled, Icon, label }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border transition ${
        filled
          ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
          : 'bg-gray-50 border-gray-200 text-gray-400'
      }`}
    >
      <Icon size={10} />
      {label}
    </span>
  );
}
