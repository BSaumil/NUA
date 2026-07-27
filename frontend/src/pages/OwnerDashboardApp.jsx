import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RefreshCw, Sparkles, AlertTriangle, AlertOctagon, Info, CheckCircle2,
  TrendingUp, CalendarClock, Users2, ShoppingCart, ArrowRight, Activity,
  Moon, Sun, LogOut as SignOutIcon, Brain, ClipboardCheck,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { analyticsAPI, nuaAPI } from '../services/api';
import { toast } from 'sonner';
import useLiveFeed from '../hooks/useLiveFeed';

const SEVERITY_STYLE = {
  critical: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', Icon: AlertOctagon },
  warning: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', Icon: AlertTriangle },
  info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', Icon: Info },
};

const TIER_COLOR = {
  excellent: 'bg-emerald-100 text-emerald-700', healthy: 'bg-green-100 text-green-700',
  watch: 'bg-amber-100 text-amber-700', at_risk: 'bg-orange-100 text-orange-700', critical: 'bg-red-100 text-red-700',
};

// Every drill-down report already lives in the main app — the Dashboard app's
// job is to surface it, not rebuild it. Point #9: reporting from every part
// of NUA POS starts here.
const QUICK_LINKS = [
  { label: 'Finance', path: '/finance', Icon: TrendingUp },
  { label: 'End of Day', path: '/end-of-day', Icon: CalendarClock },
  { label: 'Command Center', path: '/command-center', Icon: Activity },
  { label: 'Roster', path: '/staff-roster', Icon: Users2 },
  { label: 'Approvals', path: '/approvals', Icon: ClipboardCheck },
  { label: 'POS', path: '/pos', Icon: ShoppingCart },
];

