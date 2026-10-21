import { CircleCheck, CircleDot, Clock3 } from 'lucide-react';
import { cn } from '../../lib/utils';
export function Timeline({ items = [], className }) {
    return (<ol className={cn('space-y-0', className)}>
      {items.map((item, index) => {
            const isDone = item.status === 'complete' || item.status === 'completed' || item.done;
            const isCurrent = item.status === 'current' || item.current;
            const Icon = isDone ? CircleCheck : isCurrent ? CircleDot : Clock3;
            return (<li key={item.id ?? `${item.title}-${index}`} className="relative flex gap-3.5 pb-6 last:pb-0">
            {index < items.length - 1 && (<span className={cn('absolute bottom-0 left-[11px] top-6 w-px', isDone ? 'bg-mint/40' : 'bg-line')}/>)}
            <span className={cn('relative z-[1] mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full', isDone
                    ? 'bg-mint-wash text-mint'
                    : isCurrent
                        ? 'bg-brand-wash text-brand'
                        : 'bg-canvas text-ink/35')}>
              <Icon className="h-3.5 w-3.5"/>
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <p className={cn('text-[0.85rem] font-semibold', isDone || isCurrent ? 'text-ink' : 'text-ink/50')}>
                  {item.title}
                </p>
                {item.date && (<time className="text-[0.7rem] font-medium text-ink-muted">{item.date}</time>)}
              </div>
              {item.description && (<p className="mt-1 text-[0.78rem] leading-relaxed text-ink/60">
                  {item.description}
                </p>)}
              {item.meta && (<p className="mt-1.5 text-[0.7rem] font-medium text-brand">{item.meta}</p>)}
            </div>
          </li>);
        })}
    </ol>);
}
export default Timeline;
