import React, { useState, useEffect } from 'react';
import {
  DollarSign, Users, TrendingUp, ArrowRightLeft, Plus, Clock, PiggyBank
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'sonner';
import { advancedAPI, gamificationAPI } from '../services/api';

export default function TipManagement() {
  const { theme } = useTheme();
  const [tips, setTips] = useState([]);
  const [summary, setSummary] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ staffName: '', amount: '', method: 'card', pooled: false, transactionId: '', staffId: '' });
  const [distributing, setDistributing] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    const [tipsRes, sumRes] = await Promise.allSettled([
      advancedAPI.getTips(),
      advancedAPI.getTipsSummary(),
    ]);
    if (tipsRes.status === 'fulfilled') setTips(tipsRes.value.data);
    else toast.error('Failed to load tips');
    if (sumRes.status === 'fulfilled') setSummary(sumRes.value.data);
    else toast.error('Failed to load tip summary');
  };

  const handleAdd = async () => {
    if (!form.staffName || !form.amount) { toast.error('Staff name and amount required'); return; }
    try {
      await advancedAPI.addTip({ ...form, amount: parseFloat(form.amount) });
      toast.success('Tip recorded');
      setShowAdd(false);
      setForm({ staffName: '', amount: '', method: 'card', pooled: false, transactionId: '', staffId: '' });
      fetchData();
    } catch { toast.error('Failed to add tip'); }
  };

  const handleDistribute = async () => {
    setDistributing(true);
    try {
      const res = await gamificationAPI.smartDistributeTips();
      if (res.data.distributions) {
        toast.success(`Smart distributed $${res.data.poolTotal} to ${res.data.distributions.length} staff (weighted by hours + performance)`);
      } else {
        toast.info(res.data.message || 'No pooled tips to distribute');
      }
      fetchData();
    } catch { toast.error('Failed to distribute'); }
    setDistributing(false);
  };

  return (
    <div data-testid="tip-management-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Tip Management</h1>
          <p className="text-gray-500 mt-1">Track, pool, and distribute tips across staff</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleDistribute} disabled={distributing || !summary?.pooledAmount}
            data-testid="distribute-tips-btn">
            <ArrowRightLeft size={16} className="mr-1" /> Distribute Pool
          </Button>
          <Button onClick={() => setShowAdd(true)} style={{ backgroundColor: theme.primary }}
            data-testid="add-tip-btn">
            <Plus size={16} className="mr-1" /> Record Tip
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card><CardContent className="p-4 text-center">
            <DollarSign size={20} className="mx-auto mb-1 text-emerald-500" />
            <p className="text-2xl font-bold text-emerald-600">${summary.totalTips.toFixed(2)}</p>
            <p className="text-xs text-gray-500">Total Tips</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <PiggyBank size={20} className="mx-auto mb-1 text-blue-500" />
            <p className="text-2xl font-bold text-blue-600">${summary.pooledAmount.toFixed(2)}</p>
            <p className="text-xs text-gray-500">Pooled Amount</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <Users size={20} className="mx-auto mb-1 text-violet-500" />
            <p className="text-2xl font-bold text-violet-600">{summary.byStaff.length}</p>
            <p className="text-xs text-gray-500">Staff with Tips</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <TrendingUp size={20} className="mx-auto mb-1 text-amber-500" />
            <p className="text-2xl font-bold text-amber-600">{summary.tipCount}</p>
            <p className="text-xs text-gray-500">Total Entries</p>
          </CardContent></Card>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Staff Breakdown */}
        <Card className="md:col-span-1"><CardContent className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Users size={18} /> By Staff</h3>
          <div className="space-y-3">
            {summary?.byStaff.map((s, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm font-medium">{s.name}</p>
                  <p className="text-xs text-gray-400">{s.count} tips</p>
                </div>
                <span className="font-bold text-emerald-600">${s.total.toFixed(2)}</span>
              </div>
            ))}
            {(!summary?.byStaff || summary.byStaff.length === 0) && (
              <p className="text-sm text-gray-400 text-center py-4">No tips recorded yet</p>
            )}
          </div>
        </CardContent></Card>

        {/* Recent Tips */}
        <Card className="md:col-span-2"><CardContent className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Clock size={18} /> Recent Tips</h3>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {tips.slice(0, 50).map(t => (
              <div key={t.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50" data-testid={`tip-${t.id}`}>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
                    style={{ backgroundColor: theme.primary }}>
                    {t.staffName?.charAt(0) || '?'}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{t.staffName}</p>
                    <p className="text-xs text-gray-400">{new Date(t.createdAt).toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {t.pooled && <Badge className="bg-blue-100 text-blue-700 text-[10px]">Pooled</Badge>}
                  <Badge variant="outline" className="text-[10px]">{t.method}</Badge>
                  <span className="font-bold text-emerald-600">${t.amount.toFixed(2)}</span>
                </div>
              </div>
            ))}
            {tips.length === 0 && (
              <div className="text-center py-8">
                <DollarSign size={40} className="mx-auto mb-3 text-gray-300" />
                <p className="text-gray-500">No tips recorded yet</p>
                <p className="text-sm text-gray-400">Click "Record Tip" to get started</p>
              </div>
            )}
          </div>
        </CardContent></Card>
      </div>

      {/* Add Tip Dialog */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="max-w-sm" data-testid="add-tip-dialog">
          <DialogHeader><DialogTitle>Record Tip</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Staff name" value={form.staffName}
              onChange={e => setForm({ ...form, staffName: e.target.value })} data-testid="tip-staff-name" />
            <Input type="number" step="0.01" placeholder="Amount ($)" value={form.amount}
              onChange={e => setForm({ ...form, amount: e.target.value })} data-testid="tip-amount" />
            <select className="w-full p-2 border rounded-md text-sm" value={form.method}
              onChange={e => setForm({ ...form, method: e.target.value })} data-testid="tip-method">
              <option value="card">Card</option>
              <option value="cash">Cash</option>
              <option value="digital">Digital</option>
            </select>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.pooled}
                onChange={e => setForm({ ...form, pooled: e.target.checked })} data-testid="tip-pooled" />
              Add to tip pool (shared equally)
            </label>
            <Button className="w-full" style={{ backgroundColor: theme.primary }}
              onClick={handleAdd} data-testid="confirm-add-tip">
              Record Tip
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
