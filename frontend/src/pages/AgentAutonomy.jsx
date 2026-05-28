import React, { useState, useEffect } from 'react';
import { Save, Bot } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useTheme } from '../contexts/ThemeContext';
import { phaseEFAPI } from '../services/api';
import { toast } from 'sonner';

export default function AgentAutonomy() {
  const { theme } = useTheme();
  const [cfg, setCfg] = useState({});

  useEffect(() => { phaseEFAPI.getAutonomy().then(r => setCfg(r.data || {})).catch(() => {}); }, []);

  const save = async () => {
    try { await phaseEFAPI.updateAutonomy(cfg); toast.success('Autonomy config saved'); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };
  const tickExt = async () => {
    try { const r = await phaseEFAPI.tickExtended(); toast.success(`Extended tick: ${(r.data?.decisions || []).length} new decisions`); }
    catch { toast.error('Tick failed'); }
  };

  const toggle = (key) => setCfg(c => ({ ...c, [key]: !c[key] }));

  return (
    <div className="space-y-6" data-testid="autonomy-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Bot size={22} /> Ash Autonomy Controls</h1>
          <p className="text-sm text-gray-500">Owner-only switches for what Ash can do on its own.</p>
        </div>
        <Button variant="outline" onClick={tickExt} data-testid="ext-tick-btn">Run Extended Tick</Button>
      </div>

      <Card>
        <CardContent className="p-6 space-y-4">
          {[
            { key: 'autoPublishRoster', label: 'Auto-publish AI roster', desc: 'Commit AI-generated weekly shifts automatically if total cost is within cap below.' },
            { key: 'autoConfirmSMS', label: 'Auto-confirm reservation SMS', desc: 'Queue confirmation SMS for any new reservation with a phone number.' },
            { key: 'abTestingEnabled', label: 'Live menu A/B testing', desc: 'Allow public menu / table QR to serve A or B variants.' },
          ].map(item => (
            <div key={item.key} className="flex items-center justify-between p-3 border rounded-lg">
              <div><p className="font-medium text-sm">{item.label}</p><p className="text-xs text-gray-500">{item.desc}</p></div>
              <button onClick={() => toggle(item.key)} className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${cfg[item.key] ? 'bg-indigo-600' : 'bg-gray-300'}`} data-testid={`toggle-${item.key}`}>
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${cfg[item.key] ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
            </div>
          ))}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div><label className="text-xs uppercase tracking-wider text-gray-500">Roster auto-publish budget cap ($)</label><Input type="number" value={cfg.autoPublishBudgetCap || ''} onChange={e => setCfg({ ...cfg, autoPublishBudgetCap: parseFloat(e.target.value) || 0 })} data-testid="cap-budget" /></div>
            <div><label className="text-xs uppercase tracking-wider text-gray-500">VIP auto-tag spend threshold ($)</label><Input type="number" value={cfg.autoVipThresholdSpend || ''} onChange={e => setCfg({ ...cfg, autoVipThresholdSpend: parseFloat(e.target.value) || 0 })} data-testid="vip-spend" /></div>
            <div><label className="text-xs uppercase tracking-wider text-gray-500">VIP auto-tag visit threshold</label><Input type="number" value={cfg.autoVipThresholdVisits || ''} onChange={e => setCfg({ ...cfg, autoVipThresholdVisits: parseInt(e.target.value) || 0 })} data-testid="vip-visits" /></div>
            <div><label className="text-xs uppercase tracking-wider text-gray-500">Auto-reorder stock threshold</label><Input type="number" value={cfg.autoReorderThreshold || ''} onChange={e => setCfg({ ...cfg, autoReorderThreshold: parseInt(e.target.value) || 0 })} data-testid="reorder-thresh" /></div>
          </div>
        </CardContent>
      </Card>

      <Button className="w-full sm:w-auto" style={{ backgroundColor: theme.primary }} onClick={save} data-testid="save-autonomy"><Save size={16} className="mr-2" /> Save Autonomy Config</Button>
    </div>
  );
}
