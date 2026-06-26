import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Shield, Plus, FileText, AlertTriangle, CheckCircle2, Clock, RefreshCcw, Paperclip } from 'lucide-react';

/**
 * Chargeback / Dispute Console.
 *
 * Owners can open a dispute against any transaction, then attach evidence
 * (system auto-assembles tx snapshot + signature + IP on the backend). KPIs
 * across the top give an at-a-glance view of risk exposure for the period.
 *
 * UX deliberately reads like the rest of the v25 ops surfaces — soft white
 * cards, tabular density, status-keyed pill colours so the eye can scan a
 * page of 50 disputes without slowing down. No browser prompts; everything
 * happens inside an inline dialog so we can validate.
 */
const STATUS_META = {
  open:                { label: 'Open',              cls: 'bg-amber-100 text-amber-700',   icon: Clock },
  evidence_submitted:  { label: 'Evidence Submitted', cls: 'bg-blue-100 text-blue-700',     icon: Paperclip },
  won:                 { label: 'Won',               cls: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
  lost:                { label: 'Lost',              cls: 'bg-rose-100 text-rose-700',     icon: AlertTriangle },
};

const REASONS = ['fraud', 'product_not_received', 'duplicate', 'unrecognised', 'service_not_provided', 'other'];

const fmtMoney = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function Disputes() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
  const [form, setForm] = useState({ txId: '', amount: '', reason: 'fraud' });
  const [evidenceFor, setEvidenceFor] = useState(null);
  const [evidenceNotes, setEvidenceNotes] = useState('');
  const [filter, setFilter] = useState('all');

  const load = async () => {
    setBusy(true);
    try {
      const r = await v25API.disputes();
      setRows(r.data || []);
    } catch (e) {
      toast({ title: 'Failed to load disputes', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(false); }
  };
  useEffect(() => { load(); }, []);

  const kpis = useMemo(() => {
    const k = { open: 0, evidence: 0, won: 0, lost: 0, atRisk: 0, recovered: 0 };
    (rows || []).forEach(d => {
      if (d.status === 'open') { k.open++; k.atRisk += Number(d.amount || 0); }
      else if (d.status === 'evidence_submitted') { k.evidence++; k.atRisk += Number(d.amount || 0); }
      else if (d.status === 'won') { k.won++; k.recovered += Number(d.amount || 0); }
      else if (d.status === 'lost') k.lost++;
    });
    return k;
  }, [rows]);

  const filteredRows = useMemo(() => {
    if (filter === 'all') return rows;
    return rows.filter(d => d.status === filter);
  }, [rows, filter]);

  const submitDispute = async () => {
    const amt = parseFloat(form.amount || '0');
    if (!form.txId.trim()) return toast({ title: 'Transaction ID is required', variant: 'destructive' });
    if (!(amt > 0)) return toast({ title: 'Amount must be > 0', variant: 'destructive' });
    setBusy(true);
    try {
      await v25API.openDispute({ txId: form.txId.trim(), amount: amt, reason: form.reason });
      toast({ title: 'Dispute opened', description: 'Add evidence to start the response window.' });
      setOpenDialog(false);
      setForm({ txId: '', amount: '', reason: 'fraud' });
      load();
    } catch (e) {
      toast({ title: 'Failed to open', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const submitEvidence = async () => {
    if (!evidenceFor) return;
    setBusy(true);
    try {
      await v25API.attachEvidence(evidenceFor.id, evidenceNotes);
      toast({ title: 'Evidence pack assembled', description: 'Status moved to "evidence_submitted".' });
      setEvidenceFor(null);
      setEvidenceNotes('');
      load();
    } catch (e) {
      toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="disputes-page">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Shield className="text-orange-600" /> Chargeback / Dispute Console
          </h1>
          <p className="text-sm text-gray-500 mt-1">Track fraud, prepare evidence, recover revenue.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={busy} data-testid="refresh-disputes">
            <RefreshCcw size={14} className={`mr-1.5 ${busy ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button onClick={() => setOpenDialog(true)} style={{ background: theme.primary }} className="text-white" data-testid="new-dispute">
            <Plus size={14} className="mr-1.5" /> New Dispute
          </Button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="dispute-kpis">
        <Kpi label="Open" value={kpis.open} tone="bg-amber-50 border-amber-200 text-amber-800" testid="kpi-open" />
        <Kpi label="Evidence in" value={kpis.evidence} tone="bg-blue-50 border-blue-200 text-blue-800" testid="kpi-evidence" />
        <Kpi label="Won" value={kpis.won} tone="bg-emerald-50 border-emerald-200 text-emerald-800" testid="kpi-won" />
        <Kpi label="At-risk $" value={fmtMoney(kpis.atRisk)} tone="bg-rose-50 border-rose-200 text-rose-800" testid="kpi-atrisk" />
        <Kpi label="Recovered $" value={fmtMoney(kpis.recovered)} tone="bg-violet-50 border-violet-200 text-violet-800" testid="kpi-recovered" />
      </div>

      {/* Status filter pills */}
      <div className="flex items-center gap-1.5 flex-wrap" data-testid="dispute-filters">
        {[
          { v: 'all', label: 'All' },
          { v: 'open', label: 'Open' },
          { v: 'evidence_submitted', label: 'Evidence' },
          { v: 'won', label: 'Won' },
          { v: 'lost', label: 'Lost' },
        ].map(f => (
          <button
            key={f.v}
            onClick={() => setFilter(f.v)}
            className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${filter === f.v ? 'text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            style={filter === f.v ? { background: theme.primary } : {}}
            data-testid={`filter-${f.v}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="text-left px-5 py-3">Dispute ID</th>
                <th className="text-left px-5 py-3">Tx</th>
                <th className="text-left px-5 py-3">Reason</th>
                <th className="text-right px-5 py-3">Amount</th>
                <th className="text-center px-5 py-3">Status</th>
                <th className="text-left px-5 py-3">Opened</th>
                <th className="text-center px-5 py-3">Evidence</th>
                <th className="text-right px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-12 text-gray-400" data-testid="no-disputes">
                  <Shield size={32} className="mx-auto mb-2 opacity-40" />
                  No disputes in this view
                </td></tr>
              ) : (
                filteredRows.map(d => {
                  const meta = STATUS_META[d.status] || STATUS_META.open;
                  const Icon = meta.icon;
                  const ev = Array.isArray(d.evidence) ? d.evidence.length : 0;
                  return (
                    <tr key={d.id} className="border-t hover:bg-gray-50" data-testid={`dispute-${d.id}`}>
                      <td className="px-5 py-3 font-mono text-xs">{d.id}</td>
                      <td className="px-5 py-3 font-mono text-xs">{d.txId || '—'}</td>
                      <td className="px-5 py-3 capitalize text-xs">{(d.reason || 'fraud').replace(/_/g, ' ')}</td>
                      <td className="px-5 py-3 text-right font-mono">{fmtMoney(d.amount)}</td>
                      <td className="px-5 py-3 text-center">
                        <Badge className={`${meta.cls} font-semibold inline-flex items-center gap-1`}>
                          <Icon size={11} /> {meta.label}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-xs text-gray-500">
                        {d.openedAt ? new Date(d.openedAt).toLocaleString() : '—'}
                      </td>
                      <td className="px-5 py-3 text-center text-xs">
                        {ev > 0
                          ? <span className="inline-flex items-center gap-1 text-blue-700"><FileText size={11} /> {ev}</span>
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-5 py-3 text-right">
                        {d.status === 'open' && (
                          <Button size="sm" variant="outline" onClick={() => { setEvidenceFor(d); setEvidenceNotes(''); }} data-testid={`attach-${d.id}`}>
                            <Paperclip size={12} className="mr-1" /> Attach evidence
                          </Button>
                        )}
                        {d.status === 'evidence_submitted' && (
                          <span className="text-[10px] text-blue-600">Awaiting bank</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* New dispute dialog */}
      <Dialog open={openDialog} onOpenChange={setOpenDialog}>
        <DialogContent className="max-w-sm" data-testid="new-dispute-dialog">
          <DialogHeader>
            <DialogTitle>Open a Dispute</DialogTitle>
            <DialogDescription className="text-xs text-gray-500">Capture the disputed transaction so we can prepare evidence before the bank&apos;s response window closes.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-[10px] uppercase tracking-widest text-gray-500 block mb-1">Transaction ID</label>
              <Input
                value={form.txId}
                onChange={e => setForm({ ...form, txId: e.target.value })}
                placeholder="TX-… (paste from receipt or transactions page)"
                data-testid="dispute-tx-input"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-widest text-gray-500 block mb-1">Disputed amount ($)</label>
              <Input
                type="number" step="0.01" min="0.01"
                value={form.amount}
                onChange={e => setForm({ ...form, amount: e.target.value })}
                placeholder="0.00"
                data-testid="dispute-amount-input"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-widest text-gray-500 block mb-1">Reason</label>
              <select
                className="w-full p-2 border rounded text-sm"
                value={form.reason}
                onChange={e => setForm({ ...form, reason: e.target.value })}
                data-testid="dispute-reason-select"
              >
                {REASONS.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div className="flex gap-2 pt-1">
              <Button variant="outline" onClick={() => setOpenDialog(false)} className="flex-1" data-testid="dispute-cancel">Cancel</Button>
              <Button onClick={submitDispute} disabled={busy} className="flex-1 text-white" style={{ background: theme.primary }} data-testid="dispute-submit">
                {busy ? 'Opening…' : 'Open dispute'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Evidence attach dialog */}
      <Dialog open={!!evidenceFor} onOpenChange={(o) => { if (!o) setEvidenceFor(null); }}>
        <DialogContent className="max-w-md" data-testid="evidence-dialog">
          <DialogHeader>
            <DialogTitle>Attach Evidence Pack</DialogTitle>
            <DialogDescription className="text-xs text-gray-500">Auto-bundles the tx snapshot, line items, signature and IP; add any notes the bank should see.</DialogDescription>
          </DialogHeader>
          {evidenceFor && (
            <div className="space-y-3 py-2">
              <div className="text-xs text-gray-600 bg-gray-50 border rounded p-2">
                Tx <span className="font-mono">{evidenceFor.txId || '—'}</span> · <strong>{fmtMoney(evidenceFor.amount)}</strong> · reason <em>{(evidenceFor.reason || 'fraud').replace(/_/g, ' ')}</em>
              </div>
              <p className="text-[11px] text-gray-500 leading-relaxed">
                We&apos;ll auto-assemble the transaction snapshot, line items, signature and IP into the evidence pack. Add any additional notes the bank should see.
              </p>
              <textarea
                rows={4}
                value={evidenceNotes}
                onChange={e => setEvidenceNotes(e.target.value)}
                placeholder="e.g. 'Guest paid in person, signed receipt attached. Loyalty member since 2024.'"
                className="w-full p-2 border rounded text-sm"
                data-testid="evidence-notes"
              />
              <div className="flex gap-2 pt-1">
                <Button variant="outline" onClick={() => setEvidenceFor(null)} className="flex-1" data-testid="evidence-cancel">Cancel</Button>
                <Button onClick={submitEvidence} disabled={busy} className="flex-1 text-white" style={{ background: theme.primary }} data-testid="evidence-submit">
                  {busy ? 'Assembling…' : 'Assemble & submit'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

const Kpi = ({ label, value, tone, testid }) => (
  <div className={`rounded-xl border px-3 py-2 ${tone}`} data-testid={testid}>
    <div className="text-[10px] uppercase tracking-widest font-semibold opacity-80">{label}</div>
    <div className="text-xl font-bold mt-0.5">{value}</div>
  </div>
);
