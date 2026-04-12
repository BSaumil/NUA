import React, { useState, useEffect } from 'react';
import {
  FileText, DollarSign, CreditCard, Clock, TrendingUp, Receipt, BarChart3
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;
const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });

export default function EndOfDay() {
  const { theme } = useTheme();
  const [report, setReport] = useState(null);
  const [tipSummary, setTipSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchReport(); }, []);

  const fetchReport = async () => {
    try {
      const [eod, tips] = await Promise.all([
        axios.get(`${API}/api/reports/end-of-day`, { headers: authHeader() }),
        axios.get(`${API}/api/tips/summary`, { headers: authHeader() }).catch(() => ({ data: null })),
      ]);
      setReport(eod.data);
      setTipSummary(tips.data);
    } catch (e) { toast.error('Failed to load report'); }
    setLoading(false);
  };

  if (loading) return <div className="flex justify-center py-12"><div className="animate-pulse text-gray-400">Loading report...</div></div>;
  if (!report) return null;
  const s = report.summary;

  return (
    <div data-testid="end-of-day-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>End of Day Report</h1>
          <p className="text-gray-500 mt-1">{report.date}</p>
        </div>
        <Badge className="bg-emerald-100 text-emerald-700 text-sm px-3 py-1">
          <Receipt size={14} className="mr-1" /> {s.totalTransactions} Transactions
        </Badge>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card><CardContent className="p-4">
          <p className="text-sm text-gray-500 flex items-center gap-1"><DollarSign size={14} /> Gross Sales</p>
          <p className="text-2xl font-bold mt-1" style={{ color: theme.primary }}>${s.totalSales.toLocaleString()}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <p className="text-sm text-gray-500 flex items-center gap-1"><TrendingUp size={14} /> Net Sales</p>
          <p className="text-2xl font-bold mt-1 text-emerald-600">${s.netSales.toLocaleString()}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <p className="text-sm text-gray-500 flex items-center gap-1"><CreditCard size={14} /> Avg Ticket</p>
          <p className="text-2xl font-bold mt-1 text-blue-600">${s.avgTicket.toFixed(2)}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <p className="text-sm text-gray-500 flex items-center gap-1"><Receipt size={14} /> GST Collected</p>
          <p className="text-2xl font-bold mt-1 text-amber-600">${s.totalGST.toFixed(2)}</p>
        </CardContent></Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Payment Methods */}
        <Card><CardContent className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><CreditCard size={18} /> By Payment Method</h3>
          <div className="space-y-3">
            {report.byPaymentMethod.map((pm, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                <span className="text-sm font-medium">{pm.method}</span>
                <span className="font-bold">${pm.total.toFixed(2)}</span>
              </div>
            ))}
            {report.byPaymentMethod.length === 0 && <p className="text-gray-400 text-sm">No transactions today</p>}
          </div>
        </CardContent></Card>

        {/* Top Items */}
        <Card><CardContent className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><BarChart3 size={18} /> Top Selling Items</h3>
          <div className="space-y-3">
            {report.topItems.map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm font-medium">{item.name}</p>
                  <p className="text-xs text-gray-400">{item.qty} sold</p>
                </div>
                <span className="font-bold">${item.revenue.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </CardContent></Card>

        {/* Tips Summary */}
        {tipSummary && (
          <Card><CardContent className="p-5">
            <h3 className="font-semibold mb-4 flex items-center gap-2"><DollarSign size={18} /> Tips Summary</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-emerald-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-emerald-600">${tipSummary.totalTips.toFixed(2)}</p>
                <p className="text-xs text-gray-500">Total Tips</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-blue-600">${tipSummary.pooledAmount.toFixed(2)}</p>
                <p className="text-xs text-gray-500">Pooled</p>
              </div>
            </div>
            <div className="space-y-2">
              {tipSummary.byStaff.map((s, i) => (
                <div key={i} className="flex items-center justify-between text-sm py-1">
                  <span>{s.name}</span>
                  <span className="font-bold">${s.total.toFixed(2)} <span className="text-gray-400 font-normal">({s.count})</span></span>
                </div>
              ))}
            </div>
          </CardContent></Card>
        )}

        {/* Refunds & Adjustments */}
        <Card><CardContent className="p-5">
          <h3 className="font-semibold mb-4">Refunds & Adjustments</h3>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b">
              <span className="text-sm">Total Refunds</span>
              <span className="font-bold text-red-600">-${s.totalRefunds.toFixed(2)}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-sm">Total Tips</span>
              <span className="font-bold text-emerald-600">+${s.totalTips.toFixed(2)}</span>
            </div>
            <div className="flex justify-between py-2 font-bold text-lg">
              <span>Net Total</span>
              <span style={{ color: theme.primary }}>${(s.netSales + s.totalTips).toFixed(2)}</span>
            </div>
          </div>
        </CardContent></Card>
      </div>
    </div>
  );
}
