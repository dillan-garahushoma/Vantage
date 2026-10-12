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

/** Plain-language role names for the UI. */
export const roleLabels: Record<string, string> = {
  casual_visitor: 'Visitor',
  resident: 'Resident',
  investor: 'Investor',
  estate_agent: 'Estate agent',
  hoa_admin: 'HOA administrator',
  service_provider: 'Service provider',
}
