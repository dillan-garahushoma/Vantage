import { cn } from '../../lib/utils';
/** A section head: violet eyebrow, display-face title, muted description. */
export function SectionHeading({ eyebrow, title, description, action, className, }) {
    return (<div className={cn('flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between', className)}>
      <div className="min-w-0">
        {eyebrow ? (<p className="mb-2 text-[0.68rem] font-bold tracking-[0.16em] text-brand-ink uppercase">
            {eyebrow}
          </p>) : null}
        <h2 className="font-heading text-[1.35rem] font-extrabold tracking-[-0.025em] text-ink sm:text-[1.55rem]">
          {title}
        </h2>
        {description ? (<p className="mt-1.5 max-w-2xl text-[0.88rem] leading-relaxed text-ink/55">{description}</p>) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>);
}
