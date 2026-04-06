import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Users,
  BarChart3,
  FileText,
  Settings,
  Store,
  CalendarDays,
  Map,
  ClipboardList
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const menuItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/pos', icon: ShoppingCart, label: 'POS Terminal' },
  { path: '/reservations', icon: CalendarDays, label: 'Reservations' },
  { path: '/floor-plan', icon: Map, label: 'Floor Plan' },
  { path: '/waitlist', icon: ClipboardList, label: 'Waitlist' },
  { path: '/products', icon: Package, label: 'Products' },
  { path: '/customers', icon: Users, label: 'Customers' },
  { path: '/inventory', icon: Store, label: 'Inventory' },
  { path: '/accounting', icon: BarChart3, label: 'Accounting' },
  { path: '/bas-gst', icon: FileText, label: 'BAS/GST' },
  { path: '/settings', icon: Settings, label: 'Settings' }
];

const Sidebar = () => {
  const location = useLocation();
  const { theme } = useTheme();

  return (
    <div
      className="w-64 h-screen fixed left-0 top-0 border-r flex flex-col transition-all duration-300"
      style={{ backgroundColor: theme.sidebar }}
    >
      {/* Logo */}
      <div className="p-6 border-b">
        <div className="flex items-center gap-2">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-xl"
            style={{ backgroundColor: theme.primary }}
          >
            A
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: theme.text }}>Ananta POS</h1>
            <p className="text-xs text-gray-500">Pro Edition</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              className="flex items-center gap-3 px-6 py-3 transition-all duration-200 hover:bg-gray-100 relative group"
              style={{
                backgroundColor: isActive ? `${theme.primary}15` : 'transparent',
                color: isActive ? theme.primary : theme.text
              }}
            >
              {isActive && (
                <div
                  className="absolute left-0 top-0 bottom-0 w-1 rounded-r"
                  style={{ backgroundColor: theme.primary }}
                />
              )}
              <Icon size={20} />
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User info */}
      <div className="p-4 border-t">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
            style={{ backgroundColor: theme.primary }}
          >
            JD
          </div>
          <div className="flex-1">
            <p className="font-medium text-sm" style={{ color: theme.text }}>John Doe</p>
            <p className="text-xs text-gray-500">Admin</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
