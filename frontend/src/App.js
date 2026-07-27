import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { POSProvider } from './contexts/POSContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LicenseProvider } from './contexts/LicenseContext';
import { Toaster } from './components/ui/sonner';
import BottomDock from './components/BottomDock';
import LicensePage, { LicenseLockScreen, LicenseBanner } from './pages/LicensePage';
import Login from './pages/Login';
import Today from './pages/Today';
import CommandBar from './components/CommandBar';
import Dashboard from './pages/Dashboard';
import POSTerminal from './pages/POSTerminal';
import StaffApp from './pages/StaffApp';
import OwnerDashboardApp from './pages/OwnerDashboardApp';
import { getAppShell } from './lib/appShell';
import Products from './pages/Products';
import Customers from './pages/Customers';
import Inventory from './pages/Inventory';
import InventoryAccounting from './pages/InventoryAccounting';
import BookingsInbox from './pages/BookingsInbox';
import ChannelMenus from './pages/ChannelMenus';
import SocialMedia from './pages/SocialMedia';
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
import AutomationTriggers from './pages/AutomationTriggers';
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
import StaffLeaderboard from './pages/StaffLeaderboard';
import QuarterlyReview from './pages/QuarterlyReview';
import TableLayout from './pages/TableLayout';
import BookingSettings from './pages/BookingSettings';
import BookingExperience from './pages/BookingExperience';
import BookingAnalytics from './pages/BookingAnalytics';
import Clubmember from './pages/Clubmember';
import EmailMarketing from './pages/EmailMarketing';
import Marketing from './pages/Marketing';
import Super from './pages/Super';
import Payroll from './pages/Payroll';
import Vouchers from './pages/Vouchers';
import FinanceLedger from './pages/FinanceLedger';
import AshDashboard from './pages/AshDashboard';
import AshCommandCenter from './pages/AshCommandCenter';
import AshPlans from './pages/AshPlans';
import AshPermissions from './pages/AshPermissions';
import AshMemory from './pages/AshMemory';
import LoyaltyProgress from './pages/LoyaltyProgress';
import MeasuredStock from './pages/MeasuredStock';
import Approvals from './pages/Approvals';
import AuditLogUniversal from './pages/AuditLogUniversal';
import HQDashboard from './pages/HQDashboard';
import AshChat from './components/AshChat';
import NotificationBell from './components/NotificationBell';
import Temperature from './pages/Temperature';
import EndOfDay from './pages/EndOfDay';
import TipManagement from './pages/TipManagement';
import Categories from './pages/Categories';
import Modifiers from './pages/Modifiers';
import Discounts from './pages/Discounts';
import CompVoid from './pages/CompVoid';
import PaymentLinks from './pages/PaymentLinks';
import AuditLog from './pages/AuditLog';
import InventoryAnomalies from './pages/InventoryAnomalies';
import BookingHeatmap from './pages/BookingHeatmap';
import CohortRetention from './pages/CohortRetention';
import ShiftSwaps from './pages/ShiftSwaps';
import SecurityCompliance from './pages/SecurityCompliance';
import LoyaltyConfig from './pages/LoyaltyConfig';
import AgentDashboard from './pages/AgentDashboard';
import AgentAutonomy from './pages/AgentAutonomy';
import PhoneAgent from './pages/PhoneAgent';
import PurchaseOrders from './pages/PurchaseOrders';
import MenuABTesting from './pages/MenuABTesting';
import AICostCoach from './pages/AICostCoach';
import LaborForecast from './pages/LaborForecast';
import SurgePricing from './pages/SurgePricing';
import VoiceRecipe from './pages/VoiceRecipe';
import KitchenLoad from './pages/KitchenLoad';
import PriceTune from './pages/PriceTune';
import EnterpriseCommandCenter from './pages/EnterpriseCommandCenter';
import NuaPro from './pages/NuaPro';
import ProfitGuardian from './pages/ProfitGuardian';
import DigitalTwin from './pages/DigitalTwin';
import {
  ShiftManager, AutoMarketing, Exceptions, HardwareHealth, Disputes,
  SupplierMarketplace, GiftCards, PredictiveOrders, WasteTracking, Concierge,
  Reputation, Franchise, FraudDetection, MarginGuardrails, StationReadiness,
  KioskMode, CFD, ChurnRisk, RecipeCosting, DynamicPricing, Subscriptions
} from './pages/V25Pages';
import { EventsManager, StaffAvailability, MarketingEmails } from './pages/V26Pages';
import OnlineOrders from './pages/OnlineOrders';
import OrderOnline from './pages/OrderOnline';
import TrackOrder from './pages/TrackOrder';
import { useTheme } from './contexts/ThemeContext';

