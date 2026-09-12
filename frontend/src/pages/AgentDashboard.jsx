import React, { useState, useEffect } from 'react';
import { Bot, Zap, AlertCircle, CheckCircle2, Clock, RefreshCw, Users, Gift, Package, TrendingUp, Megaphone } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { agentAPI } from '../services/api';
import { toast } from 'sonner';

const ICONS = {
  at_risk_flagged: AlertCircle,
  birthday_vouchers: Gift,
  low_stock_alert: Package,
  inventory_anomaly: TrendingUp,
  blast_suggested: Megaphone,
};
const COLORS = {
  at_risk_flagged: 'text-amber-600 bg-amber-50',
  birthday_vouchers: 'text-pink-600 bg-pink-50',
  low_stock_alert: 'text-red-600 bg-red-50',
  inventory_anomaly: 'text-orange-600 bg-orange-50',
  blast_suggested: 'text-blue-600 bg-blue-50',
};

export default function AgentDashboard() {
  const { theme } = useTheme();
  const [decisions, setDecisions] = useState([]);
  const [segments, setSegments] = useState({});
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    const [decisionsRes, segmentsRes] = await Promise.allSettled([
      agentAPI.getDecisions(),
      agentAPI.getSegments(),
    ]);
    if (decisionsRes.status === 'fulfilled') setDecisions(decisionsRes.value.data || []);
    if (segmentsRes.status === 'fulfilled') setSegments(segmentsRes.value.data?.segments || {});
  };
  useEffect(() => { refresh(); }, []);

  const runTick = async () => {
    setLoading(true);
    try {
      const r = await agentAPI.tick();
      toast.success(`NUA made ${r.data?.decisionsCount || 0} new decisions`);
      refresh();
    } catch { toast.error('Agent tick failed'); }
    setLoading(false);
  };

  return (
    <div className="space-y-6" data-testid="agent-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Bot size={22} /> NUA — Autonomous AI Agent
          </h1>
          <p className="text-sm text-gray-500">Observes your business, decides what needs attention, takes action. Voice commands work everywhere via the mic.</p>
        </div>
        <Button onClick={runTick} disabled={loading} style={{ backgroundColor: theme.primary }} data-testid="agent-tick-btn">
          {loading ? <RefreshCw size={14} className="mr-1 animate-spin" /> : <Zap size={14} className="mr-1" />} Run Cycle
        </Button>
      </div>

      {/* Customer segments */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="agent-segments">
        {[
          { key: 'vip', label: 'VIP', icon: Gift, color: theme.primary },
          { key: 'regular', label: 'Regulars', icon: Users, color: '#10b981' },
          { key: 'at_risk', label: 'At-Risk', icon: AlertCircle, color: '#f59e0b' },
          { key: 'first_timer', label: 'First-Timers', icon: Users, color: '#6366f1' },
        ].map(s => {
          const Icon = s.icon;
          return (
            <Card key={s.key} data-testid={`seg-${s.key}`}>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}15`, color: s.color }}><Icon size={18} /></div>
                <div><p className="text-xs uppercase text-gray-500">{s.label}</p><p className="text-2xl font-bold">{segments[s.key] || 0}</p></div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent decisions */}
      <Card>
        <CardContent className="p-0">
          <div className="p-4 border-b"><h2 className="font-bold text-sm uppercase tracking-wider text-gray-500">Recent Decisions</h2></div>
          <div className="divide-y">
            {decisions.map(d => {
              const Icon = ICONS[d.actionType] || Bot;
              return (
                <div key={d.id} className="p-4 flex items-start gap-3" data-testid={`decision-${d.id}`}>
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${COLORS[d.actionType] || 'bg-gray-100 text-gray-600'}`}>
                    <Icon size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-medium text-sm">{d.summary}</p>
                      <Badge variant="outline" className="text-[9px]">{d.actionType.replace(/_/g, ' ')}</Badge>
                      {/* Agent tier colours per NUA_POS_DESIGN_TOKENS.md §6 (NUA Agent). */}
                      {d.status === 'suggested' && <Badge className="bg-[rgba(245,140,20,0.14)] text-[#8a4a00] text-[9px]">Suggested</Badge>}
                      {d.status === 'executed' && <Badge className="bg-[rgba(16,185,129,0.12)] text-[#046C4E] text-[9px]"><CheckCircle2 size={9} className="mr-0.5" /> Executed</Badge>}
                    </div>
                    <p className="text-[10px] text-gray-400 flex items-center gap-1"><Clock size={10} /> {new Date(d.createdAt).toLocaleString()}</p>
                  </div>
                </div>
              );
            })}
            {decisions.length === 0 && (
              <div className="py-16 text-center text-gray-400">
                <Bot size={40} className="mx-auto mb-3 opacity-30" />
                <p>NUA hasn't run yet. Click "Run Cycle" to start.</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
