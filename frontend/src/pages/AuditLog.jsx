import React, { useState, useEffect } from 'react';
import { ShieldAlert, Filter, Search, FileText } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { v15API } from '../services/api';

const TYPE_COLORS = {
  COMP: 'bg-blue-100 text-blue-700',
  VOID: 'bg-red-100 text-red-700',
  REFUND: 'bg-amber-100 text-amber-700',
  GHOST_DISCOUNT: 'bg-purple-100 text-purple-700',
};

export default function AuditLog() {
  const { theme } = useTheme();
  const [logs, setLogs] = useState([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  useEffect(() => { v15API.getAuditLogs().then(r => setLogs(r.data || [])).catch(() => {}); }, []);

  const filtered = logs.filter(l => {
    if (filter !== 'all' && l.type !== filter) return false;
    if (search && !((l.details || '').toLowerCase().includes(search.toLowerCase()) || (l.user || '').toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  });

  return (
    <div className="space-y-6" data-testid="audit-log-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <ShieldAlert size={22} /> Audit Log
        </h1>
        <p className="text-sm text-gray-500">Every sensitive action — voids, refunds, comps, ghost discounts — tracked with timestamp, operator, and amount.</p>
      </div>
      <Card>
        <CardContent className="p-0">
          <div className="p-4 flex items-center gap-2 border-b">
            <div className="relative flex-1"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><Input className="pl-8" placeholder="Search reason / user..." value={search} onChange={e => setSearch(e.target.value)} data-testid="audit-search" /></div>
            <select className="p-2 border rounded-md text-sm" value={filter} onChange={e => setFilter(e.target.value)} data-testid="audit-filter">
              <option value="all">All types</option>
              <option value="COMP">Comp</option>
              <option value="VOID">Void</option>
              <option value="REFUND">Refund</option>
              <option value="GHOST_DISCOUNT">Ghost Discount</option>
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="audit-table">
              <thead className="bg-gray-50"><tr>
                <th className="text-left p-3">Time</th>
                <th className="text-left p-3">Type</th>
                <th className="text-left p-3">User</th>
                <th className="text-left p-3">Details</th>
              </tr></thead>
              <tbody>
                {filtered.map(l => (
                  <tr key={l.id} className="border-t hover:bg-gray-50" data-testid={`audit-row-${l.id}`}>
                    <td className="p-3 text-xs text-gray-500">{l.timestamp ? new Date(l.timestamp).toLocaleString() : '—'}</td>
                    <td className="p-3"><Badge className={TYPE_COLORS[l.type] || 'bg-gray-100 text-gray-700'}>{l.type}</Badge></td>
                    <td className="p-3 text-xs font-mono">{(l.user || '').slice(0, 16)}</td>
                    <td className="p-3">{l.details}</td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan="4" className="p-12 text-center text-gray-400"><FileText size={32} className="mx-auto mb-2 opacity-30" />No audit events recorded</td></tr>}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
