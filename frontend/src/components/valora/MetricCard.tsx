import { Minus, TrendingDown, TrendingUp } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'
import { Sparkline } from './Sparkline'
import { Surface } from './Surface'

export type MetricTone = 'positive' | 'attention' | 'critical' | 'brand' | 'neutral'

export interface MetricCardProps {
  icon?: ReactNode
  label: string
  value: ReactNode
  suffix?: string
  /** A short delta label such as `+4` or `−12%`. */
  delta?: string
  deltaTone?: MetricTone
  /** Which way the trend line should point, when it is not implied by `deltaTone`. */
  trendDirection?: 'up' | 'down' | 'flat'
  hint?: ReactNode
  spark?: number[]
  className?: string
}

const toneText: Record<MetricTone, string> = {
  positive: 'text-mint-ink',
  attention: 'text-ochre-ink',
  critical: 'text-signal-ink',
  brand: 'text-brand-ink',
  neutral: 'text-ink-muted',
}

/**
 * One measured figure with its context.
 *
 * The value is passed in already formatted, and `hint` is where the number's
 * provenance goes (“Benchmark: 5 business days”) — a metric without its
 * comparison is a number, not a measurement.
 */
export function MetricCard({
  icon,
  label,
  value,
  suffix,
  delta,
  deltaTone = 'positive',
  trendDirection,
  hint,
  spark,
  className,
}: MetricCardProps) {
  const direction =
    trendDirection ?? (deltaTone === 'positive' ? 'up' : deltaTone === 'neutral' ? 'flat' : 'down')
  const TrendIcon = direction === 'down' ? TrendingDown : direction === 'flat' ? Minus : TrendingUp

  return (
    <Surface hover className={cn('flex flex-col justify-between', className)}>
      <div className="flex items-start justify-between gap-3">
        {icon ? (
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-canvas text-brand">
            {icon}
          </span>
        ) : null}
        {delta ? (
          <span
            className={cn(
              'num inline-flex items-center gap-1 rounded-full bg-canvas px-2 py-1 text-[0.7rem] font-bold',
              toneText[deltaTone],
            )}
          >
            <TrendIcon className="h-3 w-3" />
            {delta}
          </span>
        ) : null}
      </div>

      <div className="mt-5">
        <p className="num font-heading text-[1.85rem] leading-none font-extrabold tracking-[-0.02em] text-ink">
          {value}
          {suffix ? <span className="text-[1rem] font-bold text-ink/30">{suffix}</span> : null}
        </p>
        <p className="mt-2 text-[0.82rem] font-medium text-ink/60">{label}</p>
        {hint ? <p className="mt-1 text-[0.74rem] text-ink/45">{hint}</p> : null}
      </div>

      {spark && spark.length > 1 ? (
        <div className="mt-4">
          <Sparkline data={spark} tone={deltaTone} height={30} label={`${label} trend`} />
        </div>
      ) : null}
    </Surface>
  )
}
