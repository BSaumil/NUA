import React from 'react';
import Icon from './Icon';

/**
 * NUA logo lockup — see BRAND-SPEC.md §2 (wordmark colour rule) and §4.
 *
 * variant="product"   — app headers, nav bars, in-product chrome.
 *                       Space Grotesk wordmark.
 * variant="marketing" — landing hero, login/signup, decks rendered in-app.
 *                       Bold all-caps Bricolage Grotesque wordmark + flourish.
 *
 * background="dark" | "light" | "brand" — picks the wordmark colour. This is
 * purely contrast-driven, NOT a status signal: dark → orange, light → wine,
 * brand (sitting on an orange/purple/pink panel) → white knockout. Never a
 * gradient, never purple or pink on the wordmark itself — those stay
 * exclusively AI/insight colours in the icon and product UI.
 *
 * Never use the marketing variant in functional UI (buttons, nav, in-app
 * headers) — BRAND-SPEC §3.
 */
const WORDMARK_COLOR = {
  dark: 'var(--nua-orange, #f58c14)',
  light: 'var(--nua-wine, #6b2737)',
  brand: '#ffffff',
};

export default function Logo({
  variant = 'product',
  background = 'dark',
  size = 28,
  className = '',
  showIcon = true,
  tagline,
}) {
  const marketing = variant === 'marketing';
  const wordmarkColor = WORDMARK_COLOR[background] || WORDMARK_COLOR.dark;

  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`} data-testid={`nua-logo-${variant}`}>
      {showIcon && <Icon size={size} variant="color" />}
      <span className="inline-flex flex-col leading-none">
        {marketing ? (
          <>
            <svg
              height={size * 1.15}
              viewBox="0 0 132 56"
              xmlns="http://www.w3.org/2000/svg"
              role="img"
              aria-label="Nua"
              style={{ overflow: 'visible' }}
            >
              <text
                x="0"
                y="42"
                fontFamily="var(--nua-font-wordmark, 'Bricolage Grotesque', sans-serif)"
                fontWeight="700"
                fontSize="48"
                fill={wordmarkColor}
              >
                NUA
              </text>
              {/* Caveat-spirited flourish — a supporting accent only. */}
              <path
                d="M2 50 C 28 44, 74 44, 112 48"
                fill="none"
                stroke={wordmarkColor}
                strokeWidth="2.5"
                strokeLinecap="round"
                opacity="0.9"
              />
            </svg>
            {tagline && (
              <span
                className="uppercase"
                style={{
                  fontFamily: "var(--nua-font-mono, 'IBM Plex Mono', monospace)",
                  letterSpacing: 'var(--nua-tagline-tracking, 0.35em)',
                  fontSize: Math.max(8, size * 0.32),
                  opacity: 0.6,
                  marginTop: 4,
                }}
              >
                {tagline}
              </span>
            )}
          </>
        ) : (
          <>
            <span
              style={{
                fontFamily: "var(--nua-font-display, 'Space Grotesk', system-ui, sans-serif)",
                fontWeight: 700,
                fontSize: size * 0.82,
                letterSpacing: '0.02em',
                color: wordmarkColor,
              }}
            >
              NUA
            </span>
            {tagline && (
              <span
                className="uppercase"
                style={{
                  fontFamily: "var(--nua-font-mono, 'IBM Plex Mono', monospace)",
                  letterSpacing: 'var(--nua-tagline-tracking, 0.35em)',
                  fontSize: Math.max(8, size * 0.3),
                  opacity: 0.55,
                  marginTop: 3,
                }}
              >
                {tagline}
              </span>
            )}
          </>
        )}
      </span>
    </span>
  );
}
