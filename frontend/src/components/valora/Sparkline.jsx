import { cn } from '../../lib/utils';
const toneStroke = {
    positive: 'text-mint',
    attention: 'text-ochre',
    critical: 'text-signal',
    brand: 'text-brand',
    neutral: 'text-ink-muted',
};
/**
 * A trend line small enough to sit under a metric.
 *
 * Hand-rolled SVG rather than a chart library: it draws a dozen points, it needs
 * no axes or tooltips, and it stays crisp at any width because the viewBox scales
 * with the box. `preserveAspectRatio="none"` is deliberate — the line should use
 * the whole tile, not letterbox inside it.
 */
export function Sparkline({ data, tone = 'brand', height = 32, className, label, }) {
    const points = data.filter((value) => Number.isFinite(value));
    if (points.length < 2)
        return null;
    const min = Math.min(...points);
    const max = Math.max(...points);
    const span = max - min || 1;
    const width = 100;
    const step = width / (points.length - 1);
    const path = points
        .map((value, index) => {
        const x = index * step;
        const y = height - ((value - min) / span) * (height - 6) - 3;
        return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
    })
        .join(' ');
    return (<svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className={cn('h-8 w-full', toneStroke[tone], className)} role="img" aria-label={label ?? `Trend across ${points.length} readings`}>
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke"/>
    </svg>);
}
