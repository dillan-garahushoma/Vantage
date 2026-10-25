import { cn } from '../../lib/utils';
/** The supplied VALORA Property & Lifestyle Holdings logo for workspace chrome. */
export function Logo({ size = 28, withWordmark = true, className }) {
    if (!withWordmark) return (<span className={cn('flex select-none items-center justify-center', className)}>
      <img
        src="/valora-logo-mark.png"
        alt="VALORA"
        width={size}
        height={size}
        className="object-contain"
        style={{ width: size, height: size }}
      />
    </span>);
    const width = Math.round(size * 3.8);
    return (<span className={cn('flex select-none items-center', className)}>
      <img
        src="/valora-logo.png"
        alt="VALORA"
        width={width}
        height={size}
        className="object-contain object-left"
        style={{ width, height: size }}
      />
    </span>);
}
