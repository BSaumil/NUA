import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { POSProvider } from './contexts/POSContext';
import { Toaster } from './components/ui/sonner';
import Sidebar from './components/Sidebar';
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

function App() {
  return (
    <ThemeProvider>
      <POSProvider>
        <div className="App">
          <BrowserRouter>
            <div className="flex">
              <Sidebar />
              <div className="ml-64 flex-1 p-8 min-h-screen bg-gray-50">
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
                  <Route path="/products" element={<Products />} />
                  <Route path="/customers" element={<Customers />} />
                  <Route path="/inventory" element={<Inventory />} />
                  <Route path="/automation" element={<AutomationEngine />} />
                  <Route path="/accounting" element={<Accounting />} />
                  <Route path="/bas-gst" element={<BASGST />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </div>
            </div>
            <Toaster />
          </BrowserRouter>
        </div>
      </POSProvider>
    </ThemeProvider>
  );
}

export default App;
