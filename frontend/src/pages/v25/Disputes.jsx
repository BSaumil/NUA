import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { Shield, Plus } from 'lucide-react';

export default function Disputes() {
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
