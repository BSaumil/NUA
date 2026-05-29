import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { aiWave2API } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { DollarSign, AlertTriangle, TrendingDown, RefreshCw, Sparkles } from 'lucide-react';

export default function AICostCoach() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = async () => {
    setLoading(true);
    try { const r = await aiWave2API.costCoach(); setData(r.data); }
    catch (e) { toast({ title: 'Error', description: 'Failed to load cost coach', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetch(); }, []);

  return (
    <div className="space-y-6" data-testid="cost-coach-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <DollarSign className="text-emerald-600" /> AI Cost Coach
          </h1>
          <p className="text-sm text-gray-500 mt-1">30-day food-cost analysis · target 32%</p>
        </div>
        <Button onClick={fetch} variant="outline" data-testid="cost-coach-refresh"><RefreshCw size={14} className="mr-1.5" /> Refresh</Button>
      </div>

      {loading ? (
        <div className="text-center py-20 text-gray-400">Crunching numbers…</div>
      ) : data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card><CardContent className="p-5">
              <p className="text-xs uppercase tracking-widest text-gray-500">Overall Food Cost</p>
              <p className="text-3xl font-bold mt-1" style={{ color: data.overallCostPct > data.targetCostPct ? '#dc2626' : '#059669' }} data-testid="overall-cost-pct">
                {data.overallCostPct}%
              </p>
              <p className="text-xs text-gray-400 mt-1">target {data.targetCostPct}%</p>
            </CardContent></Card>
            <Card><CardContent className="p-5">
              <p className="text-xs uppercase tracking-widest text-gray-500">Revenue (30d)</p>
              <p className="text-3xl font-bold mt-1">${data.totalRevenue30d.toLocaleString()}</p>
            </CardContent></Card>
            <Card><CardContent className="p-5">
              <p className="text-xs uppercase tracking-widest text-gray-500">Food Cost (30d)</p>
              <p className="text-3xl font-bold mt-1">${data.totalFoodCost30d.toLocaleString()}</p>
            </CardContent></Card>
            <Card><CardContent className="p-5">
              <p className="text-xs uppercase tracking-widest text-gray-500">Offenders</p>
              <p className="text-3xl font-bold mt-1 text-red-600">{data.offenders.length}</p>
              <p className="text-xs text-gray-400 mt-1">items above target +5%</p>
            </CardContent></Card>
          </div>

          {Array.isArray(data.actions) && data.actions.length > 0 && (
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="p-5">
                <h2 className="text-sm font-bold uppercase tracking-widest text-amber-800 mb-3 flex items-center gap-2"><Sparkles size={14} /> AI Recommended Actions</h2>
                <ul className="space-y-2" data-testid="ai-actions">
                  {data.actions.map((a, i) => (
                    <li key={i} className="flex gap-2 text-sm text-amber-900">
                      <span className="font-bold">{i + 1}.</span><span>{a}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="p-0">
              <div className="px-5 py-4 border-b flex items-center gap-2">
                <AlertTriangle size={16} className="text-red-500" />
                <h2 className="font-bold">Top Cost Offenders</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="offenders-table">
                  <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                    <tr>
                      <th className="text-left px-5 py-3">Item</th>
                      <th className="text-right px-5 py-3">Units (30d)</th>
                      <th className="text-right px-5 py-3">Revenue</th>
                      <th className="text-right px-5 py-3">Food Cost</th>
                      <th className="text-right px-5 py-3">Cost %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.offenders.length === 0 ? (
                      <tr><td colSpan={5} className="text-center py-8 text-gray-400">No offenders. Great job!</td></tr>
                    ) : data.offenders.map(o => (
                      <tr key={o.productId} className="border-t hover:bg-gray-50" data-testid={`offender-${o.productId}`}>
                        <td className="px-5 py-3 font-medium">{o.name}</td>
                        <td className="px-5 py-3 text-right">{o.units}</td>
                        <td className="px-5 py-3 text-right">${o.revenue.toLocaleString()}</td>
                        <td className="px-5 py-3 text-right">${o.foodCost.toLocaleString()}</td>
                        <td className="px-5 py-3 text-right">
                          <Badge className="bg-red-100 text-red-700 hover:bg-red-100"><TrendingDown size={10} className="mr-0.5" /> {o.costPct}%</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
