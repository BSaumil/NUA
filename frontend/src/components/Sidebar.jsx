import React, { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard, ShoppingCart, Package, Users, Warehouse,
  Calculator, FileText, Settings, Utensils, MapPin, Clock,
  ChefHat, BarChart3, Zap, Award, TrendingUp,
  FlaskConical, Sunrise, Brain, Plug, Users2, LogOut, ShieldCheck, Store,
  Mail, ClipboardList, DollarSign, Trophy, Printer, PieChart,
  ChevronDown, ChevronRight, Timer,
  CalendarCheck, LayoutGrid, SlidersHorizontal, Boxes, Layers, Puzzle,
  Percent, XCircle, Grid3x3, Scale, Sparkles, Ticket, Megaphone, Receipt,
  FileBadge, Wallet, PiggyBank, Target, BookMarked, AlertTriangle, Cpu,
  CreditCard, KeyRound, Building2, Rocket
} from 'lucide-react';

// Progressive disclosure: the everyday screens live in a handful of merged
// groups; power/config screens live under three focused groups (rather than
// one 10-item "Advanced" catch-all) so the 95%-of-the-time sidebar stays
// clean. Every child carries its own icon now — with 4-7 items per group,
// text alone made scanning slower than it needed to be. Everything is still
// reachable — nothing was removed, only regrouped and relabeled for clarity
// (e.g. two different screens were both called "Command Center").
const NAV_STRUCTURE = [
  { path: '/today', icon: Sunrise, label: 'Today', access: ['owner', 'manager'] },
  { path: '/whats-new', icon: Rocket, label: "What's New", access: ['owner', 'manager'] },
  { path: '/pos', icon: ShoppingCart, label: 'POS Terminal', access: ['owner', 'manager', 'cashier'] },
  { path: '/kitchen', icon: ChefHat, label: 'Kitchen', access: ['owner', 'manager', 'kitchen'] },
  { path: '/coursing-analytics', icon: Timer, label: 'Coursing', access: ['owner', 'manager'] },
  {
    icon: Utensils, label: 'Bookings & Floor', access: ['owner', 'manager', 'cashier', 'kitchen'],
    children: [
      { path: '/reservations', label: 'Bookings', icon: CalendarCheck },
      { path: '/floor-plan', label: 'Floor Plan', icon: MapPin },
      { path: '/waitlist', label: 'Waitlist', icon: Clock },
      { path: '/pre-shift', label: 'Pre-Shift Briefing', icon: ClipboardList },
      { path: '/table-layout', label: 'Table Layout', icon: LayoutGrid },
      { path: '/booking-settings', label: 'Booking Rules', icon: SlidersHorizontal },
      { path: '/booking-analytics', label: 'Booking Analytics', icon: BarChart3 },
    ],
  },
  {
    icon: Package, label: 'Menu & Items', access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/products', label: 'Item Library', icon: Boxes },
      { path: '/categories', label: 'Categories', icon: Layers },
      { path: '/modifiers', label: 'Modifiers', icon: Puzzle },
      { path: '/discounts', label: 'Discounts & Offers', icon: Percent },
      { path: '/comp-void', label: 'Comp / Void', icon: XCircle },
      { path: '/menu-engineering', label: 'Menu Matrix', icon: Grid3x3 },
      { path: '/what-if', label: 'What-If Simulator', icon: FlaskConical },
    ],
  },
  {
    icon: Warehouse, label: 'Inventory', access: ['owner', 'manager'],
    children: [
      { path: '/inventory', label: 'Stock Levels', icon: Warehouse },
      { path: '/measured-stock', label: 'Measured Stock', icon: Scale },
      { path: '/ai-pantry', label: 'AI Smart Pantry', icon: Sparkles },
      { path: '/purchase-orders', label: 'Purchase Orders', icon: FileText },
      { path: '/forecasting', label: 'Forecasting', icon: TrendingUp },
    ],
  },
  {
    icon: Users, label: 'Customers', access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/customers', label: 'Customer List', icon: Users },
      { path: '/vouchers', label: 'Vouchers', icon: Ticket },
      { path: '/loyalty', label: 'Loyalty & Events', icon: Award },
      { path: '/loyalty-config', label: 'Loyalty Config', icon: Settings },
      { path: '/loyalty-progress', label: 'Loyalty Progression', icon: TrendingUp },
      { path: '/marketing', label: 'Marketing Hub', icon: Megaphone },
    ],
  },
  {
    icon: Users2, label: 'Team', access: ['owner', 'manager', 'cashier', 'kitchen'],
    children: [
      { path: '/staff', label: 'Staff', icon: Users2 },
      { path: '/staff-roster', label: 'Roster & Payrun', icon: Clock },
      { path: '/leaderboard', label: 'Leaderboard', icon: Trophy },
      { path: '/tip-management', label: 'Tip Management', icon: DollarSign },
    ],
  },
  {
    icon: Calculator, label: 'Money', access: ['owner'],
    children: [
      { path: '/finance', label: 'Finance Suite', icon: Calculator },
      { path: '/accounting', label: 'Transactions', icon: Receipt },
      { path: '/bas-gst', label: 'BAS/GST', icon: FileBadge },
      { path: '/payroll', label: 'Payroll', icon: Wallet },
      { path: '/super', label: 'Super', icon: PiggyBank },
      { path: '/end-of-day', label: 'End of Day', icon: Printer },
    ],
  },
  {
    // "Command Center" used to name two unrelated screens (this group's
    // business-analytics one and the AI group's agent-ops one) — relabeled
    // to "Margins & Insights" here to match what it actually shows.
    icon: BarChart3, label: 'Insights', access: ['owner', 'manager'],
    children: [
      { path: '/dashboard', label: 'Classic Dashboard', icon: LayoutDashboard },
      { path: '/command-center', label: 'Margins & Insights', icon: PieChart },
      { path: '/quarterly-review', label: 'Quarterly Review', icon: TrendingUp },
    ],
  },
  {
    icon: Brain, label: 'NUA AI', access: ['owner', 'manager'],
    children: [
      // "Intelligence" renamed to match what the page itself calls itself
      // (the Autonomous Operating Layer) — and "Automation Engine" (threshold
      // alerts) renamed to "Alert Rules" so it stops reading as a duplicate
      // of "Automation Brain" (the actual rule-firing engine).
      { path: '/ash', label: 'Autonomy', icon: Sparkles },
      { path: '/ash-hq', label: 'Agent Command Center', icon: Zap },
      { path: '/ash-plans', label: 'Planner', icon: Target },
      { path: '/ash-memory', label: 'Memory', icon: BookMarked },
      { path: '/automation', label: 'Alert Rules', icon: AlertTriangle },
      { path: '/automation-triggers', label: 'Automation Brain', icon: Cpu },
    ],
  },
  {
    icon: SlidersHorizontal, label: 'Configuration', access: ['owner', 'manager'], advanced: true,
    children: [
      { path: '/settings', label: 'Settings', icon: Settings },
      { path: '/integrations', label: 'Integrations', icon: Plug },
      { path: '/eftpos-terminals', label: 'EFTPOS Terminals', icon: CreditCard },
    ],
  },
  {
    icon: ShieldCheck, label: 'Governance', access: ['owner', 'manager'],
    children: [
      { path: '/approvals', label: 'Approvals', icon: ShieldCheck },
      { path: '/audit', label: 'Audit Log', icon: FileText },
      { path: '/ash-permissions', label: 'AI Permissions', icon: KeyRound },
      { path: '/license', label: 'License', icon: FileBadge },
    ],
  },
  {
    icon: Store, label: 'Organization', access: ['owner', 'manager'],
    children: [
      { path: '/hq', label: 'HQ Roll-up', icon: Store },
      { path: '/multi-business', label: 'Multi-Business', icon: Building2 },
    ],
  },
];

