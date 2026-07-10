import React, { useEffect, useState, useCallback, useMemo } from 'react';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { toast } from 'sonner';
import { ShieldCheck, RefreshCw, Search, Lock, Zap, Eye } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const H = () => ({ Authorization: `Bearer ${localStorage.getItem('nuva_token')}` });

const RISK_BG = { low: 'bg-emerald-500', medium: 'bg-amber-500', high: 'bg-rose-500', critical: 'bg-rose-700' };
const RISK_ORDER = { low: 0, medium: 1, high: 2, critical: 3 };

const PERMISSION_DESCRIPTION = {
  auto: 'NUA runs this tool immediately without asking.',
  approval: 'NUA queues this tool in /approvals for you to confirm.',
  disabled: 'NUA cannot use this tool at all.',
};

const PERMISSION_ICON = { auto: Zap, approval: Eye, disabled: Lock };
const PERMISSION_TONE = {
  auto: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  approval: 'text-amber-600 bg-amber-50 border-amber-200',
  disabled: 'text-rose-600 bg-rose-50 border-rose-200',
};

export default function AshPermissions() {
  const [tools, setTools] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState('');
  const [moduleFilter, setModuleFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const r = await axios.get(`${API}/ash/tools`, { headers: H() });
      setTools(r.data);
    } catch { toast.error('Failed to load tools'); }
    finally { setRefreshing(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setPermission = async (toolName, permission) => {
    try {
      await axios.put(`${API}/ash/tools/${toolName}/permission`, { permission }, { headers: H() });
      setTools(ts => ts.map(t => t.name === toolName ? { ...t, effectivePermission: permission } : t));
      toast.success(`${toolName} \u2192 ${permission}`);
    } catch { toast.error('Failed'); }
  };

  const modules = useMemo(() => Array.from(new Set(tools.map(t => t.module))).sort(), [tools]);

  const filtered = tools.filter(t =>
    (moduleFilter === 'all' || t.module === moduleFilter) &&
    (riskFilter === 'all' || t.risk === riskFilter) &&
    (query.trim() === '' || t.name.toLowerCase().includes(query.toLowerCase()) || t.label.toLowerCase().includes(query.toLowerCase()))
  );

  const grouped = useMemo(() => {
    const map = {};
    filtered.forEach(t => {
      map[t.module] = map[t.module] || [];
      map[t.module].push(t);
    });
    Object.values(map).forEach(arr => arr.sort((a, b) => (RISK_ORDER[b.risk] || 0) - (RISK_ORDER[a.risk] || 0)));
    return map;
  }, [filtered]);

  const batchSet = async (moduleName, permission) => {
    const targets = tools.filter(t => t.module === moduleName);
    if (!targets.length) return;
    if (!window.confirm(`Set all ${targets.length} ${moduleName} tools to "${permission}"?`)) return;
    for (const t of targets) {
      try {
        await axios.put(`${API}/ash/tools/${t.name}/permission`, { permission }, { headers: H() });
      } catch { /* skip */ }
    }
    toast.success(`${moduleName} \u2192 ${permission}`);
    load();
  };

  const stats = useMemo(() => {
    const s = { auto: 0, approval: 0, disabled: 0 };
    tools.forEach(t => { s[t.effectivePermission] = (s[t.effectivePermission] || 0) + 1; });
    return s;
  }, [tools]);

  return (
    <div className="space-y-6" data-testid="ash-permissions-page">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <ShieldCheck className="text-indigo-600" /> NUA Permissions
          </h1>
          <p className="text-sm text-slate-500 mt-1">Owner controls for every capability NUA can invoke. Approval gates route to the Approval Queue.</p>
        </div>
        <Button variant="outline" onClick={load} disabled={refreshing} data-testid="perms-refresh-btn">
          <RefreshCw size={14} className={`mr-1.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {/* Stat summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {['auto', 'approval', 'disabled'].map(k => {
          const Icon = PERMISSION_ICON[k];
          return (
            <Card key={k} className={`border ${PERMISSION_TONE[k]}`} data-testid={`stat-${k}`}>
              <CardContent className="p-5 flex items-center gap-4">
                <div className={`h-10 w-10 rounded-full flex items-center justify-center ${PERMISSION_TONE[k]}`}>
                  <Icon size={20} />
                </div>
                <div>
                  <p className="text-3xl font-bold">{stats[k] || 0}</p>
                  <p className="text-xs uppercase tracking-wider text-slate-500">{k}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{PERMISSION_DESCRIPTION[k]}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4 flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Search tools\u2026" value={query} onChange={e => setQuery(e.target.value)}
              className="pl-9" data-testid="perms-search" />
          </div>
          <Select value={moduleFilter} onValueChange={setModuleFilter}>
            <SelectTrigger className="w-40" data-testid="module-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All modules</SelectItem>
              {modules.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={riskFilter} onValueChange={setRiskFilter}>
            <SelectTrigger className="w-32" data-testid="risk-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All risks</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Tool tables grouped by module */}
      {Object.entries(grouped).map(([modName, mods]) => (
        <Card key={modName} data-testid={`module-card-${modName}`}>
          <CardContent className="p-0">
            <div className="flex justify-between items-center p-4 border-b">
              <div>
                <h3 className="font-semibold">{modName}</h3>
                <p className="text-xs text-slate-500">{mods.length} tools</p>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" onClick={() => batchSet(modName, 'auto')} data-testid={`batch-auto-${modName}`}>All auto</Button>
                <Button size="sm" variant="outline" onClick={() => batchSet(modName, 'approval')} data-testid={`batch-approval-${modName}`}>All approval</Button>
                <Button size="sm" variant="outline" onClick={() => batchSet(modName, 'disabled')} data-testid={`batch-disabled-${modName}`}>All disabled</Button>
              </div>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr className="text-xs text-slate-500 uppercase tracking-wider">
                  <th className="p-2 pl-4 text-left">Capability</th>
                  <th className="p-2 text-left">Risk</th>
                  <th className="p-2 text-left">Impact</th>
                  <th className="p-2 text-left">Default</th>
                  <th className="p-2 pr-4 text-left">Owner override</th>
                </tr>
              </thead>
              <tbody>
                {mods.map(t => (
                  <tr key={t.name} className="border-t hover:bg-slate-50" data-testid={`perm-row-${t.name}`}>
                    <td className="p-2 pl-4">
                      <p className="font-medium text-sm">{t.label}</p>
                      <p className="font-mono text-[10px] text-slate-500">{t.name}</p>
                    </td>
                    <td className="p-2"><Badge className={RISK_BG[t.risk] || 'bg-slate-500'}>{t.risk}</Badge></td>
                    <td className="p-2 text-xs text-slate-500">{t.expectedImpact}</td>
                    <td className="p-2 text-xs text-slate-500">{t.defaultPermission}</td>
                    <td className="p-2 pr-4">
                      <Select value={t.effectivePermission} onValueChange={v => setPermission(t.name, v)}>
                        <SelectTrigger className="w-32" data-testid={`perm-${t.name}`}><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">Auto</SelectItem>
                          <SelectItem value="approval">Approval</SelectItem>
                          <SelectItem value="disabled">Disabled</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ))}
      {filtered.length === 0 && (
        <Card><CardContent className="p-12 text-center text-sm text-slate-500">
          No tools match those filters.
        </CardContent></Card>
      )}
    </div>
  );
}
