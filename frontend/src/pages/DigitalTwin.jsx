import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { v25API } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { Activity, Clock, Users, DollarSign } from 'lucide-react';

export default function DigitalTwin() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  useEffect(() => { v25API.digitalTwin().then(r => setData(r.data)).catch(() => {}); }, []);
  return (
    <div className="space-y-6" data-testid="digital-twin-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Activity className="text-cyan-600" /> Restaurant Digital Twin</h1>
      {!data ? <div className="text-center py-20 text-gray-400">Simulating…</div> : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card><CardContent className="p-6">
            <p className="text-xs uppercase tracking-widest text-gray-500 flex items-center gap-1.5"><DollarSign size={12} /> Expected Revenue</p>
            <p className="text-4xl font-bold mt-2">${data.expectedRevenue?.toLocaleString()}</p>
            <p className="text-xs text-gray-500 mt-1">Range ${data.revenueLow?.toLocaleString()} – ${data.revenueHigh?.toLocaleString()}</p>
          </CardContent></Card>
          <Card><CardContent className="p-6">
            <p className="text-xs uppercase tracking-widest text-gray-500 flex items-center gap-1.5"><Users size={12} /> Expected Covers</p>
            <p className="text-4xl font-bold mt-2">{data.expectedCovers}</p>
            <p className="text-xs text-gray-500 mt-1">{data.bookings} confirmed bookings</p>
          </CardContent></Card>
          <Card><CardContent className="p-6">
            <p className="text-xs uppercase tracking-widest text-gray-500 flex items-center gap-1.5"><Clock size={12} /> Expected Wait</p>
            <p className="text-4xl font-bold mt-2">{data.expectedWaitMin} <span className="text-base text-gray-400">min</span></p>
            <p className="text-xs text-gray-500 mt-1">at peak hours</p>
          </CardContent></Card>
        </div>
      )}
    </div>
  );
}