function StaffLayout({ children }) {
  const { darkMode } = useTheme();
  return (
    <div
      className="min-h-screen pb-20 transition-colors"
      style={{
        backgroundColor: darkMode ? '#0b0b0f' : '#f6f7fb',
        color: darkMode ? '#eaeaea' : '#1f2937',
      }}
    >
      <LicenseBanner />
      <LicenseLockScreen />
      <div className="px-6 py-6 max-w-screen-2xl mx-auto">{children}</div>
      <BottomDock />
      <AshChat />
      <NotificationBell />
      <CommandBar />
    </div>
  );
}

function ProtectedRoutes() {
  const { user, loading } = useAuth();
  // Read (and persist) the shell BEFORE the login gate — a ?shell= query
  // param only ever shows up on the very first, pre-login page load, so it
  // must be captured into localStorage right away or it's lost the moment
  // the login redirect drops the query string.
  const shell = getAppShell();
  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-gray-500 text-lg">Loading...</div></div>;
  if (!user) return <Login />;

  // staff.nuapos.com.au — deliberately narrow (per the v1 scope): whatever
  // path was hit, this is the Staff app and nothing else. Same backend, same
  // login, same account — just a different, single-purpose front door with
  // none of the admin chrome (no BottomDock, no CommandBar, no Ash FAB).
  if (shell === 'staff') {
    return (
      <LicenseProvider>
        <LicenseBanner />
        <LicenseLockScreen />
        <Routes>
          <Route path="*" element={<StaffApp />} />
        </Routes>
      </LicenseProvider>
    );
  }

  // Role-based landing: owner.nuapos.com.au always opens the Dashboard app;
  // otherwise owners/managers get the Today pulse, cashiers the POS, kitchen
  // staff the KDS. Same data everywhere — different front door. Unlike the
  // staff shell, the owner shell keeps the full admin nav — the Dashboard
  // app is the front door, not a cage, since owners need to reach every
  // report and drill-down NUA POS has.
  const home = shell === 'owner' ? '/owner-dashboard'
    : user.role === 'cashier' ? '/pos' : user.role === 'kitchen' ? '/kitchen' : '/today';
  return (
    <LicenseProvider>
    <StaffLayout>
      <Routes>
        <Route path="/" element={<Navigate to={home} replace />} />
        <Route path="/today" element={<Today />} />
        <Route path="/staff-app" element={<StaffApp />} />
        <Route path="/owner-dashboard" element={<OwnerDashboardApp />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/pre-shift" element={<PreShift />} />
        <Route path="/command-center" element={<CommandCenter />} />
        <Route path="/pos" element={<POSTerminal />} />
        <Route path="/reservations" element={<Reservations />} />
        <Route path="/bookings-inbox" element={<BookingsInbox />} />
        <Route path="/channel-menus" element={<ChannelMenus />} />
        <Route path="/social-media" element={<Navigate to="/marketing?tab=social" replace />} />
        <Route path="/marketing" element={<Marketing />} />
        <Route path="/floor-plan" element={<FloorPlan />} />
        <Route path="/waitlist" element={<WaitlistPage />} />
        <Route path="/table-layout" element={<TableLayout />} />
        <Route path="/booking-settings" element={<BookingSettings />} />
        <Route path="/booking-experience" element={<Navigate to="/marketing?tab=experiences" replace />} />
        <Route path="/clubmember" element={<Navigate to="/marketing?tab=club" replace />} />
        <Route path="/booking-analytics" element={<BookingAnalytics />} />
        <Route path="/kitchen" element={<Kitchen />} />
        <Route path="/menu-engineering" element={<MenuEngineering />} />
        <Route path="/what-if" element={<WhatIfSimulator />} />
        <Route path="/products" element={<Products />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/modifiers" element={<Modifiers />} />
        <Route path="/discounts" element={<Navigate to="/marketing?tab=promotions" replace />} />
        <Route path="/comp-void" element={<CompVoid />} />
        <Route path="/payment-links" element={<PaymentLinks />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/loyalty" element={<Navigate to="/marketing?tab=loyalty" replace />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/inventory-accounting" element={<InventoryAccounting />} />
        <Route path="/forecasting" element={<Forecasting />} />
        <Route path="/automation" element={<AutomationEngine />} />
        <Route path="/automation-triggers" element={<AutomationTriggers />} />
        <Route path="/accounting" element={<Accounting />} />
        <Route path="/finance" element={<FinanceLedger />} />
        <Route path="/ash" element={<AshDashboard />} />
        <Route path="/ash-hq" element={<AshCommandCenter />} />
        <Route path="/ash-plans" element={<AshPlans />} />
        <Route path="/ash-permissions" element={<AshPermissions />} />
        <Route path="/ash-memory" element={<AshMemory />} />
        <Route path="/loyalty-progress" element={<LoyaltyProgress />} />
        <Route path="/measured-stock" element={<MeasuredStock />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/audit" element={<AuditLogUniversal />} />
        <Route path="/hq" element={<HQDashboard />} />
        <Route path="/bas-gst" element={<BASGST />} />
        <Route path="/super" element={<Super />} />
        <Route path="/payroll" element={<Payroll />} />
        <Route path="/vouchers" element={<Vouchers />} />
        <Route path="/temperature" element={<Temperature />} />
        <Route path="/integrations" element={<Integrations />} />
        <Route path="/staff" element={<StaffManagement />} />
        <Route path="/staff-roster" element={<StaffRoster />} />
        <Route path="/leaderboard" element={<StaffLeaderboard />} />
        <Route path="/quarterly-review" element={<QuarterlyReview />} />
        <Route path="/ai-pantry" element={<AIPantry />} />
        <Route path="/email-marketing" element={<Navigate to="/marketing?tab=email" replace />} />
        <Route path="/end-of-day" element={<EndOfDay />} />
        <Route path="/tip-management" element={<TipManagement />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/print-routing" element={<Navigate to="/settings?tab=print-routing" replace />} />
        <Route path="/security" element={<SecurityCompliance />} />
        <Route path="/audit-log" element={<AuditLog />} />
        <Route path="/anomalies" element={<InventoryAnomalies />} />
        <Route path="/booking-heatmap" element={<BookingHeatmap />} />
        <Route path="/cohort-retention" element={<CohortRetention />} />
        <Route path="/shift-swaps" element={<ShiftSwaps />} />
        <Route path="/loyalty-config" element={<LoyaltyConfig />} />
        <Route path="/agent" element={<AgentDashboard />} />
        <Route path="/agent-autonomy" element={<AgentAutonomy />} />
        <Route path="/phone-agent" element={<PhoneAgent />} />
        <Route path="/purchase-orders" element={<PurchaseOrders />} />
        <Route path="/ab-tests" element={<MenuABTesting />} />
        <Route path="/ai-cost-coach" element={<AICostCoach />} />
        <Route path="/labor-forecast" element={<LaborForecast />} />
        <Route path="/surge-pricing" element={<SurgePricing />} />
        <Route path="/voice-recipe" element={<VoiceRecipe />} />
        <Route path="/kitchen-load" element={<KitchenLoad />} />
        <Route path="/price-tune" element={<PriceTune />} />
        {/* v25 Enterprise Suite */}
        <Route path="/enterprise" element={<EnterpriseCommandCenter />} />
        <Route path="/ash-pro" element={<NuaPro />} />
        <Route path="/nua-pro" element={<NuaPro />} />
        <Route path="/profit-guardian" element={<ProfitGuardian />} />
        <Route path="/digital-twin" element={<DigitalTwin />} />
        <Route path="/shift-manager" element={<ShiftManager />} />
        <Route path="/auto-marketing" element={<AutoMarketing />} />
        <Route path="/exceptions" element={<Exceptions />} />
        <Route path="/hardware-health" element={<HardwareHealth />} />
        <Route path="/disputes" element={<Disputes />} />
        <Route path="/supplier-marketplace" element={<SupplierMarketplace />} />
        <Route path="/gift-cards" element={<GiftCards />} />
        <Route path="/predictive-orders" element={<PredictiveOrders />} />
        <Route path="/waste-tracking" element={<WasteTracking />} />
        <Route path="/concierge" element={<Concierge />} />
        <Route path="/reputation" element={<Reputation />} />
        <Route path="/franchise" element={<Franchise />} />
        <Route path="/fraud-detection" element={<FraudDetection />} />
        <Route path="/margin-guardrails" element={<MarginGuardrails />} />
        <Route path="/station-readiness" element={<StationReadiness />} />
        <Route path="/kiosk" element={<KioskMode />} />
        <Route path="/cfd" element={<CFD />} />
        <Route path="/churn-risk" element={<ChurnRisk />} />
        <Route path="/recipe-costing" element={<RecipeCosting />} />
        <Route path="/dynamic-pricing-rules" element={<DynamicPricing />} />
        <Route path="/subscriptions" element={<Subscriptions />} />
        {/* v26 commerce */}
        {/* /vouchers is already routed above to the Universal Voucher Engine
            (Vouchers.jsx) — VoucherManager (marketing/coupon codes) lives at
            /marketing?tab=vouchers instead, so this used to be an unreachable
            duplicate <Route path="/vouchers">. */}
        <Route path="/events" element={<EventsManager />} />
        <Route path="/staff-availability" element={<StaffAvailability />} />
        <Route path="/gift-card-sale" element={<Navigate to="/gift-cards" replace />} />
        <Route path="/marketing-emails" element={<MarketingEmails />} />
        <Route path="/online-orders" element={<OnlineOrders />} />
        <Route path="/license" element={<LicensePage />} />
      </Routes>
    </StaffLayout>
    </LicenseProvider>
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
                <Route path="/order-online" element={<OrderOnline />} />
                <Route path="/track" element={<TrackOrder />} />
                <Route path="/track/:code" element={<TrackOrder />} />
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
