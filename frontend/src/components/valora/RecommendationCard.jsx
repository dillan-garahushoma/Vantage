import { ArrowRight, Wrench } from 'lucide-react';
import { Link } from 'react-router-dom';
import { zar } from '../../lib/format';
import { cn } from '../../lib/utils';
import { Button, buttonVariants } from '../ui/button';
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
export function RecommendationCard({ recommendation, onReview, onAction, sourceAction, canAction = true, className, }) {
    const { id, kind, title, summary, evidence, confidence, confidenceValue, impact, savingsZar } = recommendation;
    return (<Surface className={cn('relative flex flex-col overflow-hidden vl-lift', className)}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[0.72rem] font-semibold text-brand-ink">{kind}</span>
        <StatusChip status={confidence} size="sm"/>
        {confidenceValue !== null && confidenceValue !== undefined ? (
          <span className="num text-[0.72rem] font-medium text-ink/55">{confidenceValue}% confidence</span>
        ) : null}
        <span className="num text-[0.72rem] font-medium text-ink/45">{id}</span>
      </div>

      <h3 className="mt-3 font-heading text-[1.02rem] leading-snug font-bold text-ink">
        {title}
      </h3>
      <p className="mt-2 text-[0.83rem] leading-relaxed text-ink/75">{summary}</p>

      {evidence.length > 0 ? (
        <div className="mt-4">
          <p className="text-[0.7rem] font-semibold text-ink/60">Recorded evidence</p>
          <ul className="mt-2 space-y-1.5">
          {evidence.slice(0, 3).map((item) => (<li key={item.label} className="flex gap-2.5 text-[0.78rem] leading-snug text-ink/60">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand"/>
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
      ) : null}

      {impact || savingsZar != null ? (
        <div className="mt-4 flex flex-wrap items-baseline gap-x-2 gap-y-1 rounded-lg bg-canvas px-3 py-2.5">
          {savingsZar != null ? (
            <span className="num font-heading text-[0.95rem] font-bold text-ink">{zar(savingsZar)}</span>
          ) : null}
          {impact ? <span className="text-[0.78rem] leading-snug text-ink/65">{impact}</span> : null}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={() => onReview(recommendation)} className="h-9 px-4 text-[0.8rem]">
          Review
          <ArrowRight className="h-3.5 w-3.5"/>
        </Button>
        {sourceAction ? (
          <Link
            to={sourceAction.to}
            state={sourceAction.state}
            className={buttonVariants({ variant: 'outline', size: 'sm', className: 'h-9 px-4 text-[0.8rem]' })}
          >
            {sourceAction.label}
          </Link>
        ) : null}
        {canAction ? (<Button variant="ink" onClick={() => onAction(recommendation)} className="h-9 px-4 text-[0.8rem]">
            <Wrench className="h-3.5 w-3.5"/>
            Create work order
          </Button>) : null}
      </div>
    </Surface>);
}
