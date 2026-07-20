import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { analyticsAPI } from '../services/api';
import {
  AlertTriangle, AlertOctagon, Info, RefreshCw, ShoppingCart, ChefHat,
  Utensils, CalendarClock, Users2, TrendingUp, CheckCircle2, ArrowRight,
} from 'lucide-react';

const SEVERITY_STYLE = {
  critical: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', Icon: AlertOctagon },
  warning: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', Icon: AlertTriangle },
  info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', Icon: Info },
};

// Role-aware quick actions: managers on the floor get service screens first,
// owners get the money screens.
const QUICK_ACTIONS = {
  owner: [
    { label: 'Finance', path: '/finance', Icon: TrendingUp },
    { label: 'End of Day', path: '/end-of-day', Icon: CalendarClock },
    { label: 'Roster', path: '/staff-roster', Icon: Users2 },
    { label: 'POS', path: '/pos', Icon: ShoppingCart },
  ],
  manager: [
    { label: 'Floor Plan', path: '/floor-plan', Icon: Utensils },
    { label: 'Roster', path: '/staff-roster', Icon: Users2 },
    { label: 'Kitchen', path: '/kitchen', Icon: ChefHat },
    { label: 'POS', path: '/pos', Icon: ShoppingCart },
  ],
};

const Today = () => {
  const { theme } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [pulse, setPulse] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { const r = await analyticsAPI.getTodayPulse(); setPulse(r.data); }
    catch { setPulse(null); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 60000); // refresh every minute — live pulse, not a report
    return () => clearInterval(id);
  }, []);

  const role = user?.role === 'owner' ? 'owner' : 'manager';
  const actions = QUICK_ACTIONS[role];
  const sales = pulse?.sales || {};
  const labor = pulse?.labor || {};
  const service = pulse?.service || {};
  const alerts = pulse?.alerts || [];
  const laborOver = labor.pct !== null && labor.pct !== undefined && labor.pct > (labor.threshold || 32);

  return (
    <div className="space-y-5" data-testid="today-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Today</h1>
          <p className="text-sm text-gray-500">
            {new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}
            {user?.name ? ` · ${user.name}` : ''}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} data-testid="today-refresh">
          <RefreshCw size={14} className={`mr-1.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {/* The four numbers that matter */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card data-testid="today-sales">
          <CardContent className="p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Sales today</p>
            <p className="text-2xl font-bold mt-1" style={{ color: theme.primary }}>
              ${(sales.today || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
            {sales.target > 0 ? (
              <div className="mt-2">
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all"
                    style={{ width: `${Math.min(sales.pctOfTarget || 0, 100)}%`,
                             background: (sales.pctOfTarget || 0) >= 100 ? '#059669' : theme.primary }} />
                </div>
                <p className="text-[11px] text-gray-500 mt-1">{sales.pctOfTarget || 0}% of ${sales.target.toLocaleString()} target</p>
              </div>
            ) : (
              <p className="text-[11px] text-gray-400 mt-2">{sales.txnCount || 0} sales · set a daily target in Settings</p>
            )}
          </CardContent>
        </Card>

        <Card data-testid="today-labor">
          <CardContent className="p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Labor</p>
            <p className={`text-2xl font-bold mt-1 ${laborOver ? 'text-red-600' : 'text-gray-800'}`}>
              {labor.pct !== null && labor.pct !== undefined ? `${labor.pct}%` : '—'}
            </p>
            <p className="text-[11px] text-gray-500 mt-2">
              ${(labor.costToday || 0).toFixed(0)} rostered · {labor.shiftsToday || 0} shifts
              {laborOver ? ` · over ${labor.threshold}% line` : ''}
            </p>
          </CardContent>
        </Card>

        <Card data-testid="today-avg-ticket">
          <CardContent className="p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Avg ticket</p>
            <p className="text-2xl font-bold mt-1 text-gray-800">${(sales.avgTicket || 0).toFixed(2)}</p>
            <p className="text-[11px] text-gray-500 mt-2">{sales.txnCount || 0} transactions</p>
          </CardContent>
        </Card>

        <Card data-testid="today-service">
          <CardContent className="p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Tonight</p>
            <p className="text-2xl font-bold mt-1 text-gray-800">{service.bookingsTonight || 0} bookings</p>
            <p className="text-[11px] text-gray-500 mt-2">{service.openKitchenTickets || 0} open kitchen tickets</p>
          </CardContent>
        </Card>
      </div>

      {/* Exceptions — problems tap you on the shoulder */}
      <Card data-testid="today-alerts">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-sm" style={{ color: theme.text }}>Needs attention</h2>
            {alerts.length > 0 && (
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700">{alerts.length}</span>
            )}
          </div>
          {loading && !pulse ? (
            <p className="text-sm text-gray-400 py-4 text-center">Checking…</p>
          ) : alerts.length === 0 ? (
            <div className="flex items-center gap-2 py-4 justify-center text-emerald-700">
              <CheckCircle2 size={18} />
              <p className="text-sm font-medium">All clear — nothing needs your attention right now.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.map((a, i) => {
                const st = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.info;
                const AlertIcon = st.Icon;
                return (
                  <button key={i} onClick={() => a.link && navigate(a.link)}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-all hover:shadow-sm ${st.bg} ${st.border}`}
                    data-testid={`today-alert-${a.kind}`}>
                    <AlertIcon size={18} className={st.text} />
                    <span className={`flex-1 text-sm font-medium ${st.text}`}>{a.message}</span>
                    <ArrowRight size={14} className={st.text} />
                  </button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Role-aware quick actions */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {actions.map(({ label, path, Icon }) => (
          <button key={path} onClick={() => navigate(path)}
            className="flex items-center gap-3 p-4 bg-white rounded-xl border hover:shadow-md transition-all"
            data-testid={`today-quick-${path.replace('/', '')}`}>
            <span className="w-9 h-9 rounded-lg flex items-center justify-center"
              style={{ background: `${theme.primary}15`, color: theme.primary }}>
              <Icon size={18} />
            </span>
            <span className="font-semibold text-sm text-gray-800">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default Today;
