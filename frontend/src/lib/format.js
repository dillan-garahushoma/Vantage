/** Presentation-only formatters. All figures render in tabular mono via `.num`. */
const zarCurrency = new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: 'ZAR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
});
/*
  The intelligence surfaces render rand as `R42,000` — the form the design uses
  for an expected saving. `money()` above keeps the en-ZA spacing convention
  (`R 42 000`) for the records it formats; the two are noted as an open question in
  the batch report rather than silently reconciled here.
*/
const zarPlain = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const zarPrecise = new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: 'ZAR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});
const decimal = new Intl.NumberFormat('en-ZA', { maximumFractionDigits: 1 });
/** R 1 250 000 — rand, no cents, South African group separators. */
export function money(value) {
    if (value === null || value === undefined || value === '')
        return '—';
    const n = typeof value === 'number' ? value : Number(value);
    if (Number.isNaN(n))
        return '—';
    return zarCurrency.format(n);
}
/** `R42000` — a rand figure with no currency symbol, grouped the SA way. */
export function zar(value) {
    return `R${zarPlain.format(Math.round(value))}`;
}
/** `R42k` / `R1.20m` — a rand figure compact enough for a metric tile. */
export function zarShort(value) {
    if (Math.abs(value) >= 1_000_000)
        return `R${(value / 1_000_000).toFixed(2)}m`;
    if (Math.abs(value) >= 1000)
        return `R${Math.round(value / 1000)}k`;
    return `R${Math.round(value)}`;
}
export function moneyPrecise(value) {
    if (value === null || value === undefined || value === '')
        return '—';
    const n = typeof value === 'number' ? value : Number(value);
    if (Number.isNaN(n))
        return '—';
    return zarPrecise.format(n);
}
export function metres(value) {
    if (value === null || value === undefined || value === '')
        return '—';
    const n = typeof value === 'number' ? value : Number(value);
    if (Number.isNaN(n))
        return '—';
    return `${decimal.format(n)} m²`;
}
export function ratio(value, suffix = '') {
    if (value === null || value === undefined || value === '')
        return '—';
    const n = typeof value === 'number' ? value : Number(value);
    if (Number.isNaN(n))
        return '—';
    return `${decimal.format(n)}${suffix}`;
}
const dayMonthYear = new Intl.DateTimeFormat('en-ZA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'Africa/Johannesburg',
});
const dayMonth = new Intl.DateTimeFormat('en-ZA', {
    day: '2-digit',
    month: 'short',
    timeZone: 'Africa/Johannesburg',
});
export function shortDate(value) {
    if (!value)
        return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime()))
        return '—';
    return dayMonth.format(date);
}
export function fullDate(value) {
    if (!value)
        return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime()))
        return '—';
    return dayMonthYear.format(date);
}
/** "3 days ago" / "in 2 days" / "today" — relative to now. */
export function relativeDays(value) {
    if (!value)
        return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime()))
        return '—';
    const diffMs = Date.now() - date.getTime();
    const days = Math.round(Math.abs(diffMs) / 86_400_000);
    const future = diffMs < 0;
    if (days === 0)
        return 'today';
    if (days === 1)
        return future ? 'tomorrow' : 'yesterday';
    if (days < 30)
        return future ? `in ${days} days` : `${days} days ago`;
    const months = Math.round(days / 30);
    return future ? `in ${months} months` : `${months} months ago`;
}
/** Hours to a human resolution duration: 6 h, 2.4 days. */
export function durationHours(hours) {
    if (hours === null || hours === undefined || hours === '')
        return '—';
    const n = typeof hours === 'number' ? hours : Number(hours);
    if (Number.isNaN(n))
        return '—';
    if (n < 24)
        return `${decimal.format(n)} h`;
    return `${decimal.format(n / 24)} days`;
}
export function initials(fullName) {
    return fullName
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() ?? '')
        .join('');
}
export function titleCase(value) {
    return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
/**
 * A published vocabulary value as display text: `general_maintenance` ->
 * `General maintenance`.
 *
 * One formatter for every contract enum, so a value added to the backend is
 * readable in the UI without anyone hand-writing a label. It never drops a
 * value: complaints filed before the vocabulary existed still carry free text
 * (`plumbing`, `roads`), and those are prettified the same way.
 */
export function displayLabel(value) {
    const spaced = value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
    if (!spaced)
        return '—';
    const lower = spaced.toLowerCase();
    return lower.charAt(0).toUpperCase() + lower.slice(1);
}
