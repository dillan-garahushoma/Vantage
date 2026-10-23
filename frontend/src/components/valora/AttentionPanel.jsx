import { ArrowRight } from 'lucide-react';
import { StatusChip } from './StatusChip';
import { Surface } from './Surface';
import { cn } from '../../lib/utils';
export function AttentionPanel({ items, onSelect, className }) {
    return (<Surface className={cn('flex flex-col', className)} padded={false}>
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4 sm:px-6">
        <div>
          <h3 className="font-heading text-[1rem] font-bold text-ink">Needs attention</h3>
          <p className="mt-0.5 text-[0.78rem] text-ink-muted">Ordered by urgency and cost exposure</p>
        </div>
        <span className="num rounded-xs bg-ochre-wash px-2.5 py-1 text-[0.7rem] font-bold text-ochre">
          {items.length}
        </span>
      </div>

      {items.length === 0 ? (<div className="px-5 py-8 text-center text-[0.82rem] text-ink-muted sm:px-6">
          No immediate attention items on record.
        </div>) : (<ul className="divide-y divide-line">
          {items.map((item) => (<li key={item.id}>
              <button type="button" onClick={() => onSelect?.(item)} className="group flex w-full flex-col gap-2.5 px-5 py-4 text-left transition-colors duration-200 hover:bg-canvas/80 sm:px-6">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[0.88rem] font-semibold leading-snug text-ink">{item.title}</p>
                  <StatusChip status={item.urgency} size="sm"/>
                </div>
                <p className="text-[0.79rem] leading-relaxed text-ink/60">{item.detail}</p>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.72rem] font-medium text-ink-muted">
                  <span>{item.area}</span>
                  <span className="h-1 w-1 rounded-full bg-line"/>
                  <span>{item.eta}</span>
                  <span className="h-1 w-1 rounded-full bg-line"/>
                  <span className="text-ink/70">{item.impact}</span>
                </div>
                <span className="mt-0.5 inline-flex items-center gap-1 text-[0.75rem] font-semibold text-brand opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                  Review signal <ArrowRight className="h-3 w-3"/>
                </span>
              </button>
            </li>))}
        </ul>)}
    </Surface>);
}
export default AttentionPanel;
