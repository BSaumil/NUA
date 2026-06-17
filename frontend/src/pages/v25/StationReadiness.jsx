import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { BarChart3 } from 'lucide-react';

export default function StationReadiness() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  useEffect(() => { v25API.stationReadiness().then(r => setData(r.data)); }, []);
  return (
    <div className="space-y-6" data-testid="station-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><BarChart3 className="text-indigo-600" /> Station Readiness</h1>
      {data && (
        <Card><CardContent className="p-8 text-center">
          <p className="text-6xl font-bold" style={{ color: data.score >= 80 ? '#059669' : data.score >= 50 ? '#d97706' : '#dc2626' }}>{data.score}</p>
          <p className="text-sm text-gray-500 mt-2">{data.status.toUpperCase()}</p>
          <div className="grid grid-cols-4 gap-3 mt-6 text-sm">
            <div><p className="text-xs text-gray-500">Pending Tickets</p><p className="font-bold">{data.factors.pendingTickets}</p></div>
            <div><p className="text-xs text-gray-500">Shifts Today</p><p className="font-bold">{data.factors.shiftsToday}</p></div>
            <div><p className="text-xs text-gray-500">Low Stock</p><p className="font-bold">{data.factors.lowStockItems}</p></div>
            <div><p className="text-xs text-gray-500">Printers</p><p className="font-bold">{data.factors.printers}</p></div>
          </div>
        </CardContent></Card>
      )}
    </div>
  );
}
