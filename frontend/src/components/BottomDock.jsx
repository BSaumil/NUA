import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { v15API } from '../services/api';
import {
  LayoutDashboard, ShoppingCart, Package, Users, Warehouse, Calculator,
  Settings, Utensils, ChefHat, BarChart3, Zap, Award, TrendingUp,
  FlaskConical, Sunrise, Brain, Plug, Users2, LogOut, Mail, ClipboardList,
  Trophy, Printer, PieChart, MoreHorizontal, X, FileText, DollarSign, Tag,
  Link2, Ban, Receipt, Calendar, MapPin, Clock, Sparkles, BookOpen, Shield,
  ShieldAlert, AlertTriangle, Flame, ArrowLeftRight
} from 'lucide-react';

// Role-default quick actions (left → right) on the bottom dock.
// 4 most-common items per role, then "More" splash button.
const QUICK_ACTIONS = {
  owner: [
    { path: '/pos', label: 'POS', icon: ShoppingCart },
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/reservations', label: 'Bookings', icon: Utensils },
    { path: '/products', label: 'Items', icon: Package },
  ],
  manager: [
    { path: '/pos', label: 'POS', icon: ShoppingCart },
    { path: '/reservations', label: 'Bookings', icon: Utensils },
    { path: '/kitchen', label: 'Kitchen', icon: ChefHat },
    { path: '/staff-roster', label: 'Roster', icon: ClipboardList },
  ],
  cashier: [
    { path: '/pos', label: 'POS', icon: ShoppingCart },
    { path: '/reservations', label: 'Bookings', icon: Utensils },
    { path: '/customers', label: 'Customers', icon: Users },
    { path: '/loyalty', label: 'Loyalty', icon: Award },
  ],
  kitchen: [
    { path: '/kitchen', label: 'Kitchen', icon: ChefHat },
    { path: '/pre-shift', label: 'Pre-Shift', icon: Sunrise },
    { path: '/inventory', label: 'Inventory', icon: Warehouse },
    { path: '/ai-pantry', label: 'AI Pantry', icon: Brain },
  ],
  barista: [
    { path: '/pos', label: 'POS', icon: ShoppingCart },
    { path: '/kitchen', label: 'Drinks', icon: ChefHat },
    { path: '/customers', label: 'Customers', icon: Users },
    { path: '/loyalty', label: 'Loyalty', icon: Award },
  ],
};

