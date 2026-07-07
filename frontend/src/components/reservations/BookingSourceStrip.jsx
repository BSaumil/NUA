import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { finalizeAPI } from '../../services/api';
import { TrendingUp, Instagram, Facebook, Globe, Phone, Mail, MessageSquare, User, ExternalLink } from 'lucide-react';

const SOURCE_META = {
  instagram: { label: 'Instagram', icon: Instagram, color: '#ec4899' },
  instagram_dm: { label: 'Instagram', icon: Instagram, color: '#ec4899' },
  facebook: { label: 'Facebook', icon: Facebook, color: '#3b82f6' },
  facebook_dm: { label: 'Facebook', icon: Facebook, color: '#3b82f6' },
  whatsapp: { label: 'WhatsApp', icon: MessageSquare, color: '#22c55e' },
  sms: { label: 'SMS', icon: MessageSquare, color: '#8b5cf6' },
  phone: { label: 'Phone', icon: Phone, color: '#f59e0b' },
  email: { label: 'Email', icon: Mail, color: '#6366f1' },
  web: { label: 'Web', icon: Globe, color: '#0ea5e9' },
  website: { label: 'Web', icon: Globe, color: '#0ea5e9' },
  web_form: { label: 'Web Form', icon: Globe, color: '#0ea5e9' },
  opentable: { label: 'OpenTable', icon: ExternalLink, color: '#ef4444' },
  'walk-in': { label: 'Walk-in', icon: User, color: '#64748b' },
  walk_in: { label: 'Walk-in', icon: User, color: '#64748b' },
  walkin: { label: 'Walk-in', icon: User, color: '#64748b' },
};

/**
 * Bookings source attribution strip — shows the top 4 booking sources over
 * the last 30 days plus a spark of QR scans. Renders next to nothing when
 * the backend has no data yet (empty CRM); never blocks the page.
 */
export default function BookingSourceStrip({ theme, days = 30 }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    finalizeAPI.marketingAnalytics(days)
      .then(r => setData(r.data))
      .catch(e => setErr(e?.response?.data?.detail || 'load-failed'));
  }, [days]);

  if (err || !data) return null;

  const bySource = data.bookingsBySource || {};
  const sources = Object.entries(bySource)
    .map(([k, v]) => ({ key: k, ...v, meta: SOURCE_META[k] || { label: k, icon: User, color: '#64748b' } }))
    .sort((a, b) => b.bookings - a.bookings);

  const totalScans = data.totalScans || 0;
  const totalBookings = data.totalBookings || 0;
  const totalCovers = sources.reduce((s, x) => s + (x.covers || 0), 0);
  const totalRevenue = sources.reduce((s, x) => s + (x.estRevenue || 0), 0);

  if (totalBookings === 0 && totalScans === 0) return null;

  const shown = sources.slice(0, 4);

  return (
    <Card className="border-0 shadow-sm" data-testid="booking-source-strip">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <TrendingUp size={14} style={{ color: theme?.primary || '#f97316' }} />
            <p className="text-xs uppercase tracking-widest font-semibold text-gray-500">
              Booking sources · last {days} days
            </p>
          </div>
          <div className="text-[11px] text-gray-500 flex items-center gap-4">
            <span data-testid="bss-total-bookings"><strong className="text-gray-800">{totalBookings}</strong> bookings</span>
            <span data-testid="bss-total-covers"><strong className="text-gray-800">{totalCovers}</strong> covers</span>
            <span data-testid="bss-total-scans"><strong className="text-gray-800">{totalScans}</strong> QR scans</span>
            {totalRevenue > 0 && <span data-testid="bss-total-revenue">Est. <strong className="text-gray-800">${totalRevenue.toFixed(0)}</strong></span>}
          </div>
        </div>

        {shown.length === 0 ? (
          <p className="text-xs text-gray-400 py-2">No source-attributed bookings yet.</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2" data-testid="bss-sources-grid">
            {shown.map(s => {
              const Icon = s.meta.icon;
              const pct = totalBookings ? Math.round((s.bookings / totalBookings) * 100) : 0;
              return (
                <div key={s.key} className="rounded-lg border bg-gray-50/40 p-2.5" data-testid={`bss-source-${s.key}`}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon size={13} style={{ color: s.meta.color }} />
                    <span className="text-xs font-medium" style={{ color: s.meta.color }}>{s.meta.label}</span>
                    <span className="text-[10px] text-gray-400 ml-auto">{pct}%</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-lg font-bold text-gray-800">{s.bookings}</span>
                    <span className="text-[10px] text-gray-500">{s.covers} covers</span>
                  </div>
                  <div className="h-1 rounded-full bg-gray-200 mt-1.5 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: s.meta.color }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
