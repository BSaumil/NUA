import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { POSProvider } from './contexts/POSContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from './components/ui/sonner';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import POSTerminal from './pages/POSTerminal';
import Products from './pages/Products';
import Customers from './pages/Customers';
import Inventory from './pages/Inventory';
import Accounting from './pages/Accounting';
import BASGST from './pages/BASGST';
import Settings from './pages/Settings';
import Reservations from './pages/Reservations';
import FloorPlan from './pages/FloorPlan';
import WaitlistPage from './pages/Waitlist';
import Kitchen from './pages/Kitchen';
import PreShift from './pages/PreShift';
import CommandCenter from './pages/CommandCenter';
import MenuEngineering from './pages/MenuEngineering';
import AutomationEngine from './pages/AutomationEngine';
import LoyaltyEvents from './pages/LoyaltyEvents';
import Forecasting from './pages/Forecasting';
import WhatIfSimulator from './pages/WhatIfSimulator';
import BookingPortal from './pages/BookingPortal';
import TableOrder from './pages/TableOrder';
import PaymentSuccess from './pages/PaymentSuccess';
import Integrations from './pages/Integrations';
import StaffManagement from './pages/StaffManagement';
import AIPantry from './pages/AIPantry';
import MemberPortal from './pages/MemberPortal';
import StaffRoster from './pages/StaffRoster';
import EmailMarketing from './pages/EmailMarketing';
import EndOfDay from './pages/EndOfDay';
import TipManagement from './pages/TipManagement';

function StaffLayout({ children }) {
  return (
    <div className="flex">
      <Sidebar />
      <div className="ml-64 flex-1 p-8 min-h-screen bg-gray-50">{children}</div>
    </div>
  );
}

function ProtectedRoutes() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-gray-500 text-lg">Loading...</div></div>;
  if (!user) return <Login />;
  return (
    <StaffLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/pre-shift" element={<PreShift />} />
        <Route path="/command-center" element={<CommandCenter />} />
        <Route path="/pos" element={<POSTerminal />} />
        <Route path="/reservations" element={<Reservations />} />
        <Route path="/floor-plan" element={<FloorPlan />} />
        <Route path="/waitlist" element={<WaitlistPage />} />
        <Route path="/kitchen" element={<Kitchen />} />
        <Route path="/menu-engineering" element={<MenuEngineering />} />
        <Route path="/what-if" element={<WhatIfSimulator />} />
        <Route path="/products" element={<Products />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/loyalty" element={<LoyaltyEvents />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/forecasting" element={<Forecasting />} />
        <Route path="/automation" element={<AutomationEngine />} />
        <Route path="/accounting" element={<Accounting />} />
        <Route path="/bas-gst" element={<BASGST />} />
        <Route path="/integrations" element={<Integrations />} />
        <Route path="/staff" element={<StaffManagement />} />
        <Route path="/staff-roster" element={<StaffRoster />} />
        <Route path="/ai-pantry" element={<AIPantry />} />
        <Route path="/email-marketing" element={<EmailMarketing />} />
        <Route path="/end-of-day" element={<EndOfDay />} />
        <Route path="/tip-management" element={<TipManagement />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </StaffLayout>
  );
}

function App() {
  return (
    <ThemeProvider>
      <POSProvider>
        <AuthProvider>
          <div className="App">
            <BrowserRouter>
              <Routes>
                {/* Public routes — no sidebar, no auth */}
                <Route path="/booking" element={<BookingPortal />} />
                <Route path="/table/:tableId" element={<TableOrder />} />
                <Route path="/join" element={<MemberPortal />} />
                <Route path="/payment-success" element={<PaymentSuccess />} />
                {/* Staff routes — auth required */}
                <Route path="/*" element={<ProtectedRoutes />} />
              </Routes>
              <Toaster />
            </BrowserRouter>
          </div>
        </AuthProvider>
      </POSProvider>
    </ThemeProvider>
  );
}

export default App;
