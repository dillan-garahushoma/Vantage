import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Sparkline } from './Sparkline';
import { StatusChip } from './StatusChip';
import { Surface } from './Surface';
/**
 * The headline number card.
 *
 * It presents a figure the backend already calculated — the caller passes the
 * formatted string, so React never rounds, weights or interpolates anything. When
 * the estate has no publishable score the card refuses to show a number and says
 * “not enough data yet”, which is the honest state, not a zero.
 */
export function ScoreCard({ value, label = 'Living Score', status, change, period = 'vs. previous snapshot', description, spark, action, empty = false, emptyLabel = 'Not enough data yet', className, }) {
    const direction = change === undefined ? 'flat' : change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
    const TrendIcon = direction === 'up' ? ArrowUpRight : direction === 'down' ? ArrowDownRight : Minus;
    return (<Surface className={cn('relative overflow-hidden', className)}>
      <div className="pointer-events-none absolute -top-10 -right-10 h-40 w-40 rounded-full bg-canvas"/>
      <div className="relative">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink/45 uppercase">
              {label}
            </p>
            {empty ? (<p className="num mt-3 font-heading text-[2.1rem] leading-none font-extrabold tracking-[-0.03em] text-ink-muted">
                ——
                <span className="ml-1 text-[1.1rem] font-bold text-ink/25">/100</span>
              </p>) : (<p className="num mt-3 font-heading text-[3.2rem] leading-none font-extrabold tracking-[-0.04em] text-ink">
                {value}
                <span className="ml-1 text-[1.25rem] font-bold text-ink/30">/100</span>
              </p>)}
          </div>
          <StatusChip status={empty ? emptyLabel : (status ?? '')}/>
        </div>

        {!empty && change !== undefined ? (<div className={cn('mt-4 inline-flex items-center gap-1.5 text-[0.78rem] font-bold', direction === 'down'
                ? 'text-signal-ink'
                : direction === 'up'
                    ? 'text-mint-ink'
                    : 'text-ink-muted')}>
            <TrendIcon className="h-4 w-4"/>
            {change > 0 ? '+' : ''}
            {change} points
            <span className="ml-1 font-medium text-ink/40">{period}</span>
          </div>) : null}

        {!empty && spark && spark.length > 1 ? (<div className="mt-4">
            <Sparkline data={spark} tone={direction === 'down' ? 'critical' : 'brand'} height={34} label="Living Score trajectory"/>
          </div>) : (<div className="mt-5 h-2 overflow-hidden rounded-full bg-line-soft">
            <div className={cn('h-full rounded-full transition-[width] duration-500 ease-soft', empty ? 'bg-ink/10' : 'bg-gradient-to-r from-brand-soft to-brand')} style={{ width: empty ? '100%' : `${Math.max(0, Math.min(100, Number(value) || 0))}%` }}/>
          </div>)}

        {description ? (<p className="mt-4 text-[0.83rem] leading-relaxed text-ink/55">{description}</p>) : null}

        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </Surface>);
}
