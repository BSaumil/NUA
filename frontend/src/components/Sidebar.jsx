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
  ChevronDown, ChevronRight, Timer
} from 'lucide-react';

// Progressive disclosure: the everyday screens live in a handful of merged
// groups; power/config screens live under "Advanced" so the 95%-of-the-time
// sidebar stays clean. Everything is still reachable — nothing was removed.
const NAV_STRUCTURE = [
  { path: '/today', icon: Sunrise, label: 'Today', access: ['owner', 'manager'] },
  { path: '/pos', icon: ShoppingCart, label: 'POS Terminal', access: ['owner', 'manager', 'cashier'] },
  { path: '/kitchen', icon: ChefHat, label: 'Kitchen', access: ['owner', 'manager', 'kitchen'] },
  { path: '/coursing-analytics', icon: Timer, label: 'Coursing', access: ['owner', 'manager'] },
  {
    icon: Utensils, label: 'Bookings & Floor', access: ['owner', 'manager', 'cashier', 'kitchen'],
    children: [
      { path: '/reservations', label: 'Bookings' },
      { path: '/floor-plan', label: 'Floor Plan' },
      { path: '/waitlist', label: 'Waitlist' },
      { path: '/pre-shift', label: 'Pre-Shift Briefing' },
      { path: '/table-layout', label: 'Table Layout' },
      { path: '/booking-settings', label: 'Booking Rules' },
      { path: '/booking-analytics', label: 'Booking Analytics' },
    ],
  },
  {
    icon: Package, label: 'Menu & Items', access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/products', label: 'Item Library' },
      { path: '/categories', label: 'Categories' },
      { path: '/modifiers', label: 'Modifiers' },
      { path: '/discounts', label: 'Discounts & Offers' },
      { path: '/comp-void', label: 'Comp / Void' },
      { path: '/menu-engineering', label: 'Menu Matrix' },
      { path: '/what-if', label: 'What-If Simulator' },
    ],
  },
  {
    icon: Warehouse, label: 'Inventory', access: ['owner', 'manager'],
    children: [
      { path: '/inventory', label: 'Stock Levels' },
      { path: '/measured-stock', label: 'Measured Stock' },
      { path: '/ai-pantry', label: 'AI Smart Pantry' },
      { path: '/purchase-orders', label: 'Purchase Orders' },
      { path: '/forecasting', label: 'Forecasting' },
    ],
  },
  {
    icon: Users, label: 'Customers', access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/customers', label: 'Customer List' },
      { path: '/vouchers', label: 'Vouchers' },
      { path: '/loyalty', label: 'Loyalty & Events' },
      { path: '/loyalty-config', label: 'Loyalty Config' },
      { path: '/loyalty-progress', label: 'Loyalty Progression' },
      { path: '/marketing', label: 'Marketing Hub' },
    ],
  },
  {
    icon: Users2, label: 'Team', access: ['owner', 'manager', 'cashier', 'kitchen'],
    children: [
      { path: '/staff', label: 'Staff' },
      { path: '/staff-roster', label: 'Roster & Payrun' },
      { path: '/leaderboard', label: 'Leaderboard' },
      { path: '/tip-management', label: 'Tip Management' },
    ],
  },
  {
    icon: Calculator, label: 'Money', access: ['owner'],
    children: [
      { path: '/finance', label: 'Finance Suite' },
      { path: '/accounting', label: 'Transactions' },
      { path: '/bas-gst', label: 'BAS/GST' },
      { path: '/payroll', label: 'Payroll' },
      { path: '/super', label: 'Super' },
      { path: '/end-of-day', label: 'End of Day' },
    ],
  },
  {
    icon: BarChart3, label: 'Insights', access: ['owner', 'manager'],
    children: [
      { path: '/dashboard', label: 'Dashboard (classic)' },
      { path: '/command-center', label: 'Command Center' },
      { path: '/quarterly-review', label: 'Quarterly Review' },
    ],
  },
  {
    icon: Brain, label: 'NUA AI', access: ['owner', 'manager'],
    children: [
      { path: '/ash', label: 'Intelligence' },
      { path: '/ash-hq', label: 'AI Command Center' },
      { path: '/ash-plans', label: 'Planner' },
      { path: '/ash-memory', label: 'Memory' },
      { path: '/automation', label: 'Automation Engine' },
      { path: '/automation-triggers', label: 'Automation Brain' },
    ],
  },
  {
    icon: Settings, label: 'Advanced', access: ['owner', 'manager'], advanced: true,
    children: [
      { path: '/settings', label: 'Settings' },
      { path: '/integrations', label: 'Integrations' },
      { path: '/approvals', label: 'Approvals' },
      { path: '/audit', label: 'Audit Log' },
      { path: '/ash-permissions', label: 'AI Permissions' },
      { path: '/hq', label: 'HQ Roll-up' },
      { path: '/multi-business', label: 'Multi-Business' },
      { path: '/license', label: 'License' },
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
                    {filteredChildren.map(child => (
                      <NavLink key={child.path} to={child.path}
                        className={({ isActive }) => `block px-3 py-1.5 rounded text-sm transition-all ${isActive ? 'font-medium text-white' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}
                        style={({ isActive }) => isActive ? { backgroundColor: theme.primary } : {}}
                        data-testid={`nav-${child.path.replace('/', '')}`}>
                        {child.label}
                      </NavLink>
                    ))}
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
