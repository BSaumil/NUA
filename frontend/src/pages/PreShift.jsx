import React, { useState, useEffect } from 'react';
import {
  Sun, Clock, Users, CalendarDays, AlertTriangle, Star, ChefHat,
  Utensils, Bell, ShieldAlert, Heart, ClipboardList, TrendingUp
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { preShiftAPI } from '../services/api';

export default function PreShift() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);

  useEffect(() => {
    preShiftAPI.getToday().then(r => setData(r.data)).catch(console.error);
  }, []);

  if (!data) return <div className="flex items-center justify-center h-64 text-gray-400">Loading pre-shift data...</div>;

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good Morning';
    if (h < 17) return 'Good Afternoon';
    return 'Good Evening';
  })();

  return (
    <div className="space-y-6" data-testid="pre-shift-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: `linear-gradient(135deg, ${theme.primary}, ${theme.accent || '#F59E0B'})` }}>
              <Sun size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ color: theme.text }}>{greeting}, Team!</h1>
              <p className="text-sm text-gray-500">Pre-Shift Briefing | {new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Reservations', val: data.totalReservations, icon: CalendarDays, color: '#3B82F6' },
          { label: 'Total Covers', val: data.totalCovers, icon: Users, color: theme.primary },
          { label: 'Confirmed', val: data.confirmed, icon: Bell, color: '#10B981' },
          { label: 'Kitchen Queue', val: data.kitchenPending, icon: ChefHat, color: '#F59E0B' },
          { label: 'Waitlist', val: data.waitlistCount, icon: ClipboardList, color: '#8B5CF6' },
        ].map((s, i) => (
          <Card key={i} className="border-0 shadow-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${s.color}15` }}>
                <s.icon size={20} style={{ color: s.color }} />
              </div>
              <div>
                <p className="text-2xl font-bold" style={{ color: theme.text }}>{s.val}</p>
                <p className="text-[10px] text-gray-500">{s.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* VIP Guests */}
        <Card className="border-0 shadow-sm col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Star size={16} className="text-amber-500" /> VIP Arrivals
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(data.vipGuests || []).length === 0 ? (
              <p className="text-xs text-gray-400 py-4 text-center">No VIP guests today</p>
            ) : data.vipGuests.map((g, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-amber-50/50">
                <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 font-bold text-xs">
                  {g.guestName?.split(' ').map(n => n[0]).join('').slice(0, 2)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{g.guestName}</p>
                  <div className="flex items-center gap-2 text-[10px] text-gray-500">
                    <span><Clock size={10} className="inline" /> {g.time}</span>
                    <span><Users size={10} className="inline" /> {g.partySize}</span>
                  </div>
                </div>
                <Badge className="bg-amber-100 text-amber-700 text-[10px]">VIP</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Dietary Alerts */}
        <Card className="border-0 shadow-sm col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <ShieldAlert size={16} className="text-red-500" /> Dietary & Allergy Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(data.dietaryAlerts || []).length === 0 ? (
              <p className="text-xs text-gray-400 py-4 text-center">No dietary alerts today</p>
            ) : data.dietaryAlerts.map((a, i) => (
              <div key={i} className="p-2 rounded-lg bg-red-50/50">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium">{a.guest}</p>
                  <span className="text-[10px] text-gray-500">{a.time}</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {a.alerts.map((alert, j) => (
                    <Badge key={j} className={`text-[10px] ${alert.startsWith('ALLERGY') ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                      {alert}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Special Requests */}
        <Card className="border-0 shadow-sm col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Heart size={16} className="text-pink-500" /> Special Requests
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(data.specialRequests || []).length === 0 ? (
              <p className="text-xs text-gray-400 py-4 text-center">No special requests today</p>
            ) : data.specialRequests.map((sr, i) => (
              <div key={i} className="p-2 rounded-lg bg-pink-50/50">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium">{sr.guest}</p>
                  <div className="flex items-center gap-2 text-[10px] text-gray-500">
                    <span><Clock size={10} className="inline" /> {sr.time}</span>
                    <span><Users size={10} className="inline" /> {sr.partySize}</span>
                  </div>
                </div>
                <p className="text-xs text-gray-600">{sr.request}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Today's Reservation Timeline */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Utensils size={16} style={{ color: theme.primary }} /> Today's Service Timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="preshift-timeline">
              <thead>
                <tr className="border-b bg-gray-50/80">
                  <th className="text-left px-3 py-2 font-medium text-gray-500">Time</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-500">Guest</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-500">Party</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-500">Table</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-500">Status</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-500">Tags</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-500">Notes</th>
                </tr>
              </thead>
              <tbody>
                {(data.reservations || []).map(r => (
                  <tr key={r.id} className="border-b hover:bg-gray-50/50">
                    <td className="px-3 py-2 font-mono font-medium">{r.time}</td>
                    <td className="px-3 py-2 font-medium">{r.guestName}</td>
                    <td className="px-3 py-2">{r.partySize}</td>
                    <td className="px-3 py-2">{r.tableNumber ? `T${r.tableNumber}` : '—'}</td>
                    <td className="px-3 py-2">
                      <Badge variant="outline" className="text-[10px] capitalize">{r.status?.replace('_', ' ')}</Badge>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        {(r.tags || []).map((t, i) => <Badge key={i} className="text-[10px]" style={{ background: `${theme.primary}15`, color: theme.primary }}>{t}</Badge>)}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 max-w-[200px] truncate">{r.specialRequests || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
