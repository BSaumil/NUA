import en from '../locales/en.json';
import es from '../locales/es.json';
import zh from '../locales/zh.json';
import fr from '../locales/fr.json';

const SUPPORTED_LANGUAGES = ['en', 'es', 'zh', 'fr'];
const DEFAULT_LANGUAGE = 'en';
const LANGUAGE_KEY = 'nua_split_language';

// All four packs are small (a few KB each) and bundled eagerly here rather
// than genuinely lazy-loaded — t() is called synchronously all over the
// guest page's render, outside any hook that could await a dynamic
// import() and re-render once it resolves, so a real lazy load would
// silently keep rendering English (or the translation key itself) until a
// second render happened to run after the import settled.
const translations = { en, es, zh, fr };

export function getLanguage() {
  if (typeof localStorage === 'undefined') return DEFAULT_LANGUAGE;
  return localStorage.getItem(LANGUAGE_KEY) || DEFAULT_LANGUAGE;
}

export function setLanguage(lang) {
  if (SUPPORTED_LANGUAGES.includes(lang)) {
    localStorage.setItem(LANGUAGE_KEY, lang);
    return true;
  }
  return false;
}

export function t(key, params = {}) {
  const lang = getLanguage();
  const keys = key.split('.');
  let value = translations[lang] || translations[DEFAULT_LANGUAGE];

  for (const k of keys) {
    if (value && typeof value === 'object') {
      value = value[k];
    } else {
      return key;
    }
  }

  if (typeof value !== 'string') return key;

  // Simple parameter replacement: {{key}} -> value
  return value.replace(/\{\{(\w+)\}\}/g, (match, param) => {
    return params[param] !== undefined ? params[param] : match;
  });
}

export function getSupportedLanguages() {
  return SUPPORTED_LANGUAGES;
}

// Lazy load language packs
export async function loadLanguage(lang) {
  if (translations[lang]) return;
  try {
    const module = await import(`../locales/${lang}.json`);
    translations[lang] = module.default;
  } catch (e) {
    console.warn(`Failed to load language: ${lang}`);
  }
}
