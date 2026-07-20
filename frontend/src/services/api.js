import axios from 'axios';

const API_BASE_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach auth token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('nuva_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Products API
export const productsAPI = {
  getAll: (params) => api.get('/products', { params }),
  create: (data) => api.post('/products', data),
  update: (id, data) => api.put(`/products/${id}`, data),
  delete: (id) => api.delete(`/products/${id}`),
  adjustStock: (id, data) => api.post(`/products/${id}/adjust-stock`, data),
};

// Promotions API
export const promotionsAPI = {
  getAll: () => api.get('/promotions'),
  getActive: () => api.get('/promotions/active'),
  create: (data) => api.post('/promotions', data),
  update: (id, data) => api.put(`/promotions/${id}`, data),
  delete: (id) => api.delete(`/promotions/${id}`),
};

// Customers API
export const customersAPI = {
  getAll: (params) => api.get('/customers', { params }),
  create: (data) => api.post('/customers', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
  getProfile: (id) => api.get(`/customers/${id}/profile`),
  getWallet: (id) => api.get(`/customers/${id}/wallet`),
};

// Feedback API
export const feedbackAPI = {
  getAll: (params) => api.get('/feedback', { params }),
  create: (data) => api.post('/feedback', data),
  respond: (id, response) => api.put(`/feedback/${id}/respond`, null, { params: { response } }),
};

// Transactions API
export const transactionsAPI = {
  getAll: (params) => api.get('/transactions', { params }),
  create: (data) => api.post('/transactions', data),
  getHourly: () => api.get('/transactions/hourly'),
  getDetail: (id) => api.get(`/transactions/${id}`),
};

// Refunds API
export const refundsAPI = {
  getAll: () => api.get('/refunds'),
  create: (data) => api.post('/refunds', data),
};

// Accounting API
export const accountingAPI = {
  getSummary: () => api.get('/accounting/summary'),
  getPandL: () => api.get('/accounting/p-and-l'),
};

// Enterprise Finance & Accounting (double-entry)
export const financeAPI = {
  // Chart of Accounts
  listAccounts: () => api.get('/accounting/accounts'),
  createAccount: (data) => api.post('/accounting/accounts', data),
  updateAccount: (code, data) => api.put(`/accounting/accounts/${code}`, data),
  deleteAccount: (code) => api.delete(`/accounting/accounts/${code}`),
  seedCoA: () => api.post('/accounting/seed'),
  // Journals
  listJournals: (params) => api.get('/accounting/journals', { params }),
  getJournal: (id) => api.get(`/accounting/journals/${id}`),
  createJournal: (data) => api.post('/accounting/journals', data),
  reverseJournal: (id, data) => api.post(`/accounting/journals/${id}/reverse`, data),
  // Reports
  trialBalance: (params) => api.get('/accounting/reports/trial-balance', { params }),
  profitLoss: (params) => api.get('/accounting/reports/profit-loss', { params }),
  balanceSheet: (params) => api.get('/accounting/reports/balance-sheet', { params }),
  cashFlow: (params) => api.get('/accounting/reports/cash-flow', { params }),
  generalLedger: (code, params) => api.get(`/accounting/reports/general-ledger/${code}`, { params }),
  budgetVsActual: (params) => api.get('/accounting/reports/budget-vs-actual', { params }),
  // AP
  listBills: (params) => api.get('/accounting/bills', { params }),
  createBill: (data) => api.post('/accounting/bills', data),
  payBill: (id, data) => api.post(`/accounting/bills/${id}/pay`, data),
  deleteBill: (id) => api.delete(`/accounting/bills/${id}`),
  // AR
  listInvoices: (params) => api.get('/accounting/invoices', { params }),
  createInvoice: (data) => api.post('/accounting/invoices', data),
  receiveInvoice: (id, data) => api.post(`/accounting/invoices/${id}/receive`, data),
  deleteInvoice: (id) => api.delete(`/accounting/invoices/${id}`),
  // Deposits
  listDeposits: (params) => api.get('/accounting/deposits', { params }),
  createDeposit: (data) => api.post('/accounting/deposits', data),
  applyDeposit: (id, data) => api.post(`/accounting/deposits/${id}/apply`, data),
  // Bank rec
  bankStatement: (code, params) => api.get(`/accounting/bank/statement/${code}`, { params }),
  importBank: (data) => api.post('/accounting/bank/import', data),
  matchBank: (lineId, jid) => api.post(`/accounting/bank/${lineId}/match/${jid}`),
  ignoreBank: (lineId) => api.post(`/accounting/bank/${lineId}/ignore`),
  // Budgets
  listBudgets: () => api.get('/accounting/budgets'),
  createBudget: (data) => api.post('/accounting/budgets', data),
  // KPIs
  kpis: () => api.get('/accounting/kpis'),
};

// BAS/GST API
export const basGstAPI = {
  getReports: () => api.get('/bas-gst/reports'),
  create: (data) => api.post('/bas-gst/reports', data),
  submit: (id, useApi) => api.post(`/bas-gst/submit/${id}`, null, { params: { use_api: useApi } }),
};

// Locations API
export const locationsAPI = {
  getAll: () => api.get('/locations'),
  create: (data) => api.post('/locations', data),
  update: (id, data) => api.put(`/locations/${id}`, data),
  delete: (id) => api.delete(`/locations/${id}`),
};

// Users API
export const usersAPI = {
  getAll: () => api.get('/users'),
  create: (data) => api.post('/users', data),
};

// Categories API
export const categoriesAPI = {
  getAll: () => api.get('/categories'),
  create: (data) => api.post('/categories', data),
};

// Product Image Library
export const productImagesAPI = {
  list: (params = {}) => api.get('/product-images', { params }),
  upload: (data) => api.post('/product-images', data),
  delete: (id) => api.delete(`/product-images/${id}`),
};

// Products bulk-edit (separate from CRUD for clarity)
export const productsBulkAPI = {
  bulkEdit: (payload) => api.post('/products/bulk-edit', payload),
};

// AI Bookings Inbox — unified inbound channels (DM, phone, web)
export const bookingsInboxAPI = {
  list: (params = {}) => api.get('/bookings/inbox', { params }),
  ingest: (data) => api.post('/bookings/inbox', data),
  ack: (id, data) => api.post(`/bookings/inbox/${id}/ack`, data),
  dismiss: (id) => api.post(`/bookings/inbox/${id}/dismiss`),
};

// Awards (Fair Work / multi-country) + Super calc
export const awardsAPI = {
  catalogue: (country) => api.get('/awards/catalogue', { params: country ? { country } : {} }),
  installed: () => api.get('/awards/installed'),
  install: (code) => api.post('/awards/install', { code }),
  uninstall: (code) => api.delete(`/awards/${code}`),
  superByAward: (payload) => api.post('/payruns/super-by-award', payload),
  syncFairwork: () => api.post('/awards/sync-fairwork'),
};

// Channel Menus — per-channel pricing, availability, prep, AI discounts
export const channelMenusAPI = {
  channels: () => api.get('/channel-menus/channels'),
  list: (channel) => api.get(`/channel-menus/${channel}`),
  patch: (channel, body) => api.post(`/channel-menus/${channel}/patch`, body),
  bulkPrice: (channel, body) => api.post(`/channel-menus/${channel}/bulk-price`, body),
  aiPrepTimes: (channel) => api.post(`/channel-menus/${channel}/ai-prep-times`),
  aiDiscountSlow: (channel, body) => api.post(`/channel-menus/${channel}/ai-discount-slow`, body),
  removeOverride: (channel, productId) => api.delete(`/channel-menus/${channel}/${productId}`),
};

// Reservations: AI table auto-assign
export const reservationsAIAPI = {
  aiAssignTable: (reservationId) => api.post(`/reservations/${reservationId}/ai-assign-table`),
  aiAssignWalkin: (body) => api.post('/walkins/ai-assign', body),
};

// Modifiers API
export const modifiersAPI = {
  getAll: () => api.get('/modifiers'),
  create: (data) => api.post('/modifiers', data),
};

// Printers API
export const printersAPI = {
  getAll: () => api.get('/printers'),
  create: (data) => api.post('/printers', data),
  print: (printerId, transactionId) => api.post(`/printers/${printerId}/print`, null, { params: { transaction_id: transactionId } }),
};

// Offline Sync API
export const offlineAPI = {
  sync: (data) => api.post('/offline/sync', data),
};

// Reservations API
export const reservationsAPI = {
  getAll: (params) => api.get('/reservations', { params }),
  get: (id) => api.get(`/reservations/${id}`),
  create: (data) => api.post('/reservations', data),
  update: (id, data) => api.put(`/reservations/${id}`, data),
  delete: (id) => api.delete(`/reservations/${id}`),
  seat: (id, tableId) => api.post(`/reservations/${id}/seat`, null, { params: { table_id: tableId } }),
  complete: (id) => api.post(`/reservations/${id}/complete`),
  noShow: (id, fee) => api.post(`/reservations/${id}/no-show`, null, { params: { fee } }),
  autoAssign: (id) => api.get(`/reservations/auto-assign/${id}`),
};

// Floor Plans API
export const floorPlansAPI = {
  getAll: () => api.get('/floor-plans'),
  get: (id) => api.get(`/floor-plans/${id}`),
  create: (data) => api.post('/floor-plans', data),
  update: (id, data) => api.put(`/floor-plans/${id}`, data),
  delete: (id) => api.delete(`/floor-plans/${id}`),
  updateTableStatus: (tableId, status, planId) => api.post(`/floor-plans/tables/${tableId}/status`, null, { params: { status, plan_id: planId } }),
  assignServer: (sectionId, serverId, planId) => api.post(`/floor-plans/sections/${sectionId}/assign`, null, { params: { server_id: serverId, plan_id: planId } }),
};

// Waitlist API
export const waitlistAPI = {
  getAll: (params) => api.get('/waitlist', { params }),
  add: (data) => api.post('/waitlist', data),
  update: (id, data) => api.put(`/waitlist/${id}`, data),
  seat: (id, tableId) => api.post(`/waitlist/${id}/seat`, null, { params: { table_id: tableId } }),
  remove: (id) => api.delete(`/waitlist/${id}`),
};

// Kitchen Display (KDS) API
export const kitchenAPI = {
  getOrders: (params) => api.get('/kitchen/orders', { params }),
  createOrder: (data) => api.post('/kitchen/orders', data),
  startOrder: (id) => api.post(`/kitchen/orders/${id}/start`),
  readyOrder: (id) => api.post(`/kitchen/orders/${id}/ready`),
  servedOrder: (id) => api.post(`/kitchen/orders/${id}/served`),
  cancelOrder: (id) => api.post(`/kitchen/orders/${id}/cancel`),
  fireCourse: (id, course) => api.post(`/kitchen/orders/${id}/fire-course/${course}`),
  holdCourse: (id, course) => api.post(`/kitchen/orders/${id}/hold-course/${course}`),
  serveCourse: (id, course) => api.post(`/kitchen/orders/${id}/serve-course/${course}`),
  setPriority: (id, priority) => api.post(`/kitchen/orders/${id}/priority`, null, { params: { priority } }),
  getPrepList: () => api.get('/kitchen/prep-list'),
  getDocketConfig: () => api.get('/kitchen/docket-config'),
  updateDocketConfig: (data) => api.put('/kitchen/docket-config', data),
};

// Pre-Shift Dashboard API
export const preShiftAPI = {
  getToday: () => api.get('/pre-shift/today'),
};

// AI Command Center API
export const analyticsAPI = {
  getCommandCenter: () => api.get('/analytics/command-center'),
  getMenuEngineering: () => api.get('/analytics/menu-engineering'),
};

// Automation API
export const automationAPI = {
  getRules: () => api.get('/automation/rules'),
  createRule: (data) => api.post('/automation/rules', data),
  updateRule: (id, data) => api.put(`/automation/rules/${id}`, data),
  deleteRule: (id) => api.delete(`/automation/rules/${id}`),
  toggleRule: (id) => api.post(`/automation/rules/${id}/toggle`),
  getAlerts: () => api.get('/automation/alerts'),
};

// Predictive Customer Matching
export const predictiveAPI = {
  predictCustomer: (items) => api.post('/orders/predict-customer', items),
  linkCustomer: (txnId, customerId, points) => api.post('/orders/link-customer', null, { params: { transaction_id: txnId, customer_id: customerId, points_earned: points } }),
};

// What-If Simulator
export const simulatorAPI = {
  simulate: (changes) => api.post('/analytics/what-if', changes),
};

// Loyalty Program
// Events & Experiences
export const eventsAPI = {
  getAll: (params) => api.get('/events', { params }),
  create: (data) => api.post('/events', data),
  update: (id, data) => api.put(`/events/${id}`, data),
  bookTicket: (id, customerId, qty) => api.post(`/events/${id}/book`, null, { params: { customer_id: customerId, quantity: qty } }),
};

// Demand Forecasting
export const forecastAPI = {
  getDemand: () => api.get('/analytics/demand-forecast'),
  getTableTurns: () => api.get('/analytics/table-turns'),
  getSmartRoster: () => api.get('/staff/smart-roster'),
};

// QR Menu
export const qrMenuAPI = {
  getData: () => api.get('/menu/qr-data'),
};

// Public Booking Portal
export const publicAPI = {
  getMenu: () => api.get('/public/menu'),
  getAvailableSlots: (date, partySize) => api.get('/public/available-slots', { params: { date, party_size: partySize } }),
  book: (data) => api.post('/public/book', data),
  joinWaitlist: (data) => api.post('/public/join-waitlist', data),
  getEvents: () => api.get('/public/events'),
};

// QR Payment
export const paymentAPI = {
  generateQR: (data) => api.post('/payments/generate-qr', data),
  createSplit: (data) => api.post('/payments/split', data),
  confirm: (paymentId) => api.post(`/payments/${paymentId}/confirm`),
};

// Table-Side Ordering (Public)
export const tableOrderAPI = {
  getMenu: (tableId) => api.get(`/table/${tableId}/menu`),
  placeOrder: (tableId, data) => api.post(`/table/${tableId}/order`, data),
  getOrders: (tableId) => api.get(`/table/${tableId}/orders`),
  getOrderStatus: (orderId) => api.get(`/table/order/${orderId}/status`),
  getTableQRCodes: () => api.get('/tables/qr-codes'),
};

// Stripe Checkout
export const stripeAPI = {
  createCheckout: (data) => api.post('/stripe/checkout', data),
  checkStatus: (sessionId) => api.get(`/stripe/checkout/status/${sessionId}`),
};

// Integrations Hub
export const integrationsAPI = {
  getAll: () => api.get('/integrations'),
  connect: (slug, data) => api.post(`/integrations/${slug}/connect`, data),
  disconnect: (slug) => api.post(`/integrations/${slug}/disconnect`),
  sync: (slug) => api.post(`/integrations/${slug}/sync`),
};

// Advanced Features — Tips, Training Mode, EOD Reports, Email Marketing, AI Insights
export const advancedAPI = {
  addTip: (data) => api.post('/tips/add', data),
  getTips: () => api.get('/tips'),
  getTipsSummary: () => api.get('/tips/summary'),
  distributeTipPool: () => api.post('/tips/pool-distribute'),
  getTrainingMode: () => api.get('/settings/training-mode'),
  setTrainingMode: (enabled) => api.post('/settings/training-mode', { enabled }),
  getEndOfDayReport: (params) => api.get('/reports/end-of-day', { params }),
  getAIInsights: (data) => api.post('/reports/ai-insights', data),
  getCampaigns: () => api.get('/marketing/campaigns'),
  createCampaign: (data) => api.post('/marketing/campaigns', data),
  sendCampaign: (id) => api.post(`/marketing/campaigns/${id}/send`),
  deleteCampaign: (id) => api.delete(`/marketing/campaigns/${id}`),
};

// Staff Management — PIN, Timecards, Roster, Payrun
export const staffMgmtAPI = {
  pinLogin: (pin) => api.post('/auth/pin-login', { pin }),
  setPin: (staffId, pin) => api.post(`/auth/staff/${staffId}/set-pin`, { pin }),
  clockIn: () => api.post('/staff/clock-in'),
  clockOut: (data) => api.post('/staff/clock-out', data || {}),
  myStatus: () => api.get('/staff/my-status'),
  getTimecards: (params) => api.get('/staff/timecards', { params }),
  getRoster: (params) => api.get('/staff/roster', { params }),
  createRosterShift: (data) => api.post('/staff/roster', data),
  updateRosterShift: (id, data) => api.put(`/staff/roster/${id}`, data),
  deleteRosterShift: (id) => api.delete(`/staff/roster/${id}`),
  calculatePayrun: (params) => api.get('/payrun/calculate', { params }),
  processPayrun: (data) => api.post('/payrun/process', data),
  getPayrunHistory: () => api.get('/payrun/history'),
  getStaffReports: (params) => api.get('/staff/reports', { params }),
  getReceiptSettings: () => api.get('/receipt/settings'),
  saveReceiptSettings: (data) => api.post('/receipt/settings', data),
};

// Menu Features — AI Import, Price Adjust, Ghost Discount, What-If Advanced
export const menuFeaturesAPI = {
  aiImportMenu: (data) => api.post('/menu/ai-import', data),
  bulkPriceAdjust: (data) => api.post('/menu/price-adjust', data),
  ghostDiscount: (data) => api.post('/pos/ghost-discount', data),
  getGhostDiscounts: () => api.get('/pos/ghost-discounts'),
  whatIfAdvanced: (data) => api.post('/analytics/what-if-advanced', data),
};

// Enterprise Features — Surcharging, Live Sales, Permissions, Reports, Hardware
export const enterpriseAPI = {
  // Surcharging
  getSurchargeSettings: () => api.get('/surcharge/settings'),
  saveSurchargeSettings: (data) => api.post('/surcharge/settings', data),
  checkSurcharge: () => api.get('/surcharge/check'),
  // Live Sales
  getLiveSales: () => api.get('/live-sales'),
  // Permissions
  getAllPermissions: () => api.get('/permissions/all'),
  getStaffPermissions: (staffId) => api.get(`/permissions/staff/${staffId}`),
  setStaffPermissions: (staffId, permissions) => api.post(`/permissions/staff/${staffId}`, { permissions }),
  // Upsells
  getUpsells: (items) => api.get('/pos/upsells', { params: { items: items.join(',') } }),
  // Reports
  getReportConfig: () => api.get('/reports/automated-config'),
  saveReportConfig: (data) => api.post('/reports/automated-config', data),
  generateReport: (data) => api.post('/reports/generate', data),
  // Hardware
  getPrinters: () => api.get('/hardware/printers'),
  addPrinter: (data) => api.post('/hardware/printers', data),
  deletePrinter: (id) => api.delete(`/hardware/printers/${id}`),
  getScanners: () => api.get('/hardware/scanners'),
  addScanner: (data) => api.post('/hardware/scanners', data),
};

// Gamification — Leaderboard, Smart Tips, Quarterly Review, Print Routing
export const gamificationAPI = {
  getLeaderboard: () => api.get('/staff/leaderboard'),
  smartDistributeTips: () => api.post('/tips/smart-distribute'),
  getQuarterlyReview: () => api.get('/reports/quarterly-review'),
  getAIAlternatives: (items) => api.post('/reports/quarterly-review/ai-alternatives', { items }),
  getPrintRouting: () => api.get('/print-routing/config'),
  savePrintRouting: (data) => api.post('/print-routing/config', data),
  sendToPrinters: (data) => api.post('/print-routing/send', data),
  getPrintQueue: (printer) => api.get('/print-routing/queue', { params: { printer } }),
  completePrintJob: (id) => api.post(`/print-routing/complete/${id}`),
};

// Reservation Features — Table Combos, Booking Rules, Schedule, Experiences, Clubmember, Analytics
export const reservationFeaturesAPI = {
  getTableCombos: () => api.get('/tables/combinations'),
  createTableCombo: (data) => api.post('/tables/combinations', data),
  deleteTableCombo: (id) => api.delete(`/tables/combinations/${id}`),
  getBookingRules: () => api.get('/booking/rules'),
  saveBookingRules: (data) => api.post('/booking/rules', data),
  getBookingSchedule: () => api.get('/booking/schedule'),
  saveBookingSchedule: (shifts) => api.post('/booking/schedule', { shifts }),
  getExperiences: () => api.get('/booking/experiences'),
  createExperience: (data) => api.post('/booking/experiences', data),
  updateExperience: (id, data) => api.put(`/booking/experiences/${id}`, data),
  deleteExperience: (id) => api.delete(`/booking/experiences/${id}`),
  getClubOffers: () => api.get('/clubmember/offers'),
  createClubOffer: (data) => api.post('/clubmember/offers', data),
  updateClubOffer: (id, data) => api.put(`/clubmember/offers/${id}`, data),
  deleteClubOffer: (id) => api.delete(`/clubmember/offers/${id}`),
  getBookingAnalytics: () => api.get('/booking/analytics'),
  getSocialAccounts: () => api.get('/clubmember/social-accounts'),
  addSocialAccount: (data) => api.post('/clubmember/social-accounts', data),
  removeSocialAccount: (id) => api.delete(`/clubmember/social-accounts/${id}`),
  sendTestEmail: (data) => api.post('/email/test', data),
  getEmailSettings: () => api.get('/email/settings'),
  saveEmailSettings: (data) => api.post('/email/settings', data),
};

// Loyalty API (enhanced)
export const loyaltyAPI = {
  getTiers: () => api.get('/loyalty/tiers'),
  updateTier: (id, data) => api.put(`/loyalty/tiers/${id}`, data),
  getRewards: () => api.get('/loyalty/rewards'),
  createReward: (data) => api.post('/loyalty/rewards', data),
  updateReward: (id, data) => api.put(`/loyalty/rewards/${id}`, data),
  deleteReward: (id) => api.delete(`/loyalty/rewards/${id}`),
};

// Items System — Categories, Modifiers, Discounts, Comp/Void, Payment Links
export const itemsSystemAPI = {
  getCategories: () => api.get('/categories'),
  createCategory: (data) => api.post('/categories', data),
  updateCategory: (id, data) => api.put(`/categories/${id}`, data),
  deleteCategory: (id) => api.delete(`/categories/${id}`),
  cleanupLegacyCategories: () => api.post('/categories/cleanup-legacy'),
  getModifiers: () => api.get('/modifiers'),
  createModifier: (data) => api.post('/modifiers', data),
  updateModifier: (id, data) => api.put(`/modifiers/${id}`, data),
  deleteModifier: (id) => api.delete(`/modifiers/${id}`),
  getDiscounts: () => api.get('/discounts'),
  createDiscount: (data) => api.post('/discounts', data),
  updateDiscount: (id, data) => api.put(`/discounts/${id}`, data),
  deleteDiscount: (id) => api.delete(`/discounts/${id}`),
  createCompVoid: (data) => api.post('/comp-void', data),
  getCompVoids: () => api.get('/comp-void'),
  createPaymentLink: (data) => api.post('/payment-links', data),
  getPaymentLinks: () => api.get('/payment-links'),
  deletePaymentLink: (id) => api.delete(`/payment-links/${id}`),
  seedCatalog: () => api.post('/seed/catalog'),
};

// AI Pantry — invoice OCR + insights
export const aiPantryAPI = {
  generate: () => api.get('/ai-pantry/generate'),
  history: () => api.get('/ai-pantry/history'),
  parseInvoice: (data) => api.post('/ai-pantry/parse-invoice', data),
  applyInvoice: (id, selections) => api.post(`/ai-pantry/apply-invoice/${id}`, { selections }),
  listInvoices: () => api.get('/ai-pantry/invoices'),
  productInsights: () => api.get('/products/insights'),
};

// Inventory + Recipes + BAS / Accounting
export const inventoryAPI = {
  listIngredients: () => api.get('/ingredients'),
  createIngredient: (data) => api.post('/ingredients', data),
  updateIngredient: (id, data) => api.put(`/ingredients/${id}`, data),
  deleteIngredient: (id) => api.delete(`/ingredients/${id}`),
  lowStock: () => api.get('/ingredients/low-stock'),
  getRecipe: (productId) => api.get(`/recipes/product/${productId}`),
  saveRecipe: (productId, data) => api.put(`/recipes/product/${productId}`, data),
  listRecipes: () => api.get('/recipes'),
  createStockTake: (data) => api.post('/stock-takes', data),
  listStockTakes: () => api.get('/stock-takes'),
  assignInvoiceToStock: (invoiceId, assignments) => api.post(`/invoices/${invoiceId}/assign-stock`, { assignments }),
  bas: (params) => api.get('/accounting/bas', { params }),
  basCsv: (params) => api.get('/accounting/bas.csv', { params, responseType: 'blob' }),
};

// Online Ordering — public storefront + owner inbox + AI ETA
export const onlineAPI = {
  publicCategories: () => api.get('/online/categories'),
  publicProducts: () => api.get('/online/products'),
  placeOrder: (data) => api.post('/online/orders', data),
  listOrders: (status) => api.get('/online/orders', { params: status ? { status } : {} }),
  getOrder: (id) => api.get(`/online/orders/${id}`),
  updateStatus: (id, data) => api.patch(`/online/orders/${id}/status`, data),
  recomputeEta: (id) => api.post(`/online/orders/${id}/eta`),
  track: (code) => api.get(`/online/orders/track/${code}`),
  kitchenLoad: () => api.get('/online/kitchen/load'),
};

// v17 — Loyalty engine + AI Agent (Ash)
export const loyaltyEngineAPI = {
  getConfig: () => api.get('/loyalty/config'),
  updateConfig: (data) => api.put('/loyalty/config', data),
  earn: (data) => api.post('/loyalty/earn', data),
  redeem: (data) => api.post('/loyalty/redeem', data),
  getBalance: (customerId) => api.get(`/loyalty/balance/${customerId}`),
  getLedger: (customerId) => api.get(`/loyalty/ledger/${customerId}`),
};
export const agentAPI = {
  getSegments: () => api.get('/agent/segments'),
  getDecisions: (limit = 100) => api.get('/agent/decisions', { params: { limit } }),
  tick: () => api.post('/agent/tick'),
  voiceCommand: (text, audioBase64, mime) => api.post('/agent/voice-command', { text, audioBase64, mime }),
  getCatalog: () => api.get('/agent/voice-catalog'),
};
// Phase E+F — Autonomy config, Phone Agent, POs, A/B tests, Your Usual
export const phaseEFAPI = {
  getAutonomy: () => api.get('/agent/autonomy'),
  updateAutonomy: (data) => api.put('/agent/autonomy', data),
  getSmsQueue: () => api.get('/comms/sms-queue'),
  autoConfirm: (resId) => api.post(`/comms/auto-confirm/${resId}`),
  voiceExtended: (text) => api.post('/agent/voice-extended', { text }),
  autoPublishRoster: (weekStart) => api.post('/agent/auto-publish-roster', { weekStart }),
  tickExtended: () => api.post('/agent/tick-extended'),
  getCalls: () => api.get('/phone-agent/calls'),
  simulateCall: (caller, transcript) => api.post('/phone-agent/simulate', { caller, transcript }),
  getPOs: () => api.get('/purchase-orders'),
  generatePOs: () => api.post('/purchase-orders/generate'),
  updatePO: (id, action) => api.post(`/purchase-orders/${id}/${action}`),
  getABTests: () => api.get('/ab-tests'),
  createABTest: (data) => api.post('/ab-tests', data),
  concludeAB: (id) => api.post(`/ab-tests/${id}/conclude`),
  yourUsual: (customerId) => api.get(`/customers/${customerId}/your-usual`),
};

// Phase E+F Wave 2 — Auto-upsell, Price-tune, Overbooking, Cost coach, Labor forecast, Surge, Voice-to-recipe, Kitchen load
export const aiWave2API = {
  upsell: (cart) => api.post('/ai/upsell', { cart }),
  priceTune: () => api.get('/ai/price-tune'),
  applyPriceTune: (productId, newPrice) => api.post('/ai/price-tune/apply', { productId, newPrice }),
  overbookingCheck: (date, time, partySize) => api.post('/ai/overbooking-check', { date, time, partySize }),
  costCoach: () => api.get('/ai/cost-coach'),
  laborForecast: () => api.get('/ai/labor-forecast'),
  surgeRecs: () => api.get('/ai/surge-recommendations'),
  applySurge: (rules) => api.post('/ai/surge/apply', { rules }),
  activeSurge: () => api.get('/ai/surge/active'),
  voiceRecipe: (text, audioBase64, mime) => api.post('/ai/voice-recipe', { text, audioBase64, mime }),
  listRecipes: () => api.get('/ai/recipes'),
  kitchenLoad: () => api.get('/ai/kitchen-load'),
};

// v25 Suite — Enterprise / AI GM / Profit / Recipes / Franchise / Fraud / etc.
export const v25API = {
  // Must-have
  pushSync: (ops) => api.post('/v25/sync-queue', { ops }),
  syncQueue: () => api.get('/v25/sync-queue'),
  processSync: () => api.post('/v25/sync-queue/process'),
  exceptions: () => api.get('/v25/exceptions'),
  sites: () => api.get('/v25/sites'),
  addSite: (data) => api.post('/v25/sites', data),
  publish: (siteIds, bundle) => api.post('/v25/sites/publish', { siteIds, bundle }),
  rollback: (pubId) => api.post(`/v25/sites/rollback/${pubId}`),
  hardware: () => api.get('/v25/hardware'),
  heartbeat: (data) => api.post('/v25/hardware/heartbeat', data),
  disputes: () => api.get('/v25/disputes'),
  openDispute: (data) => api.post('/v25/disputes', data),
  attachEvidence: (id, notes) => api.post(`/v25/disputes/${id}/evidence`, { notes }),
  compareSuppliers: (item) => api.get('/v25/suppliers/compare', { params: { item } }),
  addQuote: (data) => api.post('/v25/suppliers/quote', data),
  // Should-have
  kioskStart: (data) => api.post('/v25/kiosk/session', data),
  kioskAdd: (sid, item) => api.post(`/v25/kiosk/session/${sid}/add`, { item }),
  kioskCheckout: (sid) => api.post(`/v25/kiosk/session/${sid}/checkout`),
  kioskList: () => api.get('/v25/kiosk/sessions'),
  kioskUpsell: (sid) => api.post(`/v25/kiosk/session/${sid}/upsell`),
  cfdCurrent: () => api.get('/v25/cfd/current'),
  substitute: (productId) => api.post('/v25/substitute', { productId }),
  toggle86: (productId, eightySixed) => api.post(`/v25/products/${productId}/86`, { eightySixed }),
  churnRisk: () => api.get('/v25/recovery/churn-risk'),
  winBack: (customerIds, voucherValue) => api.post('/v25/recovery/win-back', { customerIds, voucherValue }),
  stationReadiness: () => api.get('/v25/station-readiness'),
  marginGuardrails: () => api.get('/v25/margin-guardrails'),
  // Tier 1 — NUA Pro & co
  ashPlan: () => api.get('/v25/ash-pro/plan'),
  ashApprove: (planId, actionIds) => api.post('/v25/ash-pro/approve', { planId, actionIds }),
  profitGuardian: () => api.get('/v25/profit-guardian'),
  digitalTwin: () => api.get('/v25/digital-twin'),
  shiftManager: () => api.get('/v25/shift-manager'),
  autoMarketing: (audience) => api.post('/v25/marketing/auto', { audience }),
  listMarketing: () => api.get('/v25/marketing/auto'),
  // Tier 2
  dynamicRules: () => api.get('/v25/dynamic-pricing'),
  addDynamic: (data) => api.post('/v25/dynamic-pricing', data),
  subPlans: () => api.get('/v25/subscriptions/plans'),
  addSubPlan: (data) => api.post('/v25/subscriptions/plans', data),
  enrollSub: (customerId, planId) => api.post('/v25/subscriptions/enroll', { customerId, planId }),
  subMembers: () => api.get('/v25/subscriptions/members'),
  updateSubMember: (id, data) => api.patch(`/v25/subscriptions/members/${id}`, data),
  cancelSubMember: (id) => api.delete(`/v25/subscriptions/members/${id}`),
  giftCards: () => api.get('/v25/gift-cards'),
  issueGift: (data) => api.post('/v25/gift-cards', data),
  redeemGift: (code, amount) => api.post(`/v25/gift-cards/${code}/redeem`, { amount }),
  // Tier 3
  recipes: () => api.get('/v25/recipes/list'),
  upsertRecipe: (data) => api.post('/v25/recipes/upsert', data),
  getRecipe: (pid) => api.get(`/v25/recipes/${pid}`),
  predictiveOrders: () => api.post('/v25/predictive-orders'),
  waste: () => api.get('/v25/waste'),
  logWaste: (data) => api.post('/v25/waste', data),
  wasteInsights: () => api.get('/v25/waste/insights'),
  // Tier 4
  universalGuest: (id) => api.get(`/v25/guest/${id}`),
  concierge: (message) => api.post('/v25/concierge', { message }),
  reputation: () => api.get('/v25/reputation'),
  respondReview: (reviewId, response) => api.post('/v25/reputation/respond', { reviewId, response }),
  recoveryAction: (data) => api.post('/v25/recovery-action', data),
  // Tier 5
  franchiseDashboard: () => api.get('/v25/franchise/dashboard'),
  benchmark: () => api.get('/v25/benchmark'),
  warehouseExport: (collection, limit = 1000) => api.get('/v25/warehouse/export', { params: { collection, limit } }),
  fraudDetection: () => api.get('/v25/fraud-detection'),
};

// Licensing & Entitlements
export const licenseAPI = {  me: () => api.get('/license/me'),
  audit: () => api.get('/license/audit'),
  validate: (payload) => api.post('/license/validate', payload),
  onboard: (data) => api.post('/license/onboard', data),
  activateDevice: (data) => api.post('/license/device/activate', data),
  revokeDevice: (deviceId) => api.post('/license/device/revoke', { deviceId }),
  requestAbnChange: (data) => api.post('/license/abn/change-request', data),
  billingRecovery: (returnUrl) => api.post('/license/billing/recovery-link', { returnUrl }),
  forceState: (state, reason) => api.post('/license/dev/force-state', { state, reason }),
};

// v26 Commerce — vouchers, gift cards, events, staff availability, CFD
export const v26API = {
  // Vouchers / coupons
  listVouchers: () => api.get('/v26/vouchers'),
  createVoucher: (data) => api.post('/v26/vouchers', data),
  updateVoucher: (vid, data) => api.patch(`/v26/vouchers/${vid}`, data),
  deleteVoucher: (vid) => api.delete(`/v26/vouchers/${vid}`),
  applyVoucher: (code, cart) => api.post(`/v26/vouchers/${code}/apply`, { cart }),
  recordRedemption: (vid, data) => api.post(`/v26/vouchers/${vid}/redeem`, data),
  // Auto-apply promotions
  applyPromos: (cart) => api.post('/v26/cart/apply-promos', { cart }),
  activePromos: () => api.get('/v26/promotions/active-now'),
  // Subscriptions
  updateSubPlan: (id, data) => api.patch(`/v26/subscriptions/plans/${id}`, data),
  deleteSubPlan: (id) => api.delete(`/v26/subscriptions/plans/${id}`),
  // Gift cards
  listGiftCards: (status) => api.get('/v26/gift-cards', { params: status ? { status } : {} }),
  sellGift: (data) => api.post('/v26/gift-cards/sell', data),
  assignGift: (codeOrId, customerId) => api.post(`/v26/gift-cards/${codeOrId}/assign`, { customerId }),
  lookupGift: (code) => api.get(`/v26/gift-cards/lookup/${code}`),
  activateGift: (code, data) => api.post(`/v26/gift-cards/${code}/activate`, data || {}),
  redeemGiftPartial: (code, amount, transactionId) => api.post(`/v26/gift-cards/${code}/redeem`, { amount, transactionId }),
  giftTransactions: (code) => api.get(`/v26/gift-cards/${code}/transactions`),
  // Marketing emails
  generateMarketingEmail: (data) => api.post('/v26/marketing/email/generate', data),
  listMarketingEmails: () => api.get('/v26/marketing/emails'),
  updateMarketingEmail: (id, data) => api.patch(`/v26/marketing/emails/${id}`, data),
  deleteMarketingEmail: (id) => api.delete(`/v26/marketing/emails/${id}`),
  // Events
  listEvents: (upcomingOnly = false) => api.get('/v26/events', { params: { upcomingOnly } }),
  createEvent: (data) => api.post('/v26/events', data),
  updateEvent: (eid, data) => api.patch(`/v26/events/${eid}`, data),
  deleteEvent: (eid) => api.delete(`/v26/events/${eid}`),
  bookEvent: (eid, data) => api.post(`/v26/events/${eid}/book`, data),
  eventAiPreview: (date) => api.post('/v26/events/ai-preview', { date }),
  // Staff availability
  getAvailability: (staffId) => api.get(`/v26/staff/${staffId}/availability`),
  setAvailability: (staffId, data) => api.put(`/v26/staff/${staffId}/availability`, data),
  // Roster
  clearRoster: (week) => api.post('/v26/roster/clear-all', { week }),
  syncRoster: () => api.post('/v26/roster/sync-staff'),
  // CFD enriched
  cfdEnriched: () => api.get('/v26/cfd/enriched'),
  cfdPush: (data) => api.post('/v26/cfd/push', data),
};
export const v15API = {
  getBadges: () => api.get('/dock/badges'),
  // Tabs (hold/recall)
  getTabs: () => api.get('/pos/tabs'),
  createTab: (data) => api.post('/pos/tabs', data),
  deleteTab: (id) => api.delete(`/pos/tabs/${id}`),
  // Favorites
  getFavorites: () => api.get('/pos/favorites'),
  saveFavorites: (productIds) => api.post('/pos/favorites', { productIds }),
  // Variants
  setVariants: (productId, data) => api.put(`/products/${productId}/variants`, data),
  // CSV import
  bulkImport: (rows) => api.post('/items/bulk-import', { rows }),
  // Voice POS
  voiceOrder: (audioBase64, mime) => api.post('/pos/voice-order', { audioBase64, mime }),
  // Ask NUA
  askNua: (question) => api.post('/ai/ask-nua', { question }),
  // Item image gen
  generateImage: (name, cuisine) => api.post('/items/generate-image', { name, cuisine }),
  // Anomalies
  getAnomalies: () => api.get('/analytics/inventory-anomalies'),
  // Auto-roster
  autoRoster: (weekStart) => api.post('/staff/auto-roster', { weekStart }),
  commitAutoRoster: (shifts) => api.post('/staff/roster/commit-auto', { shifts }),
  // Shift swap
  getSwaps: () => api.get('/staff/shift-swaps'),
  createSwap: (data) => api.post('/staff/shift-swaps', data),
  approveSwap: (id) => api.post(`/staff/shift-swaps/${id}/approve`),
  rejectSwap: (id) => api.post(`/staff/shift-swaps/${id}/reject`),
  // Heatmap & cohort
  getBookingHeatmap: () => api.get('/analytics/booking-heatmap'),
  getCohortRetention: () => api.get('/analytics/cohort-retention'),
  // Audit
  getAuditLogs: (limit = 200) => api.get('/audit/logs', { params: { limit } }),
  // 2FA
  setup2FA: () => api.post('/auth/2fa/setup'),
  verify2FA: (code) => api.post('/auth/2fa/verify', { code }),
  disable2FA: () => api.post('/auth/2fa/disable'),
  // GDPR
  gdprExport: (customerId) => api.get(`/customers/${customerId}/gdpr-export`),
  gdprErase: (customerId) => api.delete(`/customers/${customerId}/gdpr-erase`),
  // BAS e-file
  efileBas: (reportId, abn) => api.post(`/bas-gst/efile/${reportId}`, { abn }),
  // i18n
  getLabels: (lang) => api.get(`/i18n/labels/${lang}`),
};

// ============ Social Media Marketing ============
export const socialAPI = {
  listAccounts: () => api.get('/social/accounts'),
  connectAccount: (data) => api.post('/social/accounts', data),
  disconnectAccount: (id) => api.delete(`/social/accounts/${id}`),
  listPosts: (params = {}) => api.get('/social/posts', { params }),
  createPost: (data) => api.post('/social/posts', data),
  updatePost: (id, data) => api.patch(`/social/posts/${id}`, data),
  deletePost: (id) => api.delete(`/social/posts/${id}`),
  publishPost: (id) => api.post(`/social/posts/${id}/publish`),
  duplicatePost: (id, data = {}) => api.post(`/social/posts/${id}/duplicate`, data),
  aiGenerate: (data) => api.post('/social/ai-generate', data),
  aiWeeklyPlan: (data) => api.post('/social/ai-weekly-plan', data),
  getPlanJob: (planId) => api.get(`/social/plan-jobs/${planId}`),
  bestTimes: () => api.get('/social/best-times'),
  listPlatforms: () => api.get('/social/platforms'),
};

// ── Superannuation (Fair Work compliant) ────────────────────────────────
export const superAPI = {
  rate: (payDate) => api.get('/super/rate', { params: payDate ? { payDate } : {} }),
  calc: (body) => api.post('/super/calc', body),
  commitWeeklyRun: (body) => api.post('/super/weekly-runs', body),
  listWeeklyRuns: (params = {}) => api.get('/super/weekly-runs', { params }),
  markPaid: (id, data) => api.patch(`/super/weekly-runs/${id}`, data),
  basLine: (params) => api.get('/super/bas-line', { params }),
  summary: (fy) => api.get('/super/summary', { params: fy ? { fy } : {} }),
};

// ── Temperature Monitoring ──────────────────────────────────────────────
export const temperatureAPI = {
  brands: () => api.get('/temperature/brands'),
  listDevices: () => api.get('/temperature/devices'),
  createDevice: (data) => api.post('/temperature/devices', data),
  updateDevice: (id, data) => api.patch(`/temperature/devices/${id}`, data),
  deleteDevice: (id) => api.delete(`/temperature/devices/${id}`),
  rotateSecret: (id) => api.post(`/temperature/devices/${id}/rotate-secret`),
  logReading: (data) => api.post('/temperature/readings', data),
  listReadings: (params) => api.get('/temperature/readings', { params }),
  listAlerts: (params) => api.get('/temperature/alerts', { params }),
  ackAlert: (id) => api.post(`/temperature/alerts/${id}/acknowledge`),
  report: (params) => api.get('/temperature/report', { params }),
  scanMissing: () => api.post('/temperature/scan-missing'),
};

// ── Table Courses / Send-nudge ──────────────────────────────────────────
export const tableCoursesAPI = {
  getSettings: () => api.get('/table-courses/settings'),
  updateSettings: (data) => api.put('/table-courses/settings', data),
  listStates: () => api.get('/table-courses/states'),
  upsertState: (data) => api.post('/table-courses/states', data),
  send: (data) => api.post('/table-courses/send', data),
  listNotifications: (params) => api.get('/table-courses/notifications', { params }),
  markNotifRead: (id) => api.post(`/table-courses/notifications/${id}/read`),
};

// ── Finalize batch (v27.7): pre-shift, day rules, marketing analytics,
// channel controls, digital wallet, PDF exports, automation triggers ─────
export const finalizeAPI = {
  preShiftBriefing: () => api.get('/preshift/briefing'),
  getDayRules: () => api.get('/bookings/day-rules'),
  updateDayRule: (weekday, data) => api.put(`/bookings/day-rules/${weekday}`, data),
  promoQR: (params) => api.get('/marketing/promo-qr', { params }),
  marketingAnalytics: (days = 30) => api.get('/marketing/analytics', { params: { days } }),
  channelStates: () => api.get('/channels/state'),
  updateChannelState: (data) => api.post('/channels/state', data),
  guestWallet: (customerId) => api.get(`/customers/${customerId}/wallet`),
  guestWalletApplePkpassUrl: (customerId) => `${process.env.REACT_APP_BACKEND_URL}/api/customers/${customerId}/wallet/apple.pkpass`,
  guestWalletGoogle: (customerId) => api.get(`/customers/${customerId}/wallet/google`),
  lookupByToken: (token) => api.post('/customers/lookup-by-token', { token }),
  lowStockPdfUrl: () => `${process.env.REACT_APP_BACKEND_URL}/api/inventory/low-stock/pdf`,
  aiPantryPdfUrl: () => `${process.env.REACT_APP_BACKEND_URL}/api/ai-pantry/order-sheet/pdf`,
  listTriggers: () => api.get('/automations/triggers'),
  createTrigger: (data) => api.post('/automations/triggers', data),
  updateTrigger: (id, data) => api.patch(`/automations/triggers/${id}`, data),
  deleteTrigger: (id) => api.delete(`/automations/triggers/${id}`),
  aiSuggestAutomation: (prompt) => api.post('/automations/ai-suggest', { prompt }),
  gmbSync: (locationId) => api.post(`/locations/${locationId}/gmb-sync`),

  // Payroll (Australian compliance)
  payrunCalculate: (data) => api.post('/payroll/payrun/calculate', data),
  payrunCommit: (data) => api.post('/payroll/payrun/commit', data),
  payrollRegister: (days = 90) => api.get(`/payroll/register?days=${days}`),
  payrollYtd: (staffId) => api.get(`/payroll/ytd/${staffId}`),
  payslipPdfUrl: (runId, staffId) => `${process.env.REACT_APP_BACKEND_URL}/api/payroll/payslip/${runId}/${staffId}/pdf`,
  stpBuild: (data) => api.post('/payroll/stp/build', data),
  rosterCompliance: (daysAhead = 14) => api.get(`/payroll/roster-compliance?days_ahead=${daysAhead}`),

  // Wallet credentials
  walletCredentialsStatus: () => api.get('/settings/wallet-credentials'),
  walletCredentialsSave: (data) => api.post('/settings/wallet-credentials', data),

  // AI Bundle Discovery (market-basket)
  bundleSuggestions: (days = 30) => api.get(`/v26/promotions/bundle-suggestions?days=${days}`),

  // BAS worksheet (G1-G20, W1-W5, T1)
  basWorksheet: (start, end) => api.get(`/bas-gst/worksheet?period_start=${start}&period_end=${end}`),

  // ── v29 · Customer Commerce Platform ─────────────────────────
  // Universal Voucher Engine
  issueVoucher: (data) => api.post('/vouchers', data),
  bulkVoucher: (data) => api.post('/vouchers/bulk', data),
  listVouchers: (params = {}) => api.get('/vouchers', { params }),
  getVoucher: (id) => api.get(`/vouchers/${id}`),
  lookupVoucher: (code) => api.get(`/vouchers/lookup/${encodeURIComponent(code)}`),
  validateVoucher: (data) => api.post('/vouchers/validate', data),
  redeemVoucher: (data) => api.post('/vouchers/redeem', data),
  revokeVoucher: (id, reason) => api.post(`/vouchers/${id}/revoke`, { reason }),

  // Unified Wallet
  walletGet: (customerId) => api.get(`/wallet/${customerId}`),
  walletCredit: (customerId, data) => api.post(`/wallet/${customerId}/credit`, { customerId, ...data }),
  walletDebit: (customerId, data) => api.post(`/wallet/${customerId}/debit`, { customerId, ...data }),
  walletTimeline: (customerId) => api.get(`/wallet/${customerId}/timeline`),

  // Flexible Refunds
  createRefund: (data) => api.post('/refunds/flexible', data),

  // AI Promotion Builder
  aiPromotionGoal: (goal) => api.post('/ai/promotion-goal', { goal }),

  // Promotion Analytics
  promoAnalytics: (days = 30) => api.get(`/promo-analytics/summary?days=${days}`),

  // Loyalty 2.0
  loyaltyStatus: (customerId) => api.get(`/loyalty/status/${customerId}`),
  loyaltyAward: (data) => api.post('/loyalty/award', data),

  // AI Personalisation
  personalisation: (customerId) => api.get(`/personalisation/${customerId}`),

  // Gift Card 2.0
  scheduleGift: (data) => api.post('/gift-cards/schedule', data),
  reloadGift: (voucherId, amount) => api.post(`/gift-cards/${voucherId}/reload`, { amount }),
};

export default api;
