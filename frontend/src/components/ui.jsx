import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { IconAlert, IconClose } from './Icons';
export function cx(...parts) {
    return parts.filter(Boolean).join(' ');
}
/* ------------------------------------------------------------------ chips */
const toneClasses = {
    neutral: 'bg-ink/5 text-ink-soft',
    progress: 'bg-accent-wash text-accent-ink',
    good: 'bg-accent text-white',
    warn: 'bg-ochre-wash text-ochre-ink',
    alert: 'bg-signal-wash text-signal-ink',
};
export function Chip({ tone = 'neutral', glyph, children, className, }) {
    return (<span className={cx('inline-flex items-center gap-1.5 rounded-xs px-2 py-[3px] text-[11px] font-medium tracking-wide uppercase', toneClasses[tone], className)}>
      {glyph ? (<span aria-hidden="true" className="num text-[11px] leading-none">
          {glyph}
        </span>) : null}
      {children}
    </span>);
}
const buttonVariants = {
    primary: 'bg-accent text-white border-ink hover:bg-accent-ink lift hover:translate-y-[-1px]',
    secondary: 'bg-surface text-ink border-ink/25 hover:border-ink/50 hover:bg-paper',
    ghost: 'bg-transparent text-ink-soft border-transparent hover:bg-ink/5',
    danger: 'bg-signal-ink text-white border-ink hover:bg-brick-ink',
};
const buttonBase = 'inline-flex items-center justify-center gap-2 rounded-xs border px-3.5 py-2 text-sm font-medium transition-[transform,background-color,border-color] duration-150 disabled:cursor-not-allowed disabled:opacity-45';
export function Button({ variant = 'secondary', className, ...rest }) {
    return <button className={cx(buttonBase, buttonVariants[variant], className)} {...rest}/>;
}
export function LinkButton({ to, variant = 'secondary', className, children, }) {
    return (<Link to={to} className={cx(buttonBase, buttonVariants[variant], className)}>
      {children}
    </Link>);
}
/* ----------------------------------------------------------- containers */
export function Card({ children, className, as: Tag = 'div', }) {
    return <Tag className={cx('hairline rounded-xs bg-surface', className)}>{children}</Tag>;
}
export function SectionTitle({ title, hint, action, }) {
    return (<div className="mb-3 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
        {hint ? <p className="mt-0.5 text-[13px] text-ink-muted">{hint}</p> : null}
      </div>
      {action}
    </div>);
}
export function StatTile({ label, value, unit, hint, tone = 'neutral', }) {
    const accent = {
        neutral: 'text-ink',
        progress: 'text-accent-ink',
        good: 'text-accent-ink',
        warn: 'text-ochre-ink',
        alert: 'text-signal-ink',
    };
    return (<Card className="p-4">
      <div className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">{label}</div>
      <div className={cx('num mt-2 text-[26px] leading-none font-semibold', accent[tone])}>
        {value}
        {unit ? <span className="ml-1 text-[13px] font-normal text-ink-muted">{unit}</span> : null}
      </div>
      {hint ? <div className="mt-2 text-[12px] text-ink-muted">{hint}</div> : null}
    </Card>);
}
/** A labelled horizontal measure. Colour is always paired with a label. */
export function Meter({ label, value, max = 100, barClass = 'bg-accent', caption, }) {
    const pct = max <= 0 ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
    return (<div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[13px] text-ink-soft">{label}</span>
        <span className="num text-[13px] font-medium">{caption ?? `${Math.round(value)}`}</span>
      </div>
      <div className="mt-1.5 h-1.5 w-full bg-ink/10" role="meter" aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={max} aria-label={label}>
        <div className={cx('h-full', barClass)} style={{ width: `${pct}%` }}/>
      </div>
    </div>);
}
/* ---------------------------------------------------------------- forms */
export function Field({ label, hint, error, children, }) {
    return (<label className="block">
      <span className="mb-1.5 block text-[12px] font-medium tracking-wide text-ink-soft uppercase">
        {label}
      </span>
      {children}
      {error ? (<span className="mt-1 block text-[12px] text-signal-ink">{error}</span>) : hint ? (<span className="mt-1 block text-[12px] text-ink-muted">{hint}</span>) : null}
    </label>);
}
const controlClass = 'w-full rounded-xs border border-ink/20 bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted/70 focus:border-accent focus:outline-none';
export function Input({ className, ...rest }) {
    return <input className={cx(controlClass, className)} {...rest}/>;
}
// `ComponentPropsWithRef` so a caller can move focus into a revealed control
// (React 19 passes `ref` through as an ordinary prop).
export function Select({ className, children, ...rest }) {
    return (<select className={cx(controlClass, 'appearance-none', className)} {...rest}>
      {children}
    </select>);
}
export function Textarea({ className, ...rest }) {
    return <textarea className={cx(controlClass, 'min-h-28 resize-y', className)} {...rest}/>;
}
/* --------------------------------------------------------------- states */
export function LoadingState({ label = 'Loading' }) {
    return (<div className="flex items-center gap-3 py-10 text-ink-muted">
      <span className="inline-block h-3 w-3 animate-pulse bg-accent" aria-hidden="true"/>
      <span className="text-[13px]">{label}…</span>
    </div>);
}
/**
 * A reserved, muted shape standing in for content that has not arrived.
 *
 * Deliberately silent: it is `aria-hidden`, and the region that owns it carries
 * `aria-busy` plus a visually hidden polite status. A skeleton mirrors the
 * geometry of what replaces it, so the page does not jump when data lands, and
 * the pulse is removed globally under `prefers-reduced-motion` (see index.css).
 */
