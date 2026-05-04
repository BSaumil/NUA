import React, { useState, useEffect } from 'react';
import { BarChart3, Users, AlertTriangle, TrendingUp, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { reservationFeaturesAPI } from '../services/api';

export default function BookingAnalytics() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);

  useEffect(() => { reservationFeaturesAPI.getBookingAnalytics().then(r => setData(r.data)).catch(() => {}); }, []);

  if (!data) return <div className="flex justify-center py-12"><div className="animate-pulse text-gray-400">Loading analytics...</div></div>;

  return (
    <div className="space-y-6" data-testid="booking-analytics-page">
      <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Booking Analytics</h1><p className="text-sm text-gray-500">Performance insights for table optimisation</p></div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card><CardContent className="p-5 text-center"><BarChart3 size={20} className="mx-auto mb-2 text-blue-500" /><p className="text-2xl font-bold" style={{ color: theme.primary }}>{data.totalBookings}</p><p className="text-xs text-gray-500">Total Bookings</p></CardContent></Card>
        <Card><CardContent className="p-5 text-center"><AlertTriangle size={20} className="mx-auto mb-2 text-red-500" /><p className="text-2xl font-bold text-red-600">{data.noShowRate}%</p><p className="text-xs text-gray-500">No-Show Rate</p></CardContent></Card>
        <Card><CardContent className="p-5 text-center"><Users size={20} className="mx-auto mb-2 text-emerald-500" /><p className="text-2xl font-bold text-emerald-600">{data.avgPartySize}</p><p className="text-xs text-gray-500">Avg Party Size</p></CardContent></Card>
        <Card><CardContent className="p-5 text-center"><Calendar size={20} className="mx-auto mb-2 text-violet-500" /><p className="text-2xl font-bold text-violet-600">{data.noShows}</p><p className="text-xs text-gray-500">No-Shows</p></CardContent></Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card><CardHeader><CardTitle className="text-sm">By Shift</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {(data.byShift || []).map((s, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div><p className="font-medium">{s.shift}</p><p className="text-xs text-gray-500">{s.covers} covers</p></div>
              <Badge style={{ backgroundColor: `${theme.primary}15`, color: theme.primary }}>{s.bookings} bookings</Badge>
            </div>
          ))}
          {(data.byShift || []).length === 0 && <p className="text-gray-400 text-sm text-center py-4">No shift data</p>}
        </CardContent></Card>

        <Card><CardHeader><CardTitle className="text-sm">Peak Booking Days</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {(data.peakDays || []).map((d, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <span className="font-medium">{d.day}</span>
              <span className="font-bold" style={{ color: theme.primary }}>{d.bookings} bookings</span>
            </div>
          ))}
          {(data.peakDays || []).length === 0 && <p className="text-gray-400 text-sm text-center py-4">No data yet</p>}
        </CardContent></Card>
      </div>
    </div>
  );
}
