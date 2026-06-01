/* v25 — Compact pages for the remaining roadmap modules.
 * Each is exported individually so App.js can import them by name.
 */
import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { v25API, v26API } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useToast } from '../hooks/use-toast';
import {
  TrendingUp, AlertTriangle, Cpu, Shield, ShoppingBag, Gift, BookOpen, Star,
  MessageSquare, Building2, FileWarning, Trash2, Truck, Sparkles, Users,
  RefreshCw, Plus, CheckCircle, Smartphone, Monitor, BarChart3, ChefHat, ArrowRight
} from 'lucide-react';

// ---------------- Shift Manager ----------------
export function ShiftManager() {
  const { theme } = useTheme();
  const [data, setData] = useState({ alerts: [] });
  useEffect(() => {
    const tick = () => v25API.shiftManager().then(r => setData(r.data)).catch(() => {});
    tick(); const id = setInterval(tick, 30000); return () => clearInterval(id);
  }, []);
  return (
    <div className="space-y-6" data-testid="shift-manager-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><TrendingUp className="text-orange-600" /> AI Shift Manager</h1>
      <p className="text-sm text-gray-500">Real-time intervention alerts · auto-refresh every 30s</p>
      <div className="space-y-2">
        {data.alerts.length === 0 ? <Card><CardContent className="p-8 text-center text-emerald-600"><CheckCircle className="mx-auto mb-2" /> Service running smoothly</CardContent></Card> :
          data.alerts.map((a, i) => (
            <Card key={i} className={a.severity === 'high' ? 'border-red-300' : 'border-amber-300'} data-testid={`alert-${i}`}>
              <CardContent className="p-4 flex items-start gap-3">
                <AlertTriangle className={a.severity === 'high' ? 'text-red-600' : 'text-amber-600'} />
                <div className="flex-1"><p className="font-medium">{a.message}</p><Badge variant="outline" className="mt-1 text-[10px]">{a.type}</Badge></div>
              </CardContent>
            </Card>
          ))}
      </div>
    </div>
  );
}

