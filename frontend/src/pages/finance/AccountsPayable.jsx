import React, { useState, useEffect, useCallback } from 'react';
import { financeAPI } from '../../services/api';
import { toast } from 'sonner';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { PlusCircle } from 'lucide-react';
import { FMT, today } from './helpers';

const AccountsPayable = () => {
  const [bills, setBills] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({
    supplierId: '', supplierName: '', billNumber: '', issueDate: today(), dueDate: today(),
    total: 0, gst: 0, lines: [{ accountCode: '6900', description: '', amount: 0 }],
  });
  const [payFor, setPayFor] = useState(null);
  const [payAmt, setPayAmt] = useState(0);

  const load = useCallback(async () => {
    try { setBills((await financeAPI.listBills()).data); }
    catch { toast.error('Could not load bills'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!form.supplierName || !form.total) return toast.error('Supplier + total required');
    try {
      await financeAPI.createBill({ ...form, total: parseFloat(form.total), gst: parseFloat(form.gst || 0) });
      toast.success('Bill created & posted');
      setShow(false); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const pay = async () => {
    try {
      await financeAPI.payBill(payFor.id, { amount: parseFloat(payAmt), method: 'bank' });
      toast.success('Payment recorded'); setPayFor(null); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  return (
    <div className="space-y-4" data-testid="ap-page">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Accounts Payable · Bills</h3>
        <Button size="sm" onClick={() => setShow(true)} data-testid="bill-new-btn"><PlusCircle size={14} className="mr-1" /> New Bill</Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-slate-50"><tr>
            <th className="p-2 pl-4 text-left text-xs text-slate-500">Bill #</th>
            <th className="p-2 text-left text-xs text-slate-500">Supplier</th>
            <th className="p-2 text-left text-xs text-slate-500">Issued</th>
            <th className="p-2 text-left text-xs text-slate-500">Due</th>
            <th className="p-2 text-right text-xs text-slate-500">Total</th>
            <th className="p-2 text-right text-xs text-slate-500">Paid</th>
            <th className="p-2 text-center text-xs text-slate-500">Status</th>
            <th className="p-2 pr-4"></th>
          </tr></thead>
          <tbody>
            {bills.map(b => (
              <tr key={b.id} className="border-t hover:bg-slate-50">
                <td className="p-2 pl-4 font-mono text-xs">{b.billNumber || b.id.slice(0, 8)}</td>
                <td className="p-2">{b.supplierName}</td>
                <td className="p-2">{b.issueDate}</td>
                <td className="p-2">{b.dueDate}</td>
                <td className="p-2 text-right">{FMT(b.total)}</td>
                <td className="p-2 text-right text-emerald-600">{FMT(b.paidAmount)}</td>
                <td className="p-2 text-center"><Badge variant={b.status === 'paid' ? 'default' : 'outline'}>{b.status}</Badge></td>
                <td className="p-2 pr-4 text-right">
                  {b.status !== 'paid' && (
                    <Button size="sm" onClick={() => { setPayFor(b); setPayAmt(b.total - (b.paidAmount || 0)); }} data-testid={`bill-pay-${b.id.slice(0,6)}`}>Pay</Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {bills.length === 0 && <p className="text-center text-slate-400 py-8">No bills yet</p>}
      </CardContent></Card>

      <Dialog open={show} onOpenChange={setShow}>
        <DialogContent data-testid="bill-new-dialog">
          <DialogHeader><DialogTitle>New Bill</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Supplier ID" value={form.supplierId} onChange={e => setForm({ ...form, supplierId: e.target.value })} />
            <Input placeholder="Supplier name" value={form.supplierName} onChange={e => setForm({ ...form, supplierName: e.target.value })} data-testid="bill-supplier" />
            <Input placeholder="Bill number" value={form.billNumber} onChange={e => setForm({ ...form, billNumber: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <Input type="date" value={form.issueDate} onChange={e => setForm({ ...form, issueDate: e.target.value })} />
              <Input type="date" value={form.dueDate} onChange={e => setForm({ ...form, dueDate: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input type="number" placeholder="Total (incl. GST)" value={form.total} onChange={e => setForm({ ...form, total: e.target.value })} data-testid="bill-total" />
              <Input type="number" placeholder="GST portion" value={form.gst} onChange={e => setForm({ ...form, gst: e.target.value })} />
            </div>
            <Button className="w-full" onClick={save} data-testid="bill-save-btn">Create Bill</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!payFor} onOpenChange={o => !o && setPayFor(null)}>
        <DialogContent data-testid="bill-pay-dialog">
          <DialogHeader><DialogTitle>Pay Bill · {payFor?.billNumber}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-500">Outstanding: {FMT((payFor?.total || 0) - (payFor?.paidAmount || 0))}</p>
            <Input type="number" value={payAmt} onChange={e => setPayAmt(e.target.value)} data-testid="bill-pay-amount" />
            <Button className="w-full" onClick={pay} data-testid="bill-pay-submit">Record Payment</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AccountsPayable;
