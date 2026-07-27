import { useState, useEffect, useCallback } from 'react';
import { translate, LANGUAGES } from './translations';

// Each customer-facing surface (kiosk, QR table order, online order, CFD)
// remembers its own language choice on this device — there's no logged-in
// customer session to hang a preference off, so localStorage per storageKey
// is the right scope (a shared kiosk/tablet keeps the last guest's choice
// until someone picks a different one).
export function useLanguage(storageKey) {
  const [lang, setLangState] = useState(() => {
    try { return localStorage.getItem(storageKey) || 'en'; } catch { return 'en'; }
  });

  useEffect(() => {
    try { localStorage.setItem(storageKey, lang); } catch { /* ignore */ }
  }, [lang, storageKey]);

  const setLang = useCallback((code) => setLangState(code), []);
  const t = useCallback((key, vars) => translate(lang, key, vars), [lang]);
  const dir = (LANGUAGES.find(l => l.code === lang) || LANGUAGES[0]).dir;

  return { lang, setLang, t, dir, languages: LANGUAGES };
}
