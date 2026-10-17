import { useState, type ReactNode } from 'react'
import { MapTexture } from './MapTexture'
import { cn } from '../../lib/utils'

export interface MapMarker {
  id: string | number
  label: string
  status: 'Healthy' | 'Watch' | 'At Risk' | 'Critical' | string
  x: number // percentage 0-100
  y: number // percentage 0-100
}

export interface EstateMapProps {
  markers?: MapMarker[]
  className?: string
  height?: number | string
  footer?: ReactNode
}

const statusColorMap: Record<string, { fg: string; bg: string }> = {
  Healthy: { fg: '#2F9E73', bg: '#EAF6F0' },
  Watch: { fg: '#D98A2B', bg: '#FBF1E3' },
  'At Risk': { fg: '#C44D63', bg: '#FBE9EC' },
  Critical: { fg: '#C44D63', bg: '#FBE9EC' },
  neutral: { fg: '#7C3AED', bg: '#F1ECFF' },
}

export function EstateMap({
  markers = [],
  className,
  height = 320,
  footer,
}: EstateMapProps) {
  const [active, setActive] = useState<MapMarker | null>(null)

  return (
    <div
      className={cn('relative overflow-hidden rounded-2xl border border-line bg-surface', className)}
    >
      <div className="relative" style={{ height }}>
        <MapTexture />
        {markers.map((m) => {
          const meta = statusColorMap[m.status] ?? statusColorMap.neutral
          const isActive = active?.id === m.id
          return (
            <button
              key={m.id}
              type="button"
              onMouseEnter={() => setActive(m)}
              onFocus={() => setActive(m)}
              onMouseLeave={() => setActive(null)}
              onBlur={() => setActive(null)}
              onClick={() => setActive(isActive ? null : m)}
              className="absolute -translate-x-1/2 -translate-y-1/2 focus:outline-none"
              style={{ left: `${m.x}%`, top: `${m.y}%` }}
              aria-label={`${m.label} — ${m.status}`}
            >
              <span
                className={cn(
                  'block h-3.5 w-3.5 rounded-full border-2 border-white transition-transform duration-200',
                  isActive && 'scale-125',
                )}
                style={{ backgroundColor: meta.fg, boxShadow: `0 0 0 6px ${meta.bg}` }}
              />
            </button>
          )
        })}

        {active && (
          <div
            className="pointer-events-none absolute z-20 max-w-[210px] -translate-x-1/2 rounded-xl border border-line bg-surface/95 px-3 py-2 shadow-lift backdrop-blur"
            style={{
              left: `${Math.min(Math.max(active.x, 16), 84)}%`,
              top: `${active.y}%`,
              marginTop: -54,
            }}
          >
            <p className="text-[0.78rem] font-semibold leading-snug text-ink">{active.label}</p>
            <p
              className="mt-0.5 text-[0.68rem] font-semibold"
              style={{ color: (statusColorMap[active.status] ?? statusColorMap.neutral).fg }}
            >
              {active.status}
            </p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {['Healthy', 'Watch', 'At Risk', 'Critical'].map((s) => (
            <span key={s} className="flex items-center gap-1.5 text-[0.7rem] font-medium text-ink-muted">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: statusColorMap[s]?.fg }}
              />
              {s}
            </span>
          ))}
        </div>
        {footer && <div className="text-[0.72rem] text-ink-muted">{footer}</div>}
      </div>
    </div>
  )
}

export default EstateMap
