import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { v25API } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useToast } from '../hooks/use-toast';
import { Shield, RefreshCw, ArrowUpRight } from 'lucide-react';

export default function ProfitGuardian() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [data, setData] = useState({ alerts: [] });
  const [loading, setLoading] = useState(true);
  const fetch = async () => { setLoading(true); try { const r = await v25API.profitGuardian(); setData(r.data); } catch { toast({ title: 'Error', variant: 'destructive' }); } finally { setLoading(false); } };
  useEffect(() => { fetch(); }, []);
  return (
    <div className="space-y-6" data-testid="profit-guardian-page">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Shield className="text-emerald-600" /> Profit Guardian</h1>
        <Button variant="outline" onClick={fetch}><RefreshCw size={14} className="mr-1.5" /> Refresh</Button>
      </div>
      {loading ? <div className="text-center py-20 text-gray-400">Checking margins…</div> : (
        <Card><CardContent className="p-0">
          <table className="w-full text-sm" data-testid="alerts-table">
            <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500"><tr>
              <th className="text-left px-5 py-3">Item</th><th className="text-right px-5 py-3">Margin %</th>
              <th className="text-right px-5 py-3">Current</th><th className="text-right px-5 py-3">Suggested</th>
              <th className="text-left px-5 py-3">Reason</th>
            </tr></thead>
            <tbody>
              {data.alerts.length === 0 ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">No margin alerts</td></tr> :
                data.alerts.map(a => (
                  <tr key={a.productId} className="border-t" data-testid={`alert-${a.productId}`}>
                    <td className="px-5 py-3 font-medium">{a.name}</td>
                    <td className="px-5 py-3 text-right"><Badge className={a.marginPct < 40 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>{a.marginPct}%</Badge></td>
                    <td className="px-5 py-3 text-right font-mono">${a.price.toFixed(2)}</td>
                    <td className="px-5 py-3 text-right font-mono font-bold">${a.suggestedPrice.toFixed(2)} <ArrowUpRight size={10} className="inline text-emerald-600" /></td>
                    <td className="px-5 py-3 text-xs text-gray-500">{a.reason}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </CardContent></Card>
      )}
    </div>
  );
}
