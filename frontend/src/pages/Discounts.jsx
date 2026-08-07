import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Percent, DollarSign, Gift, Tag } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useTheme } from '../contexts/ThemeContext';
import { itemsSystemAPI } from '../services/api';
import { toast } from 'sonner';
import CompVoid from './CompVoid';

const TYPES = [
  { value: 'percentage', label: '% Off', icon: Percent },
  { value: 'fixed', label: '$ Off', icon: DollarSign },
  { value: 'bundle', label: 'Bundle', icon: Gift },
  { value: 'bogo', label: 'Buy 1 Get 1', icon: Tag },
  { value: 'half_price', label: 'Buy 1 Get Half', icon: Tag },
];

export default function Discounts() {
  const { theme } = useTheme();
  const [tab, setTab] = useState('discounts');
  const [discounts, setDiscounts] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', type: 'percentage', value: '', active: true, startDate: '', endDate: '' });

  useEffect(() => { fetchData(); }, []);
  const fetchData = async () => {
    try { const r = await itemsSystemAPI.getDiscounts(); setDiscounts(r.data); } catch {}
  };

  const openAdd = () => { setEditing(null); setForm({ name: '', type: 'percentage', value: '', active: true, startDate: '', endDate: '' }); setShowDialog(true); };
  const openEdit = (d) => { setEditing(d); setForm({ name: d.name, type: d.type, value: d.value, active: d.active, startDate: d.startDate || '', endDate: d.endDate || '' }); setShowDialog(true); };

  const handleSave = async () => {
    if (!form.name) { toast.error('Name required'); return; }
    const data = { ...form, value: parseFloat(form.value) || 0 };
    try {
      if (editing) { await itemsSystemAPI.updateDiscount(editing.id, data); toast.success('Updated'); }
      else { await itemsSystemAPI.createDiscount(data); toast.success('Created'); }
      setShowDialog(false); fetchData();
    } catch { toast.error('Failed'); }
  };

  return (
    <div className="space-y-6" data-testid="discounts-page">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Discounts, Offers & Comp/Void</h1><p className="text-sm text-gray-500">Manage discounts, BOGO offers, complementary items and voids</p></div>
        <Button style={{ backgroundColor: theme.primary }} onClick={openAdd} data-testid="add-discount-btn"><Plus size={16} className="mr-1" /> New Discount</Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList><TabsTrigger value="discounts">Discounts & Offers</TabsTrigger><TabsTrigger value="comp">Comp / Void History</TabsTrigger></TabsList>

        <TabsContent value="discounts" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {discounts.map(d => (
              <Card key={d.id} data-testid={`disc-${d.id}`}><CardContent className="p-5">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold">{d.name}</h3>
                  <div className="flex gap-1"><Button variant="ghost" size="sm" onClick={() => openEdit(d)}><Edit size={13} /></Button><Button variant="ghost" size="sm" className="text-red-500" onClick={async () => { await itemsSystemAPI.deleteDiscount(d.id); fetchData(); }}><Trash2 size={13} /></Button></div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className="text-sm" style={{ backgroundColor: `${theme.primary}15`, color: theme.primary }}>
                    {d.type === 'percentage' ? `${d.value}% OFF` : d.type === 'fixed' ? `$${d.value} OFF` : d.type === 'bogo' ? 'Buy 1 Get 1' : d.type === 'half_price' ? 'Buy 1 Get Half' : `Bundle $${d.value}`}
                  </Badge>
                  <Badge className={d.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>{d.active ? 'Active' : 'Off'}</Badge>
                </div>
                {(d.startDate || d.endDate) && <p className="text-xs text-gray-400 mt-2">{d.startDate} → {d.endDate}</p>}
              </CardContent></Card>
            ))}
            {discounts.length === 0 && <Card className="col-span-3 border-dashed"><CardContent className="py-12 text-center text-gray-400"><Tag size={40} className="mx-auto mb-3 opacity-30" /><p>No discounts yet</p></CardContent></Card>}
          </div>
        </TabsContent>

        <TabsContent value="comp" className="mt-4">
          <CompVoid embedded />
        </TabsContent>
      </Tabs>

      {/* Discount Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-sm" data-testid="discount-dialog">
          <DialogHeader><DialogTitle>{editing ? 'Edit Discount' : 'New Discount'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Discount name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="disc-name" />
            <select className="w-full p-2 border rounded-md text-sm" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} data-testid="disc-type">
              {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            {(form.type === 'percentage' || form.type === 'fixed' || form.type === 'bundle') && (
              <Input type="number" step="0.01" placeholder={form.type === 'percentage' ? 'Percentage (e.g. 10)' : 'Amount ($)'} value={form.value} onChange={e => setForm({ ...form, value: e.target.value })} data-testid="disc-value" />
            )}
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={form.startDate} onChange={e => setForm({ ...form, startDate: e.target.value })} />
              <Input type="date" value={form.endDate} onChange={e => setForm({ ...form, endDate: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.active} onChange={e => setForm({ ...form, active: e.target.checked })} /> Active</label>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={handleSave} data-testid="save-disc-btn">{editing ? 'Update' : 'Create'}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
