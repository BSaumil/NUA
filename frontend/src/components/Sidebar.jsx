import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard, ShoppingCart, Package, Users, Warehouse,
  Calculator, FileText, Settings, Utensils, MapPin, Clock,
  ChefHat, BarChart3, Zap, Award, TrendingUp,
  FlaskConical, Sunrise, Brain, Plug, Users2, LogOut, ShieldCheck, Store,
  Mail, ClipboardList, DollarSign
} from 'lucide-react';

const ALL_NAV = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard', access: ['owner', 'manager'] },
  { path: '/pre-shift', icon: Sunrise, label: 'Pre-Shift', access: ['owner', 'manager', 'kitchen'] },
  { path: '/command-center', icon: Brain, label: 'Command Center', access: ['owner', 'manager'] },
  { path: '/pos', icon: ShoppingCart, label: 'POS Terminal', access: ['owner', 'manager', 'cashier'] },
  { path: '/reservations', icon: Utensils, label: 'Reservations', access: ['owner', 'manager', 'cashier'] },
  { path: '/floor-plan', icon: MapPin, label: 'Floor Plan', access: ['owner', 'manager', 'cashier'] },
  { path: '/waitlist', icon: Clock, label: 'Waitlist', access: ['owner', 'manager', 'cashier'] },
  { path: '/kitchen', icon: ChefHat, label: 'Kitchen', access: ['owner', 'manager', 'kitchen'] },
  { path: '/menu-engineering', icon: FlaskConical, label: 'Menu Engineering', access: ['owner', 'manager'] },
  { path: '/what-if', icon: FlaskConical, label: 'What-If', access: ['owner', 'manager'] },
  { path: '/products', icon: Package, label: 'Products', access: ['owner', 'manager', 'cashier'] },
  { path: '/customers', icon: Users, label: 'Customers', access: ['owner', 'manager', 'cashier'] },
  { path: '/loyalty', icon: Award, label: 'Loyalty & Events', access: ['owner', 'manager'] },
  { path: '/inventory', icon: Warehouse, label: 'Inventory', access: ['owner', 'manager'] },
  { path: '/ai-pantry', icon: Brain, label: 'AI Smart Pantry', access: ['owner', 'manager'] },
  { path: '/forecasting', icon: TrendingUp, label: 'Forecasting', access: ['owner', 'manager'] },
  { path: '/automation', icon: Zap, label: 'Automation', access: ['owner', 'manager'] },
  { path: '/accounting', icon: Calculator, label: 'Accounting', access: ['owner'] },
  { path: '/bas-gst', icon: FileText, label: 'BAS/GST', access: ['owner'] },
  { path: '/staff', icon: Users2, label: 'Staff', access: ['owner', 'manager'] },
  { path: '/staff-roster', icon: Clock, label: 'Roster & Payrun', access: ['owner', 'manager', 'cashier', 'kitchen'] },
  { path: '/email-marketing', icon: Mail, label: 'Email Marketing', access: ['owner', 'manager'] },
  { path: '/tip-management', icon: DollarSign, label: 'Tip Management', access: ['owner'] },
  { path: '/end-of-day', icon: ClipboardList, label: 'End of Day', access: ['owner', 'manager'] },
  { path: '/integrations', icon: Plug, label: 'Integrations', access: ['owner', 'manager'] },
  { path: '/settings', icon: Settings, label: 'Settings', access: ['owner', 'manager'] },
];

const Sidebar = () => {
  const { theme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const role = user?.role || 'cashier';
  const customPerms = user?.customPermissions || user?.permissions || [];
  const hasCustomPerms = Array.isArray(customPerms) && customPerms.length > 0 && !customPerms.includes('*');

  const navItems = ALL_NAV.filter(item => {
    if (role === 'owner') return true;
    // If user has custom permissions set by owner, use those
    if (hasCustomPerms) {
      const permKey = item.path.replace('/', '') || 'dashboard';
      return customPerms.includes(permKey);
    }
    // Fallback to role-based
    return item.access.includes(role);
  });

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 flex flex-col z-50" data-testid="sidebar">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold" style={{ color: theme.primary }}>NUVA POS</h1>
        {user && (
          <div className="flex items-center gap-2 mt-2">
            <div className={`w-2 h-2 rounded-full ${user.status === 'active' ? 'bg-green-500' : 'bg-gray-300'}`} />
            <span className="text-xs text-gray-500">{user.name}</span>
            <span className="text-[10px] ml-auto px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-medium uppercase">{role}</span>
          </div>
        )}
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
        {navItems.map(item => (
          <NavLink key={item.path} to={item.path} end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                isActive ? 'text-white font-medium' : 'text-gray-600 hover:bg-gray-50'
              }`
            }
            style={({ isActive }) => isActive ? { backgroundColor: theme.primary } : {}}
            data-testid={`nav-${item.path.replace('/', '') || 'dashboard'}`}>
            <item.icon size={18} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-gray-200">
        <button onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors"
          data-testid="logout-btn">
          <LogOut size={18} /> Sign Out
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
