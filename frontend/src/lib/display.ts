/**
 * Presentation metadata only.
 *
 * Nothing here computes a score: score *bands* describe how a score the backend
 * published should be painted and labelled. The Living Score maths lives in the
 * backend service and must never be re-implemented in React.
 */

export type Tone = 'neutral' | 'progress' | 'good' | 'warn' | 'alert'

export interface ChipMeta {
  label: string
  tone: Tone
  /** Every chip carries a glyph so status never depends on colour alone. */
  glyph: string
}

export const complaintStatus: Record<string, ChipMeta> = {
  submitted: { label: 'Logged', tone: 'neutral', glyph: '○' },
  reviewed: { label: 'Under review', tone: 'progress', glyph: '◐' },
  assigned: { label: 'Assigned', tone: 'progress', glyph: '◑' },
  in_progress: { label: 'In progress', tone: 'progress', glyph: '◕' },
  resolved: { label: 'Resolved', tone: 'good', glyph: '●' },
  rated: { label: 'Rated', tone: 'good', glyph: '✓' },
  closed: { label: 'Closed', tone: 'good', glyph: '✓' },
}

export const workOrderStatus: Record<string, ChipMeta> = {
  assigned: { label: 'Assigned', tone: 'progress', glyph: '◑' },
  in_progress: { label: 'In progress', tone: 'progress', glyph: '◕' },
  completed: { label: 'Completed', tone: 'good', glyph: '●' },
  cancelled: { label: 'Cancelled', tone: 'neutral', glyph: '×' },
}

/**
 * Priority chips carry colour and a glyph; the label is `displayLabel(value)`.
 * The values themselves come from the contract (`complaintPriorities`), and a
 * test fails if this map stops covering every published priority.
 */
export interface PriorityMeta {
  tone: Tone
  glyph: string
}

export const priorityMeta: Record<string, PriorityMeta> = {
  low: { tone: 'neutral', glyph: '↓' },
  normal: { tone: 'neutral', glyph: '·' },
  high: { tone: 'warn', glyph: '↑' },
  urgent: { tone: 'alert', glyph: '!!' },
}

/** The complaint lifecycle, in order, for the timeline rail. */
export const complaintLifecycle = [
  'submitted',
  'reviewed',
  'assigned',
  'in_progress',
  'resolved',
  'rated',
] as const

// `complaintCategories` used to live here as a hand-copied list. It had already
// drifted (it offered `plumbing`, `drainage`, `roads`, `garden` and `general`,
// none of which the API accepts) and is now generated from the contract:
// see `src/api/generated/enums.ts` (`npm run gen:api`).

/**
 * Trade filter for the provider directory.
 *
 * NOT generated, and deliberately so: the backend publishes no provider-trade
 * vocabulary — `ServiceProviderResponse.trade` is a free string (the column is
 * `String(50)` and the query filter accepts any string), so there is nothing to
 * derive this from. It stays a UI list until the contract publishes one.
 */
export const trades = [
  'plumbing',
  'electrical',
  'security',
  'garden',
  'cleaning',
  'building',
] as const

export interface ScoreBand {
  key: 'high' | 'mid' | 'low'
  label: string
  barClass: string
  textClass: string
  chipClass: string
}

/** Display bands for a backend-provided Living Score (0–100). */
export function scoreBand(score: number): ScoreBand {
  if (score >= 75) {
    return {
      key: 'high',
      label: 'Healthy',
      barClass: 'bg-accent',
      textClass: 'text-accent-ink',
      chipClass: 'bg-accent-wash text-accent-ink',
    }
  }
  if (score >= 50) {
    return {
      key: 'mid',
      label: 'Watch',
      barClass: 'bg-ochre',
      textClass: 'text-ochre-ink',
      chipClass: 'bg-ochre-wash text-ochre-ink',
    }
  }
  return {
    key: 'low',
    label: 'At risk',
    barClass: 'bg-brick',
    textClass: 'text-brick-ink',
    chipClass: 'bg-brick-wash text-brick-ink',
  }
}

