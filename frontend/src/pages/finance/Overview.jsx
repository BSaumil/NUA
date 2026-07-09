import React, { useState, useEffect, useCallback } from 'react';
import { financeAPI } from '../../services/api';
import { toast } from 'sonner';
import { Card, CardContent } from '../../components/ui/card';
import { TrendingUp, Scale, Landmark, Wallet, ReceiptText, ArrowLeftRight } from 'lucide-react';
import { FMT } from './helpers';

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

export default Overview;