export default function OwnerDashboardApp() {
  const { theme, darkMode, toggleDarkMode } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [pulse, setPulse] = useState(null);
  const [briefing, setBriefing] = useState(null);
  const [insights, setInsights] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => { document.title = 'NUA Pulse'; }, []);

  const load = useCallback(async () => {
    try {
      const [p, b, i, h] = await Promise.allSettled([
        analyticsAPI.getTodayPulse(), nuaAPI.getBriefing(),
        nuaAPI.getInsights(6), nuaAPI.getHealthScore(),
      ]);
      if (p.status === 'fulfilled') setPulse(p.value.data);
      if (b.status === 'fulfilled') setBriefing(b.value.data);
      if (i.status === 'fulfilled') setInsights(i.value.data);
      if (h.status === 'fulfilled') setHealth(h.value.data);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60000); // fallback poll — never depend on the socket alone
    return () => clearInterval(id);
  }, [load]);

  // Live sync: a completed sale or roster change refreshes the pulse tiles
  // right away instead of waiting up to 60s for the next poll.
  const { connected: liveConnected } = useLiveFeed(useCallback((event) => {
    if (event.type === 'sale.completed' || event.type === 'roster.updated') load();
  }, [load]));

  const handleRegenerateBriefing = async () => {
    setRegenerating(true);
    try { const r = await nuaAPI.regenerateBriefing(); setBriefing(r.data); toast.success('Briefing refreshed'); }
    catch { toast.error('Failed to regenerate'); }
    finally { setRegenerating(false); }
  };

  const sales = pulse?.sales || {};
  const labor = pulse?.labor || {};
  const service = pulse?.service || {};
  const alerts = pulse?.alerts || [];
  const laborOver = labor.pct != null && labor.pct > (labor.threshold || 32);

  return (
    <div className="min-h-screen pb-10" style={{ background: darkMode ? '#0b0b0f' : '#f6f7fb' }} data-testid="owner-dashboard-app-page">
      <div className="sticky top-0 z-10 backdrop-blur border-b px-4 py-3 flex items-center justify-between"
        style={{ background: darkMode ? 'rgba(11,11,15,0.85)' : 'rgba(255,255,255,0.85)', borderColor: darkMode ? '#1f1f28' : '#e5e7eb' }}>
        <div className="flex items-center gap-2">
          <span className="font-bold" style={{ color: theme.primary }}>NUA</span>
          <span className="text-sm text-gray-400">Pulse</span>
        </div>
        <div className="flex items-center gap-3">
          {liveConnected && (
            <span className="flex items-center gap-1 text-[11px] text-emerald-600" title="Live sync connected" data-testid="owner-dashboard-live-indicator">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live
            </span>
          )}
          {health && <Badge className={TIER_COLOR[health.tier] || TIER_COLOR.watch} data-testid="owner-dashboard-health">{health.overall} · {health.tier.replace('_', ' ')}</Badge>}
          <button onClick={load} className="text-gray-400 hover:text-gray-600" data-testid="owner-dashboard-refresh"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
          <button onClick={toggleDarkMode} className="text-gray-400 hover:text-gray-600">{darkMode ? <Sun size={18} /> : <Moon size={18} />}</button>
          <button onClick={logout} className="text-gray-400 hover:text-red-500"><SignOutIcon size={18} /></button>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 pt-5 space-y-5">
        <div>
          <h1 className="text-xl font-bold" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, {user?.name?.split(' ')[0]}</h1>
          <p className="text-sm text-gray-400">{new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}</p>
        </div>

        {/* AI briefing — the AI-at-fingertips centerpiece of this app */}
        <Card className="border-0" style={{ background: darkMode ? '#15151d' : 'linear-gradient(135deg,#f5f3ff,#fdf4ff)' }} data-testid="owner-dashboard-briefing">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-violet-600"><Brain size={13} /> NUA Briefing</span>
              <button onClick={handleRegenerateBriefing} disabled={regenerating} className="text-[11px] text-violet-500 hover:text-violet-700" data-testid="owner-dashboard-regenerate-briefing">
                {regenerating ? 'Thinking…' : 'Regenerate'}
              </button>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: darkMode ? '#e5e7eb' : '#3730a3' }}>
              {briefing?.narrative || 'No briefing yet — check back after opening hours, or hit Regenerate.'}
            </p>
          </CardContent>
        </Card>

        {/* The four numbers that matter, reused straight from Today */}
        <div className="grid grid-cols-2 gap-3">
          <Card data-testid="owner-dashboard-sales"><CardContent className="p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Sales today</p>
            <p className="text-xl font-bold mt-1" style={{ color: theme.primary }}>${(sales.today || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
            {sales.target > 0 && <p className="text-[11px] text-gray-400 mt-1">{sales.pctOfTarget || 0}% of ${sales.target.toLocaleString()} target</p>}
          </CardContent></Card>
          <Card data-testid="owner-dashboard-labor"><CardContent className="p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Labor</p>
            <p className={`text-xl font-bold mt-1 ${laborOver ? 'text-red-600' : ''}`} style={!laborOver ? { color: darkMode ? '#eaeaea' : '#111827' } : {}}>{labor.pct != null ? `${labor.pct}%` : '—'}</p>
            <p className="text-[11px] text-gray-400 mt-1">{labor.shiftsToday || 0} shifts rostered</p>
          </CardContent></Card>
          <Card data-testid="owner-dashboard-avg-ticket"><CardContent className="p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Avg ticket</p>
            <p className="text-xl font-bold mt-1" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>${(sales.avgTicket || 0).toFixed(2)}</p>
            <p className="text-[11px] text-gray-400 mt-1">{sales.txnCount || 0} transactions</p>
          </CardContent></Card>
          <Card data-testid="owner-dashboard-service"><CardContent className="p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Tonight</p>
            <p className="text-xl font-bold mt-1" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>{service.bookingsTonight || 0} bookings</p>
            <p className="text-[11px] text-gray-400 mt-1">{service.openKitchenTickets || 0} open tickets</p>
          </CardContent></Card>
        </div>

        {/* Exceptions */}
        <Card data-testid="owner-dashboard-alerts">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-sm" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>Needs attention</h2>
              {alerts.length > 0 && <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700">{alerts.length}</span>}
            </div>
            {alerts.length === 0 ? (
              <div className="flex items-center gap-2 py-3 justify-center text-emerald-700">
                <CheckCircle2 size={16} /><p className="text-sm font-medium">All clear.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {alerts.map((a, i) => {
                  const st = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.info;
                  const AlertIcon = st.Icon;
                  return (
                    <button key={i} onClick={() => a.link && navigate(a.link)}
                      className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left ${st.bg} ${st.border}`} data-testid={`owner-dashboard-alert-${a.kind}`}>
                      <AlertIcon size={16} className={st.text} />
                      <span className={`flex-1 text-sm font-medium ${st.text}`}>{a.message}</span>
                      <ArrowRight size={13} className={st.text} />
                    </button>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI insights, most severe first */}
        {insights.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold flex items-center gap-1.5" style={{ color: darkMode ? '#eaeaea' : '#111827' }}><Sparkles size={14} /> NUA Insights</h2>
              <button onClick={() => navigate('/ash')} className="text-[11px] text-gray-400 hover:text-gray-600">View all →</button>
            </div>
            <div className="space-y-2">
              {insights.map(ins => (
                <Card key={ins.id} data-testid={`owner-dashboard-insight-${ins.id}`}>
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">{ins.title}</p>
                      <Badge variant="outline" className="text-[10px] shrink-0">{ins.severity}</Badge>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">{ins.body}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Quick links into every drill-down report */}
        <div>
          <h2 className="text-sm font-semibold mb-2" style={{ color: darkMode ? '#eaeaea' : '#111827' }}>Reports & Tools</h2>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_LINKS.map(({ label, path, Icon }) => (
              <button key={path} onClick={() => navigate(path)}
                className="flex items-center gap-2.5 p-3 rounded-xl border hover:shadow-sm transition-all"
                style={{ background: darkMode ? '#15151d' : '#fff', borderColor: darkMode ? '#242430' : '#e5e7eb' }}
                data-testid={`owner-dashboard-link-${path.replace('/', '')}`}>
                <span className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${theme.primary}15`, color: theme.primary }}>
                  <Icon size={15} />
                </span>
                <span className="text-sm font-medium" style={{ color: darkMode ? '#eaeaea' : '#374151' }}>{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
