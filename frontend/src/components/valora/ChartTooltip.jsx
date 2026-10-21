import { cn } from '../../lib/utils';
export function ChartTooltip({ active, payload, label, formatter, labelPrefix = '', }) {
    if (!active || !payload?.length)
        return null;
    return (<div className="min-w-[150px] rounded-xl border border-line bg-surface/95 px-3.5 py-3 shadow-lift backdrop-blur">
      {label !== undefined && (<p className="text-[0.68rem] font-semibold tracking-[0.14em] text-ink-muted uppercase">
          {labelPrefix}
          {label}
        </p>)}
      <div className="mt-2 space-y-1.5">
        {payload.map((entry, idx) => (<div key={entry.dataKey ?? entry.name ?? idx} className="flex items-center justify-between gap-5">
            <span className="flex items-center gap-2 text-[0.78rem] text-ink/70">
              <span className={cn('h-2 w-2 rounded-full')} style={{ backgroundColor: entry.color || entry.payload?.fill || '#7C3AED' }}/>
              {entry.name}
            </span>
            <span className="num text-[0.78rem] font-bold text-ink">
              {formatter ? formatter(entry.value, entry) : entry.value}
            </span>
          </div>))}
      </div>
    </div>);
}
export default ChartTooltip;
