import React, { useState, useEffect } from 'react';
import { Flame } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { v15API } from '../services/api';

export default function BookingHeatmap() {
  const { theme } = useTheme();
  const [data, setData] = useState({ heatmap: {}, days: [], hours: [] });

  useEffect(() => { v15API.getBookingHeatmap().then(r => setData(r.data || { heatmap: {}, days: [], hours: [] })).catch(() => {}); }, []);

  const max = Math.max(1, ...Object.values(data.heatmap).flatMap(h => Object.values(h)));
  const cellColor = (val) => {
    const t = val / max;
    if (t === 0) return '#f9fafb';
    const r = Math.round(99 + (236 - 99) * t);
    const g = Math.round(102 + (72 - 102) * t);
    const b = Math.round(241 + (153 - 241) * t);
    return `rgb(${r},${g},${b})`;
  };

  return (
    <div className="space-y-6" data-testid="heatmap-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Flame size={22} className="text-orange-500" /> Reservation Busy-Time Heatmap</h1>
        <p className="text-sm text-gray-500">Aggregate guest-count by day of week × hour. Hotter cells = more guests.</p>
      </div>
      <Card>
        <CardContent className="p-6 overflow-x-auto">
          <table className="text-xs" data-testid="heatmap-table">
            <thead>
              <tr>
                <th className="p-2"></th>
                {data.hours.map(h => <th key={h} className="p-2 text-gray-500 font-medium">{h}:00</th>)}
              </tr>
            </thead>
            <tbody>
              {data.days.map(d => (
                <tr key={d}>
                  <td className="p-2 font-semibold pr-3 text-gray-600">{d}</td>
                  {data.hours.map(h => {
                    const val = data.heatmap[d]?.[h] || 0;
                    return (
                      <td key={h} className="p-0">
                        <div className="w-10 h-10 flex items-center justify-center text-[10px] font-medium" style={{ backgroundColor: cellColor(val), color: val > max * 0.5 ? 'white' : '#6b7280' }} title={`${d} ${h}:00 — ${val} guests`} data-testid={`heat-${d}-${h}`}>
                          {val || ''}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