const Sidebar = () => {
  const { theme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState({});

  const role = user?.role || 'cashier';
  // Use customPermissions if non-empty, otherwise fall back to permissions
  const customPerms = (user?.customPermissions?.length > 0) ? user.customPermissions : (user?.permissions || []);
  const hasCustomPerms = Array.isArray(customPerms) && customPerms.length > 0 && !customPerms.includes('*');

  const toggleGroup = (label) => {
    setOpenGroups(prev => ({ ...prev, [label]: !prev[label] }));
  };

  const isAllowed = (item) => {
    if (role === 'owner') return true;
    if (hasCustomPerms) {
      if (item.path) {
        const permKey = item.path.replace('/', '') || 'dashboard';
        return customPerms.includes(permKey);
      }
      if (item.children) {
        return item.children.some(c => {
          const permKey = c.path.replace('/', '') || 'dashboard';
          return customPerms.includes(permKey);
        });
      }
    }
    return item.access?.includes(role);
  };

  const isGroupActive = (children) => {
    return children?.some(c => location.pathname === c.path);
  };

  const handleLogout = async () => { await logout(); navigate('/'); };

  return (
    <div className="fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 flex flex-col z-50" data-testid="sidebar">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold" style={{ color: theme.primary }}>NUA</h1>
        {user && (
          <div className="flex items-center gap-2 mt-2">
            <div className={`w-2 h-2 rounded-full ${user.status === 'active' ? 'bg-green-500' : 'bg-gray-300'}`} />
            <span className="text-xs text-gray-500">{user.name}</span>
            <span className="text-[10px] ml-auto px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-medium uppercase">{role}</span>
          </div>
        )}
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
        {NAV_STRUCTURE.filter(isAllowed).map((item, idx) => {
          // Grouped item with children (dropdown)
          if (item.children) {
            const isOpen = openGroups[item.label] || isGroupActive(item.children);
            const Icon = item.icon;
            const filteredChildren = hasCustomPerms && role !== 'owner'
              ? item.children.filter(c => customPerms.includes(c.path.replace('/', '')))
              : item.children;
            if (filteredChildren.length === 0) return null;
            return (
              <div key={item.label} className={item.advanced ? 'pt-2 mt-2 border-t border-gray-100' : ''}>
                <button onClick={() => toggleGroup(item.label)}
                  className={`flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-all ${isGroupActive(item.children) ? 'font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
                  style={isGroupActive(item.children) ? { color: theme.primary } : {}}
                  data-testid={`nav-group-${item.label.toLowerCase().replace(/\s/g, '-')}`}>
                  <Icon size={18} />
                  <span className="flex-1 text-left">{item.label}</span>
                  {isOpen ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
                </button>
                {isOpen && (
                  <div className="ml-7 mt-0.5 space-y-0.5 border-l-2 pl-3" style={{ borderColor: `${theme.primary}30` }}>
                    {filteredChildren.map(child => {
                      const ChildIcon = child.icon;
                      return (
                        <NavLink key={child.path} to={child.path}
                          className={({ isActive }) => `flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-all ${isActive ? 'font-medium text-white' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}
                          style={({ isActive }) => isActive ? { backgroundColor: theme.primary } : {}}
                          data-testid={`nav-${child.path.replace('/', '')}`}>
                          {ChildIcon && <ChildIcon size={13} className="flex-shrink-0" />}
                          <span>{child.label}</span>
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          }
          // Single item (no dropdown)
          const Icon = item.icon;
          return (
            <NavLink key={item.path} to={item.path} end={item.path === '/dashboard'}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${isActive ? 'text-white font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
              style={({ isActive }) => isActive ? { backgroundColor: theme.primary } : {}}
              data-testid={`nav-${item.path.replace('/', '') || 'dashboard'}`}>
              <Icon size={18} /><span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="p-3 border-t border-gray-200">
        <button onClick={handleLogout} className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors" data-testid="logout-btn">
          <LogOut size={18} /> Sign Out
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