export function Skeleton({ className }) {
    return <div aria-hidden="true" className={cx('animate-pulse bg-ink/10', className)}/>;
}
/** A paragraph-shaped skeleton: full lines, with a shorter last line. */
export function SkeletonText({ lines = 3, className }) {
    return (<div aria-hidden="true" className={cx('space-y-2', className)}>
      {Array.from({ length: lines }, (_, index) => (<div key={index} className={cx('h-3 animate-pulse bg-ink/10', index === lines - 1 ? 'w-2/3' : 'w-full')}/>))}
    </div>);
}
export function EmptyState({ title, body, action, }) {
    return (<div className="hairline rounded-xs bg-surface px-6 py-10 text-center">
      <p className="text-[15px] font-medium">{title}</p>
      {body ? <p className="mx-auto mt-1.5 max-w-md text-[13px] text-ink-muted">{body}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>);
}
export function ErrorState({ title = 'That request was rejected', message, requestId, action, }) {
    return (<div className="hairline rounded-xs border-l-2 border-l-signal bg-signal-wash px-4 py-3.5">
      <div className="flex items-start gap-2.5">
        <IconAlert size={18} className="mt-0.5 shrink-0 text-signal-ink"/>
        <div className="min-w-0">
          <p className="text-[14px] font-medium text-signal-ink">{title}</p>
          <p className="mt-1 text-[13px] text-ink-soft">{message}</p>
          {requestId ? (<p className="num mt-1.5 text-[11px] text-ink-muted">ref {requestId}</p>) : null}
          {action ? <div className="mt-3">{action}</div> : null}
        </div>
      </div>
    </div>);
}
/* --------------------------------------------------------------- drawer */
export function Drawer({ open, onClose, title, subtitle, children, footer, }) {
    useEffect(() => {
        if (!open)
            return;
        const onKey = (event) => {
            if (event.key === 'Escape')
                onClose();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [open, onClose]);
    if (!open)
        return null;
    return (<div className="fixed inset-0 z-40 flex justify-end">
      <button type="button" aria-label="Close panel" onClick={onClose} className="absolute inset-0 cursor-default bg-ink/25"/>
      <aside role="dialog" aria-modal="true" aria-label={title} className="rise relative flex h-full w-full max-w-xl flex-col border-l border-ink/20 bg-paper shadow-[-4px_0_0_0_rgba(20,24,28,0.08)]">
        <header className="flex items-start justify-between gap-4 border-b border-ink/15 bg-surface px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-[16px] font-semibold">{title}</h2>
            {subtitle ? (<p className="num mt-0.5 truncate text-[12px] text-ink-muted">{subtitle}</p>) : null}
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-xs border border-transparent p-1.5 text-ink-muted hover:border-ink/20 hover:bg-paper">
            <IconClose size={18}/>
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer ? (<footer className="border-t border-ink/15 bg-surface px-5 py-3">{footer}</footer>) : null}
      </aside>
    </div>);
}
/* ----------------------------------------------------------------- table */
export function TableShell({ children, className }) {
    return (<div className={cx('hairline overflow-x-auto rounded-xs bg-surface', className)}>
      <table className="w-full border-collapse text-left text-[13px]">{children}</table>
    </div>);
}
export function Th({ children, className }) {
    return (<th scope="col" className={cx('border-b border-ink/15 bg-paper px-3.5 py-2.5 text-[11px] font-medium tracking-wider text-ink-muted uppercase', className)}>
      {children}
    </th>);
}
export function Td({ children, className }) {
    return <td className={cx('border-b border-ink/8 px-3.5 py-3 align-top', className)}>{children}</td>;
}
