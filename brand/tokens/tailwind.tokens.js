/* Merge into theme.extend in tailwind.config.js. */
module.exports = {
  colors: {
    nua: {
      orange: '#f58c14',  // Primary / CTA
      purple: '#8b5cf6',  // AI features only
      pink:   '#ec4899',  // Insights / alerts
      ink:    '#1c1917',
      paper:  '#fdfcfa',
    },
  },
  fontFamily: {
    'nua-wordmark':  ["'Instrument Serif'", 'Georgia', 'serif'],
    'nua-display':   ["'Space Grotesk'", 'ui-sans-serif', 'system-ui', 'sans-serif'],
    'nua-body':      ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
    'nua-mono':      ["'IBM Plex Mono'", 'ui-monospace', 'Menlo', 'monospace'],
    'nua-signature': ['Caveat', 'cursive'],
  },
  letterSpacing: { tagline: '0.35em' },
};
