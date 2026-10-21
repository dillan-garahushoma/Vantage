import { cn } from '../../lib/utils';
/** A single-line text control. Lavender hairline, violet focus, soft radius. */
export function Input({ className, type = 'text', ...rest }) {
    return (<input type={type} className={cn('flex h-10 w-full rounded-xl border border-line bg-surface px-3 py-1.5 text-sm text-ink transition-colors duration-200 placeholder:text-ink-muted/70 focus-visible:border-brand-soft focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50', className)} {...rest}/>);
}
