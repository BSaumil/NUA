import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Truck, RefreshCw } from 'lucide-react';

export default function PredictiveOrders() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [data, setData] = useState({ bySupplier: [] });
  const run = async () => { try { const r = await v25API.predictiveOrders(); setData(r.data); toast({ title: 'Generated' }); } catch { toast({ title: 'Error', variant: 'destructive' }); } };
  useEffect(() => { run(); }, []);
  return (
    <div className="space-y-6" data-testid="predictive-orders-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Truck className="text-indigo-600" /> Predictive Ordering</h1>
        <Button onClick={run}><RefreshCw size={14} className="mr-1.5" /> Re-run</Button>
      </div>
      {data.bySupplier.length === 0 ? <Card><CardContent className="p-8 text-center text-gray-400">No suggestions — sales history insufficient</CardContent></Card> :
        data.bySupplier.map(s => (
          <Card key={s.supplier} data-testid={`po-${s.supplier}`}>
            <CardContent className="p-5">
              <div className="flex justify-between mb-3"><p className="font-bold">{s.supplier}</p><p className="text-lg font-bold">${s.total.toFixed(2)}</p></div>
              <div className="space-y-1 text-sm">{s.items.map(i => <div key={i.productId} className="flex justify-between"><span>{i.name}</span><span>{i.orderQty} units</span></div>)}</div>
            </CardContent>
          </Card>
        ))}
    </div>
  );
}