// Full feature catalog for the "More" splash modal — grouped by role access
const ALL_FEATURES = [
  { group: 'Operations', items: [
    { path: '/pos', label: 'POS Terminal', icon: ShoppingCart, access: ['owner', 'manager', 'cashier', 'barista'] },
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, access: ['owner', 'manager'] },
    { path: '/pre-shift', label: 'Pre-Shift', icon: Sunrise, access: ['owner', 'manager', 'kitchen'] },
    { path: '/command-center', label: 'Command Center', icon: Brain, access: ['owner', 'manager'] },
    { path: '/kitchen', label: 'Kitchen Display', icon: ChefHat, access: ['owner', 'manager', 'kitchen'] },
  ]},
  { group: 'Reservations', items: [
    { path: '/reservations', label: 'Bookings', icon: Utensils, access: ['owner', 'manager', 'cashier'] },
    { path: '/floor-plan', label: 'Floor Plan', icon: MapPin, access: ['owner', 'manager', 'cashier'] },
    { path: '/waitlist', label: 'Waitlist', icon: Clock, access: ['owner', 'manager', 'cashier'] },
    { path: '/table-layout', label: 'Table Layout', icon: MapPin, access: ['owner', 'manager'] },
    { path: '/booking-settings', label: 'Settings & Rules', icon: Settings, access: ['owner', 'manager'] },
    { path: '/booking-experience', label: 'Experience', icon: Sparkles, access: ['owner', 'manager'] },
    { path: '/clubmember', label: 'Clubmember', icon: Award, access: ['owner', 'manager'] },
    { path: '/booking-analytics', label: 'Analytics', icon: BarChart3, access: ['owner', 'manager'] },
  ]},
  { group: 'Items', items: [
    { path: '/products', label: 'Item Library', icon: Package, access: ['owner', 'manager', 'cashier'] },
    { path: '/categories', label: 'Categories', icon: Tag, access: ['owner', 'manager'] },
    { path: '/modifiers', label: 'Modifiers', icon: ClipboardList, access: ['owner', 'manager'] },
    { path: '/discounts', label: 'Discounts & Offers', icon: DollarSign, access: ['owner', 'manager'] },
    { path: '/comp-void', label: 'Comp / Void', icon: Ban, access: ['owner', 'manager'] },
    { path: '/payment-links', label: 'Payment Links', icon: Link2, access: ['owner', 'manager'] },
  ]},
  { group: 'Menu Engineering', items: [
    { path: '/menu-engineering', label: 'Menu Matrix', icon: FlaskConical, access: ['owner', 'manager'] },
    { path: '/what-if', label: 'What-If', icon: TrendingUp, access: ['owner', 'manager'] },
    { path: '/inventory', label: 'Inventory', icon: Warehouse, access: ['owner', 'manager', 'kitchen'] },
    { path: '/ai-pantry', label: 'AI Pantry', icon: Brain, access: ['owner', 'manager', 'kitchen'] },
    { path: '/forecasting', label: 'Forecasting', icon: BarChart3, access: ['owner', 'manager'] },
    { path: '/quarterly-review', label: 'Quarterly Review', icon: PieChart, access: ['owner', 'manager'] },
  ]},
  { group: 'Team', items: [
    { path: '/staff', label: 'Staff', icon: Users2, access: ['owner', 'manager'] },
    { path: '/staff-roster', label: 'Roster & Payrun', icon: ClipboardList, access: ['owner', 'manager'] },
    { path: '/leaderboard', label: 'Leaderboard', icon: Trophy, access: ['owner', 'manager', 'cashier', 'kitchen'] },
    { path: '/tip-management', label: 'Tip Management', icon: DollarSign, access: ['owner', 'manager'] },
  ]},
  { group: 'Customers', items: [
    { path: '/customers', label: 'Customer List', icon: Users, access: ['owner', 'manager', 'cashier'] },
    { path: '/loyalty', label: 'Loyalty & Events', icon: Award, access: ['owner', 'manager', 'cashier'] },
    { path: '/email-marketing', label: 'Email Marketing', icon: Mail, access: ['owner', 'manager'] },
  ]},
  { group: 'Accounting', items: [
    { path: '/accounting', label: 'Transactions', icon: Receipt, access: ['owner'] },
    { path: '/bas-gst', label: 'BAS/GST', icon: FileText, access: ['owner'] },
    { path: '/end-of-day', label: 'End of Day', icon: Calendar, access: ['owner'] },
    { path: '/integrations', label: 'Integrations', icon: Plug, access: ['owner'] },
  ]},
  { group: 'System', items: [
    { path: '/automation', label: 'Automation', icon: Zap, access: ['owner', 'manager'] },
    { path: '/settings', label: 'Settings', icon: Settings, access: ['owner', 'manager'] },
  ]},
];

