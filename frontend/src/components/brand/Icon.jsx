import React from 'react';

/**
 * NUA Pulse Grid icon — see brand/BRAND-SPEC.md and brand/assets/icons.
 *
 * variant="color" — full-colour 2x2 tile grid. Minimum 24px (BRAND-SPEC §3).
 * variant="mono"  — single-tone favicon/tab-bar mark. Minimum 14px.
 *
 * Tile order is fixed: orange (top-left), purple (top-right, carries the
 * pulse stroke — the one fixed exception to purple being AI-only), pink
 * (bottom-left), ink (bottom-right).
 */
export default function Icon({ size = 32, variant = 'color', className = '', title = 'NUA', ...rest }) {
  const common = {
    width: size, height: size, viewBox: '0 0 100 100',
    xmlns: 'http://www.w3.org/2000/svg', className,
    role: 'img', 'aria-label': title, ...rest,
  };

  if (variant === 'mono') {
    return (
      <svg {...common}>
        <title>{title}</title>
        <rect x="4" y="4" width="92" height="92" rx="20" fill="#f58c14" />
        <polyline
          points="22,54 34,54 40,32 51,70 59,54 78,54"
          fill="none" stroke="#ffffff" strokeWidth="7.5"
          strokeLinecap="round" strokeLinejoin="round"
        />
      </svg>
    );
  }

  return (
    <svg {...common}>
      <title>{title}</title>
      <rect x="6" y="6" width="40" height="40" rx="10" fill="#f58c14" />
      <rect x="54" y="6" width="40" height="40" rx="10" fill="#8b5cf6" />
      <rect x="6" y="54" width="40" height="40" rx="10" fill="#ec4899" />
      <rect x="54" y="54" width="40" height="40" rx="10" fill="#1c1917" />
      <polyline
        points="60,27 65,27 68,17 72,39 75,27 88,27"
        fill="none" stroke="#ffffff" strokeWidth="4.2"
        strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}
