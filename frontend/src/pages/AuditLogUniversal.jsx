import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { Button } from '../components/ui/button';
import { History, Search, User, Shield, Clock } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const H = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });

const ACTION_COLORS = { created: 'bg-emerald-100 text-emerald-700', updated: 'bg-blue-100 text-blue-700', deleted: 'bg-rose-100 text-rose-700', restored: 'bg-purple-100 text-purple-700' };

export default function AuditLog() {
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [entityType, setEntityType] = useState('');
  const [action, setAction] = useState('');
  const [actor, setActor] = useState('');
  const [expanded, setExpanded] = useState(null);

  const load = useCallback(async () => {
    try {
      const params = {};
      if (entityType) params.entity_type = entityType;
      if (action) params.action = action;
      if (actor) params.actor = actor;
      params.limit = 200;
      const [e, s] = await Promise.all([
        axios.get(`${API}/audit/events`, { headers: H(), params }),
        axios.get(`${API}/audit/summary`, { headers: H() }),
      ]);
      setEvents(e.data); setSummary(s.data);
    } catch { toast.error('Failed to load audit log'); }
  }, [entityType, action, actor]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6" data-testid="audit-log-page">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2"><History className="text-slate-600" /> Universal Audit Log</h1>
        <p className="text-sm text-slate-500 mt-1">Every mutation, everywhere. Filter and drill into the full before/after diff.</p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SmallStat label="Total Events" value={summary.total} icon={History} />
          <SmallStat label="Entity Types" value={summary.byEntity.length} icon={Shield} />
          <SmallStat label="Actors" value={summary.byActor.length} icon={User} />
          <SmallStat label="Most active" value={summary.byActor[0]?._id || '—'} icon={Clock} small />
        </div>
      )}

      <Card><CardContent className="p-4 grid grid-cols-1 md:grid-cols-4 gap-2">
        <Input placeholder="Entity type (customer, product, transaction…)" value={entityType} onChange={e => setEntityType(e.target.value)} data-testid="filter-entity" />
        <Select value={action} onValueChange={setAction}>
          <SelectTrigger data-testid="filter-action"><SelectValue placeholder="Any action" /></SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">Any action</SelectItem>
            <SelectItem value="created">Created</SelectItem>
            <SelectItem value="updated">Updated</SelectItem>
            <SelectItem value="deleted">Deleted</SelectItem>
            <SelectItem value="restored">Restored</SelectItem>
          </SelectContent>
        </Select>
        <Input placeholder="Actor email…" value={actor} onChange={e => setActor(e.target.value)} data-testid="filter-actor" />
        <Button onClick={load} data-testid="filter-apply"><Search size={14} className="mr-1" /> Filter</Button>
      </CardContent></Card>

      <Card><CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-slate-50"><tr>
            <th className="p-2 pl-4 text-left text-xs text-slate-500">Time</th>
            <th className="p-2 text-left text-xs text-slate-500">Actor</th>
            <th className="p-2 text-left text-xs text-slate-500">Action</th>
            <th className="p-2 text-left text-xs text-slate-500">Entity</th>
            <th className="p-2 text-left text-xs text-slate-500">Memo</th>
            <th className="p-2 pr-4 text-left text-xs text-slate-500">Device / IP</th>
          </tr></thead>
          <tbody>
            {events.map(e => (
              <React.Fragment key={e.id}>
                <tr className="border-t hover:bg-slate-50 cursor-pointer" onClick={() => setExpanded(expanded === e.id ? null : e.id)}>
                  <td className="p-2 pl-4 text-xs">{new Date(e.ts).toLocaleString()}</td>
                  <td className="p-2 text-xs font-mono">{e.actor}</td>
                  <td className="p-2"><Badge className={`text-[10px] ${ACTION_COLORS[e.action] || 'bg-slate-100'}`}>{e.action}</Badge></td>
                  <td className="p-2 text-xs"><span className="font-mono">{e.entityType}</span> · {(e.entityId || '').slice(0, 8)}</td>
                  <td className="p-2 text-xs text-slate-500 truncate max-w-xs">{e.memo}</td>
                  <td className="p-2 pr-4 text-[10px] text-slate-400">{(e.device || '?').slice(0, 40)} · {e.ip}</td>
                </tr>
                {expanded === e.id && (
                  <tr className="border-t bg-slate-50/70">
                    <td colSpan="6" className="p-4">
                      <div className="grid md:grid-cols-2 gap-3 text-[11px]">
                        <div>
                          <p className="font-medium mb-1">Before</p>
                          <pre className="bg-white border rounded p-2 overflow-auto max-h-64">{JSON.stringify(e.before, null, 2)}</pre>
                        </div>
                        <div>
                          <p className="font-medium mb-1">After</p>
                          <pre className="bg-white border rounded p-2 overflow-auto max-h-64">{JSON.stringify(e.after, null, 2)}</pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {events.length === 0 && <p className="text-center text-slate-400 py-8">No events match your filters.</p>}
      </CardContent></Card>
    </div>
  );
}

const SmallStat = ({ label, value, icon: Icon, small }) => (
  <Card><CardContent className="p-4 flex justify-between items-center">
    <div>
      <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`font-bold mt-1 ${small ? 'text-sm' : 'text-2xl'}`}>{value}</p>
    </div>
    <Icon size={28} className="opacity-30 text-slate-500" />
  </CardContent></Card>
);
