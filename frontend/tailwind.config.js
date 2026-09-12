/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	extend: {
  		// NUA POS design tokens — see NUA_POS_DESIGN_TOKENS.md. `nua-purple`
  		// is a data hue reserved for AI-surfaced features/agent state; never
  		// use it decoratively.
  		fontFamily: {
  			'nua-wordmark':  ["'Bricolage Grotesque'", 'sans-serif'],
  			'nua-display':   ["'Bricolage Grotesque'", 'ui-sans-serif', 'system-ui', 'sans-serif'],
  			'nua-body':      ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
  			'nua-mono':      ["'JetBrains Mono'", 'ui-monospace', 'Menlo', 'monospace'],
  			'nua-signature': ['Caveat', 'cursive']
  		},
  		letterSpacing: { tagline: '0.35em' },
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			// NUA POS colour system — see NUA_POS_DESIGN_TOKENS.md. Chrome
  			// (nav, headings, buttons, links) is burgundy-on-ivory; the icon
  			// hues (orange/purple/pink/ink) are reserved for DATA — floor
  			// plans, kitchen tickets, order states, charts. Don't mix layers.
  			nua: {
  				// Brand icon hues — Tier 1 data marks. Never used as chrome.
  				orange: '#f58c14',
  				purple: '#8b5cf6',
  				pink:   '#ec4899',
  				ink:    '#1c1917',
  				paper:  '#fdfcfa',
  				wine:   '#6b2737', // deprecated — use `burgundy`; kept only for old references

  				// Chrome grounds
  				bg:      '#FAF8F3',
  				bgAlt:   '#F8F4ED',
  				surface: '#FFFDF9',
  				white:   '#FFFFFF',

  				// Chrome brand (wordmark, primary buttons, links, active nav)
  				burgundy:       '#750D28',
  				burgundyDark:   '#5F1A23',
  				burgundyBright: '#8A1433',
  				burgundyWash:   '#F5ECEA',

  				// Chrome type
  				chromeInk:  '#29241E',
  				chromeInk2: '#655D53',
  				chromeMuted:     '#756D67',
  				chromeMutedSoft: '#8D847D', // decorative only — fails AA for text

  				// Chrome lines
  				chromeBorder:        '#E8DED4',
  				chromeBorderStrong:  '#D9CFC5',
  				chromeBorderControl: '#9A928B',

  				// Dark chrome surfaces — occasional dark panels only, not a full dark UI
  				chromeDark:       '#29241E',
  				chromeDarkText:   '#FAF8F3',
  				chromeDarkBody:   '#D9D1C8',
  				chromeDarkAccent: '#E26383',
  			},
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};