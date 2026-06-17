import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { FileWarning } from 'lucide-react';

export default function FraudDetection() {
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
