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
  ChevronDown, ChevronRight
} from 'lucide-react';

const NAV_STRUCTURE = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', access: ['owner', 'manager'] },
  { path: '/pre-shift', icon: Sunrise, label: 'Pre-Shift', access: ['owner', 'manager', 'kitchen'] },
  { path: '/command-center', icon: Brain, label: 'Command Center', access: ['owner', 'manager'] },
  { path: '/ash-hq', icon: Brain, label: 'NUA Command Center', access: ['owner', 'manager'] },
  { path: '/ash-plans', icon: Trophy, label: 'NUA Planner', access: ['owner', 'manager'] },
  { path: '/ash-permissions', icon: ShieldCheck, label: 'NUA Permissions', access: ['owner'] },
  { path: '/ash-memory', icon: FileText, label: 'NUA Memory', access: ['owner', 'manager'] },
  { path: '/ash', icon: Brain, label: 'NUA Intelligence', access: ['owner', 'manager'] },
  { path: '/hq', icon: Store, label: 'HQ Roll-up', access: ['owner'] },
  { path: '/approvals', icon: ShieldCheck, label: 'Approvals', access: ['owner', 'manager'] },
  { path: '/audit', icon: FileText, label: 'Audit Log', access: ['owner'] },
  { path: '/pos', icon: ShoppingCart, label: 'POS Terminal', access: ['owner', 'manager', 'cashier'] },
  {
    icon: Utensils, label: 'Reservations', access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/reservations', label: 'Bookings' },
      { path: '/floor-plan', label: 'Floor Plan' },
      { path: '/waitlist', label: 'Waitlist' },
      { path: '/table-layout', label: 'Table Layout' },
      { path: '/booking-settings', label: 'Settings & Rules' },
      { path: '/booking-experience', label: 'Experience' },
      { path: '/clubmember', label: 'Clubmember' },
      { path: '/booking-analytics', label: 'Analytics' },
    ],
  },
  { path: '/kitchen', icon: ChefHat, label: 'Kitchen', access: ['owner', 'manager', 'kitchen'] },
  {
    icon: FlaskConical, label: 'Menu Engineering', access: ['owner', 'manager'],
    children: [
      { path: '/menu-engineering', label: 'Menu Matrix' },
      { path: '/what-if', label: 'What-If Simulator' },
      { path: '/inventory', label: 'Inventory' },
      { path: '/ai-pantry', label: 'AI Smart Pantry' },
      { path: '/forecasting', label: 'Forecasting' },
      { path: '/quarterly-review', label: 'Quarterly Review' },
    ],
  },
  {
    icon: Package, label: 'Items', access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/products', label: 'Item Library' },
      { path: '/categories', label: 'Categories' },
      { path: '/modifiers', label: 'Modifiers' },
      { path: '/discounts', label: 'Discounts & Offers' },
      { path: '/comp-void', label: 'Comp / Void' },
      { path: '/payment-links', label: 'Payment Links' },
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
    icon: Users, label: 'Customers', access: ['owner', 'manager', 'cashier'],
    children: [
      { path: '/customers', label: 'Customer List' },
      { path: '/vouchers', label: 'Vouchers' },
      { path: '/loyalty', label: 'Loyalty & Events' },
      { path: '/loyalty-config', label: 'Loyalty Config' },
      { path: '/loyalty-progress', label: 'Loyalty Progression' },
      { path: '/email-marketing', label: 'Email Marketing' },
    ],
  },
  {
    icon: Zap, label: 'Automation', access: ['owner', 'manager'],
    children: [
      { path: '/automation', label: 'Automation Engine' },
      { path: '/automation-triggers', label: 'Automation Brain' },
    ],
  },
  {
    icon: Calculator, label: 'Accounting', access: ['owner'],
    children: [
      { path: '/finance', label: 'Finance Suite' },
      { path: '/accounting', label: 'Transactions' },
      { path: '/bas-gst', label: 'BAS/GST' },
      { path: '/payroll', label: 'Payroll' },
      { path: '/super', label: 'Super' },
      { path: '/end-of-day', label: 'End of Day' },
      { path: '/integrations', label: 'Integrations' },
    ],
  },
  { path: '/settings', icon: Settings, label: 'Settings', access: ['owner', 'manager'] },
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
              <div key={item.label}>
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
