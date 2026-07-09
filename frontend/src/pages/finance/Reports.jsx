import React, { useState, useEffect, useCallback } from 'react';
import { financeAPI } from '../../services/api';
import { toast } from 'sonner';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { TrendingUp, Scale, FileSpreadsheet, Wallet } from 'lucide-react';
import { FMT, fyStart, today } from './helpers';

const PnlSection = ({ title, rows }) => (
  <div className="mt-4">
    <p className="text-sm font-medium text-slate-700">{title}</p>
    {rows.length === 0 && <p className="text-xs text-slate-400 pl-4">—</p>}
    {rows.map(r => (
      <div key={r.code} className="flex justify-between text-sm py-0.5 pl-4">
        <span className="text-slate-600">{r.code} · {r.name}</span><span>{FMT(r.amount)}</span>
      </div>
    ))}
  </div>
);

const BSList = ({ rows, total, label }) => (
  <div>
    {rows.map(r => (
      <div key={r.code} className="flex justify-between text-sm py-0.5">
        <span className="text-slate-600">{r.code} · {r.name}</span><span>{FMT(r.amount)}</span>
      </div>
    ))}
    <div className="flex justify-between font-medium pt-1 border-t mt-1"><span>{label}</span><span>{FMT(total)}</span></div>
  </div>
);

