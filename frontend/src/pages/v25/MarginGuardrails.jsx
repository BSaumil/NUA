import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';

export default function MarginGuardrails() {
  const { theme } = useTheme();
  const [data, setData] = useState({ warnings: [] });
  useEffect(() => { v25API.marginGuardrails().then(r => setData(r.data)); }, []);
  return (
    <div className="space-y-6" data-testid="margin-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>Menu Margin Guardrails</h1>
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
