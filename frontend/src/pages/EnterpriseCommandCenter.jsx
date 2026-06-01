import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useNavigate } from 'react-router-dom';
import { v25API } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import {
  Brain, Shield, Activity, TrendingUp, Truck, BookOpen, BarChart3, DollarSign,
  Trash2, Gift, Star, MessageSquare, Users, Building2, AlertTriangle, Sparkles,
  Monitor, Smartphone, Cpu, FileWarning, ShoppingBag, RefreshCw, ChefHat
} from 'lucide-react';

const TILES = [
  // Tier 1
  { path: '/ash-pro', label: 'Ash Pro · AI GM', icon: Brain, color: 'violet', desc: 'One-click execution of daily plan' },
  { path: '/profit-guardian', label: 'Profit Guardian', icon: Shield, color: 'emerald', desc: 'Nightly margin alerts' },
  { path: '/digital-twin', label: 'Digital Twin', icon: Activity, color: 'cyan', desc: 'Today\'s revenue + wait forecast' },
  { path: '/shift-manager', label: 'AI Shift Manager', icon: TrendingUp, color: 'orange', desc: 'Real-time intervention alerts' },
  { path: '/auto-marketing', label: 'Auto Marketing', icon: Sparkles, color: 'pink', desc: 'AI-drafted campaigns' },
  // Tier 2
  { path: '/dynamic-pricing-rules', label: 'Dynamic Pricing', icon: TrendingUp, color: 'amber', desc: 'Time/day price rules' },
  { path: '/subscriptions', label: 'Subscriptions', icon: Star, color: 'yellow', desc: 'Recurring memberships' },
  { path: '/gift-cards', label: 'Smart Gift Cards', icon: Gift, color: 'rose', desc: 'Issue + redeem' },
  // Tier 3
  { path: '/recipe-costing', label: 'Recipe Costing', icon: ChefHat, color: 'red', desc: 'Ingredient-level margins' },
  { path: '/predictive-orders', label: 'Predictive Ordering', icon: Truck, color: 'indigo', desc: 'AI weekly POs' },
  { path: '/waste-tracking', label: 'Waste Tracking', icon: Trash2, color: 'slate', desc: 'Spoilage + leakage' },
  // Tier 4
  { path: '/concierge', label: 'AI Concierge', icon: MessageSquare, color: 'purple', desc: 'Auto reservations from text' },
  { path: '/reputation', label: 'Reputation Center', icon: Star, color: 'yellow', desc: 'Reviews · AI responses' },
  // Tier 5
  { path: '/franchise', label: 'Franchise Command', icon: Building2, color: 'blue', desc: 'Multi-site + benchmarking' },
  { path: '/fraud-detection', label: 'AI Fraud Detection', icon: FileWarning, color: 'red', desc: 'Staff risk scoring' },
  { path: '/exceptions', label: 'Loss Control', icon: AlertTriangle, color: 'red', desc: 'Voids · comps · refunds' },
  { path: '/hardware-health', label: 'Hardware Health', icon: Cpu, color: 'gray', desc: 'Printer · terminal status' },
  { path: '/disputes', label: 'Chargeback Console', icon: Shield, color: 'orange', desc: 'Evidence packs' },
  { path: '/supplier-marketplace', label: 'Supplier Marketplace', icon: ShoppingBag, color: 'teal', desc: 'Compare quotes · save' },
  { path: '/margin-guardrails', label: 'Margin Guardrails', icon: DollarSign, color: 'emerald', desc: 'Low-GP alerts' },
  { path: '/station-readiness', label: 'Station Readiness', icon: BarChart3, color: 'indigo', desc: 'Combined ops score' },
  { path: '/kiosk', label: 'Self-Service Kiosk', icon: Smartphone, color: 'blue', desc: 'Tableside ordering' },
  { path: '/cfd', label: 'Customer Display', icon: Monitor, color: 'gray', desc: 'Mirror cart to guest screen' },
  { path: '/churn-risk', label: 'Guest Recovery', icon: Users, color: 'orange', desc: 'Win-back at-risk guests' },
];

export default function EnterpriseCommandCenter() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [signals, setSignals] = useState({ readiness: null, twin: null, plan: null });

  useEffect(() => {
    Promise.allSettled([v25API.stationReadiness(), v25API.digitalTwin(), v25API.shiftManager()])
      .then(([s, t, m]) => setSignals({
        readiness: s.status === 'fulfilled' ? s.value.data : null,
        twin: t.status === 'fulfilled' ? t.value.data : null,
        shifts: m.status === 'fulfilled' ? m.value.data : null,
      }));
  }, []);

  return (
    <div className="space-y-6" data-testid="enterprise-center">
      <div>
        <h1 className="text-4xl font-bold tracking-tight" style={{ color: theme.text }}>Enterprise Command Center</h1>
        <p className="text-sm text-gray-500 mt-1">v25 — Every advanced module in one place</p>
      </div>

      {/* Top signal strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="signal-strip">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-widest text-gray-500">Station Readiness</p>
              {signals.readiness && <Badge className={
                signals.readiness.score >= 80 ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100' :
                signals.readiness.score >= 50 ? 'bg-amber-100 text-amber-700 hover:bg-amber-100' :
                'bg-red-100 text-red-700 hover:bg-red-100'
              }>{signals.readiness.status}</Badge>}
            </div>
            <p className="text-3xl font-bold mt-1">{signals.readiness?.score ?? '—'}<span className="text-base text-gray-400">/100</span></p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-widest text-gray-500">Expected Revenue Today</p>
            <p className="text-3xl font-bold mt-1">${signals.twin?.expectedRevenue?.toLocaleString() ?? '—'}</p>
            <p className="text-xs text-gray-400">±8% · {signals.twin?.expectedCovers || 0} covers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-widest text-gray-500">Live Alerts</p>
            <p className="text-3xl font-bold mt-1">{signals.shifts?.alerts?.length ?? 0}</p>
            <p className="text-xs text-gray-400">{signals.shifts?.alerts?.[0]?.message?.slice(0, 50) || 'All clear'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Module tile grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3" data-testid="modules-grid">
        {TILES.map(t => {
          const Icon = t.icon;
          return (
            <button
              key={t.path}
              onClick={() => navigate(t.path)}
              className="text-left p-4 rounded-xl bg-white border hover:shadow-md hover:-translate-y-0.5 transition-all"
              data-testid={`tile-${t.path.replace('/', '')}`}
            >
              <div className={`w-10 h-10 rounded-lg mb-2 flex items-center justify-center bg-${t.color}-100 text-${t.color}-700`} style={{ background: `${theme.primary}12`, color: theme.primary }}>
                <Icon size={18} />
              </div>
              <p className="font-semibold text-sm leading-tight">{t.label}</p>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{t.desc}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
