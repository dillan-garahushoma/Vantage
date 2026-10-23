import { Link } from 'react-router-dom';
import { cx } from './ui';
/** The VALORA mark: a surveyor's plot with one measured point. */
export function Mark({ size = 28, className }) {
    return (<svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="VALORA" className={className}>
      <rect width="64" height="64" rx="3" className="fill-ink"/>
      <path d="M12 44 L32 12 L52 44" fill="none" stroke="#F6F4EF" strokeWidth="3.5" strokeLinecap="square"/>
      <path d="M20 44 L20 54 M44 44 L44 54 M12 44 L52 44" fill="none" stroke="#F6F4EF" strokeWidth="3.5" strokeLinecap="square"/>
      <rect x="29" y="24" width="6" height="6" className="fill-accent"/>
    </svg>);
}
export function Wordmark({ to = '/', compact = false }) {
    return (<Link to={to} className="flex items-center" aria-label="VALORA home">
      <img
        src="/valora-logo.png"
        alt="VALORA Property & Lifestyle Holdings"
        className={compact ? 'h-9 w-[60px] object-contain object-left' : 'h-11 w-[76px] object-contain object-left sm:h-14 sm:w-[94px]'}
      />
    </Link>);
}
/**
 * A keyline used as a section divider — the survey line motif, drawn once.
 */
export function Keyline({ className }) {
    return (<div className={cx('flex items-center gap-2', className)} aria-hidden="true">
      <span className="h-px flex-1 bg-ink/15"/>
      <span className="h-1.5 w-1.5 rotate-45 bg-accent"/>
      <span className="h-px flex-1 bg-ink/15"/>
    </div>);
}
