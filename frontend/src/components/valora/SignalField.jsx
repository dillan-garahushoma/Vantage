import { statusToneClasses } from '../../lib/display';
import { cn } from '../../lib/utils';
/** Deterministic node positions — a radar with no jitter on every render. */
const NODES = [
    { left: '12%', top: '26%', delay: '0s' },
    { left: '34%', top: '68%', delay: '0.6s' },
    { left: '58%', top: '20%', delay: '1.2s' },
    { left: '76%', top: '58%', delay: '1.8s' },
    { left: '46%', top: '44%', delay: '2.4s' },
];
/**
 * The signal field behind the weekly briefing.
 *
 * Concentric rings suggest a sweep and the dots are the estate's telemetry
 * channels; the tile grid, when signals are supplied, is made of *measured*
 * counts the caller fetched. An empty field is decoration and is hidden from
 * assistive technology rather than pretending to be data.
 */
export function SignalField({ signals = [], className, label }) {
    const hasSignals = signals.length > 0;
    return (<div className={cn('relative overflow-hidden rounded-2xl border border-line bg-canvas p-5', className)} aria-hidden={hasSignals ? undefined : true}>
      <div className="pointer-events-none absolute inset-0 opacity-60">
        <div className="absolute top-1/2 left-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 animate-pulse-dot rounded-full border border-brand-soft/40"/>
        <div className="absolute top-1/2 left-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 animate-pulse-dot rounded-full border border-brand-soft/30 [animation-delay:0.9s]"/>
        <div className="absolute top-1/2 left-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 animate-pulse-dot rounded-full border border-brand-soft/20 [animation-delay:1.8s]"/>
        {NODES.map((node) => (<span key={`${node.left}-${node.top}`} style={{ left: node.left, top: node.top, animationDelay: node.delay }} className="absolute h-1.5 w-1.5 animate-pulse-dot rounded-full bg-brand"/>))}
      </div>

      {hasSignals ? (<>
          <p className="sr-only">{label ?? 'Live estate telemetry'}</p>
          <div className="relative grid min-h-[200px] grid-cols-1 gap-3 sm:grid-cols-3">
            {signals.map((signal, index) => (<div key={signal.id} className={cn('flex min-h-[84px] flex-col justify-between gap-2 rounded-2xl border border-line bg-surface/90 p-3.5 text-left shadow-soft backdrop-blur', index % 3 === 1 && 'sm:translate-y-5')}>
                <div className="flex items-start justify-between gap-3">
                  <span className="text-[0.74rem] leading-snug font-semibold text-ink/60">
                    {signal.label}
                  </span>
                  <span className={cn('mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full', statusToneClasses[signal.tone].dot)}/>
                </div>
                <div>
                  <p className="num font-heading text-[1.25rem] leading-none font-extrabold text-ink">
                    {signal.value}
                  </p>
                  {signal.source ? (<p className="mt-1 text-[0.66rem] text-ink/40">{signal.source}</p>) : null}
                </div>
              </div>))}
          </div>
        </>) : null}
    </div>);
}
