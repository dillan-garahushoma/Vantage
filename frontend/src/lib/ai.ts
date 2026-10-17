/**
 * Typed calls for the two AI surfaces (BATCH AI-5).
 *
 * Presentation only: nothing here computes a score, infers a category, or
 * invents a label. Request and response shapes come from the generated contract
 * (`src/api/generated/schema.d.ts`, refreshed with `npm run gen:api`); the
 * vocabularies the override dropdowns need come from
 * `src/api/generated/enums.ts`. Neither is retyped by hand.
 *
 * `estate_id` is a scope selector, never proof of access — the server resolves
 * the caller's membership on every call.
 */
import type { components } from '../api/generated/schema'
import { api, ApiError } from './api'

export type HealthBrief = components['schemas']['HealthBriefResponse']
export type HealthBriefFacts = components['schemas']['BriefFacts']
export type BriefComponent = components['schemas']['BriefComponent']
export type HealthBriefFeedback = components['schemas']['HealthBriefFeedbackResponse']
export type TriageSuggestion = components['schemas']['TriageSuggestionResponse']
export type TriageDecisionRequest = components['schemas']['TriageDecisionRequest']

const BRIEF_PATH = '/api/v1/analytics/health-brief'

/** The stored brief, or the deterministic template when no AI brief exists. */
export function readHealthBrief(estateId: number): Promise<HealthBrief> {
  return api.get<HealthBrief>(BRIEF_PATH, { estate_id: estateId })
}

/**
 * Ask for the AI brief (HOA admin only). Idempotent, and a provider failure is
 * answered as a template brief with `ai_unavailable_reason` set — not an error.
 */
export function generateHealthBrief(estateId: number): Promise<HealthBrief> {
  return api.post<HealthBrief>(BRIEF_PATH, undefined, { estate_id: estateId })
}

export function sendHealthBriefFeedback(
  estateId: number,
  insightId: number,
  payload: { helpful: boolean; comment: string | null },
): Promise<HealthBriefFeedback> {
  return api.post<HealthBriefFeedback>(`${BRIEF_PATH}/${insightId}/feedback`, payload, {
    estate_id: estateId,
  })
}

const suggestionPath = (complaintId: number) =>
  `/api/v1/complaints/${complaintId}/ai-suggestion`

/** The stored suggestion, or 404 when none has been requested. */
export function readTriageSuggestion(
  estateId: number,
  complaintId: number,
): Promise<TriageSuggestion> {
  return api.get<TriageSuggestion>(suggestionPath(complaintId), { estate_id: estateId })
}

/** Ask for the suggestion (HOA admin only). Idempotent: one suggestion per complaint. */
export function requestTriageSuggestion(
  estateId: number,
  complaintId: number,
): Promise<TriageSuggestion> {
  return api.post<TriageSuggestion>(suggestionPath(complaintId), undefined, {
    estate_id: estateId,
  })
}

/** Accept, override or dismiss — once, and never both. */
export function decideTriageSuggestion(
  estateId: number,
  complaintId: number,
  payload: TriageDecisionRequest,
): Promise<TriageSuggestion> {
  return api.post<TriageSuggestion>(`${suggestionPath(complaintId)}/decision`, payload, {
    estate_id: estateId,
  })
}

/**
 * The AI layer being off, out of budget or failing is a normal state, not an
 * incident: the panel says so quietly and the product keeps working.
 */
export function isAiUnavailable(error: ApiError): boolean {
  return error.status === 503 && error.code === 'AI_UNAVAILABLE'
}
