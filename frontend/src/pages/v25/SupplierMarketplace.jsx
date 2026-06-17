import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { ShoppingBag } from 'lucide-react';

export default function SupplierMarketplace() {
  const { theme } = useTheme();
  const [item, setItem] = useState('');
  const [rows, setRows] = useState([]);
  const load = () => v25API.compareSuppliers(item).then(r => setRows(r.data || [])).catch(() => {});
  useEffect(() => { load(); }, []);
  return (
    <div className="space-y-6" data-testid="supplier-marketplace-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><ShoppingBag className="text-teal-600" /> Supplier Marketplace</h1>
      <div className="flex gap-2">
        <Input value={item} onChange={e => setItem(e.target.value)} placeholder="Filter by item..." className="max-w-sm" />
        <Button onClick={load}>Search</Button>
      </div>
      <div className="space-y-3">
        {rows.length === 0 ? <Card><CardContent className="p-8 text-center text-gray-400">No quotes yet — add some via POST /api/v25/suppliers/quote</CardContent></Card> :
          rows.map(c => (
            <Card key={c.item} data-testid={`compare-${c.item}`}>
              <CardContent className="p-5">
                <div className="flex justify-between items-center mb-2">
                  <p className="font-bold">{c.item}</p>
                  {c.annualSavings > 0 && <Badge className="bg-emerald-100 text-emerald-700">Save ${c.annualSavings.toLocaleString()}/yr</Badge>}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {c.quotes.map(q => (
                    <div key={q.id} className={`p-3 border rounded ${q.supplier === c.cheapest ? 'border-emerald-400 bg-emerald-50' : ''}`}>
                      <p className="text-xs text-gray-500">{q.supplier}</p>
                      <p className="font-bold">${q.pricePerUnit}/{q.unit || 'unit'}</p>
                      {q.supplier === c.cheapest && <Badge className="bg-emerald-600 mt-1 text-[10px]">CHEAPEST</Badge>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
      </div>
    </div>
  );
}
