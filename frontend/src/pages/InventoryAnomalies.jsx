import React, { useState, useEffect } from 'react';
import { AlertTriangle, TrendingUp, RefreshCw } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { v15API } from '../services/api';

export default function InventoryAnomalies() {
  const { theme } = useTheme();
  const [data, setData] = useState({ anomalies: [], checkedAt: null });
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try { const r = await v15API.getAnomalies(); setData(r.data || { anomalies: [] }); } catch {}
    setLoading(false);
  };
  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-6" data-testid="anomalies-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <AlertTriangle size={22} className="text-amber-500" /> Inventory Anomalies
          </h1>
          <p className="text-sm text-gray-500">AI-flagged items with unusual sales velocity vs 30-day average.</p>
        </div>
        <Button variant="outline" onClick={refresh} disabled={loading} data-testid="refresh-anomalies"><RefreshCw size={14} className="mr-1" /> Refresh</Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.anomalies.map(a => (
          <Card key={a.productId} data-testid={`anomaly-${a.productId}`}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-bold">{a.productName}</h3>
                <Badge className="bg-amber-100 text-amber-700">+{a.spikePercent}%</Badge>
              </div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Recent daily</span><span className="font-semibold">{a.recentDaily}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Historical avg</span><span>{a.historicalDaily}</span></div>
              </div>
              <p className="text-xs text-amber-700 mt-3 bg-amber-50 p-2 rounded">{a.suggestion}</p>
            </CardContent>
          </Card>
        ))}
        {data.anomalies.length === 0 && !loading && (
          <Card className="col-span-3 border-dashed"><CardContent className="py-12 text-center text-gray-400"><TrendingUp size={40} className="mx-auto mb-3 opacity-30" /><p>No anomalies detected. Inventory velocity looks normal.</p></CardContent></Card>
        )}
      </div>
      {data.checkedAt && <p className="text-[10px] text-gray-400 text-right">Last checked: {new Date(data.checkedAt).toLocaleString()}</p>}
    </div>
  );
}
