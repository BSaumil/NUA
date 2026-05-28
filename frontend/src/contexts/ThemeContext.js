import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

const defaultTheme = {
  primary: '#6366f1',
  secondary: '#8b5cf6',
  accent: '#ec4899',
  background: '#ffffff',
  text: '#1f2937',
  sidebar: '#f9fafb'
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('posTheme');
    return saved ? JSON.parse(saved) : defaultTheme;
  });
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('nua_dark') === '1');
  const [lang, setLang] = useState(() => localStorage.getItem('nua_lang') || 'en');

  useEffect(() => {
    localStorage.setItem('posTheme', JSON.stringify(theme));
    Object.entries(theme).forEach(([key, value]) => {
      document.documentElement.style.setProperty(`--theme-${key}`, value);
    });
  }, [theme]);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      document.body.style.backgroundColor = '#0a0e17';
      document.body.style.color = '#e5e7eb';
    } else {
      document.documentElement.classList.remove('dark');
      document.body.style.backgroundColor = '';
      document.body.style.color = '';
    }
    localStorage.setItem('nua_dark', darkMode ? '1' : '0');
  }, [darkMode]);

  useEffect(() => { localStorage.setItem('nua_lang', lang); }, [lang]);

  const updateTheme = (updates) => setTheme(prev => ({ ...prev, ...updates }));
  const resetTheme = () => setTheme(defaultTheme);
  const toggleDarkMode = () => setDarkMode(d => !d);

  return (
    <ThemeContext.Provider value={{ theme, updateTheme, resetTheme, darkMode, toggleDarkMode, lang, setLang }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
