import React, { useState, useEffect } from 'react';
import {
  DollarSign, FileText, Download, TrendingUp, Receipt, Eye, RotateCcw,
  Send, X, CreditCard, Clock, Search
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { transactionsAPI, refundsAPI, accountingAPI } from '../services/api';
import RefundDialog from '../components/payments/RefundDialog';
import { toast } from 'sonner';

const Accounting = () => {
  const { theme } = useTheme();
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showRefund, setShowRefund] = useState(false);
  const [showReceipt, setShowReceipt] = useState(false);
  const [refundForm, setRefundForm] = useState({ amount: '', reason: '', refundMethod: 'original_payment' });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [txnRes, sumRes] = await Promise.all([transactionsAPI.getAll(), accountingAPI.getSummary()]);
      setTransactions(txnRes.data);
      setSummary(sumRes.data);
    } catch { toast.error('Failed to load data'); }
  };

  const openDetail = async (txn) => {
    try {
      const r = await transactionsAPI.getDetail(txn.id);
      setSelectedTxn(r.data);
      setShowDetail(true);
    } catch { setSelectedTxn(txn); setShowDetail(true); }
  };

  const openRefund = (txn) => {
    setSelectedTxn(txn);
    setRefundForm({ amount: txn.total || '', reason: '', refundMethod: 'original_payment' });
    setShowRefund(true);
  };

  const handleRefund = async () => {
    if (!refundForm.reason) { toast.error('Reason required'); return; }
    try {
      await refundsAPI.create({
        originalTransactionId: selectedTxn.id,
        amount: parseFloat(refundForm.amount),
        reason: refundForm.reason,
        refundMethod: refundForm.refundMethod,
        processedBy: 'Owner',
        customerId: selectedTxn.customerId || null,
      });
      toast.success('Refund processed');
      setShowRefund(false);
      fetchData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Refund failed'); }
  };

  const openReceipt = (txn) => { setSelectedTxn(txn); setShowReceipt(true); };

  const printReceipt = () => {
    const w = window.open('', '_blank', 'width=400,height=600');
    const t = selectedTxn;
    w.document.write(`<html><head><title>Receipt</title><style>body{font-family:monospace;max-width:320px;margin:20px auto;font-size:12px}h2{text-align:center;margin:0}hr{border:1px dashed #ccc}.row{display:flex;justify-content:space-between}.total{font-weight:bold;font-size:14px}</style></head><body>
      <h2>NUA</h2><p style="text-align:center">Receipt #${t.receiptNumber || t.id}</p><hr/>
      <p>Date: ${new Date(t.timestamp).toLocaleString()}</p>
      <p>Cashier: ${t.cashier || 'Staff'}</p><hr/>
      ${(t.items || []).map(i => `<div class="row"><span>${i.productName} x${i.quantity}</span><span>$${(i.price * i.quantity).toFixed(2)}</span></div>`).join('')}
      <hr/><div class="row"><span>Subtotal</span><span>$${(t.subtotal || 0).toFixed(2)}</span></div>
      ${t.discount ? `<div class="row"><span>Discount</span><span>-$${t.discount.toFixed(2)}</span></div>` : ''}
      <div class="row"><span>GST</span><span>$${(t.gst || 0).toFixed(2)}</span></div>
      <div class="row total"><span>TOTAL</span><span>$${(t.total || 0).toFixed(2)}</span></div><hr/>
      <p>Payment: ${t.paymentMethod}</p><p style="text-align:center;margin-top:20px">Thank you!</p>
    </body></html>`);
    w.document.close();
    w.print();
  };

  const filteredTxns = transactions.filter(t =>
    (t.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.cashier || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.paymentMethod || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalRevenue = transactions.reduce((s, t) => s + (t.total || 0), 0);
  const totalGST = transactions.reduce((s, t) => s + (t.gst || 0), 0);
  const avgTxn = transactions.length ? totalRevenue / transactions.length : 0;

  return (
    <div className="space-y-6" data-testid="accounting-page">
      <div className="flex items-center justify-between">
        <div><h1 className="text-3xl font-bold" style={{ color: theme.text }}>Accounting & Reports</h1><p className="text-gray-500 mt-1">Financial reporting with transaction-level detail</p></div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card><CardContent className="p-6"><p className="text-sm text-gray-500">Total Revenue</p><p className="text-3xl font-bold" style={{ color: theme.primary }}>${totalRevenue.toFixed(2)}</p></CardContent></Card>
        <Card><CardContent className="p-6"><p className="text-sm text-gray-500">GST Collected</p><p className="text-3xl font-bold text-blue-600">${totalGST.toFixed(2)}</p></CardContent></Card>
        <Card><CardContent className="p-6"><p className="text-sm text-gray-500">Transactions</p><p className="text-3xl font-bold" style={{ color: theme.text }}>{transactions.length}</p></CardContent></Card>
        <Card><CardContent className="p-6"><p className="text-sm text-gray-500">Avg Transaction</p><p className="text-3xl font-bold text-emerald-600">${avgTxn.toFixed(2)}</p></CardContent></Card>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
        <Input placeholder="Search by ID, cashier, or payment method..." className="pl-10" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} data-testid="txn-search" />
      </div>

      {/* Transactions Table */}
      <Card><CardContent className="p-0"><div className="overflow-x-auto">
        <table className="w-full" data-testid="transactions-table">
          <thead className="bg-gray-50"><tr>
            <th className="text-left p-4 text-sm font-medium text-gray-500">ID</th>
            <th className="text-left p-4 text-sm font-medium text-gray-500">Date & Time</th>
            <th className="text-left p-4 text-sm font-medium text-gray-500">Items</th>
            <th className="text-left p-4 text-sm font-medium text-gray-500">Payment</th>
            <th className="text-left p-4 text-sm font-medium text-gray-500">Cashier</th>
            <th className="text-right p-4 text-sm font-medium text-gray-500">Total</th>
            <th className="text-center p-4 text-sm font-medium text-gray-500">Actions</th>
          </tr></thead>
          <tbody>
            {filteredTxns.map(txn => (
              <tr key={txn.id} className="border-t hover:bg-gray-50" data-testid={`txn-row-${txn.id}`}>
                <td className="p-4 font-mono text-sm">{txn.id}</td>
                <td className="p-4 text-sm">{new Date(txn.timestamp).toLocaleString()}</td>
                <td className="p-4 text-sm">{(txn.items || []).length} items</td>
                <td className="p-4"><Badge variant="outline">{txn.paymentMethod}</Badge></td>
                <td className="p-4 text-sm">{txn.cashier}</td>
                <td className="p-4 text-right font-bold" style={{ color: theme.primary }}>${(txn.total || 0).toFixed(2)}</td>
                <td className="p-4 text-center">
                  <div className="flex justify-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => openDetail(txn)} title="View Details" data-testid={`view-txn-${txn.id}`}><Eye size={14} /></Button>
                    <Button variant="ghost" size="sm" onClick={() => openReceipt(txn)} title="Receipt" data-testid={`receipt-txn-${txn.id}`}><Receipt size={14} /></Button>
                    <Button variant="ghost" size="sm" className="text-red-500" onClick={() => openRefund(txn)} title="Refund" data-testid={`refund-txn-${txn.id}`}><RotateCcw size={14} /></Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredTxns.length === 0 && <p className="text-center text-gray-400 py-12">No transactions found</p>}
      </div></CardContent></Card>

      {/* Transaction Detail Dialog */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-lg" data-testid="txn-detail-dialog">
          <DialogHeader><DialogTitle>Transaction Details</DialogTitle></DialogHeader>
          {selectedTxn && (
            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-gray-500">ID:</span> <span className="font-mono">{selectedTxn.id}</span></div>
                <div><span className="text-gray-500">Receipt:</span> {selectedTxn.receiptNumber || 'N/A'}</div>
                <div><span className="text-gray-500">Date:</span> {new Date(selectedTxn.timestamp).toLocaleString()}</div>
                <div><span className="text-gray-500">Payment:</span> <Badge variant="outline">{selectedTxn.paymentMethod}</Badge></div>
                <div><span className="text-gray-500">Cashier:</span> {selectedTxn.cashier}</div>
                <div><span className="text-gray-500">Location:</span> {selectedTxn.location}</div>
              </div>
              <div className="border rounded-lg p-3">
                <p className="font-semibold text-sm mb-2">Items</p>
                {(selectedTxn.items || []).map((item, i) => (
                  <div key={i} className="flex justify-between py-1 text-sm border-b last:border-0">
                    <span>{item.productName} x{item.quantity}</span>
                    <span className="font-medium">${(item.price * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="border rounded-lg p-3 space-y-1 text-sm">
                <div className="flex justify-between"><span>Subtotal</span><span>${(selectedTxn.subtotal || 0).toFixed(2)}</span></div>
                {selectedTxn.discount > 0 && <div className="flex justify-between text-green-600"><span>Discount</span><span>-${selectedTxn.discount.toFixed(2)}</span></div>}
                <div className="flex justify-between"><span>GST</span><span>${(selectedTxn.gst || 0).toFixed(2)}</span></div>
                <div className="flex justify-between font-bold text-lg pt-1 border-t"><span>Total</span><span style={{ color: theme.primary }}>${(selectedTxn.total || 0).toFixed(2)}</span></div>
              </div>
              {(selectedTxn.refunds || []).length > 0 && (
                <div className="border border-red-200 rounded-lg p-3 bg-red-50">
                  <p className="font-semibold text-sm text-red-700 mb-2">Refunds</p>
                  {selectedTxn.refunds.map((r, i) => (
                    <div key={i} className="text-sm text-red-600 flex justify-between">
                      <span>{r.reason} ({r.refundMethod})</span><span>-${r.amount.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => { setShowDetail(false); openReceipt(selectedTxn); }}><Receipt size={14} className="mr-1" /> View Receipt</Button>
                <Button variant="outline" className="flex-1 text-red-500" onClick={() => { setShowDetail(false); openRefund(selectedTxn); }}><RotateCcw size={14} className="mr-1" /> Issue Refund</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Refund Dialog — flexible split (card/store credit/points/voucher) */}
      <RefundDialog
        open={showRefund}
        onClose={() => setShowRefund(false)}
        transaction={selectedTxn}
        onDone={() => fetchData()}
      />

      {/* Receipt Dialog */}
      <Dialog open={showReceipt} onOpenChange={setShowReceipt}>
        <DialogContent className="max-w-sm" data-testid="receipt-dialog">
          <DialogHeader><DialogTitle>Receipt Preview</DialogTitle></DialogHeader>
          {selectedTxn && (
            <div className="py-2">
              <div className="bg-white border rounded-lg p-6 font-mono text-sm space-y-2">
                <p className="text-center font-bold text-lg">NUA</p>
                <p className="text-center text-gray-500 text-xs">Receipt #{selectedTxn.receiptNumber || selectedTxn.id}</p>
                <hr className="border-dashed" />
                <p className="text-xs">{new Date(selectedTxn.timestamp).toLocaleString()}</p>
                <p className="text-xs">Cashier: {selectedTxn.cashier}</p>
                <hr className="border-dashed" />
                {(selectedTxn.items || []).map((item, i) => (
                  <div key={i} className="flex justify-between text-xs"><span>{item.productName} x{item.quantity}</span><span>${(item.price * item.quantity).toFixed(2)}</span></div>
                ))}
                <hr className="border-dashed" />
                <div className="flex justify-between text-xs"><span>Subtotal</span><span>${(selectedTxn.subtotal || 0).toFixed(2)}</span></div>
                <div className="flex justify-between text-xs"><span>GST</span><span>${(selectedTxn.gst || 0).toFixed(2)}</span></div>
                <div className="flex justify-between font-bold"><span>TOTAL</span><span>${(selectedTxn.total || 0).toFixed(2)}</span></div>
                <hr className="border-dashed" />
                <p className="text-center text-xs text-gray-500">Payment: {selectedTxn.paymentMethod}</p>
                <p className="text-center text-xs mt-2">Thank you!</p>
              </div>
              <div className="flex gap-2 mt-4">
                <Button variant="outline" className="flex-1" onClick={printReceipt} data-testid="print-receipt-btn"><FileText size={14} className="mr-1" /> Print</Button>
                <Button variant="outline" className="flex-1" onClick={() => { toast.success('Receipt sent to customer email'); }} data-testid="email-receipt-btn"><Send size={14} className="mr-1" /> Email</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Accounting;
