import React, { useState, useEffect } from 'react';
import { FlaskConical, Plus, Trophy } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { phaseEFAPI, productsAPI } from '../services/api';
import { toast } from 'sonner';

export default function MenuABTesting() {
  const { theme } = useTheme();
  const [tests, setTests] = useState([]);
  const [products, setProducts] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ productId: '', nameA: '', priceA: '', nameB: '', priceB: '' });

  const refresh = async () => { try { const r = await phaseEFAPI.getABTests(); setTests(r.data || []); } catch {} };
  useEffect(() => { refresh(); productsAPI.getAll().then(r => setProducts(r.data || [])).catch(() => {}); }, []);

  const create = async () => {
    if (!form.productId || !form.nameA || !form.nameB) { toast.error('Product + both variants required'); return; }
    try {
      await phaseEFAPI.createABTest({
        productId: form.productId,
        variantA: { name: form.nameA, price: parseFloat(form.priceA) || 0 },
        variantB: { name: form.nameB, price: parseFloat(form.priceB) || 0 },
        metric: 'conversions',
      });
      toast.success('A/B test launched');
      setShow(false); setForm({ productId: '', nameA: '', priceA: '', nameB: '', priceB: '' });
      refresh();
    } catch { toast.error('Failed'); }
  };

  const conclude = async (id) => {
    try { const r = await phaseEFAPI.concludeAB(id); toast.success(`Winner: Variant ${r.data?.winner}`); refresh(); }
    catch { toast.error('Failed'); }
  };

  const rate = (test, v) => { const e = test.exposures?.[v] || 0; return e > 0 ? ((test.conversions?.[v] || 0) / e * 100).toFixed(1) : '—'; };

  return (
    <div className="space-y-6" data-testid="ab-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}><FlaskConical size={22} /> Live Menu A/B Testing</h1>
          <p className="text-sm text-gray-500">Test variants on public menu / table-side QR. Half see A, half see B. Winner auto-calculated.</p>
        </div>
        <Button onClick={() => setShow(true)} style={{ backgroundColor: theme.primary }} data-testid="new-ab-btn"><Plus size={14} className="mr-1" /> New Test</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tests.map(t => {
          const p = products.find(pp => pp.id === t.productId);
          const winnerA = t.status === 'concluded' && t.winner === 'A';
          const winnerB = t.status === 'concluded' && t.winner === 'B';
          return (
            <Card key={t.id} data-testid={`ab-${t.id}`}>
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold">{p?.name || t.productId}</h3>
                  <Badge className={t.status === 'running' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}>{t.status}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {['A','B'].map(v => (
                    <div key={v} className={`p-3 rounded-lg border-2 ${(v === 'A' && winnerA) || (v === 'B' && winnerB) ? 'border-amber-400 bg-amber-50' : 'border-gray-200'}`}>
                      <div className="flex items-center gap-1 mb-1">
                        <span className="text-xs font-bold text-gray-500">Variant {v}</span>
                        {((v === 'A' && winnerA) || (v === 'B' && winnerB)) && <Trophy size={12} className="text-amber-500" />}
                      </div>
                      <p className="text-sm font-semibold">{t[`variant${v}`]?.name}</p>
                      <p className="text-xs text-gray-500">${t[`variant${v}`]?.price}</p>
                      <p className="text-xs mt-2"><strong>{t.exposures?.[v] || 0}</strong> shown · <strong>{t.conversions?.[v] || 0}</strong> bought · <span style={{ color: theme.primary }}>{rate(t, v)}%</span></p>
                    </div>
                  ))}
                </div>
                {t.status === 'running' && <Button className="w-full mt-3" size="sm" variant="outline" onClick={() => conclude(t.id)} data-testid={`conclude-${t.id}`}>Conclude & Pick Winner</Button>}
              </CardContent>
            </Card>
          );
        })}
        {tests.length === 0 && <Card className="border-dashed col-span-2"><CardContent className="py-12 text-center text-gray-400"><FlaskConical size={40} className="mx-auto mb-3 opacity-30" /><p>No A/B tests yet</p></CardContent></Card>}
      </div>

      <Dialog open={show} onOpenChange={setShow}>
        <DialogContent className="max-w-md" data-testid="ab-dialog">
          <DialogHeader><DialogTitle>New A/B Test</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <select className="w-full p-2 border rounded-md text-sm" value={form.productId} onChange={e => setForm({ ...form, productId: e.target.value })} data-testid="ab-product">
              <option value="">Select product...</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <div className="p-3 border-2 border-blue-200 rounded-lg space-y-2">
              <p className="text-xs font-bold uppercase text-blue-700">Variant A</p>
              <Input placeholder="Display name (e.g. Avocado Toast)" value={form.nameA} onChange={e => setForm({ ...form, nameA: e.target.value })} data-testid="ab-nameA" />
              <Input type="number" step="0.01" placeholder="Price" value={form.priceA} onChange={e => setForm({ ...form, priceA: e.target.value })} data-testid="ab-priceA" />
            </div>
            <div className="p-3 border-2 border-purple-200 rounded-lg space-y-2">
              <p className="text-xs font-bold uppercase text-purple-700">Variant B</p>
              <Input placeholder="Display name (e.g. Smashed Avo on Sourdough)" value={form.nameB} onChange={e => setForm({ ...form, nameB: e.target.value })} data-testid="ab-nameB" />
              <Input type="number" step="0.01" placeholder="Price" value={form.priceB} onChange={e => setForm({ ...form, priceB: e.target.value })} data-testid="ab-priceB" />
            </div>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={create} data-testid="ab-submit">Launch Test</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
