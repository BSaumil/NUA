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

const AccountsReceivable = () => {
  const [invoices, setInvoices] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({
    customerId: '', customerName: '', invoiceNumber: '', issueDate: today(), dueDate: today(),
    total: 0, gst: 0,
  });
  const [rcvFor, setRcvFor] = useState(null);
  const [rcvAmt, setRcvAmt] = useState(0);

  const load = useCallback(async () => {
    try { setInvoices((await financeAPI.listInvoices()).data); }
    catch { toast.error('Could not load invoices'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!form.customerName || !form.total) return toast.error('Customer + total required');
    try {
      await financeAPI.createInvoice({ ...form, total: parseFloat(form.total), gst: parseFloat(form.gst || 0) });
      toast.success('Invoice issued'); setShow(false); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const receive = async () => {
    try {
      await financeAPI.receiveInvoice(rcvFor.id, { amount: parseFloat(rcvAmt), method: 'bank' });
      toast.success('Receipt recorded'); setRcvFor(null); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  return (
    <div className="space-y-4" data-testid="ar-page">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Accounts Receivable · Invoices</h3>
        <Button size="sm" onClick={() => setShow(true)} data-testid="invoice-new-btn"><PlusCircle size={14} className="mr-1" /> New Invoice</Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-slate-50"><tr>
            <th className="p-2 pl-4 text-left text-xs text-slate-500">Inv #</th>
            <th className="p-2 text-left text-xs text-slate-500">Customer</th>
            <th className="p-2 text-left text-xs text-slate-500">Issued</th>
            <th className="p-2 text-left text-xs text-slate-500">Due</th>
            <th className="p-2 text-right text-xs text-slate-500">Total</th>
            <th className="p-2 text-right text-xs text-slate-500">Received</th>
            <th className="p-2 text-center text-xs text-slate-500">Status</th>
            <th className="p-2 pr-4"></th>
          </tr></thead>
          <tbody>
            {invoices.map(inv => (
              <tr key={inv.id} className="border-t hover:bg-slate-50">
                <td className="p-2 pl-4 font-mono text-xs">{inv.invoiceNumber || inv.id.slice(0, 8)}</td>
                <td className="p-2">{inv.customerName}</td>
                <td className="p-2">{inv.issueDate}</td>
                <td className="p-2">{inv.dueDate}</td>
                <td className="p-2 text-right">{FMT(inv.total)}</td>
                <td className="p-2 text-right text-emerald-600">{FMT(inv.paidAmount)}</td>
                <td className="p-2 text-center"><Badge variant={inv.status === 'paid' ? 'default' : 'outline'}>{inv.status}</Badge></td>
                <td className="p-2 pr-4 text-right">
                  {inv.status !== 'paid' && (
                    <Button size="sm" onClick={() => { setRcvFor(inv); setRcvAmt(inv.total - (inv.paidAmount || 0)); }} data-testid={`invoice-receive-${inv.id.slice(0,6)}`}>Receive</Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoices.length === 0 && <p className="text-center text-slate-400 py-8">No invoices yet</p>}
      </CardContent></Card>

      <Dialog open={show} onOpenChange={setShow}>
        <DialogContent data-testid="invoice-new-dialog">
          <DialogHeader><DialogTitle>New Invoice</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Customer ID" value={form.customerId} onChange={e => setForm({ ...form, customerId: e.target.value })} />
            <Input placeholder="Customer name" value={form.customerName} onChange={e => setForm({ ...form, customerName: e.target.value })} data-testid="invoice-customer" />
            <Input placeholder="Invoice number" value={form.invoiceNumber} onChange={e => setForm({ ...form, invoiceNumber: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <Input type="date" value={form.issueDate} onChange={e => setForm({ ...form, issueDate: e.target.value })} />
              <Input type="date" value={form.dueDate} onChange={e => setForm({ ...form, dueDate: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input type="number" placeholder="Total" value={form.total} onChange={e => setForm({ ...form, total: e.target.value })} data-testid="invoice-total" />
              <Input type="number" placeholder="GST" value={form.gst} onChange={e => setForm({ ...form, gst: e.target.value })} />
            </div>
            <Button className="w-full" onClick={save} data-testid="invoice-save-btn">Create Invoice</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!rcvFor} onOpenChange={o => !o && setRcvFor(null)}>
        <DialogContent data-testid="invoice-receive-dialog">
          <DialogHeader><DialogTitle>Receive Payment · {rcvFor?.invoiceNumber}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-500">Outstanding: {FMT((rcvFor?.total || 0) - (rcvFor?.paidAmount || 0))}</p>
            <Input type="number" value={rcvAmt} onChange={e => setRcvAmt(e.target.value)} data-testid="invoice-receive-amount" />
            <Button className="w-full" onClick={receive} data-testid="invoice-receive-submit">Record Receipt</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AccountsReceivable;
