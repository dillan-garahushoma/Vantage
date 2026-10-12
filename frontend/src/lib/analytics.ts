/**
 * The analytics surface the app reads.
 *
 * One rule, and it is the whole point: **the backend calculates, React displays.**
 * Nothing here derives, re-weights, averages or interpolates a score. The endpoint
 * returns a stored snapshot exactly as the engine wrote it, including a `null`
 * overall score when the estate was too little measurable to justify one — and a
 * `null` is shown as "not enough data yet", never as a zero.
 *
 * `estate_id` is a scope selector, not proof of access: the server resolves the
 * caller's membership and answers 403/404 from that.
 */
import { api } from './api'
import type { LivingScoreSnapshot } from './contract'

/** The estate's latest stored Living Score. 404 when it has never been scored. */
export function getLivingScore(estateId: number): Promise<LivingScoreSnapshot> {
  return api.get<LivingScoreSnapshot>('/api/v1/analytics/living-score', {
    estate_id: estateId,
  })
}

/** Calculate and append a new snapshot. An HOA admin of that estate only. */
export function recalculateLivingScore(estateId: number): Promise<LivingScoreSnapshot> {
  return api.post<LivingScoreSnapshot>(
    '/api/v1/analytics/living-score/recalculate',
    {},
    { estate_id: estateId },
  )
}
