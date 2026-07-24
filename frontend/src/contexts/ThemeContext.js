import React, { createContext, useContext, useState, useEffect } from 'react';
import { advancedAPI } from '../services/api';

const ThemeContext = createContext();

// NUA Brand Identity (Feb 2026)
// Primary: #f58c14 (Orange) — energy, action, CTAs, highlights
// Secondary: #8b5cf6 (Purple) — AI, intelligence, system depth
// Accent: #ec4899 (Pink) — innovation, alerts, engagement moments
const defaultTheme = {
  primary: '#f58c14',
  secondary: '#8b5cf6',
  accent: '#ec4899',
  background: '#ffffff',
  text: '#1f2937',
  sidebar: '#f6f7fb'
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('posTheme');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Migrate legacy indigo primary to NUA orange brand color
        if (parsed.primary === '#6366f1') parsed.primary = '#f58c14';
        if (parsed.sidebar === '#f9fafb') parsed.sidebar = '#f6f7fb';
        return parsed;
      } catch {
        return defaultTheme;
      }
    }
    return defaultTheme;
  });
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('nua_dark') === '1');
  const [lang, setLang] = useState(() => localStorage.getItem('nua_lang') || 'en');

  useEffect(() => {
    localStorage.setItem('posTheme', JSON.stringify(theme));
    Object.entries(theme).forEach(([key, value]) => {
      document.documentElement.style.setProperty(`--theme-${key}`, value);
    });
    // NUA brand palette as CSS vars for global usage
    document.documentElement.style.setProperty('--nua-primary', '#f58c14');
    document.documentElement.style.setProperty('--nua-secondary', '#8b5cf6');
    document.documentElement.style.setProperty('--nua-accent', '#ec4899');
  }, [theme]);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      // NUA dark base palette
      document.body.style.backgroundColor = '#0b0b0f';
      document.body.style.color = '#eaeaea';
      document.documentElement.style.setProperty('--nua-bg', '#0b0b0f');
      document.documentElement.style.setProperty('--nua-surface', '#15151d');
      document.documentElement.style.setProperty('--nua-card', '#1c1c26');
      document.documentElement.style.setProperty('--nua-text', '#eaeaea');
      document.documentElement.style.setProperty('--nua-muted', '#a1a1aa');
    } else {
      document.documentElement.classList.remove('dark');
      document.body.style.backgroundColor = '#f6f7fb';
      document.body.style.color = '#1f2937';
      document.documentElement.style.setProperty('--nua-bg', '#f6f7fb');
      document.documentElement.style.setProperty('--nua-surface', '#ffffff');
      document.documentElement.style.setProperty('--nua-card', '#ffffff');
      document.documentElement.style.setProperty('--nua-text', '#1f2937');
      document.documentElement.style.setProperty('--nua-muted', '#6b7280');
    }
    localStorage.setItem('nua_dark', darkMode ? '1' : '0');
  }, [darkMode]);

  useEffect(() => { localStorage.setItem('nua_lang', lang); }, [lang]);

  // Business-wide theme: colors are per-browser (localStorage) until saved,
  // at which point every other terminal/device picks it up on next load —
  // otherwise an owner setting the brand color on one register would never
  // see it reflected on the others.
  const [themeSaving, setThemeSaving] = useState(false);
  const [themeSavedAt, setThemeSavedAt] = useState(null);
  useEffect(() => {
    advancedAPI.getTheme()
      .then(r => { if (r.data && Object.keys(r.data).length > 0) setTheme(prev => ({ ...prev, ...r.data })); })
      .catch(() => {}); // no saved business theme yet, or not reachable — keep local/default
  }, []);

  const updateTheme = (updates) => setTheme(prev => ({ ...prev, ...updates }));
  const resetTheme = () => setTheme(defaultTheme);
  const toggleDarkMode = () => setDarkMode(d => !d);
  const saveThemeToServer = async () => {
    setThemeSaving(true);
    try {
      await advancedAPI.saveTheme(theme);
      setThemeSavedAt(Date.now());
    } finally {
      setThemeSaving(false);
    }
  };

  // theme.text is consumed all over the app via inline `style={{color: theme.text}}`
  // for headings — that's a static hex meant for a light background, so pages
  // using it went dark-gray-on-black (nearly invisible) whenever dark mode was
  // on. Flip it here rather than in stored state, so the owner's light-mode
  // text color choice survives toggling dark mode on and off.
  const effectiveTheme = darkMode ? { ...theme, text: '#f4f4f5' } : theme;

  return (
    <ThemeContext.Provider value={{
      theme: effectiveTheme, updateTheme, resetTheme, darkMode, toggleDarkMode, lang, setLang,
      saveThemeToServer, themeSaving, themeSavedAt,
    }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
