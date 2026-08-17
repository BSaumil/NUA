import React, { useState, useEffect, useCallback, useRef } from 'react';
import { financeAPI } from '../../services/api';
import { toast } from 'sonner';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { PlusCircle, Upload, Brain, RefreshCw } from 'lucide-react';
import { FMT, today } from './helpers';

const emptyForm = { customerId: '', customerName: '', invoiceNumber: '', issueDate: today(), dueDate: today(), total: 0, gst: 0, lines: [] };

const AccountsReceivable = () => {
  const [invoices, setInvoices] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [customerMatched, setCustomerMatched] = useState(null); // null = manual entry, true/false = from an upload
  const [rcvFor, setRcvFor] = useState(null);
  const [rcvAmt, setRcvAmt] = useState(0);
  // Upload-to-draft — AI OCR reads a photo/pasted invoice into the form above
  // instead of typing every field by hand.
  const [showUpload, setShowUpload] = useState(false);
  const [uploadText, setUploadText] = useState('');
  const [parsing, setParsing] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    try { setInvoices((await financeAPI.listInvoices()).data); }
    catch { toast.error('Could not load invoices'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!form.customerName || !form.total) return toast.error('Customer + total required');
    if (!form.customerId) return toast.error('Customer ID required — pick a match or enter one manually');
    try {
      await financeAPI.createInvoice({ ...form, total: parseFloat(form.total), gst: parseFloat(form.gst || 0) });
      toast.success('Invoice issued'); setShow(false); setForm(emptyForm); setCustomerMatched(null); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const parseUpload = async (payload) => {
    setParsing(true);
    try {
      const r = await financeAPI.parseInvoiceUpload(payload);
      setForm({
        customerId: r.data.customerId || '', customerName: r.data.customerName || '',
        invoiceNumber: r.data.invoiceNumber || '', issueDate: r.data.issueDate || today(),
        dueDate: r.data.dueDate || today(), total: r.data.total || 0, gst: r.data.gst || 0,
        lines: r.data.lines || [],
      });
      setCustomerMatched(r.data.customerMatched);
      setShowUpload(false); setUploadText(''); setShow(true);
      toast.success(r.data.customerMatched ? `Matched customer: ${r.data.customerName}` : 'Parsed — no customer match, check the ID before saving');
    } catch (e) { toast.error(e.response?.data?.detail || 'Could not parse that invoice'); }
    setParsing(false);
  };

  const handleFileUpload = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.toString().split(',')[1];
      parseUpload({ imageBase64: base64 });
    };
    reader.readAsDataURL(file);
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
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowUpload(true)} data-testid="invoice-upload-btn"><Upload size={14} className="mr-1" /> Upload Invoice</Button>
          <Button size="sm" onClick={() => { setForm(emptyForm); setCustomerMatched(null); setShow(true); }} data-testid="invoice-new-btn"><PlusCircle size={14} className="mr-1" /> New Invoice</Button>
        </div>
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
            {customerMatched === true && (
              <p className="text-xs text-emerald-700 bg-emerald-50 rounded-lg px-3 py-2" data-testid="invoice-match-found">
                Matched to an existing customer — review the details below before saving.
              </p>
            )}
            {customerMatched === false && (
              <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2" data-testid="invoice-match-missing">
                No existing customer matched "{form.customerName}" — enter their Customer ID manually.
              </p>
            )}
            <Input placeholder="Customer ID" value={form.customerId} onChange={e => setForm({ ...form, customerId: e.target.value })} data-testid="invoice-customer-id" />
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
            {form.lines?.length > 0 && (
              <div className="rounded-lg border p-2 text-xs space-y-1" data-testid="invoice-parsed-lines">
                <p className="text-[10px] uppercase font-bold text-slate-400">Line items from upload</p>
                {form.lines.map((l, i) => (
                  <div key={i} className="flex justify-between text-slate-600">
                    <span>{l.description || '—'} {l.quantity ? `×${l.quantity}` : ''}</span>
                    <span>{FMT(l.amount || 0)}</span>
                  </div>
                ))}
              </div>
            )}
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

      <Dialog open={showUpload} onOpenChange={setShowUpload}>
        <DialogContent data-testid="invoice-upload-dialog">
          <DialogHeader><DialogTitle>Upload Invoice</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-500">
              Upload a photo of the invoice or paste its text. AI reads the customer, dates, line items
              and total, matches it to an existing customer where it can, and fills in a draft for you
              to review — nothing is saved until you confirm.
            </p>
            <div
              className="border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center gap-2 hover:border-purple-400 transition cursor-pointer"
              onClick={() => fileRef.current?.click()}
              data-testid="invoice-upload-drop-zone"
            >
              <Upload size={26} className="text-purple-500" />
              <p className="text-sm font-medium">Click to upload invoice image / PDF</p>
              <p className="text-xs text-slate-400">JPG, PNG, PDF</p>
              <input ref={fileRef} type="file" accept="image/*,application/pdf" className="hidden"
                onChange={e => handleFileUpload(e.target.files?.[0])} data-testid="invoice-upload-file-input" />
            </div>
            <div>
              <label className="text-xs uppercase font-bold text-slate-400">Or paste invoice text</label>
              <Textarea rows={5} value={uploadText} onChange={e => setUploadText(e.target.value)}
                placeholder="Paste the invoice text here…" data-testid="invoice-upload-text" />
              <Button onClick={() => parseUpload({ text: uploadText })} disabled={!uploadText || parsing}
                className="mt-2 w-full" data-testid="invoice-upload-parse-btn">
                {parsing ? <><RefreshCw size={14} className="mr-1.5 animate-spin" /> Parsing…</> : <><Brain size={14} className="mr-1.5" /> Parse with AI</>}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AccountsReceivable;
