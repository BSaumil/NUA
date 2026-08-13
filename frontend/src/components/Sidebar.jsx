import React, { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useBusiness } from '../contexts/BusinessContext';
import { getMenuLabels } from '../lib/businessVertical';
import {
  LayoutDashboard, ShoppingCart, Package, Users, Warehouse,
  Calculator, FileText, Settings, Utensils, MapPin, Clock,
  ChefHat, BarChart3, Zap, Award, TrendingUp,
  FlaskConical, Sunrise, Brain, Plug, Users2, LogOut, ShieldCheck, Store,
  Mail, ClipboardList, DollarSign, Trophy, Printer, PieChart,
  ChevronDown, ChevronRight, Timer,
  CalendarCheck, LayoutGrid, SlidersHorizontal, Boxes, Layers, Puzzle,
  Percent, XCircle, Grid3x3, Scale, Sparkles, Ticket, Megaphone, Receipt,
  FileBadge, Wallet, PiggyBank, Target, BookMarked, Cpu,
  CreditCard, KeyRound, Building2, Rocket, Fingerprint, ArrowLeftRight
} from 'lucide-react';

// Progressive disclosure: the everyday screens live in a handful of merged
// groups; power/config screens live under three focused groups (rather than
// one 10-item "Advanced" catch-all) so the 95%-of-the-time sidebar stays
// clean. Every child carries its own icon now — with 4-7 items per group,
// text alone made scanning slower than it needed to be. Everything is still
// reachable — nothing was removed, only regrouped and relabeled for clarity
// (e.g. two different screens were both called "Command Center").
//
// Vertical-aware: a handful of entries only make sense for a restaurant
// (kitchen dockets, course timing, table floor plans) and are hidden
// outside the 'hospitality' vertical via `verticals`. Everything else is
// generic enough to keep showing everywhere — an item library and a
// customer list mean the same thing to a cafe, a retail shop, or a salon,
// they just get relabeled per vertical so the words on screen match the
// owner's business. No `verticals` on an entry means "show for everyone."
// Retail (Phase 2) and beauty/services (Phase 4) get their own real
// feature pages later; for now this only changes what's visible and what
// it's called, not what it does.
const buildNavStructure = (vertical) => {
  const menu = getMenuLabels(vertical);
  return [
  { path: '/today', icon: Sunrise, label: 'Today', access: ['owner', 'manager'] },
  { path: '/whats-new', icon: Rocket, label: "What's New", access: ['owner', 'manager'] },
  { path: '/pos', icon: ShoppingCart, label: 'POS Terminal', access: ['owner', 'manager', 'cashier'] },
  { path: '/kitchen', icon: ChefHat, label: 'Kitchen', access: ['owner', 'manager', 'kitchen'], verticals: ['hospitality'] },
  { path: '/coursing-analytics', icon: Timer, label: 'Coursing', access: ['owner', 'manager'], verticals: ['hospitality'] },
  {
    icon: Utensils, label: 'Bookings & Floor', access: ['owner', 'manager', 'cashier', 'kitchen'], verticals: ['hospitality'],
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
    icon: Package, label: menu.group, access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/products', label: menu.itemLabel, icon: Boxes },
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
      { path: '/stock-transfers', label: 'Stock Transfers', icon: ArrowLeftRight, verticals: ['hospitality', 'retail'] },
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
      // GET /staff and GET|POST /tips* are owner/manager-only server-side —
      // a cashier or kitchen role reaching either of these used to get a
      // silently-failed toast and a blank page, since the group itself
      // (and therefore every child in it, pre-fix) was visible to them.
      { path: '/staff', label: 'Staff', icon: Users2, access: ['owner', 'manager'] },
      { path: '/staff-roster', label: 'Roster & Payrun', icon: Clock },
      { path: '/leaderboard', label: 'Leaderboard', icon: Trophy },
      { path: '/tip-management', label: 'Tip Management', icon: DollarSign, access: ['owner', 'manager'] },
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
      // (the Autonomous Operating Layer). The old "Automation Engine" entry
      // (threshold alerts, rebranded "Alert Rules") is gone entirely now —
      // its rules were write-only, never read by anything that could fire
      // them. "Automation Brain" is the one real, event-driven rules engine.
      { path: '/ash', label: 'Autonomy', icon: Sparkles },
      { path: '/ash-hq', label: 'Agent Command Center', icon: Zap },
      { path: '/ash-plans', label: 'Planner', icon: Target },
      { path: '/ash-memory', label: 'Memory', icon: BookMarked },
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
      { path: '/identity-settings', label: 'Identity & Add-Ons', icon: Fingerprint },
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
};

const Sidebar = () => {
  const { theme } = useTheme();
  const { user, logout } = useAuth();
  const { vertical } = useBusiness();
  const navigate = useNavigate();
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState({});

  const role = user?.role || 'cashier';
  // Use customPermissions if non-empty, otherwise fall back to permissions
  const customPerms = (user?.customPermissions?.length > 0) ? user.customPermissions : (user?.permissions || []);
  const hasCustomPerms = Array.isArray(customPerms) && customPerms.length > 0 && !customPerms.includes('*');
  const navStructure = buildNavStructure(vertical);

  const toggleGroup = (label) => {
    setOpenGroups(prev => ({ ...prev, [label]: !prev[label] }));
  };

  // Vertical gate applies ahead of (and independent from) role/permission
  // checks below — an owner running a retail shop still shouldn't see
  // "Kitchen" in their own nav just because owners see everything else.
  const matchesVertical = (item) => !item.verticals || item.verticals.includes(vertical);

  const isAllowed = (item) => {
    if (!matchesVertical(item)) return false;
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
        {navStructure.filter(isAllowed).map((item, idx) => {
          // Grouped item with children (dropdown)
          if (item.children) {
            const isOpen = openGroups[item.label] || isGroupActive(item.children);
            const Icon = item.icon;
            // Most groups are uniform — every child open to whoever can see
            // the group. A few (Team: Staff/Tip Management vs Roster/
            // Leaderboard) mix screens with genuinely different backend
            // access requirements under one group; `access` on a child
            // narrows the group's default for that child only, e.g. so
            // Tip Management doesn't show for a cashier the backend was
            // always going to 403.
            const filteredChildren = hasCustomPerms && role !== 'owner'
              ? item.children.filter(c => customPerms.includes(c.path.replace('/', '')))
              : item.children.filter(c => role === 'owner' || !c.access || c.access.includes(role));
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