/**
 * The tone vocabulary the filled status pills use.
 *
 * `Tone` above describes how the hairlines and chips of the older screens are
 * painted; this is the same idea for the intelligence surfaces, expressed as the
 * five families the palette actually has: mint (healthy), amber (watch), rose
 * (risk), violet (in progress / informational) and grey (no state yet).
 *
 * Look-up is case-insensitive and tolerant of the shape the *backend* uses
 * (`in_progress`) as well as the shape a card shows (`In progress`), because
 * both reach this function.
 */
export type StatusTone = 'positive' | 'attention' | 'critical' | 'brand' | 'neutral'

export const statusToneClasses: Record<StatusTone, { pill: string; dot: string }> = {
  positive: { pill: 'bg-mint-wash text-mint-ink', dot: 'bg-mint' },
  attention: { pill: 'bg-ochre-wash text-ochre-ink', dot: 'bg-ochre' },
  critical: { pill: 'bg-signal-wash text-signal-ink', dot: 'bg-signal' },
  brand: { pill: 'bg-brand-wash text-brand-ink', dot: 'bg-brand' },
  neutral: { pill: 'bg-ink/5 text-ink-muted', dot: 'bg-ink/30' },
}

const STATUS_TONES: Record<string, StatusTone> = {
  // healthy / done
  healthy: 'positive',
  'on track': 'positive',
  operational: 'positive',
  complete: 'positive',
  completed: 'positive',
  resolved: 'positive',
  rated: 'positive',
  'within sla': 'positive',
  confirmed: 'positive',
  preferred: 'positive',
  approved: 'positive',
  sent: 'positive',
  active: 'positive',
  // watch
  watch: 'attention',
  attention: 'attention',
  open: 'attention',
  pending: 'attention',
  'under investigation': 'attention',
  investigating: 'attention',
  medium: 'attention',
  'awaiting approval': 'attention',
  'awaiting sign-off': 'attention',
  'at risk': 'critical',
  // risk
  critical: 'critical',
  urgent: 'critical',
  high: 'critical',
  overdue: 'critical',
  escalated: 'critical',
  breached: 'critical',
  declined: 'critical',
  failed: 'critical',
  // in flight / informational
  scheduled: 'brand',
  triaged: 'brand',
  'in progress': 'brand',
  'in review': 'brand',
  good: 'brand',
  // nothing recorded yet
  received: 'neutral',
  planned: 'neutral',
  draft: 'neutral',
  low: 'neutral',
  inactive: 'neutral',
  neutral: 'neutral',
}

/** The tone for a status word, from either the backend or the screen. */
export function statusTone(status: string | null | undefined): StatusTone {
  if (!status) return 'neutral'
  const key = status.replace(/[_-]+/g, ' ').trim().toLowerCase()
  return STATUS_TONES[key] ?? 'neutral'
}

/**
 * How a Living Score *band* is painted and labelled.
 *
 * The thresholds describe the number the backend published; nothing here
 * calculates one. 85+ is healthy, 75+ warrants a watch, 65+ is at risk, and
 * below that the estate is critical.
 */
export function pillarBand(score: number): { tone: StatusTone; label: string } {
  if (score >= 85) return { tone: 'positive', label: 'Healthy' }
  if (score >= 75) return { tone: 'attention', label: 'Watch' }
  if (score >= 65) return { tone: 'critical', label: 'At risk' }
  return { tone: 'critical', label: 'Critical' }
}

/** Plain-language role names for the UI. */
export const roleLabels: Record<string, string> = {
  casual_visitor: 'Visitor',
  resident: 'Resident',
  investor: 'Investor',
  estate_agent: 'Estate agent',
  hoa_admin: 'HOA administrator',
  service_provider: 'Service provider',
}
