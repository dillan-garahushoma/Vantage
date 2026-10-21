import { ArrowUpRight, CalendarDays, MapPin, UserRound, Wrench } from 'lucide-react';
import { StatusChip } from './StatusChip';
import { Surface } from './Surface';
import { zarShort } from '../../lib/format';
import { cn } from '../../lib/utils';
export function WorkOrderCard({ workOrder, onClick, className, compact = false, }) {
    const order = workOrder;
    return (<Surface as="article" role={onClick ? 'button' : undefined} tabIndex={onClick ? 0 : undefined} onClick={onClick} hover={Boolean(onClick)} className={cn('w-full text-left', compact && 'p-4', className)}>
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-canvas text-brand">
          <Wrench className="h-4 w-4"/>
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="num text-[0.7rem] font-bold text-ink-muted">
              {order.reference ?? `#${order.id}`}
            </span>
            <StatusChip status={order.status} size="sm"/>
          </div>
          <h3 className="mt-2 line-clamp-2 font-heading text-[0.92rem] font-bold leading-snug text-ink">
            {order.title}
          </h3>
          {!compact && order.description && (<p className="mt-1.5 line-clamp-2 text-[0.8rem] leading-relaxed text-ink/60">
              {order.description}
            </p>)}
        </div>
        {onClick && <ArrowUpRight className="mt-1 h-4 w-4 shrink-0 text-ink/30"/>}
      </div>

      <div className={cn('mt-4 grid gap-2 border-t border-line-soft pt-3.5', compact ? 'grid-cols-2' : 'grid-cols-2 sm:grid-cols-4')}>
        {order.location && (<div className="flex min-w-0 items-center gap-1.5 text-[0.74rem] text-ink/60">
            <MapPin className="h-3.5 w-3.5 shrink-0 text-ink/35"/>
            <span className="truncate">{order.location}</span>
          </div>)}
        {order.provider && (<div className="flex min-w-0 items-center gap-1.5 text-[0.74rem] text-ink/60">
            <UserRound className="h-3.5 w-3.5 shrink-0 text-ink/35"/>
            <span className="truncate">{order.provider}</span>
          </div>)}
        {order.dueDate && (<div className="flex items-center gap-1.5 text-[0.74rem] text-ink/60">
            <CalendarDays className="h-3.5 w-3.5 shrink-0 text-ink/35"/>
            <span>{order.dueDate}</span>
          </div>)}
        {order.cost != null && (<div className="num text-[0.74rem] font-semibold text-ink/75">
            {typeof order.cost === 'number' ? zarShort(order.cost) : order.cost}
          </div>)}
      </div>
    </Surface>);
}
export default WorkOrderCard;