const Reports = () => {
  const [tab, setTab] = useState('pnl');
  const [range, setRange] = useState({ from: fyStart(), to: today() });
  const [pnl, setPnl] = useState(null);
  const [tb, setTb] = useState(null);
  const [bs, setBs] = useState(null);
  const [cf, setCf] = useState(null);

  const loadAll = useCallback(async () => {
    try {
      const [a, b, c, d] = await Promise.all([
        financeAPI.profitLoss({ from: range.from, to: range.to }),
        financeAPI.trialBalance({ as_of: range.to }),
        financeAPI.balanceSheet({ as_of: range.to }),
        financeAPI.cashFlow({ from: range.from, to: range.to }),
      ]);
      setPnl(a.data); setTb(b.data); setBs(c.data); setCf(d.data);
    } catch { toast.error('Could not load reports'); }
  }, [range]);
  useEffect(() => { loadAll(); }, [loadAll]);

  return (
    <div className="space-y-4" data-testid="reports-page">
      <div className="flex gap-2 items-end flex-wrap">
        <div>
          <label className="text-xs text-slate-500">From</label>
          <Input type="date" value={range.from} onChange={e => setRange({ ...range, from: e.target.value })} className="w-40" data-testid="report-from" />
        </div>
        <div>
          <label className="text-xs text-slate-500">To</label>
          <Input type="date" value={range.to} onChange={e => setRange({ ...range, to: e.target.value })} className="w-40" data-testid="report-to" />
        </div>
        <Button size="sm" onClick={loadAll} data-testid="report-run-btn">Run</Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="pnl" data-testid="tab-pnl"><TrendingUp size={14} className="mr-1" /> Profit &amp; Loss</TabsTrigger>
          <TabsTrigger value="bs" data-testid="tab-bs"><Scale size={14} className="mr-1" /> Balance Sheet</TabsTrigger>
          <TabsTrigger value="tb" data-testid="tab-tb"><FileSpreadsheet size={14} className="mr-1" /> Trial Balance</TabsTrigger>
          <TabsTrigger value="cf" data-testid="tab-cf"><Wallet size={14} className="mr-1" /> Cash Flow</TabsTrigger>
        </TabsList>

        <TabsContent value="pnl">
          {pnl && (
            <Card><CardContent className="p-6" data-testid="pnl-content">
              <p className="text-xs text-slate-500">{pnl.from} → {pnl.to}</p>
              <PnlSection title="Revenue" rows={pnl.revenue} />
              <div className="flex justify-between font-medium py-1 border-t"><span>Total Revenue</span><span>{FMT(pnl.totalRevenue)}</span></div>
              <PnlSection title="Cost of Goods Sold" rows={pnl.cogs} />
              <div className="flex justify-between font-medium py-1 border-t"><span>Gross Profit</span><span className="text-emerald-600">{FMT(pnl.grossProfit)} ({pnl.grossMarginPct}%)</span></div>
              <PnlSection title="Operating Expenses" rows={pnl.expenses} />
              <div className="flex justify-between font-medium py-1 border-t"><span>Operating Profit</span><span>{FMT(pnl.operatingProfit)}</span></div>
              {pnl.otherRevenue.length > 0 && <PnlSection title="Other Revenue" rows={pnl.otherRevenue} />}
              <div className="flex justify-between font-bold text-lg py-2 border-t-2 border-slate-800"><span>Net Profit</span><span className="text-indigo-600">{FMT(pnl.netProfit)} ({pnl.netMarginPct}%)</span></div>
            </CardContent></Card>
          )}
        </TabsContent>

        <TabsContent value="bs">
          {bs && (
            <Card><CardContent className="p-6" data-testid="bs-content">
              <p className="text-xs text-slate-500">As of {bs.asOf} · {bs.balanced ? '✔ Balanced' : '⚠ Unbalanced'}</p>
              <div className="grid md:grid-cols-2 gap-6 mt-4">
                <div>
                  <h4 className="font-semibold mb-2">Assets</h4>
                  <BSList rows={bs.assets} total={bs.totalAssets} label="Total Assets" />
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Liabilities & Equity</h4>
                  <BSList rows={bs.liabilities} total={bs.totalLiabilities} label="Total Liabilities" />
                  <div className="mt-3"><BSList rows={bs.equity} total={bs.totalEquity} label="Total Equity" /></div>
                  <div className="flex justify-between font-bold pt-2 border-t-2"><span>Liabilities + Equity</span><span>{FMT(bs.totalLiabilitiesAndEquity)}</span></div>
                </div>
              </div>
            </CardContent></Card>
          )}
        </TabsContent>

        <TabsContent value="tb">
          {tb && (
            <Card><CardContent className="p-0" data-testid="tb-content">
              <table className="w-full text-sm">
                <thead className="bg-slate-50"><tr>
                  <th className="p-2 pl-4 text-left text-xs text-slate-500">Code</th>
                  <th className="p-2 text-left text-xs text-slate-500">Account</th>
                  <th className="p-2 text-left text-xs text-slate-500">Type</th>
                  <th className="p-2 text-right text-xs text-slate-500">Debit</th>
                  <th className="p-2 pr-4 text-right text-xs text-slate-500">Credit</th>
                </tr></thead>
                <tbody>
                  {tb.rows.map(r => (
                    <tr key={r.code} className="border-t">
                      <td className="p-2 pl-4 font-mono text-xs">{r.code}</td>
                      <td className="p-2">{r.name}</td>
                      <td className="p-2 text-slate-500 capitalize">{r.type}</td>
                      <td className="p-2 text-right">{r.debit ? FMT(r.debit) : '—'}</td>
                      <td className="p-2 pr-4 text-right">{r.credit ? FMT(r.credit) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 font-bold">
                  <tr>
                    <td colSpan="3" className="p-2 pl-4">Totals · {tb.balanced ? '✔ Balanced' : '⚠ Unbalanced'}</td>
                    <td className="p-2 text-right">{FMT(tb.totalDebit)}</td>
                    <td className="p-2 pr-4 text-right">{FMT(tb.totalCredit)}</td>
                  </tr>
                </tfoot>
              </table>
            </CardContent></Card>
          )}
        </TabsContent>

        <TabsContent value="cf">
          {cf && (
            <Card><CardContent className="p-6" data-testid="cf-content">
              <p className="text-xs text-slate-500">{cf.from} → {cf.to}</p>
              <div className="flex justify-between py-1"><span>Opening Balance</span><span>{FMT(cf.openingBalance)}</span></div>
              <div className="mt-3 mb-1 font-medium">Inflows</div>
              {cf.inflows.map(i => <div key={i.category} className="flex justify-between text-sm py-0.5 pl-4"><span className="capitalize">{i.category.replace(/_/g, ' ')}</span><span className="text-emerald-600">{FMT(i.amount)}</span></div>)}
              <div className="mt-3 mb-1 font-medium">Outflows</div>
              {cf.outflows.map(o => <div key={o.category} className="flex justify-between text-sm py-0.5 pl-4"><span className="capitalize">{o.category.replace(/_/g, ' ')}</span><span className="text-rose-600">-{FMT(o.amount)}</span></div>)}
              <div className="flex justify-between font-medium py-2 border-t mt-3"><span>Net Cash Movement</span><span>{FMT(cf.netCash)}</span></div>
              <div className="flex justify-between font-bold text-lg pt-2 border-t-2 border-slate-800"><span>Closing Balance</span><span className="text-blue-600">{FMT(cf.closingBalance)}</span></div>
            </CardContent></Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Reports;
