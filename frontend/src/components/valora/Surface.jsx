import { cn } from '../../lib/utils';
/**
 * The panel everything operational sits on: white, lavender hairline, soft
 * shadow, 2xl radius. Cards, drawers and the Intelligence briefing hero all use
 * it, so the product has exactly one surface treatment.
 */
export function Surface({ as = 'div', hover = false, padded = true, className, children, ...rest }) {
    // `as` is a short list of block-level tags, all of which take the same props;
    // the cast keeps one surface API instead of one component per tag.
    const Tag = as;
    return (<Tag className={cn('rounded-2xl border border-line bg-surface shadow-soft', padded && 'p-5', hover &&
            'vl-lift transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-soft/60 hover:shadow-card', className)} {...rest}>
      {children}
    </Tag>);
}
