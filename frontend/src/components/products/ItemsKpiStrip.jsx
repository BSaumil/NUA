import React, { useMemo } from 'react';
import { Package, AlertTriangle, XCircle, CheckCircle2, EyeOff } from 'lucide-react';

/**
 * KPI strip for the Items page.
 *
 * Five clickable tiles that each apply a corresponding filter to the
 * product table below — total, low-stock, out-of-stock, active,
 * inactive/86. Clicking a tile again (i.e. the currently-active one)
 * clears the filter and returns to "all". This keeps the whole surface
 * one-click reachable from the top of the page.
 */
export const ItemsKpiStrip = ({ theme, products, filterStatus, setFilterStatus }) => {
  const counts = useMemo(() => {
    let total = 0, lowStock = 0, outOfStock = 0, active = 0, inactive = 0;
    (products || []).forEach(p => {
      total++;
      const stock = Number(p.stock ?? 0);
      const threshold = Number(p.lowStockThreshold ?? 5);
      if (stock <= 0) outOfStock++;
      else if (stock <= threshold) lowStock++;
      if (p.eightySixed) inactive++;
      else active++;
    });
    return { total, lowStock, outOfStock, active, inactive };
  }, [products]);

  const tiles = [
    { key: 'all',        label: 'Total items',    value: counts.total,      icon: Package,        tone: 'from-slate-50 to-slate-100 text-slate-700 border-slate-200' },
    { key: 'lowStock',   label: 'Low stock',      value: counts.lowStock,   icon: AlertTriangle,  tone: 'from-amber-50 to-amber-100 text-amber-800 border-amber-200' },
    { key: 'outOfStock', label: 'Out of stock',   value: counts.outOfStock, icon: XCircle,        tone: 'from-rose-50 to-rose-100 text-rose-800 border-rose-200' },
    { key: 'active',     label: 'Active',         value: counts.active,     icon: CheckCircle2,   tone: 'from-emerald-50 to-emerald-100 text-emerald-800 border-emerald-200' },
    { key: '86',         label: 'Inactive / 86',  value: counts.inactive,   icon: EyeOff,         tone: 'from-gray-50 to-gray-100 text-gray-700 border-gray-200' },
  ];

  const onClick = (key) => {
    // Second click on the same tile clears the filter.
    setFilterStatus(filterStatus === key ? 'all' : key);
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="items-kpi-strip">
      {tiles.map(t => {
        const Icon = t.icon;
        const active = filterStatus === t.key;
        return (
          <button
            key={t.key}
            onClick={() => onClick(t.key)}
            data-testid={`items-kpi-${t.key}`}
            className={`rounded-xl border bg-gradient-to-br px-4 py-3 text-left transition-all
              ${t.tone}
              ${active ? 'ring-2 ring-offset-1 scale-[1.02] shadow-md' : 'hover:shadow-sm hover:-translate-y-0.5'}
            `}
            style={active ? { '--tw-ring-color': theme?.primary || '#F97316' } : {}}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-widest font-semibold opacity-80">{t.label}</span>
              <Icon size={14} className="opacity-70" />
            </div>
            <div className="text-2xl font-bold mt-1">{t.value}</div>
            {active && (
              <div className="text-[10px] mt-1 opacity-70 font-medium">Click again to clear filter</div>
            )}
          </button>
        );
      })}
    </div>
  );
};
