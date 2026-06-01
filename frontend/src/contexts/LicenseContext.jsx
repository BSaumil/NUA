/* LicenseProvider — app-wide license state with periodic revalidation.
 * Stores: state, token, warnings, errorCode. POS pages can read this via useLicense().
 */
import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { licenseAPI } from '../services/api';

const LicenseContext = createContext(null);

// Stable per-browser device ID — first install creates it, never changes.
function getDeviceId() {
  let id = localStorage.getItem('nua-device-id');
  if (!id) {
    id = 'dev-' + (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now());
    localStorage.setItem('nua-device-id', id);
  }
  return id;
}

export function LicenseProvider({ children }) {
  const [state, setState] = useState({
    loading: true,
    ok: null,                 // true | false | null
    licenseState: 'unknown',  // active | past_due | grace | suspended | cancelled | abn_review
    errorCode: null,
    warnings: [],
    token: null,
    plan: null,
    abnEntityName: null,
    graceEndAt: null,
  });
  const tokenRef = useRef(null);

  const revalidate = useCallback(async () => {
    try {
      const deviceId = getDeviceId();
      const r = await licenseAPI.validate({
        tenantId: 'default', deviceId, appVersion: 'v25',
        token: tokenRef.current,
      });
      const d = r.data || {};
      tokenRef.current = d.token || null;
      setState({
        loading: false,
        ok: !!d.ok,
        licenseState: d.state || (d.errorCode === 'NO_LICENSE' ? 'no_license' : 'unknown'),
        errorCode: d.errorCode || null,
        warnings: d.warnings || [],
        token: d.token || null,
        plan: d.plan || null,
        abnEntityName: d.abnEntityName || null,
        graceEndAt: d.graceEndAt || null,
        message: d.message || null,
      });
    } catch (e) {
      // Network failure — keep prior state if any; don't lock the user out
      setState(s => ({ ...s, loading: false }));
    }
  }, []);

  useEffect(() => {
    revalidate();
    // Spec: periodic online revalidation. Token TTL is 30 min; revalidate every 10 min.
    const id = setInterval(revalidate, 10 * 60 * 1000);
    return () => clearInterval(id);
  }, [revalidate]);

  return (
    <LicenseContext.Provider value={{ ...state, revalidate, deviceId: getDeviceId() }}>
      {children}
    </LicenseContext.Provider>
  );
}

export function useLicense() {
  const ctx = useContext(LicenseContext);
  if (!ctx) throw new Error('useLicense must be used inside LicenseProvider');
  return ctx;
}
