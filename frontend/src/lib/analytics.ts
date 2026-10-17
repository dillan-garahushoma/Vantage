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
import type { LivingScoreHistory, LivingScoreSnapshot } from './contract'

/** The estate's latest stored Living Score. 404 when it has never been scored. */
export function getLivingScore(estateId: number): Promise<LivingScoreSnapshot> {
  return api.get<LivingScoreSnapshot>('/api/v1/analytics/living-score', {
    estate_id: estateId,
  })
}

/**
 * The estate's stored snapshots, newest first. Values are returned exactly as the
 * engine wrote them, so a trajectory is a series of published numbers, never a
 * line the browser invented.
 */
export function getLivingScoreHistory(estateId: number, pageSize = 12): Promise<LivingScoreHistory> {
  return api.get<LivingScoreHistory>('/api/v1/analytics/living-score/history', {
    estate_id: estateId,
    page: 1,
    page_size: pageSize,
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
