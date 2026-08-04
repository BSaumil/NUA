import React from 'react';

/**
 * NUA Pulse Grid icon.
 *
 * variant="color" — full-colour tiles. Minimum 24px (BRAND-SPEC §3).
 * variant="mono"  — single tone via currentColor. Use anywhere below ~24px,
 *                   where the full-colour tiles muddy into noise. Minimum 14px.
 *
 * The purple tile is the AI-feature signal and is the one fixed exception to
 * purple being reserved for AI surfaces — so it stays purple in the colour
 * variant and must not be recoloured.
 */
export default function Icon({ size = 32, variant = 'color', className = '', title = 'NUA', ...rest }) {
  const common = {
    width: size, height: size, viewBox: '0 0 64 64',
    xmlns: 'http://www.w3.org/2000/svg', className,
    role: 'img', 'aria-label': title, ...rest,
  };

  if (variant === 'mono') {
    return (
      <svg {...common}>
        <title>{title}</title>
        <g fill="currentColor">
          <rect x="4" y="44" width="16" height="16" rx="4.5" opacity="0.45" />
          <rect x="24" y="24" width="16" height="16" rx="4.5" opacity="0.7" />
          <rect x="24" y="44" width="16" height="16" rx="4.5" opacity="0.9" />
          <rect x="44" y="4" width="16" height="16" rx="4.5" />
          <rect x="44" y="24" width="16" height="16" rx="4.5" />
          <rect x="44" y="44" width="16" height="16" rx="4.5" />
        </g>
      </svg>
    );
  }

  // Unique gradient id per instance — two icons on one page would otherwise
  // share (and fight over) the same def.
  const gid = React.useId ? React.useId() : `nua-${Math.random().toString(36).slice(2)}`;
  const warm = `warm-${gid}`;
  return (
    <svg {...common}>
      <title>{title}</title>
      <defs>
        <linearGradient id={warm} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#f58c14" />
          <stop offset="100%" stopColor="#f9a03f" />
        </linearGradient>
      </defs>
      <rect x="4" y="44" width="16" height="16" rx="4.5" fill={`url(#${warm})`} opacity="0.55" />
      <rect x="24" y="24" width="16" height="16" rx="4.5" fill={`url(#${warm})`} opacity="0.8" />
      <rect x="24" y="44" width="16" height="16" rx="4.5" fill={`url(#${warm})`} />
      <rect x="44" y="4" width="16" height="16" rx="4.5" fill="#8b5cf6" />
      <rect x="44" y="24" width="16" height="16" rx="4.5" fill="#ec4899" />
      <rect x="44" y="44" width="16" height="16" rx="4.5" fill={`url(#${warm})`} />
    </svg>
  );
}
