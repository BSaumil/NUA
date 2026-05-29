import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { aiWave2API } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { Tag, RefreshCw, Check, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function PriceTune() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [data, setData] = useState({ recommendations: [], medianVelocity: 0 });
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(null);

  const fetch = async () => {
    setLoading(true);
    try { const r = await aiWave2API.priceTune(); setData(r.data || { recommendations: [] }); }
    catch { toast({ title: 'Error', description: 'Failed to load recommendations', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetch(); }, []);

  const apply = async (rec) => {
    setApplying(rec.productId);
    try {
      await aiWave2API.applyPriceTune(rec.productId, rec.recommendedPrice);
      toast({ title: 'Price updated', description: `${rec.name} → $${rec.recommendedPrice}` });
      await fetch();
    } catch { toast({ title: 'Error', description: 'Failed to apply', variant: 'destructive' }); }
    finally { setApplying(null); }
  };

  return (
    <div className="space-y-6" data-testid="price-tune-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Tag className="text-amber-600" /> Auto Price-Tune
          </h1>
          <p className="text-sm text-gray-500 mt-1">30-day velocity analysis · median {data.medianVelocity} units</p>
        </div>
        <Button onClick={fetch} variant="outline" data-testid="ptune-refresh"><RefreshCw size={14} className="mr-1.5" /> Refresh</Button>
      </div>

      {loading ? <div className="text-center py-20 text-gray-400">Analyzing sales velocity…</div> : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="ptune-table">
                <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                  <tr>
                    <th className="text-left px-5 py-3">Item</th>
                    <th className="text-right px-5 py-3">Current</th>
                    <th className="text-right px-5 py-3">Recommended</th>
                    <th className="text-right px-5 py-3">Δ</th>
                    <th className="text-left px-5 py-3">Reason</th>
                    <th className="text-right px-5 py-3">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recommendations.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-400">No price changes recommended right now</td></tr>
                  ) : data.recommendations.map(r => (
                    <tr key={r.productId} className="border-t hover:bg-gray-50" data-testid={`ptune-row-${r.productId}`}>
                      <td className="px-5 py-3 font-medium">{r.name}</td>
                      <td className="px-5 py-3 text-right font-mono">${r.currentPrice.toFixed(2)}</td>
                      <td className="px-5 py-3 text-right font-mono font-bold">${r.recommendedPrice.toFixed(2)}</td>
                      <td className="px-5 py-3 text-right">
                        <Badge className={r.direction === 'raise' ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100' : 'bg-blue-100 text-blue-700 hover:bg-blue-100'}>
                          {r.direction === 'raise' ? <ArrowUpRight size={10} className="mr-0.5" /> : <ArrowDownRight size={10} className="mr-0.5" />}
                          ${Math.abs(r.delta).toFixed(2)}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-xs text-gray-500 max-w-xs">{r.reason}</td>
                      <td className="px-5 py-3 text-right">
                        <Button size="sm" disabled={applying === r.productId} onClick={() => apply(r)} style={{ background: theme.primary }} data-testid={`ptune-apply-${r.productId}`}>
                          <Check size={12} className="mr-1" /> {applying === r.productId ? 'Applying…' : 'Apply'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
