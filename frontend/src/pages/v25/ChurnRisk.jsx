import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Users } from 'lucide-react';

export default function ChurnRisk() {
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