export default function BottomDock() {
  const { theme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showMore, setShowMore] = useState(false);
  const [badges, setBadges] = useState({});

  useEffect(() => {
    if (!user) return;
    const tick = async () => { try { const r = await v15API.getBadges(); setBadges(r.data || {}); } catch {} };
    tick();
    const id = setInterval(tick, 30000); // poll every 30s
    return () => clearInterval(id);
  }, [user]);

  if (!user) return null;
  const role = user.role || 'cashier';
  const customPerms = (user?.customPermissions?.length > 0) ? user.customPermissions : (user?.permissions || []);
  const hasCustomPerms = Array.isArray(customPerms) && customPerms.length > 0 && !customPerms.includes('*');

  const isAllowed = (item) => {
    if (role === 'owner') return true;
    if (hasCustomPerms) {
      const key = item.path.replace('/', '') || 'dashboard';
      return customPerms.includes(key);
    }
    return item.access?.includes(role);
  };

  // Quick actions are role-based defaults — no permission filtering (use splash for granular access)
  const quick = (QUICK_ACTIONS[role] || QUICK_ACTIONS.cashier).slice(0, 4);

  const handleLogout = async () => { setShowMore(false); await logout(); navigate('/'); };

  return (
    <>
      {/* BOTTOM DOCK */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-gray-200 shadow-[0_-4px_20px_rgba(0,0,0,0.06)]" data-testid="bottom-dock">
        <div className="max-w-screen-2xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-1 text-sm">
            <span className="font-bold tracking-wider px-2" style={{ color: theme.primary }}>NUA</span>
            <span className="text-[10px] text-gray-400 mr-2 hidden sm:inline">{user.name} · {role}</span>
          </div>
          <div className="flex items-center gap-1 flex-1 justify-center max-w-xl">
            {quick.map(q => {
              const Icon = q.icon;
              const isActive = location.pathname === q.path;
              const badgeKey = q.path === '/reservations' ? 'reservations' :
                                q.path === '/kitchen' ? 'kitchen' :
                                q.path === '/pos' ? 'pos' :
                                q.path === '/waitlist' ? 'waitlist' : null;
              const count = badgeKey ? badges[badgeKey] : 0;
              return (
                <button
                  key={q.path}
                  onClick={() => navigate(q.path)}
                  className={`relative flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl transition-all min-w-[64px] ${isActive ? 'text-white' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'}`}
                  style={isActive ? { backgroundColor: theme.primary } : {}}
                  data-testid={`dock-${q.path.replace('/', '')}`}
                >
                  <div className="relative">
                    <Icon size={18} />
                    {count > 0 && (
                      <span className="absolute -top-2 -right-2 min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center" data-testid={`badge-${q.path.replace('/', '')}`}>
                        {count > 99 ? '99+' : count}
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] font-medium">{q.label}</span>
                </button>
              );
            })}
            <button
              onClick={() => setShowMore(true)}
              className="flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-all min-w-[64px]"
              data-testid="dock-more"
            >
              <MoreHorizontal size={18} />
              <span className="text-[10px] font-medium">More</span>
            </button>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 px-3 py-2 rounded-xl text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all"
            data-testid="dock-logout"
          >
            <LogOut size={16} />
            <span className="text-xs hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </div>

      {/* MORE SPLASH — full-screen modal */}
      {showMore && (
        <div className="fixed inset-0 z-50 bg-gray-900/40 backdrop-blur-sm flex items-end sm:items-center justify-center animate-in fade-in duration-200" data-testid="more-splash" onClick={() => setShowMore(false)}>
          <div className="bg-white w-full sm:w-[90vw] sm:max-w-5xl max-h-[85vh] sm:max-h-[80vh] overflow-y-auto rounded-t-3xl sm:rounded-2xl shadow-2xl animate-in slide-in-from-bottom duration-300" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
              <div>
                <h2 className="text-xl font-bold" style={{ color: theme.text }}>All Features</h2>
                <p className="text-xs text-gray-500">Tap any tile to navigate · Showing what {user.name} can access</p>
              </div>
              <button onClick={() => setShowMore(false)} className="p-2 hover:bg-gray-100 rounded-lg" data-testid="close-more-btn"><X size={20} /></button>
            </div>
            <div className="px-6 py-5 space-y-6">
              {ALL_FEATURES.map(group => {
                const visible = group.items.filter(isAllowed);
                if (visible.length === 0) return null;
                return (
                  <div key={group.group}>
                    <h3 className="text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-2.5">{group.group}</h3>
                    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
                      {visible.map(item => {
                        const Icon = item.icon;
                        return (
                          <button
                            key={item.path}
                            onClick={() => { setShowMore(false); navigate(item.path); }}
                            className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border bg-white hover:shadow-md hover:-translate-y-0.5 transition-all"
                            style={{ borderColor: '#f3f4f6' }}
                            data-testid={`splash-${item.path.replace('/', '')}`}
                          >
                            <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${theme.primary}15`, color: theme.primary }}>
                              <Icon size={18} />
                            </div>
                            <span className="text-[11px] text-center text-gray-700 font-medium leading-tight">{item.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
