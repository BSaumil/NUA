import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Trash2 } from 'lucide-react';

export default function WasteTracking() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [log, setLog] = useState([]); const [ins, setIns] = useState(null);
  const [form, setForm] = useState({ productName: '', quantity: 1, reason: 'spoilage', estCost: 0 });
  const load = () => {
    v25API.waste().then(r => setLog(r.data || []));
    v25API.wasteInsights().then(r => setIns(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  const submit = async () => { await v25API.logWaste(form); toast({ title: 'Logged' }); load(); };
  return (
    <div className="space-y-6" data-testid="waste-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Trash2 className="text-slate-600" /> Waste Tracking</h1>
      {ins && (
        <div className="grid grid-cols-3 gap-4">
          <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">30-day Cost</p><p className="text-2xl font-bold">${ins.totalCost30d}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Entries</p><p className="text-2xl font-bold">{ins.entries}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Top Reason</p><p className="font-bold">{Object.entries(ins.byReason || {})[0]?.[0] || 'n/a'}</p></CardContent></Card>
        </div>
      )}
      <Card><CardContent className="p-5 space-y-2">
        <p className="text-sm font-bold">Log Waste</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Input placeholder="Item name" value={form.productName} onChange={e => setForm({ ...form, productName: e.target.value })} />
          <Input type="number" placeholder="Qty" value={form.quantity} onChange={e => setForm({ ...form, quantity: parseFloat(e.target.value) || 0 })} />
          <select className="border rounded px-2" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })}>
            <option>spoilage</option><option>breakage</option><option>staff meals</option><option>over-prep</option>
          </select>
          <Input type="number" placeholder="Cost $" value={form.estCost} onChange={e => setForm({ ...form, estCost: parseFloat(e.target.value) || 0 })} />
        </div>
        <Button onClick={submit} data-testid="log-waste-btn" style={{ background: theme.primary }}>Log</Button>
      </CardContent></Card>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="text-left px-5 py-3">Item</th><th className="text-right px-5 py-3">Qty</th><th className="text-left px-5 py-3">Reason</th><th className="text-right px-5 py-3">Cost</th></tr></thead>
          <tbody>{log.slice(0, 20).map(w => <tr key={w.id} className="border-t"><td className="px-5 py-3">{w.productName}</td><td className="px-5 py-3 text-right">{w.quantity}</td><td className="px-5 py-3">{w.reason}</td><td className="px-5 py-3 text-right">${w.estCost}</td></tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}
