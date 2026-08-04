/**
 * NUA OS branch glyphs.
 * Colour is inherited via currentColor and set by tier — do NOT override per branch.
 *   core branches → #f58c14   |   ai branches → #8b5cf6
 *
 * Usage: <BranchIcon name="payments" size={24} />
 */

const TIER = {
  autopilot: "ai",
  forecast: "ai",
  growth: "core",
  loyalty: "core",
  compliance: "core",
  payments: "core",
  delivery: "core",
  booking: "core",
};

const TIER_COLOR = { core: "#f58c14", ai: "#8b5cf6" };

const PATHS = {
  autopilot: (
    <path d="M50 26 L57 44 L75 50 L57 56 L50 74 L43 56 L25 50 L43 44 Z" fill="currentColor" />
  ),
  forecast: (
    <>
      <polyline points="24,64 38,52 50,58" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="50,58 64,40 78,34" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="8 7" />
      <circle cx="78" cy="34" r="6" fill="currentColor" />
    </>
  ),
  growth: (
    <>
      <polyline points="26,66 42,50 56,60 76,34" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="62,34 76,34 76,48" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  loyalty: (
    <>
      <circle cx="34" cy="40" r="7" fill="currentColor" />
      <circle cx="55" cy="40" r="7" fill="currentColor" />
      <circle cx="34" cy="62" r="7" fill="currentColor" />
      <circle cx="55" cy="62" r="7" fill="none" stroke="currentColor" strokeWidth="4" />
      <circle cx="74" cy="51" r="5" fill="none" stroke="currentColor" strokeWidth="4" strokeDasharray="3 3" />
    </>
  ),
  compliance: (
    <>
      <path d="M50 24 L74 33 V52 Q74 68 50 78 Q26 68 26 52 V33 Z" fill="none" stroke="currentColor" strokeWidth="5.5" strokeLinejoin="round" />
      <polyline points="39,50 47,58 63,42" fill="none" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  payments: (
    <>
      <rect x="22" y="36" width="42" height="30" rx="5" fill="none" stroke="currentColor" strokeWidth="5.5" />
      <line x1="22" y1="46" x2="64" y2="46" stroke="currentColor" strokeWidth="5.5" />
      <path d="M72 40 Q79 51 72 62" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
    </>
  ),
  delivery: (
    <>
      <path d="M30 70 Q30 46 50 46 Q70 46 70 30" fill="none" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" strokeDasharray="1 11" />
      <circle cx="30" cy="70" r="7" fill="currentColor" />
      <path d="M70 22 L78 34 H62 Z" fill="currentColor" />
    </>
  ),
  booking: (
    <>
      <rect x="24" y="30" width="52" height="44" rx="6" fill="none" stroke="currentColor" strokeWidth="5.5" />
      <line x1="24" y1="44" x2="76" y2="44" stroke="currentColor" strokeWidth="5.5" />
      <line x1="37" y1="22" x2="37" y2="34" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" />
      <line x1="63" y1="22" x2="63" y2="34" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" />
      <circle cx="50" cy="59" r="5" fill="currentColor" />
    </>
  ),
};

export default function BranchIcon({ name, size = 24, showFrame = true, className = "" }) {
  const glyph = PATHS[name];
  if (!glyph) return null;
  const color = TIER_COLOR[TIER[name]];

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      className={className}
      style={{ color }}
      role="img"
      aria-label={`NUA ${name} OS`}
    >
      {showFrame && (
        <rect x="6" y="6" width="88" height="88" rx="22" fill="none" stroke="currentColor" strokeWidth="5" />
      )}
      {glyph}
    </svg>
  );
}

export { TIER, TIER_COLOR };
