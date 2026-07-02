import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { superAPI } from '../services/api';
import axios from 'axios';
const API = process.env.REACT_APP_BACKEND_URL;
const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });
import { useTheme } from '../contexts/ThemeContext';
import { useToast } from '../hooks/use-toast';
import { Shield, Calculator, Save, CheckCircle2, Clock, DollarSign, Info, Calendar } from 'lucide-react';

/**
 * Superannuation console — Fair Work Commission compliant.
 *
 * The owner runs a WEEKLY pay-run calculation, reviews per-employee SG, then
 * commits it. Committed weekly runs flow into the "Superannuation payable"
 * line on BAS/GST for the quarter, and into a yearly summary for AGM/EOFY.
 */
export default function Super() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [rateInfo, setRateInfo] = useState(null);
  const [staff, setStaff] = useState([]);            // {name, role, awardCode, grossPay, include}
  const [payDate, setPayDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [periodStart, setPeriodStart] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 6);
    return d.toISOString().slice(0, 10);
  });
  const [periodEnd, setPeriodEnd] = useState(() => new Date().toISOString().slice(0, 10));
  const [override, setOverride] = useState('');       // owner override %
  const [calc, setCalc] = useState(null);
  const [history, setHistory] = useState([]);
  const [summary, setSummary] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [r, s, runs, sum] = await Promise.all([
          superAPI.rate(payDate),
          axios.get(`${API}/api/auth/staff`, { headers: authHeader() }).catch(() => ({ data: [] })),
          superAPI.listWeeklyRuns(),
          superAPI.summary(),
        ]);
        setRateInfo(r.data);
        setStaff((s.data || []).map(x => ({
          staffId: x.id, name: x.name, role: x.role, awardCode: x.awardCode || '',
          grossPay: 0, include: true,
        })));
        setHistory(runs.data || []);
        setSummary(sum.data);
      } catch (e) {
        toast({ title: 'Load failed', description: e?.response?.data?.detail, variant: 'destructive' });
      }
    })();
  }, []);

  useEffect(() => {
    superAPI.rate(payDate).then(r => setRateInfo(r.data)).catch(() => {});
  }, [payDate]);

  const doCalc = async () => {
    const payload = {
      payPeriodStart: periodStart,
      payPeriodEnd: periodEnd,
      payDate,
      staff: staff.filter(s => s.include).map(s => ({
        staffId: s.staffId, name: s.name, role: s.role,
        awardCode: s.awardCode, grossPay: Number(s.grossPay || 0),
      })),
      ...(override && !Number.isNaN(parseFloat(override)) ? { rate: parseFloat(override) } : {}),
    };
    if (payload.staff.length === 0) {
      toast({ title: 'Select at least one employee', variant: 'destructive' });
      return;
    }
    setBusy(true);
    try {
      const r = await superAPI.calc(payload);
      setCalc(r.data);
    } catch (e) {
      toast({ title: 'Calc failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const commit = async () => {
    if (!calc) return;
    setBusy(true);
    try {
      const r = await superAPI.commitWeeklyRun({
        payPeriodStart: periodStart, payPeriodEnd: periodEnd, payDate,
        staff: staff.filter(s => s.include).map(s => ({
          staffId: s.staffId, name: s.name, role: s.role,
          awardCode: s.awardCode, grossPay: Number(s.grossPay || 0),
        })),
        ...(override && !Number.isNaN(parseFloat(override)) ? { rate: parseFloat(override) } : {}),
        note: `Weekly SG for ${periodStart} → ${periodEnd}`,
      });
      toast({ title: 'Committed to BAS ledger', description: `$${r.data.totalSuper?.toFixed(2)} SG accrued.` });
      const [runs, sum] = await Promise.all([superAPI.listWeeklyRuns(), superAPI.summary()]);
      setHistory(runs.data || []);
      setSummary(sum.data);
    } catch (e) {
      toast({ title: 'Commit failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const markPaid = async (run) => {
    setBusy(true);
    try {
      await superAPI.markPaid(run.id, { status: 'paid', paidAt: new Date().toISOString() });
      toast({ title: 'Marked paid' });
      const runs = await superAPI.listWeeklyRuns();
      setHistory(runs.data || []);
    } catch (e) {
      toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const totalGross = useMemo(
    () => staff.filter(s => s.include).reduce((t, s) => t + Number(s.grossPay || 0), 0),
    [staff]
  );

  return (
    <div className="space-y-6" data-testid="super-page">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Shield className="text-blue-600" /> Superannuation
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Fair Work compliant. Weekly runs feed the BAS/GST &quot;Superannuation payable&quot; line.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="super-kpis">
        <Kpi label="Current SG rate" value={rateInfo ? `${rateInfo.rate}%` : '—'} tone="bg-blue-50 border-blue-200 text-blue-800" testid="kpi-rate" />
        <Kpi label="Runs this FY" value={summary?.quarters?.reduce((t, q) => t + q.runs, 0) ?? 0} tone="bg-slate-50 border-slate-200 text-slate-800" testid="kpi-runs" />
        <Kpi label="FY total SG" value={summary ? `$${summary.totalSuper.toFixed(0)}` : '—'} tone="bg-emerald-50 border-emerald-200 text-emerald-800" testid="kpi-fy-total" />
        <Kpi label="Paid to fund" value={summary ? `$${summary.totalPaid.toFixed(0)}` : '—'} tone="bg-violet-50 border-violet-200 text-violet-800" testid="kpi-fy-paid" />
      </div>

      {/* Rate ladder */}
      {rateInfo && (
        <Card><CardContent className="p-4 flex items-start gap-3">
          <Info className="text-blue-500 mt-0.5" size={18} />
          <div className="text-sm text-gray-700 space-y-1">
            <div><strong>{rateInfo.rate}%</strong> for pay date <span className="font-mono">{rateInfo.date}</span> (source: {rateInfo.source.replace(/_/g, ' ')}).</div>
            <div className="flex gap-2 flex-wrap text-[10px] text-gray-500">
              {rateInfo.tiers.map(t => (
                <span key={t.effectiveFrom} className="border rounded px-2 py-0.5">
                  from {t.effectiveFrom}: <strong>{t.rate}%</strong>
                </span>
              ))}
            </div>
          </div>
        </CardContent></Card>
      )}

      {/* Calculator */}
      <Card data-testid="super-calculator">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-center gap-2 text-lg font-semibold"><Calculator size={18} /> Weekly Pay-Run Calculator</div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <Field label="Period start">
              <Input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} data-testid="period-start" />
            </Field>
            <Field label="Period end">
              <Input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} data-testid="period-end" />
            </Field>
            <Field label="Pay date">
              <Input type="date" value={payDate} onChange={e => setPayDate(e.target.value)} data-testid="pay-date" />
            </Field>
            <Field label={`Rate override (default ${rateInfo?.rate ?? '—'}%)`}>
              <Input type="number" step="0.1" min="0" max="30" value={override} onChange={e => setOverride(e.target.value)} placeholder="—" data-testid="rate-override" />
            </Field>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-3 py-2 text-left"><input type="checkbox"
                    checked={staff.every(s => s.include)}
                    onChange={e => setStaff(staff.map(s => ({ ...s, include: e.target.checked })))} /></th>
                  <th className="px-3 py-2 text-left">Employee</th>
                  <th className="px-3 py-2 text-left">Role</th>
                  <th className="px-3 py-2 text-left">Award</th>
                  <th className="px-3 py-2 text-right">Gross ($)</th>
                </tr>
              </thead>
              <tbody>
                {staff.length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-6 text-gray-400" data-testid="no-staff">No staff yet — add them in Team → Staff.</td></tr>
                ) : staff.map((s, idx) => (
                  <tr key={s.staffId || idx} className="border-t" data-testid={`super-row-${s.staffId || idx}`}>
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={s.include}
                        onChange={e => setStaff(staff.map((x, i) => i === idx ? { ...x, include: e.target.checked } : x))} />
                    </td>
                    <td className="px-3 py-2 font-medium">{s.name}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{s.role || '—'}</td>
                    <td className="px-3 py-2 text-xs font-mono text-gray-500">{s.awardCode || '—'}</td>
                    <td className="px-3 py-2 text-right">
                      <Input type="number" step="0.01" min="0" value={s.grossPay}
                        onChange={e => setStaff(staff.map((x, i) => i === idx ? { ...x, grossPay: e.target.value } : x))}
                        className="text-right w-32 ml-auto"
                        data-testid={`gross-${s.staffId || idx}`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
              {staff.length > 0 && (
                <tfoot className="bg-gray-50 font-semibold text-sm">
                  <tr><td colSpan={4} className="px-3 py-2 text-right">Total gross OTE</td>
                    <td className="px-3 py-2 text-right">${totalGross.toFixed(2)}</td></tr>
                </tfoot>
              )}
            </table>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={doCalc} disabled={busy} data-testid="calc-btn">
              <Calculator size={14} className="mr-1.5" /> Calculate
            </Button>
            <Button onClick={commit} disabled={busy || !calc} style={{ background: theme.primary }} className="text-white" data-testid="commit-btn">
              <Save size={14} className="mr-1.5" /> Commit to BAS ledger
            </Button>
          </div>

          {/* Result */}
          {calc && (
            <div className="rounded-lg border bg-gradient-to-br from-emerald-50 to-blue-50 p-4 space-y-2" data-testid="super-result">
              <div className="text-sm font-semibold flex items-center gap-2">
                <DollarSign size={16} /> Result — rate {calc.rate}% ({calc.rateSource.replace(/_/g, ' ')})
              </div>
              <table className="w-full text-xs">
                <thead className="text-gray-500">
                  <tr>
                    <th className="text-left">Employee</th>
                    <th className="text-right">Gross</th>
                    <th className="text-right">OTE</th>
                    <th className="text-right">SG @ {calc.rate}%</th>
                  </tr>
                </thead>
                <tbody>
                  {calc.employees.map((e, i) => (
                    <tr key={i} className="border-t">
                      <td className="py-1">{e.name}</td>
                      <td className="text-right">${e.grossPay.toFixed(2)}</td>
                      <td className="text-right">${e.ordinaryTimeEarnings.toFixed(2)}</td>
                      <td className="text-right font-mono">${e.superContribution.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t-2 border-double font-semibold">
                  <tr><td colSpan={3} className="text-right py-1">Total SG payable</td>
                    <td className="text-right font-mono">${calc.totalSuper.toFixed(2)}</td></tr>
                </tfoot>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Committed weekly runs history */}
      <Card data-testid="super-history">
        <CardContent className="p-0">
          <div className="p-4 flex items-center gap-2 border-b">
            <Clock size={16} /> <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500">Committed weekly runs</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="text-left px-4 py-2">Pay date</th>
                <th className="text-left px-4 py-2">Period</th>
                <th className="text-right px-4 py-2">OTE</th>
                <th className="text-right px-4 py-2">SG</th>
                <th className="text-center px-4 py-2">Rate</th>
                <th className="text-center px-4 py-2">Status</th>
                <th className="text-right px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-gray-400" data-testid="no-history">
                  No committed runs yet. Calculate + Commit above to start the ledger.
                </td></tr>
              ) : history.map(r => (
                <tr key={r.id} className="border-t" data-testid={`super-run-${r.id}`}>
                  <td className="px-4 py-2 font-mono text-xs">{r.payDate}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">{r.payPeriodStart} → {r.payPeriodEnd}</td>
                  <td className="px-4 py-2 text-right">${r.totalOTE?.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right font-mono">${r.totalSuper?.toFixed(2)}</td>
                  <td className="px-4 py-2 text-center">{r.rate}%</td>
                  <td className="px-4 py-2 text-center">
                    <Badge className={r.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>
                      {r.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {r.status !== 'paid' && (
                      <Button size="sm" variant="outline" onClick={() => markPaid(r)} data-testid={`mark-paid-${r.id}`}>
                        <CheckCircle2 size={11} className="mr-1" /> Mark paid
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Quarterly summary */}
      {summary && (
        <Card data-testid="super-yearly-summary">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <Calendar size={16} /> <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500">FY {summary.fy} — quarterly summary</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {summary.quarters.map(q => (
                <div key={q.quarter} className="border rounded-lg p-3 bg-gradient-to-br from-slate-50 to-slate-100" data-testid={`quarter-${q.quarter}`}>
                  <div className="text-[10px] uppercase tracking-widest text-gray-500 font-semibold">{q.quarter}</div>
                  <div className="text-lg font-bold">${q.totalSuper.toFixed(0)}</div>
                  <div className="text-[10px] text-gray-500">{q.runs} runs · paid ${q.totalPaid.toFixed(0)}</div>
                  <div className="text-[10px] text-gray-400 mt-1">{q.start} → {q.end}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

const Kpi = ({ label, value, tone, testid }) => (
  <div className={`rounded-xl border px-3 py-2 ${tone}`} data-testid={testid}>
    <div className="text-[10px] uppercase tracking-widest font-semibold opacity-80">{label}</div>
    <div className="text-xl font-bold mt-0.5">{value}</div>
  </div>
);

const Field = ({ label, children }) => (
  <div>
    <label className="text-[10px] uppercase tracking-widest text-gray-500 block mb-1 font-semibold">{label}</label>
    {children}
  </div>
);
