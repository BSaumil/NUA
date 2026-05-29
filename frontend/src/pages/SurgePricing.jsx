import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { aiWave2API } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { TrendingUp, RefreshCw, Save, Zap, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function SurgePricing() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [recs, setRecs] = useState([]);
  const [avg, setAvg] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState({});

  const fetch = async () => {
    setLoading(true);
    try {
      const [r, a] = await Promise.all([aiWave2API.surgeRecs(), aiWave2API.activeSurge()]);
      setRecs(r.data?.recommendations || []);
      setAvg(r.data?.avgOrdersPerHour || 0);
      const initial = {};
      (a.data?.all || []).forEach(rule => { initial[`${rule.dow}-${rule.hour}`] = true; });
      setSelected(initial);
    } catch { toast({ title: 'Error', description: 'Failed to load surge data', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetch(); }, []);

  const apply = async () => {
    const rules = recs.filter(r => selected[`${r.dow}-${r.hour}`]);
    try {
      await aiWave2API.applySurge(rules);
      toast({ title: 'Applied', description: `${rules.length} surge rules saved` });
    } catch { toast({ title: 'Error', description: 'Failed to apply (Owner only)', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6" data-testid="surge-pricing-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <TrendingUp className="text-purple-600" /> Dynamic Surge Pricing
          </h1>
          <p className="text-sm text-gray-500 mt-1">Per-hour multipliers based on demand · avg {avg} orders/hr</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetch} variant="outline" data-testid="surge-refresh"><RefreshCw size={14} className="mr-1.5" /> Refresh</Button>
          <Button onClick={apply} style={{ background: theme.primary }} data-testid="surge-apply"><Save size={14} className="mr-1.5" /> Apply Selected</Button>
        </div>
      </div>

      {loading ? <div className="text-center py-20 text-gray-400">Analyzing demand…</div> : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="surge-table">
                <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                  <tr>
                    <th className="text-left px-5 py-3">Use</th>
                    <th className="text-left px-5 py-3">Day</th>
                    <th className="text-left px-5 py-3">Hour</th>
                    <th className="text-right px-5 py-3">Demand</th>
                    <th className="text-right px-5 py-3">Multiplier</th>
                    <th className="text-left px-5 py-3">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {recs.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-400">No surge data — need more sales history</td></tr>
                  ) : recs.map(r => {
                    const key = `${r.dow}-${r.hour}`;
                    const isUp = r.multiplier > 1;
                    return (
                      <tr key={key} className="border-t hover:bg-gray-50" data-testid={`surge-row-${key}`}>
                        <td className="px-5 py-3">
                          <input type="checkbox" checked={!!selected[key]} onChange={e => setSelected(s => ({ ...s, [key]: e.target.checked }))} className="h-4 w-4" data-testid={`surge-check-${key}`} />
                        </td>
                        <td className="px-5 py-3 font-medium">{r.day}</td>
                        <td className="px-5 py-3 font-mono">{String(r.hour).padStart(2, '0')}:00</td>
                        <td className="px-5 py-3 text-right text-gray-500">{r.demandRatio}x</td>
                        <td className="px-5 py-3 text-right">
                          <Badge className={isUp ? 'bg-red-100 text-red-700 hover:bg-red-100' : 'bg-blue-100 text-blue-700 hover:bg-blue-100'}>
                            {isUp ? <ArrowUpRight size={10} className="mr-0.5" /> : <ArrowDownRight size={10} className="mr-0.5" />}
                            {(r.multiplier * 100 - 100).toFixed(0)}%
                          </Badge>
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-500">{r.reason}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
