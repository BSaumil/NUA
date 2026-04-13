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
  fireCourse: (id, course) => api.post(`/kitchen/orders/${id}/fire-course`, null, { params: { course } }),
  setPriority: (id, priority) => api.post(`/kitchen/orders/${id}/priority`, null, { params: { priority } }),
  getPrepList: () => api.get('/kitchen/prep-list'),
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
export const loyaltyAPI = {
  getRewards: () => api.get('/loyalty/rewards'),
  createReward: (data) => api.post('/loyalty/rewards', data),
  deleteReward: (id) => api.delete(`/loyalty/rewards/${id}`),
  redeem: (customerId, rewardId) => api.post('/loyalty/redeem', null, { params: { customer_id: customerId, reward_id: rewardId } }),
  getTiers: () => api.get('/loyalty/tiers'),
};

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

// Advanced Features — Tips, Training Mode, EOD Reports, Email Marketing
export const advancedAPI = {
  // Tips
  addTip: (data) => api.post('/tips/add', data),
  getTips: () => api.get('/tips'),
  getTipsSummary: () => api.get('/tips/summary'),
  distributeTipPool: () => api.post('/tips/pool-distribute'),
  // Training Mode
  getTrainingMode: () => api.get('/settings/training-mode'),
  setTrainingMode: (enabled) => api.post('/settings/training-mode', { enabled }),
  // End-of-Day
  getEndOfDayReport: (params) => api.get('/reports/end-of-day', { params }),
  // Email Marketing
  getCampaigns: () => api.get('/marketing/campaigns'),
  createCampaign: (data) => api.post('/marketing/campaigns', data),
  sendCampaign: (id) => api.post(`/marketing/campaigns/${id}/send`),
  deleteCampaign: (id) => api.delete(`/marketing/campaigns/${id}`),
};

export default api;
