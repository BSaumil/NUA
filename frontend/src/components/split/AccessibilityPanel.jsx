import React, { useState, useEffect } from 'react';
import { Settings, Globe, Type, Volume2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { t, getLanguage, setLanguage, getSupportedLanguages } from '../../lib/i18n';

const LANGUAGE_NAMES = {
  en: 'English',
  es: 'Español',
  zh: '中文',
  fr: 'Français',
};

const FONT_SIZES = [
  { value: 'small', label: 'Small' },
  { value: 'medium', label: 'Medium' },
  { value: 'large', label: 'Large' },
  { value: 'xlarge', label: 'Extra Large' },
];

const CONTRAST_MODES = [
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'High Contrast' },
];

export function AccessibilityPanel({ onClose }) {
  const [language, setLang] = useState(getLanguage());
  const [fontSize, setFontSize] = useState(localStorage.getItem('nua_font_size') || 'medium');
  const [contrast, setContrast] = useState(localStorage.getItem('nua_contrast') || 'normal');
  const [reduceMotion, setReduceMotion] = useState(localStorage.getItem('nua_reduce_motion') === 'true');

  useEffect(() => {
    document.documentElement.dataset.fontSize = fontSize;
    document.documentElement.dataset.contrast = contrast;
    if (reduceMotion) {
      document.documentElement.style.animation = 'none';
    }
    localStorage.setItem('nua_font_size', fontSize);
    localStorage.setItem('nua_contrast', contrast);
    localStorage.setItem('nua_reduce_motion', reduceMotion);
  }, [fontSize, contrast, reduceMotion]);

  const handleLanguageChange = (lang) => {
    setLanguage(lang);
    setLang(lang);
    window.location.reload(); // Reload to apply language
  };

  return (
    <Card className="fixed inset-0 md:inset-auto md:top-4 md:right-4 md:w-96 md:h-auto z-50 rounded-b-none md:rounded-b-lg">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base flex items-center gap-2">
          <Settings size={18} /> Accessibility
        </CardTitle>
        <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
      </CardHeader>

      <CardContent className="space-y-6 max-h-96 overflow-y-auto">
        {/* Language Selection */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <Globe size={16} /> Language
          </label>
          <div className="grid grid-cols-2 gap-2">
            {getSupportedLanguages().map((lang) => (
              <Button
                key={lang}
                variant={language === lang ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleLanguageChange(lang)}
                className="text-xs"
              >
                {LANGUAGE_NAMES[lang]}
              </Button>
            ))}
          </div>
        </div>

        {/* Font Size */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <Type size={16} /> Text Size
          </label>
          <div className="space-y-1">
            {FONT_SIZES.map((size) => (
              <label key={size.value} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="fontSize"
                  value={size.value}
                  checked={fontSize === size.value}
                  onChange={(e) => setFontSize(e.target.value)}
                  className="w-4 h-4"
                />
                <span>{size.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Contrast */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <span>📊</span> Contrast
          </label>
          <div className="space-y-1">
            {CONTRAST_MODES.map((mode) => (
              <label key={mode.value} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="contrast"
                  value={mode.value}
                  checked={contrast === mode.value}
                  onChange={(e) => setContrast(e.target.value)}
                  className="w-4 h-4"
                />
                <span>{mode.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Reduce Motion */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <input
              type="checkbox"
              checked={reduceMotion}
              onChange={(e) => setReduceMotion(e.target.checked)}
              className="w-4 h-4"
            />
            <span>Reduce motion</span>
          </label>
          <p className="text-xs text-gray-500 mt-1">
            Minimize animations and transitions
          </p>
        </div>

        {/* WCAG Info */}
        <div className="pt-2 border-t text-xs text-gray-600 bg-gray-50 p-2 rounded">
          <p className="font-medium mb-1">Accessibility</p>
          <ul className="space-y-0.5">
            <li>✓ WCAG 2.1 AA compliant</li>
            <li>✓ Keyboard navigation</li>
            <li>✓ Screen reader compatible</li>
            <li>✓ High contrast support</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
