import React, { useState } from 'react';

// Dependency-free bar/line chart: this codebase has no charting library, so
// every "chart" is hand-rolled SVG. This is the one shared implementation —
// pages plug in {label, value} data and a theme color instead of each
// hand-rolling their own static width-percentage bars.
export default function MiniChart({ data, type = 'bar', color = '#f58c14', height = 160, valueFormatter }) {
  const [hoverIdx, setHoverIdx] = useState(null);

  if (!data || data.length === 0) {
    return <p className="text-gray-400 text-center py-8 text-sm">No data</p>;
  }

  const fmt = valueFormatter || (v => `${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`);
  const width = 100;
  const padding = 3;
  const labelSpace = 20;
  const plotW = width - padding * 2;
  const plotH = height - labelSpace;
  const n = data.length;
  const values = data.map(d => d.value);
  const max = Math.max(...values, 0);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  const xFor = (i) => padding + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
  const yFor = (v) => plotH - ((v - min) / range) * plotH;
  const zeroY = yFor(0);

  return (
    <div className="relative select-none" style={{ height }}>
      <svg viewBox={`0 0 ${width} ${plotH}`} preserveAspectRatio="none" className="w-full block" style={{ height: plotH }}>
        {type === 'bar' ? (
          data.map((d, i) => {
            const barW = (plotW / n) * 0.55;
            const x = xFor(i) - barW / 2;
            const y = Math.min(yFor(d.value), zeroY);
            const h = Math.max(Math.abs(yFor(d.value) - zeroY), 0.6);
            return (
              <rect
                key={i} x={x} y={y} width={barW} height={h} rx={0.8}
                fill={color}
                opacity={hoverIdx === null || hoverIdx === i ? 1 : 0.35}
                style={{ cursor: 'pointer', transition: 'opacity 0.15s' }}
                onMouseEnter={() => setHoverIdx(i)}
                onMouseLeave={() => setHoverIdx(null)}
                data-testid={`minichart-bar-${i}`}
              />
            );
          })
        ) : (
          <>
            <polyline
              points={data.map((d, i) => `${xFor(i)},${yFor(d.value)}`).join(' ')}
              fill="none" stroke={color} strokeWidth={1.5}
              strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke"
            />
            {data.map((d, i) => (
              <circle
                key={i} cx={xFor(i)} cy={yFor(d.value)} r={hoverIdx === i ? 2.4 : 1.3}
                fill={color}
                style={{ cursor: 'pointer', transition: 'r 0.15s' }}
                onMouseEnter={() => setHoverIdx(i)}
                onMouseLeave={() => setHoverIdx(null)}
                data-testid={`minichart-point-${i}`}
              />
            ))}
          </>
        )}
      </svg>
      <div className="flex mt-1 px-1">
        {data.map((d, i) => (
          <span
            key={i}
            className="text-[9px] text-gray-400 truncate text-center"
            style={{ flex: `0 0 ${100 / n}%` }}
          >
            {d.label}
          </span>
        ))}
      </div>
      {hoverIdx !== null && (
        <div
          className="absolute px-2 py-1 rounded-md text-[11px] font-semibold text-white shadow-lg pointer-events-none whitespace-nowrap z-10"
          style={{
            backgroundColor: color,
            left: `${xFor(hoverIdx)}%`,
            top: 0,
            transform: 'translate(-50%, -110%)',
          }}
          data-testid="minichart-tooltip"
        >
          {data[hoverIdx].label}: {fmt(data[hoverIdx].value)}
        </div>
      )}
    </div>
  );
}

export function ChartTypeToggle({ value, onChange, color }) {
  return (
    <div className="inline-flex rounded-lg border overflow-hidden text-xs" data-testid="chart-type-toggle">
      {['bar', 'line'].map(t => (
        <button
          key={t}
          type="button"
          onClick={() => onChange(t)}
          className="px-2.5 py-1 capitalize font-medium transition-colors"
          style={value === t ? { backgroundColor: color, color: '#fff' } : { color: '#9ca3af' }}
          data-testid={`chart-type-${t}`}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
