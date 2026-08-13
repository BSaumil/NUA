import React, { createContext, useContext, useEffect, useState } from 'react';
import { useAuth } from './AuthContext';
import { businessAPI } from '../services/api';
import { getVertical } from '../lib/businessVertical';

const BusinessContext = createContext(null);

// Fetches the logged-in staff member's own business once per session so the
// nav (and anything else that wants to look/behave differently for a
// restaurant vs a retail shop vs a salon) has somewhere to read `vertical`
// from without every consumer re-fetching /business/{id} itself.
export function BusinessProvider({ children }) {
  const { user } = useAuth();
  const [business, setBusiness] = useState(null);

  useEffect(() => {
    if (!user || !user.businessId) { setBusiness(null); return; }
    let cancelled = false;
    businessAPI.get(user.businessId)
      .then(r => { if (!cancelled) setBusiness(r.data); })
      .catch(() => { if (!cancelled) setBusiness(null); });
    return () => { cancelled = true; };
  }, [user?.businessId]);

  const value = { business, vertical: getVertical(business?.type), refresh: () => {
    if (user?.businessId) businessAPI.get(user.businessId).then(r => setBusiness(r.data)).catch(() => {});
  } };

  return <BusinessContext.Provider value={value}>{children}</BusinessContext.Provider>;
}

export const useBusiness = () => useContext(BusinessContext) || { business: null, vertical: 'hospitality', refresh: () => {} };
