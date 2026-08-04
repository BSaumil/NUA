import React from 'react';
import Icon from './Icon';

/**
 * NUA logo lockup.
 *
 * variant="product"   — app headers, nav bars, in-product chrome.
 *                       Plain Space Grotesk wordmark, no gradient, no flourish.
 * variant="marketing" — landing hero, login/signup, decks rendered in-app.
 *                       Gradient Instrument Serif wordmark + Caveat flourish.
 *
 * Never use the marketing variant in functional UI (buttons, nav, in-app
 * headers) — BRAND-SPEC §3.
 */
export default function Logo({
  variant = 'product',
  size = 28,
  className = '',
  showIcon = true,
  tagline,
}) {
  const marketing = variant === 'marketing';
  const gradientId = 'nua-wordmark-gradient';

  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`} data-testid={`nua-logo-${variant}`}>
      {showIcon && <Icon size={size} variant={marketing ? 'color' : 'color'} />}
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
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#f58c14" />
                  <stop offset="50%" stopColor="#ec4899" />
                  <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
              <text
                x="0"
                y="42"
                fontFamily="var(--nua-font-wordmark, 'Instrument Serif', Georgia, serif)"
                fontStyle="italic"
                fontSize="48"
                fill={`url(#${gradientId})`}
              >
                Nua
              </text>
              {/* Caveat-spirited flourish — a supporting accent only. */}
              <path
                d="M2 50 C 28 44, 74 44, 112 48"
                fill="none"
                stroke="#f58c14"
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
