import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { StatusChip } from './StatusChip'
import { Surface } from './Surface'
import { cn } from '../../lib/utils'

export interface ProviderItem {
  id?: string | number
  name: string
  category: string
  status: string
  sla: number // percentage e.g. 94
  costVariance: number // percentage e.g. -2.1 or 4.5
  feedback: number // e.g. 4.6
  trend?: number
}

export interface ProviderScorecardProps {
  provider: ProviderItem
  onClick?: () => void
  className?: string
}

function ScoreBar({ value }: { value: number }) {
  const tone = value >= 90 ? '#2F9E73' : value >= 85 ? '#7C3AED' : '#D98A2B'
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-line-soft">
      <div className="h-full rounded-full" style={{ width: `${Math.min(value, 100)}%`, backgroundColor: tone }} />
    </div>
  )
}

export function ProviderScorecard({ provider, onClick, className }: ProviderScorecardProps) {
  const TrendIcon =
    (provider.trend ?? 0) > 0 ? ArrowUpRight : (provider.trend ?? 0) < 0 ? ArrowDownRight : Minus

  return (
    <Surface
      as="article"
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      hover={Boolean(onClick)}
      className={cn('w-full text-left', className)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-heading text-[0.98rem] font-bold text-ink">{provider.name}</p>
          <p className="mt-0.5 text-[0.76rem] text-ink-muted">{provider.category}</p>
        </div>
        <StatusChip status={provider.status} size="sm" />
      </div>

      <div className="mt-5 space-y-3.5">
        <div>
          <div className="flex items-center justify-between text-[0.76rem]">
            <span className="font-medium text-ink/60">SLA achievement</span>
            <span className="num font-bold text-ink">{provider.sla}%</span>
          </div>
          <div className="mt-1.5">
            <ScoreBar value={provider.sla} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[0.7rem] font-semibold tracking-[0.1em] text-ink-muted uppercase">
              Cost variance
            </p>
            <p
              className={cn(
                'num mt-1 flex items-center gap-1 text-[0.86rem] font-bold',
                provider.costVariance > 3
                  ? 'text-ochre'
                  : provider.costVariance < 0
                    ? 'text-mint'
                    : 'text-ink',
              )}
            >
              <TrendIcon className="h-3.5 w-3.5 shrink-0" />
              <span>
                {provider.costVariance > 0 ? '+' : ''}
                {provider.costVariance.toFixed(1)}%
              </span>
            </p>
          </div>
          <div>
            <p className="text-[0.7rem] font-semibold tracking-[0.1em] text-ink-muted uppercase">
              Resident feedback
            </p>
            <p className="num mt-1 text-[0.86rem] font-bold text-ink">
              {provider.feedback.toFixed(1)} / 5
            </p>
          </div>
        </div>
      </div>
    </Surface>
  )
}

export default ProviderScorecard
