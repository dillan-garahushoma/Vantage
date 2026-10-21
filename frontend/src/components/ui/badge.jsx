import { cva } from 'class-variance-authority';
import { cn } from '../../lib/utils';
/**
 * A small, filled label. Colour is never the only carrier of meaning in VALORA —
 * every badge in the product pairs its tone with words (see `StatusChip`), so
 * these tones are supporting weight, not the message.
 */
export const badgeVariants = cva('inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.7rem] font-semibold leading-none', {
    variants: {
        variant: {
            default: 'bg-brand-wash text-brand-ink',
            brand: 'bg-brand text-white',
            secondary: 'bg-canvas text-ink-soft',
            outline: 'border border-line bg-surface text-ink-soft',
            positive: 'bg-mint-wash text-mint-ink',
            attention: 'bg-ochre-wash text-ochre-ink',
            risk: 'bg-signal-wash text-signal-ink',
            ink: 'bg-ink text-white',
        },
    },
    defaultVariants: { variant: 'default' },
});
export function Badge({ className, variant, ...rest }) {
    return <span className={cn(badgeVariants({ variant }), className)} {...rest}/>;
}
