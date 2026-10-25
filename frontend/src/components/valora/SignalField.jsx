import { statusToneClasses } from '../../lib/display';
import { cn } from '../../lib/utils';

export function SignalField({ signals = [], className, label = 'Measured estate signals' }) {
  if (signals.length === 0) return null;

  return (
    <section className={cn('rounded-xl bg-surface p-4 sm:p-5', className)} aria-labelledby="signal-field-title">
      <h2 id="signal-field-title" className="font-heading text-sm font-semibold text-ink">
        {label}
      </h2>
      <dl className="mt-3 divide-y divide-line-soft">
        {signals.map((signal) => (
          <div key={signal.id} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
            <dt className="min-w-0">
              <span className="flex items-center gap-2 text-sm font-medium text-ink">
                <span
                  className={cn('h-2 w-2 shrink-0 rounded-full', statusToneClasses[signal.tone].dot)}
                  aria-hidden="true"
                />
                {signal.label}
              </span>
              {signal.source ? <span className="mt-1 block pl-4 text-xs text-ink-muted">{signal.source}</span> : null}
            </dt>
            <dd className="num shrink-0 font-heading text-xl font-semibold text-ink">{signal.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
