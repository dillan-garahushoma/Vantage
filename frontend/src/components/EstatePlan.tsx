/**
 * Generated artwork: a surveyor's plan of a private estate.
 *
 * Drawn as vectors rather than a raster image so it stays crisp, weighs nothing,
 * inherits the design tokens, and can annotate itself with real measurements.
 */
export function EstatePlan({ className }: { className?: string }) {
  const units = [
    { x: 74, y: 92, w: 58, h: 40, label: 'HR-01' },
    { x: 140, y: 92, w: 52, h: 40, label: 'HR-02' },
    { x: 200, y: 92, w: 58, h: 40, label: 'HR-03' },
    { x: 74, y: 146, w: 58, h: 44, label: 'HR-04' },
    { x: 140, y: 146, w: 52, h: 44, label: 'HR-05' },
    { x: 200, y: 146, w: 58, h: 44, label: 'HR-06' },
  ]

  const perimeter = [
    [52, 62],
    [286, 62],
    [300, 200],
    [52, 200],
  ]

  const sensors = [
    [52, 62],
    [169, 62],
    [286, 62],
    [300, 130],
    [300, 200],
    [169, 200],
    [52, 200],
    [52, 130],
  ]

  return (
    <svg
      viewBox="0 0 340 260"
      className={className}
      role="img"
      aria-label="Survey plan of a private estate, with six units and a monitored perimeter"
    >
      <defs>
        <pattern id="plan-grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path
            d="M20 0H0V20"
            fill="none"
            stroke="currentColor"
            strokeOpacity="0.12"
            strokeWidth="1"
          />
        </pattern>
      </defs>

      <rect width="340" height="260" fill="url(#plan-grid)" />

      {/* Perimeter — the security boundary */}
      <polygon
        points={perimeter.map((p) => p.join(',')).join(' ')}
        fill="#E7EFEC"
        stroke="#14181C"
        strokeWidth="2"
      />

      {/* Internal service road */}
      <line x1="52" y1="136" x2="300" y2="136" stroke="#14181C" strokeOpacity="0.35" strokeWidth="1" strokeDasharray="6 4" />

      {/* Units */}
      {units.map((unit) => (
        <g key={unit.label}>
          <rect
            x={unit.x}
            y={unit.y}
            width={unit.w}
            height={unit.h}
            fill="#FFFFFF"
            stroke="#14181C"
            strokeWidth="1.2"
          />
          <text
            x={unit.x + 6}
            y={unit.y + 15}
            fontFamily="JetBrains Mono, monospace"
            fontSize="8.5"
            fill="#14181C"
          >
            {unit.label}
          </text>
          <rect x={unit.x + 6} y={unit.y + unit.h - 12} width={unit.w - 24} height="4" fill="#1F6F5C" />
        </g>
      ))}

      {/* Perimeter sensors */}
      {sensors.map(([cx, cy], index) => (
        <circle key={index} cx={cx} cy={cy} r="3.6" fill="#E4572E" stroke="#F6F4EF" strokeWidth="1.2" />
      ))}

      {/* North arrow */}
      <g transform="translate(310 44)">
        <path d="M0 14 L4 0 L8 14 L4 10 Z" fill="#14181C" />
        <text x="-3" y="24" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#14181C">
          N
        </text>
      </g>

      {/* Scale bar — 1 unit = 10 m */}
      <g transform="translate(52 226)">
        <line x1="0" y1="0" x2="60" y2="0" stroke="#14181C" strokeWidth="1.6" />
        <line x1="0" y1="-3" x2="0" y2="3" stroke="#14181C" strokeWidth="1.6" />
        <line x1="60" y1="-3" x2="60" y2="3" stroke="#14181C" strokeWidth="1.6" />
        <text y="13" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#63686E">
          60 m
        </text>
      </g>

      {/* Mono annotations */}
      <text
        x="300"
        y="248"
        fontFamily="JetBrains Mono, monospace"
        fontSize="8.5"
        fill="#63686E"
        textAnchor="end"
      >
        6 units · 8 sensors · 1 gate
      </text>
    </svg>
  )
}
