import React from 'react';
import { Languages } from 'lucide-react';

// variant 'dark' — for surfaces on a black/dark background (CFD, TableOrder);
// variant 'light' — for surfaces on a light background (Kiosk, OrderOnline).
export function LanguageSelector({ lang, setLang, languages, variant = 'light', label, className = '' }) {
  const dark = variant === 'dark';
  return (
    <label
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs font-medium cursor-pointer ${
        dark ? 'bg-white/10 text-white' : 'bg-white border border-gray-200 text-gray-700'
      } ${className}`}
      data-testid="language-selector"
    >
      <Languages size={14} className={dark ? 'text-white/80' : 'text-gray-400'} />
      <select
        value={lang}
        onChange={(e) => setLang(e.target.value)}
        aria-label={label || 'Language'}
        className={`bg-transparent outline-none cursor-pointer ${dark ? 'text-white' : 'text-gray-700'}`}
        data-testid="language-select"
      >
        {languages.map(l => (
          <option key={l.code} value={l.code} className="text-gray-900">{l.label}</option>
        ))}
      </select>
    </label>
  );
}
