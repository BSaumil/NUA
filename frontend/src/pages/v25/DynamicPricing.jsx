import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../hooks/use-toast';
import { TrendingUp, Plus } from 'lucide-react';

export default function DynamicPricing() {
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