// ---------------- Auto Marketing ----------------
export function AutoMarketing() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [campaigns, setCampaigns] = useState([]);
  const [running, setRunning] = useState(false);
  const load = () => v25API.listMarketing().then(r => setCampaigns(r.data || []));
  useEffect(() => { load(); }, []);
  const run = async (aud) => {
    setRunning(true);
    try { await v25API.autoMarketing(aud); toast({ title: 'Campaign drafted' }); await load(); }
    catch { toast({ title: 'Error', variant: 'destructive' }); }
    finally { setRunning(false); }
  };
  return (
    <div className="space-y-6" data-testid="auto-marketing-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Sparkles className="text-pink-600" /> Autonomous Marketing</h1>
      <div className="flex gap-2 flex-wrap">
        {['all', 'VIP', 'Gold', 'Silver'].map(a => (
          <Button key={a} onClick={() => run(a)} disabled={running} variant="outline" data-testid={`run-${a}`}>{running ? 'Drafting…' : `Run for ${a}`}</Button>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="campaigns-list">
        {campaigns.map(c => (
          <Card key={c.id} data-testid={`campaign-${c.id}`}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2"><Badge>{c.audience}</Badge><span className="text-xs text-gray-500">{c.recipients} recipients</span></div>
              <p className="font-semibold">{c.emailSubject}</p>
              <p className="text-sm text-gray-600 mt-1">{c.emailBody}</p>
              <p className="text-xs text-gray-500 mt-2 italic">SMS: {c.sms}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------- Exceptions / Loss Control ----------------
export function Exceptions() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  useEffect(() => { v25API.exceptions().then(r => setData(r.data)).catch(() => {}); }, []);
  return (
    <div className="space-y-6" data-testid="exceptions-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><AlertTriangle className="text-red-600" /> Loss Control Center</h1>
      {!data ? <div className="text-center py-20 text-gray-400">Loading…</div> : (
        <>
          <div className="grid grid-cols-4 gap-4">
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Voids</p><p className="text-3xl font-bold">{data.totals.voids}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Comps</p><p className="text-3xl font-bold">{data.totals.comps}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Discounts</p><p className="text-3xl font-bold">${data.totals.discounts}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Refunds</p><p className="text-3xl font-bold">{data.totals.refunds}</p></CardContent></Card>
          </div>
          {data.suspicious.length > 0 && (
            <Card className="border-red-300 bg-red-50"><CardContent className="p-5">
              <p className="font-bold text-red-700 mb-2">Suspicious activity</p>
              {data.suspicious.map(s => <div key={s.user} className="text-sm">{s.user}: {s.voids} voids in 14 days</div>)}
            </CardContent></Card>
          )}
        </>
      )}
    </div>
  );
}

// ---------------- Hardware Health ----------------
export function HardwareHealth() {
  const { theme } = useTheme();
  const [devices, setDevices] = useState([]);
  useEffect(() => { v25API.hardware().then(r => setDevices(r.data || [])); }, []);
  return (
    <div className="space-y-6" data-testid="hardware-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Cpu className="text-gray-600" /> Hardware Health</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map(d => (
          <Card key={d.id} data-testid={`device-${d.id}`}>
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="font-medium">{d.name}</p>
                <p className="text-xs text-gray-500">{d.kind} · {d.id}</p>
              </div>
              <Badge className={d.status === 'online' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{d.status}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------- Disputes ----------------
export function Disputes() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const load = () => v25API.disputes().then(r => setRows(r.data || []));
  useEffect(() => { load(); }, []);
  const open = async () => {
    const txId = prompt('Transaction ID?'); if (!txId) return;
    const amount = parseFloat(prompt('Amount?') || '0');
    await v25API.openDispute({ txId, amount, reason: 'fraud' });
    toast({ title: 'Dispute opened' }); load();
  };
  return (
    <div className="space-y-6" data-testid="disputes-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Shield className="text-orange-600" /> Chargeback / Dispute Console</h1>
        <Button onClick={open} style={{ background: theme.primary }} data-testid="new-dispute"><Plus size={14} className="mr-1.5" /> New</Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr><th className="text-left px-5 py-3">ID</th><th className="text-left px-5 py-3">Tx</th><th className="text-right px-5 py-3">Amount</th><th className="text-left px-5 py-3">Status</th><th className="text-left px-5 py-3">Opened</th></tr>
          </thead>
          <tbody>
            {rows.length === 0 ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">No disputes</td></tr> :
              rows.map(d => <tr key={d.id} className="border-t" data-testid={`dispute-${d.id}`}>
                <td className="px-5 py-3 font-mono text-xs">{d.id}</td><td className="px-5 py-3">{d.txId}</td>
                <td className="px-5 py-3 text-right font-mono">${d.amount}</td>
                <td className="px-5 py-3"><Badge variant="outline">{d.status}</Badge></td>
                <td className="px-5 py-3 text-xs text-gray-500">{new Date(d.openedAt).toLocaleString()}</td>
              </tr>)}
          </tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}

// ---------------- Supplier Marketplace ----------------
export function SupplierMarketplace() {
  const { theme } = useTheme();
  const [item, setItem] = useState('');
  const [rows, setRows] = useState([]);
  const load = () => v25API.compareSuppliers(item).then(r => setRows(r.data || [])).catch(() => {});
  useEffect(() => { load(); }, []);
  return (
    <div className="space-y-6" data-testid="supplier-marketplace-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><ShoppingBag className="text-teal-600" /> Supplier Marketplace</h1>
      <div className="flex gap-2">
        <Input value={item} onChange={e => setItem(e.target.value)} placeholder="Filter by item..." className="max-w-sm" />
        <Button onClick={load}>Search</Button>
      </div>
      <div className="space-y-3">
        {rows.length === 0 ? <Card><CardContent className="p-8 text-center text-gray-400">No quotes yet — add some via POST /api/v25/suppliers/quote</CardContent></Card> :
          rows.map(c => (
            <Card key={c.item} data-testid={`compare-${c.item}`}>
              <CardContent className="p-5">
                <div className="flex justify-between items-center mb-2">
                  <p className="font-bold">{c.item}</p>
                  {c.annualSavings > 0 && <Badge className="bg-emerald-100 text-emerald-700">Save ${c.annualSavings.toLocaleString()}/yr</Badge>}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {c.quotes.map(q => (
                    <div key={q.id} className={`p-3 border rounded ${q.supplier === c.cheapest ? 'border-emerald-400 bg-emerald-50' : ''}`}>
                      <p className="text-xs text-gray-500">{q.supplier}</p>
                      <p className="font-bold">${q.pricePerUnit}/{q.unit || 'unit'}</p>
                      {q.supplier === c.cheapest && <Badge className="bg-emerald-600 mt-1 text-[10px]">CHEAPEST</Badge>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
      </div>
    </div>
  );
}

// ---------------- Gift Cards ----------------
export function GiftCards() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [cards, setCards] = useState([]);
  const [amount, setAmount] = useState(50);
  const load = () => v25API.giftCards().then(r => setCards(r.data || []));
  useEffect(() => { load(); }, []);
  const issue = async () => {
    const recipientName = prompt('Recipient name?') || 'Guest';
    await v25API.issueGift({ amount, recipientName, bonus: amount >= 100 ? 20 : 0, occasion: 'general' });
    toast({ title: 'Gift card issued' }); load();
  };
  return (
    <div className="space-y-6" data-testid="gift-cards-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Gift className="text-rose-600" /> Smart Gift Cards</h1>
        <div className="flex gap-2 items-center">
          <Input type="number" value={amount} onChange={e => setAmount(parseFloat(e.target.value) || 0)} className="w-24" />
          <Button onClick={issue} style={{ background: theme.primary }} data-testid="issue-gift">Issue</Button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {cards.map(c => (
          <Card key={c.id} className="bg-gradient-to-br from-rose-50 to-pink-100" data-testid={`gift-${c.id}`}>
            <CardContent className="p-5">
              <p className="text-xs text-gray-500">{c.occasion} · {c.recipientName}</p>
              <p className="font-mono text-lg mt-1">{c.code}</p>
              <p className="text-2xl font-bold mt-2">${c.amount}{c.bonus > 0 && <span className="text-sm text-emerald-600"> +${c.bonus}</span>}</p>
              <Badge variant="outline" className="mt-2">{c.status}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------- Predictive Orders ----------------
export function PredictiveOrders() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [data, setData] = useState({ bySupplier: [] });
  const run = async () => { try { const r = await v25API.predictiveOrders(); setData(r.data); toast({ title: 'Generated' }); } catch { toast({ title: 'Error', variant: 'destructive' }); } };
  useEffect(() => { run(); }, []);
  return (
    <div className="space-y-6" data-testid="predictive-orders-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Truck className="text-indigo-600" /> Predictive Ordering</h1>
        <Button onClick={run}><RefreshCw size={14} className="mr-1.5" /> Re-run</Button>
      </div>
      {data.bySupplier.length === 0 ? <Card><CardContent className="p-8 text-center text-gray-400">No suggestions — sales history insufficient</CardContent></Card> :
        data.bySupplier.map(s => (
          <Card key={s.supplier} data-testid={`po-${s.supplier}`}>
            <CardContent className="p-5">
              <div className="flex justify-between mb-3"><p className="font-bold">{s.supplier}</p><p className="text-lg font-bold">${s.total.toFixed(2)}</p></div>
              <div className="space-y-1 text-sm">{s.items.map(i => <div key={i.productId} className="flex justify-between"><span>{i.name}</span><span>{i.orderQty} units</span></div>)}</div>
            </CardContent>
          </Card>
        ))}
    </div>
  );
}

// ---------------- Waste Tracking ----------------
export function WasteTracking() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [log, setLog] = useState([]); const [ins, setIns] = useState(null);
  const [form, setForm] = useState({ productName: '', quantity: 1, reason: 'spoilage', estCost: 0 });
  const load = () => {
    v25API.waste().then(r => setLog(r.data || []));
    v25API.wasteInsights().then(r => setIns(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  const submit = async () => { await v25API.logWaste(form); toast({ title: 'Logged' }); load(); };
  return (
    <div className="space-y-6" data-testid="waste-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Trash2 className="text-slate-600" /> Waste Tracking</h1>
      {ins && (
        <div className="grid grid-cols-3 gap-4">
          <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">30-day Cost</p><p className="text-2xl font-bold">${ins.totalCost30d}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Entries</p><p className="text-2xl font-bold">{ins.entries}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Top Reason</p><p className="font-bold">{Object.entries(ins.byReason || {})[0]?.[0] || 'n/a'}</p></CardContent></Card>
        </div>
      )}
      <Card><CardContent className="p-5 space-y-2">
        <p className="text-sm font-bold">Log Waste</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Input placeholder="Item name" value={form.productName} onChange={e => setForm({ ...form, productName: e.target.value })} />
          <Input type="number" placeholder="Qty" value={form.quantity} onChange={e => setForm({ ...form, quantity: parseFloat(e.target.value) || 0 })} />
          <select className="border rounded px-2" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })}>
            <option>spoilage</option><option>breakage</option><option>staff meals</option><option>over-prep</option>
          </select>
          <Input type="number" placeholder="Cost $" value={form.estCost} onChange={e => setForm({ ...form, estCost: parseFloat(e.target.value) || 0 })} />
        </div>
        <Button onClick={submit} data-testid="log-waste-btn" style={{ background: theme.primary }}>Log</Button>
      </CardContent></Card>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="text-left px-5 py-3">Item</th><th className="text-right px-5 py-3">Qty</th><th className="text-left px-5 py-3">Reason</th><th className="text-right px-5 py-3">Cost</th></tr></thead>
          <tbody>{log.slice(0, 20).map(w => <tr key={w.id} className="border-t"><td className="px-5 py-3">{w.productName}</td><td className="px-5 py-3 text-right">{w.quantity}</td><td className="px-5 py-3">{w.reason}</td><td className="px-5 py-3 text-right">${w.estCost}</td></tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}

// ---------------- AI Concierge ----------------
export function Concierge() {
  const { theme } = useTheme();
  const [msg, setMsg] = useState(''); const [resp, setResp] = useState(null); const [loading, setLoading] = useState(false);
  const send = async () => { if (!msg.trim()) return; setLoading(true); try { const r = await v25API.concierge(msg); setResp(r.data); } finally { setLoading(false); } };
  return (
    <div className="space-y-6" data-testid="concierge-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><MessageSquare className="text-purple-600" /> AI Concierge</h1>
      <Card><CardContent className="p-5 space-y-3">
        <textarea className="w-full p-3 border rounded text-sm" rows={3} placeholder="e.g. Need a table for 6 tonight at 7:30, John needs gluten-free" value={msg} onChange={e => setMsg(e.target.value)} data-testid="concierge-input" />
        <Button onClick={send} disabled={loading} style={{ background: theme.primary }} data-testid="concierge-send">{loading ? 'Thinking…' : 'Process'}</Button>
        {resp && (
          <div className="p-4 bg-purple-50 border border-purple-200 rounded space-y-1" data-testid="concierge-response">
            <p className="text-sm font-bold">Intent: <Badge>{resp.intent}</Badge> {resp.created && <Badge className="bg-emerald-600">Reservation: {resp.reservationId}</Badge>}</p>
            <p className="text-sm">{resp.reply}</p>
          </div>
        )}
      </CardContent></Card>
    </div>
  );
}

// ---------------- Reputation ----------------
export function Reputation() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [data, setData] = useState(null);
  const load = () => v25API.reputation().then(r => setData(r.data));
  useEffect(() => { load(); }, []);
  const respond = async (id) => { await v25API.respondReview(id, ''); toast({ title: 'AI response drafted' }); load(); };
  return (
    <div className="space-y-6" data-testid="reputation-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Star className="text-yellow-500" /> Reputation Center</h1>
      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">Average</p><p className="text-3xl font-bold">{data.avgRating} ★</p></CardContent></Card>
            {data.bySource.map(s => <Card key={s.source}><CardContent className="p-5"><p className="text-xs uppercase text-gray-500">{s.source}</p><p className="text-3xl font-bold">{s.avg}</p><p className="text-xs text-gray-400">{s.count} reviews</p></CardContent></Card>)}
          </div>
          <div className="space-y-2">
            {data.reviews.map(r => (
              <Card key={r.id} data-testid={`review-${r.id}`}><CardContent className="p-4">
                <div className="flex justify-between"><p className="font-medium">{r.author} · {r.source}</p><Badge className={r.rating >= 4 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{r.rating}★</Badge></div>
                <p className="text-sm mt-1 text-gray-700">{r.text}</p>
                {r.response && <p className="text-xs mt-2 italic text-gray-500">Reply: {r.response}</p>}
                {!r.responded && <Button size="sm" variant="outline" className="mt-2" onClick={() => respond(r.id)} data-testid={`respond-${r.id}`}>Draft AI Response</Button>}
              </CardContent></Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------- Franchise + Benchmark ----------------
export function Franchise() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [data, setData] = useState({ sites: [], recentPublications: [] });
  const [bench, setBench] = useState([]);
  const load = () => {
    v25API.franchiseDashboard().then(r => setData(r.data || { sites: [], recentPublications: [] }));
    v25API.benchmark().then(r => setBench(r.data || []));
  };
  useEffect(() => { load(); }, []);
  const add = async () => {
    const name = prompt('Site name?'); if (!name) return;
    const city = prompt('City?') || '';
    await v25API.addSite({ name, city }); load();
  };
  return (
    <div className="space-y-6" data-testid="franchise-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Building2 className="text-blue-600" /> Franchise Command Center</h1>
        <Button onClick={add} style={{ background: theme.primary }} data-testid="add-site"><Plus size={14} className="mr-1.5" /> Add Site</Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data.sites.map(s => <Card key={s.id} data-testid={`site-${s.id}`}><CardContent className="p-5"><p className="font-bold">{s.name}</p><p className="text-xs text-gray-500">{s.city}</p><Badge variant="outline" className="mt-2">{s.active ? 'active' : 'inactive'}</Badge></CardContent></Card>)}
      </div>
      <Card><CardContent className="p-0">
        <div className="px-5 py-3 border-b font-bold">Multi-Store Benchmark</div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="text-left px-5 py-3">Site</th><th className="text-right px-5 py-3">Revenue</th><th className="text-right px-5 py-3">Food %</th><th className="text-right px-5 py-3">Labour %</th><th className="text-right px-5 py-3">Guest Sat</th></tr></thead>
          <tbody>{bench.map(b => <tr key={b.siteId} className="border-t"><td className="px-5 py-3 font-medium">{b.siteName}</td><td className="px-5 py-3 text-right">${b.revenue.toLocaleString()}</td><td className="px-5 py-3 text-right">{b.foodCostPct}%</td><td className="px-5 py-3 text-right">{b.labourPct}%</td><td className="px-5 py-3 text-right">{b.guestSat} ★</td></tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}

// ---------------- Fraud Detection ----------------
export function FraudDetection() {
  const { theme } = useTheme();
  const [data, setData] = useState({ users: [] });
  useEffect(() => { v25API.fraudDetection().then(r => setData(r.data)); }, []);
  return (
    <div className="space-y-6" data-testid="fraud-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><FileWarning className="text-red-600" /> AI Fraud Detection</h1>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="text-left px-5 py-3">Staff</th><th className="text-right px-5 py-3">Tx</th><th className="text-right px-5 py-3">Voids</th><th className="text-right px-5 py-3">Comps</th><th className="text-right px-5 py-3">Discounts</th><th className="text-right px-5 py-3">Refunds</th><th className="text-right px-5 py-3">Risk</th></tr></thead>
          <tbody>{data.users.map(u => <tr key={u.user} className="border-t" data-testid={`risk-${u.user}`}>
            <td className="px-5 py-3 font-medium">{u.user}</td><td className="px-5 py-3 text-right">{u.tx}</td><td className="px-5 py-3 text-right">{u.voids}</td><td className="px-5 py-3 text-right">{u.comps}</td><td className="px-5 py-3 text-right">${u.discounts.toFixed(2)}</td><td className="px-5 py-3 text-right">{u.refunds}</td>
            <td className="px-5 py-3 text-right"><Badge className={u.riskScore > 40 ? 'bg-red-100 text-red-700' : u.riskScore > 20 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}>{u.riskScore}</Badge></td>
          </tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}

// ---------------- Margin Guardrails ----------------
export function MarginGuardrails() {
  const { theme } = useTheme();
  const [data, setData] = useState({ warnings: [] });
  useEffect(() => { v25API.marginGuardrails().then(r => setData(r.data)); }, []);
  return (
    <div className="space-y-6" data-testid="margin-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>📊 Menu Margin Guardrails</h1>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="text-left px-5 py-3">Item</th><th className="text-right px-5 py-3">Margin</th><th className="text-right px-5 py-3">Price</th><th className="text-right px-5 py-3">Cost</th><th className="text-left px-5 py-3">Severity</th></tr></thead>
          <tbody>{data.warnings.length === 0 ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">All margins healthy</td></tr> :
            data.warnings.map(w => <tr key={w.productId} className="border-t"><td className="px-5 py-3 font-medium">{w.name}</td><td className="px-5 py-3 text-right font-bold">{w.marginPct}%</td><td className="px-5 py-3 text-right">${w.price}</td><td className="px-5 py-3 text-right">${w.cost}</td><td className="px-5 py-3"><Badge className={w.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>{w.severity}</Badge></td></tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}

// ---------------- Station Readiness ----------------
export function StationReadiness() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  useEffect(() => { v25API.stationReadiness().then(r => setData(r.data)); }, []);
  return (
    <div className="space-y-6" data-testid="station-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><BarChart3 className="text-indigo-600" /> Station Readiness</h1>
      {data && (
        <Card><CardContent className="p-8 text-center">
          <p className="text-6xl font-bold" style={{ color: data.score >= 80 ? '#059669' : data.score >= 50 ? '#d97706' : '#dc2626' }}>{data.score}</p>
          <p className="text-sm text-gray-500 mt-2">{data.status.toUpperCase()}</p>
          <div className="grid grid-cols-4 gap-3 mt-6 text-sm">
            <div><p className="text-xs text-gray-500">Pending Tickets</p><p className="font-bold">{data.factors.pendingTickets}</p></div>
            <div><p className="text-xs text-gray-500">Shifts Today</p><p className="font-bold">{data.factors.shiftsToday}</p></div>
            <div><p className="text-xs text-gray-500">Low Stock</p><p className="font-bold">{data.factors.lowStockItems}</p></div>
            <div><p className="text-xs text-gray-500">Printers</p><p className="font-bold">{data.factors.printers}</p></div>
          </div>
        </CardContent></Card>
      )}
    </div>
  );
}

// ---------------- Kiosk ----------------
export function KioskMode() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [session, setSession] = useState(null);
  const [cart, setCart] = useState([]);
  useEffect(() => { fetch(`${process.env.REACT_APP_BACKEND_URL}/api/products`).then(r => r.json()).then(setProducts).catch(() => {}); }, []);
  const start = async () => { const r = await v25API.kioskStart({ guests: 2 }); setSession(r.data); setCart([]); };
  const add = (p) => { setCart([...cart, p]); v25API.kioskAdd(session.id, { productId: p.id, name: p.name, price: p.price, quantity: 1 }); };
  const checkout = async () => { await v25API.kioskCheckout(session.id); toast({ title: 'Order sent to kitchen' }); setSession(null); setCart([]); };
  return (
    <div className="space-y-6" data-testid="kiosk-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Smartphone className="text-blue-600" /> Self-Service Kiosk</h1>
        {!session ? <Button onClick={start} style={{ background: theme.primary }} data-testid="kiosk-start">Start Order</Button> :
          <Button onClick={checkout} style={{ background: theme.primary }} data-testid="kiosk-checkout">Checkout ({cart.length})</Button>}
      </div>
      {session && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {products.slice(0, 12).map(p => (
            <button key={p.id} onClick={() => add(p)} className="border rounded-xl p-4 hover:shadow-md hover:-translate-y-0.5 transition-all text-left" data-testid={`kiosk-prod-${p.id}`}>
              <p className="font-bold">{p.name}</p><p className="text-lg" style={{ color: theme.primary }}>${p.price}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------- CFD ----------------
export function CFD() {
  const { theme } = useTheme();
  const [data, setData] = useState({ cart: [] });
  useEffect(() => {
    // Use the v26 enriched feed (name + table + points) — falls back to v25 if older backend
    const tick = () => v26API.cfdEnriched()
      .then(r => setData(r.data || { cart: [] }))
      .catch(() => v25API.cfdCurrent().then(r => setData(r.data || { cart: [] })));
    tick();
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, []);
  const total = (data.cart || []).reduce((s, i) => s + (i.price || 0) * (i.quantity || 1), 0);
  return (
    <div className="min-h-screen bg-black text-white p-8 -m-6" data-testid="cfd-page">
      <div className="flex justify-between items-start mb-6">
        <h1 className="text-5xl font-bold flex items-center gap-3"><Monitor /> Welcome</h1>
        {data.tableNumber && <div className="text-right">
          <p className="text-xs text-gray-400 uppercase tracking-widest">Table</p>
          <p className="text-4xl font-bold text-amber-400">{data.tableNumber}</p>
        </div>}
      </div>
      {data.customerName && (
        <p className="text-2xl text-amber-300 mb-4" data-testid="cfd-customer">
          {data.isMember ? '⭐ ' : ''}{data.customerName}{data.membershipTier ? ` · ${data.membershipTier}` : ''}
        </p>
      )}
      <div className="space-y-3">
        {(data.cart || []).map((it, i) => (
          <div key={i} className="flex justify-between text-2xl border-b border-gray-700 pb-2">
            <span>{it.quantity || 1}× {it.name}</span>
            <span>${((it.price || 0) * (it.quantity || 1)).toFixed(2)}</span>
          </div>
        ))}
      </div>
      <div className="mt-8 text-5xl font-bold flex justify-between border-t-2 border-white pt-4">
        <span>TOTAL</span><span>${total.toFixed(2)}</span>
      </div>
      {data.pointsEarned > 0 && (
        <p className="mt-6 text-2xl text-emerald-400" data-testid="points-earned">
          ⭐ You'll earn {data.pointsEarned} points
        </p>
      )}
      {data.pointsMissed > 0 && !data.customerName && (
        <p className="mt-6 text-xl text-orange-400" data-testid="points-missed">
          ✨ Sign up to earn {data.pointsMissed} points — ask staff to add you!
        </p>
      )}
    </div>
  );
}

// ---------------- Churn Risk ----------------
export function ChurnRisk() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rows, setRows] = useState([]); const [selected, setSelected] = useState({});
  const load = () => v25API.churnRisk().then(r => setRows(r.data?.atRisk || []));
  useEffect(() => { load(); }, []);
  const send = async () => {
    const ids = Object.entries(selected).filter(([k, v]) => v).map(([k]) => k);
    if (ids.length === 0) return;
    await v25API.winBack(ids, 20); toast({ title: `Win-back queued for ${ids.length}` }); setSelected({}); load();
  };
  return (
    <div className="space-y-6" data-testid="churn-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Users className="text-orange-600" /> Guest Recovery — Churn Risk</h1>
        <Button onClick={send} disabled={Object.values(selected).filter(Boolean).length === 0} style={{ background: theme.primary }} data-testid="send-winback">Send $20 Win-Back</Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-5 py-3">Use</th><th className="text-left px-5 py-3">Guest</th><th className="text-right px-5 py-3">Visits</th><th className="text-left px-5 py-3">Last Seen</th><th className="text-left px-5 py-3">Tier</th></tr></thead>
          <tbody>{rows.length === 0 ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">No at-risk guests</td></tr> :
            rows.map(r => <tr key={r.id} className="border-t"><td className="px-5 py-3"><input type="checkbox" checked={!!selected[r.id]} onChange={e => setSelected({ ...selected, [r.id]: e.target.checked })} /></td>
            <td className="px-5 py-3 font-medium">{r.name}</td><td className="px-5 py-3 text-right">{r.visits}</td><td className="px-5 py-3 text-xs text-gray-500">{(r.lastSeen || '').slice(0, 10)}</td><td className="px-5 py-3"><Badge variant="outline">{r.tier}</Badge></td></tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}

// ---------------- Recipe Costing ----------------
export function RecipeCosting() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [ings, setIngs] = useState([]);
  useEffect(() => { fetch(`${process.env.REACT_APP_BACKEND_URL}/api/products`).then(r => r.json()).then(setProducts); }, []);
  const open = async (p) => { setSelected(p); const r = await v25API.getRecipe(p.id); setIngs(r.data?.ingredients || []); };
  const save = async () => { await v25API.upsertRecipe({ productId: selected.id, ingredients: ings }); toast({ title: 'Recipe saved · cost updated' }); };
  const total = ings.reduce((s, i) => s + (parseFloat(i.quantity) || 0) * (parseFloat(i.costPerUnit) || 0), 0);
  return (
    <div className="space-y-6" data-testid="recipe-costing-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><ChefHat className="text-red-600" /> Recipe Costing Engine</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-1"><CardContent className="p-0">
          <div className="px-4 py-3 border-b font-bold">Menu Items</div>
          <div className="max-h-[60vh] overflow-y-auto">
            {products.map(p => (
              <button key={p.id} onClick={() => open(p)} className={`w-full text-left px-4 py-2.5 text-sm border-b hover:bg-gray-50 ${selected?.id === p.id ? 'bg-amber-50' : ''}`} data-testid={`prod-${p.id}`}>
                <div className="flex justify-between"><span>{p.name}</span><span className="text-xs text-gray-500">${p.price}</span></div>
              </button>
            ))}
          </div>
        </CardContent></Card>
        <Card className="md:col-span-2"><CardContent className="p-5">
          {!selected ? <p className="text-center py-12 text-gray-400">Pick an item to cost it</p> : (
            <>
              <div className="flex justify-between items-baseline mb-3">
                <h2 className="font-bold">{selected.name}</h2>
                <div className="text-right"><p className="text-xs text-gray-500">Cost / Sells / Margin</p><p className="font-mono">${total.toFixed(2)} / ${selected.price} / {selected.price > 0 ? ((selected.price - total)/selected.price*100).toFixed(1) : 0}%</p></div>
              </div>
              <div className="space-y-2">
                {ings.map((ing, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-center">
                    <Input className="col-span-5" placeholder="Ingredient" value={ing.item || ''} onChange={e => { const a = [...ings]; a[i].item = e.target.value; setIngs(a); }} />
                    <Input className="col-span-2" type="number" placeholder="Qty" value={ing.quantity || ''} onChange={e => { const a = [...ings]; a[i].quantity = parseFloat(e.target.value) || 0; setIngs(a); }} />
                    <Input className="col-span-2" placeholder="Unit" value={ing.unit || ''} onChange={e => { const a = [...ings]; a[i].unit = e.target.value; setIngs(a); }} />
                    <Input className="col-span-2" type="number" placeholder="$/unit" value={ing.costPerUnit || ''} onChange={e => { const a = [...ings]; a[i].costPerUnit = parseFloat(e.target.value) || 0; setIngs(a); }} />
                    <Button size="sm" variant="ghost" className="col-span-1" onClick={() => setIngs(ings.filter((_, x) => x !== i))}>×</Button>
                  </div>
                ))}
                <Button variant="outline" onClick={() => setIngs([...ings, { item: '', quantity: 0, unit: 'g', costPerUnit: 0 }])} data-testid="add-ing"><Plus size={14} className="mr-1" /> Add Ingredient</Button>
              </div>
              <Button onClick={save} className="mt-4" style={{ background: theme.primary }} data-testid="save-recipe">Save Recipe & Update Cost</Button>
            </>
          )}
        </CardContent></Card>
      </div>
    </div>
  );
}

// ---------------- Dynamic Pricing Rules ----------------
export function DynamicPricing() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rules, setRules] = useState([]);
  const load = () => v25API.dynamicRules().then(r => setRules(r.data || []));
  useEffect(() => { load(); }, []);
  const add = async () => {
    const category = prompt('Category? (blank for all)') || '';
    const dow = parseInt(prompt('Day of week 0=Mon..6=Sun? (blank=any)') || '-1');
    const hourStart = parseInt(prompt('Start hour?') || '0');
    const hourEnd = parseInt(prompt('End hour?') || '24');
    const multiplier = parseFloat(prompt('Multiplier (e.g. 1.10 for +10%)?') || '1');
    await v25API.addDynamic({ category, dow: dow >= 0 ? dow : null, hourStart, hourEnd, multiplier });
    toast({ title: 'Rule added' }); load();
  };
  return (
    <div className="space-y-6" data-testid="dyn-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><TrendingUp className="text-amber-600" /> Dynamic Pricing Rules</h1>
        <Button onClick={add} style={{ background: theme.primary }}><Plus size={14} className="mr-1.5" /> Add Rule</Button>
      </div>
      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="text-left px-5 py-3">Category</th><th className="text-left px-5 py-3">Day</th><th className="text-right px-5 py-3">Hours</th><th className="text-right px-5 py-3">Multiplier</th></tr></thead>
          <tbody>{rules.length === 0 ? <tr><td colSpan={4} className="text-center py-8 text-gray-400">No rules</td></tr> :
            rules.map(r => <tr key={r.id} className="border-t"><td className="px-5 py-3">{r.category || 'All'}</td><td className="px-5 py-3">{r.dow !== null ? ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][r.dow] : 'Any'}</td><td className="px-5 py-3 text-right">{r.hourStart}:00 – {r.hourEnd}:00</td><td className="px-5 py-3 text-right"><Badge className={r.multiplier > 1 ? 'bg-red-100 text-red-700' : r.multiplier < 1 ? 'bg-blue-100 text-blue-700' : ''}>{((r.multiplier - 1) * 100).toFixed(0)}%</Badge></td></tr>)}</tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}

// ---------------- Subscriptions ----------------
export function Subscriptions() {
  const { theme } = useTheme();
  const [plans, setPlans] = useState([]); const [members, setMembers] = useState([]);
  useEffect(() => { v25API.subPlans().then(r => setPlans(r.data || [])); v25API.subMembers().then(r => setMembers(r.data || [])); }, []);
  return (
    <div className="space-y-6" data-testid="subs-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Star className="text-yellow-500" /> Subscription Memberships</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {plans.map(p => (
          <Card key={p.id} className="bg-gradient-to-br from-amber-50 to-yellow-100"><CardContent className="p-5">
            <p className="font-bold text-lg">{p.name}</p>
            <p className="text-3xl font-bold mt-2">${p.priceMonthly}<span className="text-sm text-gray-500">/mo</span></p>
            <ul className="text-sm mt-3 space-y-1">{(p.perks || []).map((perk, i) => <li key={i}>· {perk}</li>)}</ul>
            <Badge className="mt-3">{members.filter(m => m.planId === p.id).length} members</Badge>
          </CardContent></Card>
        ))}
      </div>
    </div>
  );
}
