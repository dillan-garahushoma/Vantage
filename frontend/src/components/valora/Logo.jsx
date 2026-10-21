import { cn } from '../../lib/utils';
/** The VALORA mark: two strokes that meet at a point, violet signal dot. */
export function Logo({ size = 28, tone = 'ink', withWordmark = true, className }) {
    const stroke = tone === 'light' ? '#FFFFFF' : '#1F1733';
    return (<span className={cn('flex select-none items-center gap-2.5', className)}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="shrink-0">
        <path d="M5 7 L13.6 25" stroke={stroke} strokeWidth="2.5" strokeLinecap="round"/>
        <path d="M27 7 L22.3 16.7 L20.4 13.2 L17.8 25" stroke="#7C3AED" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="15.8" cy="26" r="2.1" fill="#A78BFA"/>
      </svg>
      {withWordmark ? (<span className={cn('font-heading text-[1.02rem] leading-none font-extrabold tracking-[0.2em]', tone === 'light' ? 'text-white' : 'text-ink')}>
          VALORA
        </span>) : null}
    </span>);
}
