import { ArrowRight, Wrench } from 'lucide-react';
import { zar } from '../../lib/format';
import { cn } from '../../lib/utils';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { StatusChip } from './StatusChip';
import { Surface } from './Surface';
/**
 * One priority recommendation.
 *
 * The card is explicit that it is a *recommendation*: it shows the confidence,
 * the rand value at stake and the evidence lines it was drawn from, and every
 * action it offers leads to a human decision (review the finding, or raise the
 * work order) rather than changing anything on its own.
 */
export function RecommendationCard({ recommendation, index = 0, onReview, onAction, canAction = true, className, }) {
    const { id, kind, title, summary, evidence, confidence, confidenceValue, impact, savingsZar } = recommendation;
    return (<Surface className={cn('relative flex flex-col overflow-hidden vl-lift', className)}>
      <span className="absolute inset-y-0 left-0 w-1 bg-brand-soft"/>

      <div className="flex items-start justify-between gap-4 pl-2">
        <Badge variant="default" className="tracking-[0.08em]">
          {kind}
        </Badge>
        <span className="num font-heading text-[1.05rem] font-extrabold text-ink/20">
          {String(index + 1).padStart(2, '0')}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 pl-2">
        <StatusChip status={confidence} size="sm"/>
        {confidenceValue != null ? <span className="num text-[0.7rem] font-semibold text-ink/45">
          {confidenceValue}% confidence
        </span> : null}
        <span className="text-ink/20">·</span>
        <span className="text-[0.7rem] font-medium text-ink/45">{id}</span>
      </div>

      <h3 className="mt-3 pl-2 font-heading text-[1.02rem] leading-snug font-bold text-ink">
        {title}
      </h3>
      <p className="mt-2 pl-2 text-[0.83rem] leading-relaxed text-ink/60">{summary}</p>

      <div className="mt-4 pl-2">
        <p className="text-[0.64rem] font-semibold tracking-[0.14em] text-ink/40 uppercase">
          Evidence
        </p>
        <ul className="mt-2 space-y-1.5">
          {evidence.slice(0, 3).map((item) => (<li key={item.label} className="flex gap-2.5 text-[0.78rem] leading-snug text-ink/60">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-soft"/>
              <span>
                {item.label}
                {item.source ? (<span className="mt-0.5 block text-[0.68rem] text-ink/35">{item.source}</span>) : null}
              </span>
            </li>))}
          {evidence.length > 3 ? (<li className="text-[0.74rem] font-medium text-brand-ink">
              +{evidence.length - 3} more in the review
            </li>) : null}
        </ul>
      </div>

      <div className="mt-4 flex items-start gap-2.5 rounded-xl bg-canvas p-3 pl-3">
        {savingsZar != null ? <span className="num mt-px font-heading text-[0.95rem] font-extrabold text-mint-ink">
          {zar(savingsZar)}
        </span> : null}
        <span className="text-[0.78rem] leading-snug text-ink/60">{impact}</span>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 pt-1">
        <Button variant="outline" onClick={() => onReview(recommendation)} className="h-9 px-4 text-[0.8rem]">
          Review
          <ArrowRight className="h-3.5 w-3.5"/>
        </Button>
        {canAction ? (<Button variant="ink" onClick={() => onAction(recommendation)} className="h-9 px-4 text-[0.8rem]">
            <Wrench className="h-3.5 w-3.5"/>
            {id.startsWith('overdue_work_order-') ? 'View work orders' : 'Create work order'}
          </Button>) : null}
      </div>
    </Surface>);
}
