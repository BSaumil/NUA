import axios from 'axios';

const API_BASE_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Products API
export const productsAPI = {
  getAll: (params) => api.get('/products', { params }),
  create: (data) => api.post('/products', data),
  update: (id, data) => api.put(`/products/${id}`, data),
  delete: (id) => api.delete(`/products/${id}`),
};

// Promotions API
export const promotionsAPI = {
  getAll: () => api.get('/promotions'),
  getActive: () => api.get('/promotions/active'),
  create: (data) => api.post('/promotions', data),
};

// Customers API
export const customersAPI = {
  getAll: (params) => api.get('/customers', { params }),
  create: (data) => api.post('/customers', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
};

// Transactions API
export const transactionsAPI = {
  getAll: (params) => api.get('/transactions', { params }),
  create: (data) => api.post('/transactions', data),
  getHourly: () => api.get('/transactions/hourly'),
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
};

// Users API
export const usersAPI = {
  getAll: () => api.get('/users'),
  create: (data) => api.post('/users', data),
};

export default api;
