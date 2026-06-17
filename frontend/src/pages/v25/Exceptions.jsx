import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { AlertTriangle } from 'lucide-react';

export default function Exceptions() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  useEffect(() => { v25API.exceptions().then(r => setData(r.data)).catch(() => {}); }, []);
  return (
    <div className="space-y-6" data-testid="exceptions-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><AlertTriangle className="text-red-600" /> Loss Control Center</h1>
      {!data ? <div className="text-center py-20 text-gray-400">Loading…</div> : (
        <>
          <div className="grid grid-cols-4 gap-4">
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Voids</p><p className="text-3xl font-bold">{data.totals.voids}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Comps</p><p className="text-3xl font-bold">{data.totals.comps}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Discounts</p><p className="text-3xl font-bold">${data.totals.discounts}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Refunds</p><p className="text-3xl font-bold">{data.totals.refunds}</p></CardContent></Card>
          </div>
          {data.suspicious.length > 0 && (
            <Card className="border-red-300 bg-red-50"><CardContent className="p-5">
              <p className="font-bold text-red-700 mb-2">Suspicious activity</p>
              {data.suspicious.map(s => <div key={s.user} className="text-sm">{s.user}: {s.voids} voids in 14 days</div>)}
            </CardContent></Card>
          )}
        </>
      )}
    </div>
  );
}
