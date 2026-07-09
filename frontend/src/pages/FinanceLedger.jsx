import React, { useState, useEffect, useCallback } from 'react';
import { financeAPI } from '../services/api';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { BookOpenCheck, FileSpreadsheet, Landmark, ReceiptText, ArrowLeftRight, Wallet, Scale, TrendingUp, PlusCircle, Trash2, ChevronRight } from 'lucide-react';

const FMT = (n) => (n ?? 0).toLocaleString('en-AU', { style: 'currency', currency: 'AUD', minimumFractionDigits: 2 });
const today = () => new Date().toISOString().slice(0, 10);
const fyStart = () => {
  const t = new Date();
  const y = t.getMonth() >= 6 ? t.getFullYear() : t.getFullYear() - 1;
  return `${y}-07-01`;
};

/* ────────────────────────────────────────────────────────────────────── */
/*  Overview / KPI dashboard                                              */
/* ────────────────────────────────────────────────────────────────────── */
const Overview = () => {
  const [kpis, setKpis] = useState(null);
  const load = useCallback(async () => {
    try {
      const r = await financeAPI.kpis();
      setKpis(r.data);
    } catch { toast.error('Could not load KPIs'); }
  }, []);
  useEffect(() => { load(); }, [load]);
  if (!kpis) return <div className="p-6 text-slate-500">Loading KPIs…</div>;

  const cards = [
    { label: 'Revenue (FYTD)', value: kpis.revenue, color: 'text-emerald-600', icon: TrendingUp },
    { label: 'Gross Profit', value: kpis.grossProfit, sub: `${kpis.grossMarginPct}%`, color: 'text-emerald-700', icon: Scale },
    { label: 'Net Profit', value: kpis.netProfit, sub: `${kpis.netMarginPct}%`, color: 'text-indigo-600', icon: Landmark },
    { label: 'Cash on Hand', value: kpis.cashOnHand, color: 'text-blue-600', icon: Wallet },
    { label: 'AR Outstanding', value: kpis.arOutstanding, sub: `${kpis.openInvoices} invoices`, color: 'text-amber-600', icon: ReceiptText },
    { label: 'AP Outstanding', value: kpis.apOutstanding, sub: `${kpis.openBills} bills`, color: 'text-rose-600', icon: ArrowLeftRight },
  ];

  return (
    <div className="space-y-5" data-testid="finance-overview">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map(c => {
          const Icon = c.icon;
          return (
            <Card key={c.label} data-testid={`kpi-${c.label.replace(/\s+/g, '-').toLowerCase()}`}>
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-slate-500">{c.label}</p>
                    <p className={`text-2xl font-bold mt-1 ${c.color}`}>{FMT(c.value)}</p>
                    {c.sub && <p className="text-xs text-slate-500 mt-1">{c.sub}</p>}
                  </div>
                  <Icon className={`opacity-30 ${c.color}`} size={40} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
      <p className="text-xs text-slate-400">FY start: {kpis.fyStart} · As of {kpis.asOf}</p>
    </div>
  );
};

/* ────────────────────────────────────────────────────────────────────── */
/*  Chart of Accounts                                                     */
/* ────────────────────────────────────────────────────────────────────── */
const ChartOfAccounts = () => {
  const [accounts, setAccounts] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', type: 'expense', subType: '' });

  const load = useCallback(async () => {
    try { setAccounts((await financeAPI.listAccounts()).data); }
    catch { toast.error('Could not load accounts'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!form.code || !form.name) return toast.error('Code + name required');
    try {
      await financeAPI.createAccount(form);
      toast.success(`Account ${form.code} created`);
      setShowAdd(false);
      setForm({ code: '', name: '', type: 'expense', subType: '' });
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const remove = async (code) => {
    if (!window.confirm(`Delete account ${code}?`)) return;
    try { await financeAPI.deleteAccount(code); toast.success('Deleted'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const grouped = accounts.reduce((acc, a) => { (acc[a.type] = acc[a.type] || []).push(a); return acc; }, {});
  const order = ['asset', 'liability', 'equity', 'revenue', 'expense'];

  return (
    <div className="space-y-4" data-testid="coa-page">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Chart of Accounts</h3>
        <Button size="sm" onClick={() => setShowAdd(true)} data-testid="coa-add-btn">
          <PlusCircle size={14} className="mr-1" /> New Account
        </Button>
      </div>
      {order.filter(t => grouped[t]).map(t => (
        <Card key={t}>
          <CardHeader className="pb-2"><CardTitle className="capitalize text-base">{t}s</CardTitle></CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm" data-testid={`coa-table-${t}`}>
              <thead className="bg-slate-50"><tr>
                <th className="text-left p-2 pl-4 text-xs text-slate-500">Code</th>
                <th className="text-left p-2 text-xs text-slate-500">Name</th>
                <th className="text-left p-2 text-xs text-slate-500">Sub-type</th>
                <th className="text-left p-2 text-xs text-slate-500">Flags</th>
                <th className="p-2 pr-4"></th>
              </tr></thead>
              <tbody>
                {grouped[t].sort((a, b) => a.code.localeCompare(b.code)).map(a => (
                  <tr key={a.code} className="border-t">
                    <td className="p-2 pl-4 font-mono">{a.code}</td>
                    <td className="p-2">{a.name}</td>
                    <td className="p-2 text-slate-500">{a.subType || '—'}</td>
                    <td className="p-2 space-x-1">
                      {a.isBank && <Badge variant="outline" className="text-xs">Bank</Badge>}
                      {a.isLocked && <Badge variant="secondary" className="text-xs">System</Badge>}
                    </td>
                    <td className="p-2 pr-4 text-right">
                      {!a.isLocked && (
                        <Button size="sm" variant="ghost" className="text-rose-500" onClick={() => remove(a.code)}
                                data-testid={`coa-delete-${a.code}`}>
                          <Trash2 size={14} />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ))}

      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent data-testid="coa-add-dialog">
          <DialogHeader><DialogTitle>New Account</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Code (e.g. 6900)" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} data-testid="coa-input-code" />
            <Input placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="coa-input-name" />
            <Select value={form.type} onValueChange={v => setForm({ ...form, type: v })}>
              <SelectTrigger data-testid="coa-select-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="asset">Asset</SelectItem>
                <SelectItem value="liability">Liability</SelectItem>
                <SelectItem value="equity">Equity</SelectItem>
                <SelectItem value="revenue">Revenue</SelectItem>
                <SelectItem value="expense">Expense</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Sub-type (optional)" value={form.subType} onChange={e => setForm({ ...form, subType: e.target.value })} />
            <Button className="w-full" onClick={save} data-testid="coa-save-btn">Create</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

/* ────────────────────────────────────────────────────────────────────── */
/*  Journals                                                              */
/* ────────────────────────────────────────────────────────────────────── */
const Journals = () => {
  const [journals, setJournals] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [entry, setEntry] = useState({
    date: today(), memo: '',
    lines: [{ accountCode: '', debit: 0, credit: 0 }, { accountCode: '', debit: 0, credit: 0 }],
  });

  const load = useCallback(async () => {
    try {
      const [j, a] = await Promise.all([financeAPI.listJournals({ limit: 100 }), financeAPI.listAccounts()]);
      setJournals(j.data); setAccounts(a.data);
    } catch { toast.error('Could not load journals'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const totals = entry.lines.reduce((acc, l) => ({
    debit: acc.debit + parseFloat(l.debit || 0),
    credit: acc.credit + parseFloat(l.credit || 0),
  }), { debit: 0, credit: 0 });
  const balanced = Math.abs(totals.debit - totals.credit) < 0.005 && totals.debit > 0;

  const save = async () => {
    if (!balanced) return toast.error('Entry must be balanced');
    if (entry.lines.some(l => !l.accountCode)) return toast.error('All lines need an account');
    try {
      await financeAPI.createJournal({
        date: entry.date, memo: entry.memo,
        lines: entry.lines.map(l => ({
          accountCode: l.accountCode,
          debit: parseFloat(l.debit || 0),
          credit: parseFloat(l.credit || 0),
          description: l.description || '',
        })),
      });
      toast.success('Journal posted');
      setShowNew(false);
      setEntry({ date: today(), memo: '', lines: [{ accountCode: '', debit: 0, credit: 0 }, { accountCode: '', debit: 0, credit: 0 }] });
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const reverse = async (id) => {
    if (!window.confirm('Reverse this journal? A new balancing entry will be posted.')) return;
    try { await financeAPI.reverseJournal(id, {}); toast.success('Reversed'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const updateLine = (i, patch) => {
    const next = entry.lines.map((l, ix) => ix === i ? { ...l, ...patch } : l);
    setEntry({ ...entry, lines: next });
  };

  return (
    <div className="space-y-4" data-testid="journals-page">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">General Journal</h3>
        <Button size="sm" onClick={() => setShowNew(true)} data-testid="journal-new-btn">
          <PlusCircle size={14} className="mr-1" /> New Entry
        </Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-slate-50"><tr>
            <th className="text-left p-2 pl-4 text-xs text-slate-500">Journal #</th>
            <th className="text-left p-2 text-xs text-slate-500">Date</th>
            <th className="text-left p-2 text-xs text-slate-500">Source</th>
            <th className="text-left p-2 text-xs text-slate-500">Memo</th>
            <th className="text-right p-2 pr-4 text-xs text-slate-500">Amount</th>
            <th className="p-2 pr-4"></th>
          </tr></thead>
          <tbody>
            {journals.map(j => {
              const amount = (j.lines || []).reduce((s, l) => s + (l.debit || 0), 0);
              return (
                <tr key={j.id} className="border-t hover:bg-slate-50" data-testid={`journal-row-${j.journalNumber}`}>
                  <td className="p-2 pl-4 font-mono text-xs">{j.journalNumber}</td>
                  <td className="p-2">{j.date}</td>
                  <td className="p-2"><Badge variant="outline" className="text-xs">{j.sourceType}</Badge></td>
                  <td className="p-2 text-slate-600">{j.memo}</td>
                  <td className="p-2 pr-4 text-right font-medium">{FMT(amount)}</td>
                  <td className="p-2 pr-4 text-right">
                    <Button size="sm" variant="ghost" onClick={() => reverse(j.id)} data-testid={`journal-reverse-${j.journalNumber}`}>
                      <ArrowLeftRight size={14} />
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {journals.length === 0 && <p className="text-center text-slate-400 py-8">No journals yet</p>}
      </CardContent></Card>

      <Dialog open={showNew} onOpenChange={setShowNew}>
        <DialogContent className="max-w-3xl" data-testid="journal-new-dialog">
          <DialogHeader><DialogTitle>New Journal Entry</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Input type="date" value={entry.date} onChange={e => setEntry({ ...entry, date: e.target.value })} data-testid="journal-date" />
              <Input placeholder="Memo" value={entry.memo} onChange={e => setEntry({ ...entry, memo: e.target.value })} data-testid="journal-memo" />
            </div>
            <table className="w-full text-sm border rounded overflow-hidden">
              <thead className="bg-slate-50">
                <tr>
                  <th className="p-2 text-left">Account</th>
                  <th className="p-2 text-right w-32">Debit</th>
                  <th className="p-2 text-right w-32">Credit</th>
                  <th className="p-2 text-left">Description</th>
                </tr>
              </thead>
              <tbody>
                {entry.lines.map((l, i) => (
                  <tr key={i} className="border-t">
                    <td className="p-2">
                      <Select value={l.accountCode} onValueChange={v => updateLine(i, { accountCode: v })}>
                        <SelectTrigger data-testid={`journal-line-${i}-account`}><SelectValue placeholder="Select…" /></SelectTrigger>
                        <SelectContent>
                          {accounts.map(a => <SelectItem key={a.code} value={a.code}>{a.code} — {a.name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="p-2"><Input type="number" step="0.01" value={l.debit} onChange={e => updateLine(i, { debit: e.target.value, credit: 0 })} className="text-right" data-testid={`journal-line-${i}-debit`} /></td>
                    <td className="p-2"><Input type="number" step="0.01" value={l.credit} onChange={e => updateLine(i, { credit: e.target.value, debit: 0 })} className="text-right" data-testid={`journal-line-${i}-credit`} /></td>
                    <td className="p-2"><Input placeholder="Line memo" value={l.description || ''} onChange={e => updateLine(i, { description: e.target.value })} /></td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50 font-medium">
                <tr>
                  <td className="p-2 text-right">Totals</td>
                  <td className="p-2 text-right">{FMT(totals.debit)}</td>
                  <td className="p-2 text-right">{FMT(totals.credit)}</td>
                  <td className="p-2">
                    {balanced ? <Badge className="bg-emerald-500">Balanced</Badge> : <Badge className="bg-rose-500">Off {FMT(totals.debit - totals.credit)}</Badge>}
                  </td>
                </tr>
              </tfoot>
            </table>
            <div className="flex justify-between">
              <Button variant="outline" size="sm" onClick={() => setEntry({ ...entry, lines: [...entry.lines, { accountCode: '', debit: 0, credit: 0 }] })} data-testid="journal-add-line">
                + Add line
              </Button>
              <Button onClick={save} disabled={!balanced} data-testid="journal-post-btn">Post Journal</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

/* ────────────────────────────────────────────────────────────────────── */
/*  Reports — Trial Balance / P&L / Balance Sheet / Cash Flow             */
/* ────────────────────────────────────────────────────────────────────── */
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

/* ────────────────────────────────────────────────────────────────────── */
/*  Accounts Payable                                                       */
/* ────────────────────────────────────────────────────────────────────── */
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

/* ────────────────────────────────────────────────────────────────────── */
/*  Accounts Receivable                                                    */
/* ────────────────────────────────────────────────────────────────────── */
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

/* ────────────────────────────────────────────────────────────────────── */
/*  Bank Reconciliation                                                    */
/* ────────────────────────────────────────────────────────────────────── */
const BankRec = () => {
  const [accounts, setAccounts] = useState([]);
  const [code, setCode] = useState('1000');
  const [rows, setRows] = useState([]);

  useEffect(() => {
    financeAPI.listAccounts().then(r => setAccounts(r.data.filter(a => a.isBank)));
  }, []);

  const load = useCallback(async () => {
    try { setRows((await financeAPI.bankStatement(code)).data); }
    catch { toast.error('Failed to load'); }
  }, [code]);
  useEffect(() => { load(); }, [load]);

  const importSample = async () => {
    const sample = {
      accountCode: code,
      lines: [
        { statementDate: today(), description: 'Card settlement', amount: 121, externalId: `demo-${Date.now()}` },
      ],
    };
    try { await financeAPI.importBank(sample); toast.success('Sample line imported'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const match = async (lineId, jid) => {
    try { await financeAPI.matchBank(lineId, jid); toast.success('Matched'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };
  const ignore = async (lineId) => {
    try { await financeAPI.ignoreBank(lineId); toast.success('Ignored'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  return (
    <div className="space-y-4" data-testid="bank-rec-page">
      <div className="flex gap-2 items-center">
        <Select value={code} onValueChange={setCode}>
          <SelectTrigger className="w-64" data-testid="bank-account-select"><SelectValue /></SelectTrigger>
          <SelectContent>
            {accounts.map(a => <SelectItem key={a.code} value={a.code}>{a.code} — {a.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" onClick={importSample} data-testid="bank-import-sample">Import demo line</Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-slate-50"><tr>
            <th className="p-2 pl-4 text-left text-xs text-slate-500">Date</th>
            <th className="p-2 text-left text-xs text-slate-500">Description</th>
            <th className="p-2 text-right text-xs text-slate-500">Amount</th>
            <th className="p-2 text-left text-xs text-slate-500">Suggested match</th>
            <th className="p-2 pr-4 text-center text-xs text-slate-500">Actions</th>
          </tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id} className="border-t">
                <td className="p-2 pl-4">{r.statementDate}</td>
                <td className="p-2">{r.description}</td>
                <td className={`p-2 text-right ${r.amount >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>{FMT(r.amount)}</td>
                <td className="p-2 text-xs text-slate-500">
                  {r.matchedJournalLineId ? <Badge className="bg-emerald-500">Matched</Badge> :
                    r.ignored ? <Badge variant="outline">Ignored</Badge> :
                    (r.suggestedMatches?.[0] ? <span>{r.suggestedMatches[0].journalNumber} · {r.suggestedMatches[0].memo}</span> : '—')}
                </td>
                <td className="p-2 pr-4 text-center">
                  {!r.matchedJournalLineId && !r.ignored && r.suggestedMatches?.[0] && (
                    <Button size="sm" variant="ghost" onClick={() => match(r.id, r.suggestedMatches[0].journalId)} data-testid={`bank-match-${r.id.slice(0,6)}`}>Match</Button>
                  )}
                  {!r.matchedJournalLineId && !r.ignored && (
                    <Button size="sm" variant="ghost" className="text-slate-400" onClick={() => ignore(r.id)}>Ignore</Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="text-center text-slate-400 py-8">No statement lines. Import a bank export or use demo.</p>}
      </CardContent></Card>
    </div>
  );
};

/* ────────────────────────────────────────────────────────────────────── */
/*  Root page                                                             */
/* ────────────────────────────────────────────────────────────────────── */
const FinanceLedger = () => {
  const [tab, setTab] = useState('overview');
  return (
    <div className="space-y-6" data-testid="finance-ledger-page">
      <div>
        <h1 className="text-3xl font-bold">Finance &amp; Accounting</h1>
        <p className="text-slate-500 mt-1">Double-entry ledger · P&amp;L · Balance Sheet · AP/AR · Bank Rec</p>
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview" data-testid="fin-tab-overview"><TrendingUp size={14} className="mr-1" /> Overview</TabsTrigger>
          <TabsTrigger value="reports" data-testid="fin-tab-reports"><FileSpreadsheet size={14} className="mr-1" /> Reports</TabsTrigger>
          <TabsTrigger value="ap" data-testid="fin-tab-ap"><ArrowLeftRight size={14} className="mr-1" /> Bills (AP)</TabsTrigger>
          <TabsTrigger value="ar" data-testid="fin-tab-ar"><ReceiptText size={14} className="mr-1" /> Invoices (AR)</TabsTrigger>
          <TabsTrigger value="bank" data-testid="fin-tab-bank"><Landmark size={14} className="mr-1" /> Bank Rec</TabsTrigger>
          <TabsTrigger value="journals" data-testid="fin-tab-journals"><BookOpenCheck size={14} className="mr-1" /> Journals</TabsTrigger>
          <TabsTrigger value="coa" data-testid="fin-tab-coa"><ChevronRight size={14} className="mr-1" /> Chart of Accounts</TabsTrigger>
        </TabsList>
        <TabsContent value="overview"><Overview /></TabsContent>
        <TabsContent value="reports"><Reports /></TabsContent>
        <TabsContent value="ap"><AccountsPayable /></TabsContent>
        <TabsContent value="ar"><AccountsReceivable /></TabsContent>
        <TabsContent value="bank"><BankRec /></TabsContent>
        <TabsContent value="journals"><Journals /></TabsContent>
        <TabsContent value="coa"><ChartOfAccounts /></TabsContent>
      </Tabs>
    </div>
  );
};

export default FinanceLedger;
