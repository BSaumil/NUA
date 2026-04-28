import React, { useState, useEffect } from 'react';
import {
  FileText, DollarSign, CreditCard, Clock, TrendingUp, Receipt, BarChart3,
  Users, UserPlus, UserCheck, ShoppingBag, PieChart, CalendarDays, Sparkles, Loader2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'sonner';
import { advancedAPI } from '../services/api';

const PERIODS = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'week', label: 'This Week' },
  { value: 'month', label: 'This Month' },
  { value: 'quarter', label: 'This Quarter' },
  { value: 'custom', label: 'Custom Range' },
];

export default function EndOfDay() {
  const { theme } = useTheme();
  const [report, setReport] = useState(null);
  const [tipSummary, setTipSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('today');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [activeSection, setActiveSection] = useState('overview');
  const [aiInsights, setAiInsights] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => { fetchReport(); }, [period]);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const params = { period };
      if (period === 'custom' && customStart && customEnd) {
        params.start_date = customStart;
        params.end_date = customEnd;
      }
      const [eod, tips] = await Promise.all([
        advancedAPI.getEndOfDayReport(params),
        advancedAPI.getTipsSummary().catch(() => ({ data: null })),
      ]);
      setReport(eod.data);
      setTipSummary(tips.data);
    } catch { toast.error('Failed to load report'); }
    setLoading(false);
  };

  if (loading) return <div className="flex justify-center py-12"><div className="animate-pulse text-gray-400">Loading report...</div></div>;
  if (!report) return null;
  const s = report.summary;
  const ca = report.customerAnalytics || {};

  const sections = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'items', label: 'Item Sales', icon: ShoppingBag },
    { id: 'categories', label: 'Categories', icon: PieChart },
    { id: 'customers', label: 'Customers', icon: Users },
    { id: 'hourly', label: 'Hourly', icon: Clock },
    { id: 'ai', label: 'AI Insights', icon: Sparkles },
  ];

  const generateAIInsights = async () => {
    setAiLoading(true);
    try {
      const res = await advancedAPI.getAIInsights({ reportData: report, period });
      setAiInsights(res.data);
    } catch { toast.error('Failed to generate insights'); }
    setAiLoading(false);
  };

  return (
    <div data-testid="end-of-day-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Reports</h1>
          <p className="text-gray-500 mt-1">Comprehensive business analytics</p>
        </div>
        <Badge className="bg-emerald-100 text-emerald-700 text-sm px-3 py-1">
          <Receipt size={14} className="mr-1" /> {s.totalTransactions} Transactions
        </Badge>
      </div>

      {/* Period Selector */}
      <div className="flex flex-wrap gap-2 mb-4">
        {PERIODS.map(p => (
          <Button key={p.value} size="sm" variant={period === p.value ? 'default' : 'outline'}
            style={period === p.value ? { backgroundColor: theme.primary } : {}}
            onClick={() => setPeriod(p.value)} data-testid={`period-${p.value}`}>
            {p.label}
          </Button>
        ))}
      </div>
      {period === 'custom' && (
        <div className="flex items-center gap-3 mb-4">
          <Input type="date" value={customStart} onChange={e => setCustomStart(e.target.value)} data-testid="custom-start" />
          <span className="text-gray-400">to</span>
          <Input type="date" value={customEnd} onChange={e => setCustomEnd(e.target.value)} data-testid="custom-end" />
          <Button size="sm" style={{ backgroundColor: theme.primary }} onClick={fetchReport} data-testid="apply-custom-btn">Apply</Button>
        </div>
      )}

      {/* Section Tabs */}
      <div className="flex gap-2 mb-6 border-b pb-2">
        {sections.map(sec => (
          <button key={sec.id} onClick={() => setActiveSection(sec.id)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-t text-sm font-medium transition-colors"
            data-testid={`section-${sec.id}`}
            style={{ color: activeSection === sec.id ? theme.primary : '#6B7280', borderBottom: activeSection === sec.id ? `2px solid ${theme.primary}` : 'none' }}>
            <sec.icon size={15} />{sec.label}
          </button>
        ))}
      </div>

      {/* === OVERVIEW === */}
      {activeSection === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                {(report.byPaymentMethod || []).map((pm, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                    <span className="text-sm font-medium">{pm.method}</span>
                    <span className="font-bold">${pm.total.toFixed(2)}</span>
                  </div>
                ))}
                {(report.byPaymentMethod || []).length === 0 && <p className="text-gray-400 text-sm text-center py-4">No transactions</p>}
              </div>
            </CardContent></Card>

            {/* Refunds & Tips */}
            <Card><CardContent className="p-5">
              <h3 className="font-semibold mb-4">Refunds, Tips & Net</h3>
              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b"><span className="text-sm">Total Refunds</span><span className="font-bold text-red-600">-${s.totalRefunds.toFixed(2)}</span></div>
                <div className="flex justify-between py-2 border-b"><span className="text-sm">Total Tips</span><span className="font-bold text-emerald-600">+${s.totalTips.toFixed(2)}</span></div>
                <div className="flex justify-between py-2 font-bold text-lg"><span>Net Total</span><span style={{ color: theme.primary }}>${(s.netSales + s.totalTips).toFixed(2)}</span></div>
              </div>
            </CardContent></Card>

            {/* Tips Summary */}
            {tipSummary && tipSummary.tipCount > 0 && (
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
                  {tipSummary.byStaff.map((st, i) => (
                    <div key={i} className="flex items-center justify-between text-sm py-1">
                      <span>{st.name}</span><span className="font-bold">${st.total.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </CardContent></Card>
            )}
          </div>
        </div>
      )}

      {/* === ITEM SALES === */}
      {activeSection === 'items' && (
        <Card><CardContent className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><ShoppingBag size={18} /> Item Sales</h3>
          <table className="w-full text-sm" data-testid="item-sales-table">
            <thead><tr className="border-b">
              <th className="text-left py-2">Item</th>
              <th className="text-left py-2">Category</th>
              <th className="text-right py-2">Qty Sold</th>
              <th className="text-right py-2">Revenue</th>
            </tr></thead>
            <tbody>
              {(report.topItems || []).map((item, i) => (
                <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="py-2 font-medium">{item.name}</td>
                  <td className="py-2 text-gray-500">{item.category || '-'}</td>
                  <td className="py-2 text-right">{item.qty}</td>
                  <td className="py-2 text-right font-bold" style={{ color: theme.primary }}>${item.revenue.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {(report.topItems || []).length === 0 && <p className="text-gray-400 text-center py-8">No item sales data</p>}
        </CardContent></Card>
      )}

      {/* === CATEGORIES === */}
      {activeSection === 'categories' && (
        <Card><CardContent className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><PieChart size={18} /> Category Sales</h3>
          <div className="space-y-3">
            {(report.byCategory || []).map((cat, i) => {
              const maxRev = Math.max(...(report.byCategory || []).map(c => c.revenue), 1);
              return (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{cat.category}</span>
                    <span>{cat.qty} sold — <span className="font-bold" style={{ color: theme.primary }}>${cat.revenue.toFixed(2)}</span></span>
                  </div>
                  <div className="w-full h-3 bg-gray-100 rounded-full">
                    <div className="h-full rounded-full" style={{ width: `${(cat.revenue / maxRev) * 100}%`, backgroundColor: theme.primary, transition: 'width 0.5s' }} />
                  </div>
                </div>
              );
            })}
            {(report.byCategory || []).length === 0 && <p className="text-gray-400 text-center py-8">No category data</p>}
          </div>
        </CardContent></Card>
      )}

      {/* === CUSTOMERS === */}
      {activeSection === 'customers' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card><CardContent className="p-4 text-center">
              <Users size={20} className="mx-auto mb-1 text-blue-500" />
              <p className="text-2xl font-bold">{ca.totalCovers || 0}</p>
              <p className="text-xs text-gray-500">Total Covers</p>
            </CardContent></Card>
            <Card><CardContent className="p-4 text-center">
              <UserCheck size={20} className="mx-auto mb-1 text-emerald-500" />
              <p className="text-2xl font-bold">{ca.returningCustomers || 0}</p>
              <p className="text-xs text-gray-500">Returning</p>
            </CardContent></Card>
            <Card><CardContent className="p-4 text-center">
              <UserPlus size={20} className="mx-auto mb-1 text-violet-500" />
              <p className="text-2xl font-bold">{ca.newCustomers || 0}</p>
              <p className="text-xs text-gray-500">New Customers</p>
            </CardContent></Card>
            <Card><CardContent className="p-4 text-center">
              <Users size={20} className="mx-auto mb-1 text-amber-500" />
              <p className="text-2xl font-bold">{ca.walkIns || 0}</p>
              <p className="text-xs text-gray-500">Walk-ins</p>
            </CardContent></Card>
            <Card><CardContent className="p-4 text-center">
              <DollarSign size={20} className="mx-auto mb-1 text-emerald-500" />
              <p className="text-2xl font-bold">${ca.avgCustomerSpend || 0}</p>
              <p className="text-xs text-gray-500">Avg Spend</p>
            </CardContent></Card>
          </div>

          {(ca.topSpenders || []).length > 0 && (
            <Card><CardContent className="p-5">
              <h3 className="font-semibold mb-4">Top Spenders</h3>
              <div className="space-y-2">
                {ca.topSpenders.map((sp, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: theme.primary }}>{i + 1}</div>
                      <span className="text-sm font-medium">{sp.name}</span>
                    </div>
                    <span className="font-bold" style={{ color: theme.primary }}>${sp.total.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </CardContent></Card>
          )}
        </div>
      )}

      {/* === HOURLY === */}
      {activeSection === 'hourly' && (
        <Card><CardContent className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Clock size={18} /> Sales by Hour</h3>
          <div className="space-y-2">
            {(report.byHour || []).map((h, i) => {
              const maxHour = Math.max(...(report.byHour || []).map(x => x.total), 1);
              const label = `${h.hour.toString().padStart(2, '0')}:00`;
              return (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-sm font-mono w-12 text-gray-500">{label}</span>
                  <div className="flex-1 h-6 bg-gray-100 rounded relative">
                    <div className="h-full rounded" style={{ width: `${(h.total / maxHour) * 100}%`, backgroundColor: theme.primary, transition: 'width 0.5s' }} />
                  </div>
                  <span className="text-sm font-bold w-20 text-right">${h.total.toFixed(2)}</span>
                </div>
              );
            })}
            {(report.byHour || []).length === 0 && <p className="text-gray-400 text-center py-8">No hourly data</p>}
          </div>
        </CardContent></Card>
      )}
      {/* === AI INSIGHTS === */}
      {activeSection === 'ai' && (
        <div className="space-y-4">
          {!aiInsights ? (
            <Card><CardContent className="p-8 text-center">
              <Sparkles size={40} className="mx-auto mb-4 text-amber-500" />
              <h3 className="font-semibold text-lg mb-2">AI-Powered Business Insights</h3>
              <p className="text-gray-500 text-sm mb-4">Get GPT-powered analysis of your sales data with actionable recommendations.</p>
              <Button onClick={generateAIInsights} disabled={aiLoading} style={{ backgroundColor: theme.primary }} data-testid="generate-ai-btn">
                {aiLoading ? <><Loader2 size={16} className="mr-2 animate-spin" /> Analyzing...</> : <><Sparkles size={16} className="mr-2" /> Generate Insights</>}
              </Button>
            </CardContent></Card>
          ) : (
            <Card><CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold flex items-center gap-2"><Sparkles size={18} className="text-amber-500" /> AI Analysis</h3>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{new Date(aiInsights.generatedAt).toLocaleString()}</span>
                  <Button size="sm" variant="outline" onClick={generateAIInsights} disabled={aiLoading}>Regenerate</Button>
                </div>
              </div>
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap" data-testid="ai-insights-content">
                {aiInsights.insights}
              </div>
            </CardContent></Card>
          )}
        </div>
      )}
    </div>
  );
}
