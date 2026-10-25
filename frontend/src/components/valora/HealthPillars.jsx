import { ArrowDownRight, ArrowUpRight, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { pillarBand, statusToneClasses } from '../../lib/display';
import { cn } from '../../lib/utils';
import { StatusChip } from './StatusChip';
/**
 * The five weighted pillars behind a Living Score, from the stored snapshot.
 *
 * Every number here is read from the engine's own response — the bar length is
 * `score`, the percentage is the engine's published `weight`, and a pillar it
 * could not measure says “no evidence yet” rather than rendering as a zero. Each
 * row expands to the explanation and drivers the engine attached to it.
 */
export function HealthPillars({ pillars, expandedDefault = false, showWeights = true, className, }) {
    const [open, setOpen] = useState(expandedDefault ? (pillars[0]?.key ?? null) : null);
    if (pillars.length === 0) {
        return (<p className="py-4 text-[0.85rem] text-ink-muted">
        The engine has published no pillar breakdown for this estate yet.
      </p>);
    }
    return (<div className={cn('divide-y divide-line', className)}>
      {pillars.map((pillar) => {
            const band = pillarBand(pillar.score);
            const measured = pillar.measured ?? true;
            const isOpen = open === pillar.key;
            const expandable = Boolean(pillar.summary || (pillar.drivers?.length ?? 0) > 0);
            const TrendIcon = (pillar.trend ?? 0) >= 0 ? ArrowUpRight : ArrowDownRight;
            return (<div key={pillar.key} className="py-4 first:pt-0 last:pb-0">
            <button type="button" onClick={() => expandable && setOpen(isOpen ? null : pillar.key)} aria-expanded={expandable ? isOpen : undefined} disabled={!expandable} className={cn('group flex w-full items-center gap-4 rounded-xl px-1 py-1.5 text-left transition-colors duration-200', expandable && 'hover:bg-canvas/70')}>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-heading text-[0.95rem] font-bold text-ink">
                    {pillar.name}
                  </span>
                  <StatusChip status={measured ? band.label : 'No evidence yet'} size="sm" className={measured ? undefined : statusToneClasses.neutral.pill}/>
                  {showWeights ? (<span className="text-[0.68rem] font-medium text-ink/35">
                      {Math.round(pillar.weight)}% of score
                    </span>) : null}
                </div>
                <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-line-soft">
                  <div className={cn('h-full rounded-full transition-[width] duration-500 ease-soft', measured ? statusToneClasses[band.tone].dot : 'bg-ink/15')} style={{ width: `${Math.max(0, Math.min(100, pillar.score))}%` }}/>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-3">
                <div className="text-right">
                  <p className="num font-heading text-[1.15rem] leading-none font-extrabold text-ink">
                    {measured ? pillar.score : 'Not scored'}
                  </p>
                  {measured && pillar.trend !== undefined ? (<p className={cn('num mt-1 inline-flex items-center gap-0.5 text-[0.7rem] font-bold', pillar.trend >= 0 ? 'text-mint-ink' : 'text-signal-ink')}>
                      <TrendIcon className="h-3 w-3"/>
                      {pillar.trend > 0 ? '+' : ''}
                      {pillar.trend}
                    </p>) : null}
                </div>
                {expandable ? (<ChevronDown className={cn('h-4 w-4 shrink-0 text-ink/30 transition-transform duration-200', isOpen && 'rotate-180')}/>) : null}
              </div>
            </button>

            {isOpen && expandable ? (<div className="animate-fade-in px-1 pt-3 pb-2">
                {pillar.summary ? (<p className="text-[0.85rem] leading-relaxed text-ink/65">{pillar.summary}</p>) : null}
                {pillar.drivers?.length ? (<ul className="mt-3 space-y-2">
                    {pillar.drivers.map((driver) => (<li key={driver} className="flex gap-2.5 text-[0.82rem] text-ink/55">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-soft"/>
                        {driver}
                      </li>))}
                  </ul>) : null}
              </div>) : null}
          </div>);
        })}
    </div>);
}
