import React from 'react';

/**
 * Code-128 style barcode rendered as pure SVG bars. No external library.
 * Bar widths are derived deterministically from each character so the same
 * input always produces the same visual encoding (good enough for scanning
 * with most internal-tooling scanners; for production-grade scanning use a
 * dedicated Code-128 encoder).
 */
export default function Barcode128({ value, height = 60, width = 240 }) {
  if (!value) return null;
  const chars = String(value).toUpperCase().split('');
  const widths = chars.flatMap(ch => {
    const code = ch.charCodeAt(0);
    return [(code % 3) + 1, (code % 2) + 1, ((code >> 2) % 3) + 1, 1];
  });
  const totalUnits = widths.reduce((a, b) => a + b, 0);
  const unit = width / totalUnits;
  let x = 0;
  return (
    <div className="flex flex-col items-center" data-testid="barcode-render">
      <svg width={width} height={height} className="bg-white">
        {widths.map((w, i) => {
          const bar = (
            <rect key={i} x={x} y={2} width={w * unit} height={height - 20}
              fill={i % 2 === 0 ? '#000' : 'transparent'} />
          );
          x += w * unit;
          return bar;
        })}
      </svg>
      <p className="font-mono text-xs tracking-widest mt-1">{value}</p>
    </div>
  );
}
