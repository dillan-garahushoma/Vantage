/**
 * VALORA Intelligence — the typed contract for the briefing, the priority
 * recommendations and “Ask VALORA”.
 *
 * Two rules this file exists to hold:
 *
 *  1. **A recommendation is not a measured result.** The briefing and the
 *     findings below are the demonstration estate's sample signals, labelled as
 *     such wherever they are rendered. Measured figures — the Living Score, an
 *     incident count, spend — always come from the API. Nothing here is written
 *     back as though an estate had recorded it.
 *  2. **Everything is traceable to a source.** Each finding carries the signals
 *     it was drawn from, and each signal names the record it came from, so a
 *     human can check the claim before acting on it.
 *
 * When `VITE_N8N_INTELLIGENCE_URL` is set the answers come from that service;
 * until then the panel answers from the estate-domain fallback below. Both paths
 * return the same shape, so the UI does not change when the service is connected.
 */

import { api } from './api'

/* ------------------------------------------------------------------ types */

export type RecommendationKind =
  | 'PREVENTIVE MAINTENANCE'
  | 'EMERGING SERVICE RISK'
  | 'BUDGET & PROVIDER OPTIMISATION'

export type Confidence = 'High' | 'Medium' | 'Low'

export interface RecommendationEvidence {
  /** What was observed. */
  label: string
  /** The measured detail behind it. */
  detail: string
  /** The record it came from, so the finding can be checked. */
  source: string
}

export interface WorkOrderDefaults {
  title: string
  asset?: string
  provider?: string
  priority: 'urgent' | 'high' | 'medium' | 'low'
  assetClass?: string
  location?: string
  costZar?: number
  description?: string
}

export interface PriorityRecommendation {
  /** Stable reference shown on the card, e.g. `AI-01`. */
  id: string
  kind: RecommendationKind
  title: string
  summary: string
  evidence: RecommendationEvidence[]
  confidence: Confidence
  /** The model's confidence as a percentage, e.g. 91. */
  confidenceValue: number
  impact: string
  /** Expected saving in rand if the recommendation is acted on. */
  savingsZar: number
  suggestedAction: string
  workOrderDefaults: WorkOrderDefaults
}

export interface WeeklyBriefing {
  headline: string
  body: string
  /** The window the findings were drawn from, in words. */
  windowLabel: string
  signalsReviewed: number
  sources: number
  /** Total avoidable spend across the findings, in rand. */
  avoidableZar: number
}

export interface ValoraAnswer {
  summary: string
  evidence: string[]
  recommendation: string
  related: string[]
}

export interface ValoraAnswerResult extends ValoraAnswer {
  /** Where the answer came from, for the footer disclaimer. */
  source: 'n8n' | 'estate-domain'
}

export interface EstateIntelligenceResponse {
  estateId: number
  estateName: string
  asOf: string
  briefing: WeeklyBriefing
  recommendations: PriorityRecommendation[]
  operationalSignals: {
    openComplaints: number
    workOrdersInFlight: number
    unresolvedIncidents: number
  }
  source: 'n8n' | 'live_llm' | 'sample_baseline'
}

/* ---------------------------------------------- the demonstration briefing */

/**
 * The sample briefing for the seeded estate.
 *
 * Deliberately declared as *sample* data: it is shown as “sample signals” in the
 * interface and is replaced wholesale once the n8n service is configured.
 */
export const weeklyBriefing: WeeklyBriefing = {
  headline: 'Three issues deserve attention this week.',
  body: 'Acting on two of them could prevent an estimated R86,000 in reactive maintenance.',
  windowLabel: 'Rolling 7 days',
  signalsReviewed: 1284,
  sources: 9,
  avoidableZar: 86000,
}

export const priorityRecommendations: PriorityRecommendation[] = [
  {
    id: 'AI-01',
    kind: 'PREVENTIVE MAINTENANCE',
    title: 'Pool Pump 02 bearing will fail before the December season',
    summary:
      'Three overload trips in eleven days on the same pump, with winding temperature climbing after each restart. The bearing is the likely cause and a replacement takes one workshop day; a failure in December would take the pool offline at peak occupancy with an emergency call-out premium.',
    evidence: [
      {
        label: 'Three overload trips on Pool Pump 02',
        detail: 'Trips logged on 4, 9 and 15 October, each clearing after a manual reset.',
        source: 'SCADA relay log · Clubhouse pump plant',
      },
      {
        label: 'Winding temperature rising after restart',
        detail: 'Peak winding temperature moved from 71 °C to 84 °C across the three trips.',
        source: 'Telemetry · Pool Pump 02',
      },
      {
        label: 'Vibration above the pump model’s service band',
        detail: 'Last reading 4.6 mm/s against a 2.8 mm/s service threshold.',
        source: 'Monthly asset inspection · 2 October',
      },
      {
        label: 'Bearing never replaced in the service history',
        detail: 'Six years of records on this asset show servicing but no bearing replacement.',
        source: 'Service history · asset PUMP-002',
      },
    ],
    confidence: 'High',
    confidenceValue: 91,
    impact: 'R42,000 avoided in pump replacement and emergency call-out',
    savingsZar: 42000,
    suggestedAction:
      'Book a bearing replacement on Pool Pump 02 before the December occupancy peak, with the pump isolated on the morning of the visit.',
    workOrderDefaults: {
      title: 'Replace Pool Pump 02 bearing before December season',
      asset: 'Pool Pump 02',
      provider: 'KZN Lift & Pump Services',
      priority: 'high',
      assetClass: 'Pump',
      location: 'Clubhouse · Pool plant',
      costZar: 9800,
      description:
        'Three overload trips in eleven days with winding temperature rising to 84 °C and vibration at 4.6 mm/s. Replace the bearing and re-check alignment before the December occupancy peak.',
    },
  },
  {
    id: 'AI-02',
    kind: 'EMERGING SERVICE RISK',
    title: 'Irrigation pressure loss is wasting 640 kl of water in Block C',
    summary:
      'Block C’s pressure-reducing valve is holding 1.9 bar against a 3.2 bar set point, so the irrigation cycle runs almost twice as long to reach the same moisture. The valve is the cheapest repair in this briefing and the leak it is masking is costing the most water.',
    evidence: [
      {
        label: 'Downstream pressure 1.9 bar against a 3.2 bar set point',
        detail: 'Measured at the Block C riser on every irrigation cycle in the period.',
        source: 'Telemetry · Block C PRV',
      },
      {
        label: 'Irrigation runtime up 71% with no change in set schedule',
        detail: 'Cycle duration moved from 34 to 58 minutes per zone.',
        source: 'Irrigation controller · Block C',
      },
      {
        label: 'Consumption up 640 kl on the same period last year',
        detail: 'Bulk meter difference for Block C, weather-corrected.',
        source: 'Bulk water meter · Block C',
      },
    ],
    confidence: 'High',
    confidenceValue: 84,
    impact: 'R28,000 a year in water and pumping, before any repair',
    savingsZar: 28000,
    suggestedAction:
      'Replace the Block C pressure-reducing valve and re-verify the downstream pressure during the next irrigation cycle.',
    workOrderDefaults: {
      title: 'Replace Block C irrigation pressure-reducing valve',
      asset: 'Block C PRV',
      provider: 'AquaFix Plumbing',
      priority: 'high',
      assetClass: 'Water',
      location: 'Block C · Irrigation riser',
      costZar: 6400,
      description:
        'Downstream pressure is holding 1.9 bar against a 3.2 bar set point; irrigation runtime is up 71% and consumption up 640 kl. Replace the PRV and verify pressure on the next cycle.',
    },
  },
  {
    id: 'AI-03',
    kind: 'BUDGET & PROVIDER OPTIMISATION',
    title: 'Cedar Lane lighting can move to solar LED on a four-year payback',
    summary:
      'Cedar Lane’s 42 pole lights run on mains power at full brightness all night. A solar LED conversion cuts the estate’s lighting account, removes these poles from the municipal outage load and needs no trenching, so it can be done between occupancy cycles.',
    evidence: [
      {
        label: 'Lighting account up 18% year on year',
        detail: 'Cedar Lane lighting circuit cost rose from R71,000 to R84,000.',
        source: 'Financial ledger · utilities',
      },
      {
        label: '42 pole lights running on mains supply',
        detail: 'Every pole on Cedar Lane is on the metered lighting circuit.',
        source: 'Asset register · lighting',
      },
      {
        label: 'Two municipal outages hit the circuit this quarter',
        detail: 'Lighting was out for 6.5 hours in total across both events.',
        source: 'Incident log · utility outages',
      },
    ],
    confidence: 'High',
    confidenceValue: 88,
    impact: 'R16,000 a year saved, with a four-year payback',
    savingsZar: 16000,
    suggestedAction:
      'Request quotations for a solar LED conversion of the 42 Cedar Lane pole lights and schedule the work between occupancy cycles.',
    workOrderDefaults: {
      title: 'Quotation: solar LED conversion for 42 Cedar Lane pole lights',
      asset: 'Cedar Lane street lighting',
      provider: 'BrightSpark Electrical',
      priority: 'medium',
      assetClass: 'Lighting',
      location: 'Cedar Lane',
      costZar: 64000,
      description:
        'Lighting account up 18% year on year and two outage events this quarter. Obtain quotations for a solar LED conversion of the 42 poles and confirm the payback.',
    },
  },
]

/* ------------------------------------------------------- “Ask VALORA” */

export const askValoraPrompts = [
  'Why did our estate health score change?',
  'What is likely to need attention next month?',
  'Summarise infrastructure risks for the board.',
] as const

const domainAnswers: Record<string, ValoraAnswer> = {
  'Why did our estate health score change?': {
    summary:
      'The score moved because complaint resolution slowed in the first half of the window while security incidents stayed flat. Two pillars account for almost all of the change: resolution speed and infrastructure maintenance.',
    evidence: [
      'Resolution speed is the heaviest pillar and its average fell to 4.6 days from 3.2 days (complaint event log, last 90 days).',
      'Three complaints reopened after being marked resolved, which the engine counts as unresolved again (complaint event log).',
      'Infrastructure maintenance is unchanged in volume but shifted later: 5 work orders completed beyond their estimated completion date (work order records).',
      'Security incidents and resident satisfaction both held steady, so neither moved the score (incident records, work order ratings).',
    ],
    recommendation:
      'Clear the three reopened complaints first — they are already past resolution and each one is costing the heaviest pillar for as long as it stays open.',
    related: ['Estate health · 90-day history', 'Maintenance · open work orders', 'Complaints · reopened'],
  },
  'What is likely to need attention next month?': {
    summary:
      'Three things are trending toward a failure rather than a cost: the Clubhouse pool pump, Block C’s irrigation pressure, and the Cedar Lane lighting circuit into summer load.',
    evidence: [
      'Pool Pump 02 has tripped on overload three times in eleven days with rising winding temperature (SCADA relay log).',
      'Block C irrigation pressure is holding 1.9 bar against a 3.2 bar set point and consumption is up 640 kl (telemetry, bulk meter).',
      'Cedar Lane lighting demand rises with the December occupancy peak (financial ledger, asset register).',
      'Seasonal pattern: reactive maintenance requests rose 34% in December last year over November (complaint records).',
    ],
    recommendation:
      'Act on the pump and the pressure valve this month. Both are cheap now and expensive in December, when call-outs carry a premium and the estate is at peak occupancy.',
    related: ['Assets · Pool Pump 02', 'Assets · Block C PRV', 'Maintenance · December season'],
  },
  'Summarise infrastructure risks for the board.': {
    summary:
      'The estate’s infrastructure risk is concentrated in water and pumping. Nothing is at the level of a safety failure, but two items are one failure away from an unplanned capital spend.',
    evidence: [
      'Water: Block C pressure loss accounts for 640 kl of unbilled consumption and a R28,000 annual run-rate.',
      'Pumping: Pool Pump 02 is showing bearing-wear signals and a replacement in season carries an emergency premium.',
      'Electrical: the Cedar Lane lighting circuit is the only mains-critical circuit with no redundancy and no outage cover.',
      'Governance: every finding above traces to a stored record, so the board can request the underlying evidence for any line.',
    ],
    recommendation:
      'Approve a standing preventative-maintenance line for pumping and water assets. Both findings this quarter would have been caught by a scheduled inspection rather than a resident report.',
    related: ['Board report · infrastructure', 'Assets · critical systems', 'Financial · maintenance spend'],
  },
}

/** The answer shown when a question is not one the domain fallback covers. */
function genericAnswer(question: string, estateName?: string | null): ValoraAnswer {
  return {
    summary: `I read your question as: “${question}”. The signals I hold cover the estate’s recent operations — maintenance, assets, incidents, spend and resident feedback.`,
    evidence: [
      'Five health pillars are scored from stored operational records and never on read.',
      'Every complaint, work order, incident and rating is an append-only record with its own timestamp.',
      estateName
        ? `Your question is scoped to ${estateName}; switching estate changes the signals I can read.`
        : 'Answers are scoped to the estate you have selected.',
    ],
    recommendation:
      'Narrow the question to a block, asset or provider — “which Block C work orders ran late?” — and the answer can cite the individual records.',
    related: ['Estate health · 90-day history', 'Maintenance · open work orders'],
  }
}

/* --------------------------------------------------------- service hook */

const N8N_URL = (import.meta.env.VITE_N8N_INTELLIGENCE_URL ?? '').replace(/\/$/, '')

/** True when the intelligence service is wired up in this build. */
export const intelligenceServiceConfigured = N8N_URL.length > 0

export interface AskValoraContext {
  estateId: number | null
  estateName?: string | null
}

/**
 * Ask VALORA a question.
 *
 * With `VITE_N8N_INTELLIGENCE_URL` set the question is posted to that service and
 * its answer is returned unchanged; anything else (no service, a refusal, a
 * malformed body) falls back to the estate-domain answer, and the panel labels
 * which of the two answered. `source` is what the footer disclaimer reads, so a
 * sample answer is never mistaken for a live one.
 */
export async function askValora(
  question: string,
  context: AskValoraContext,
): Promise<ValoraAnswerResult> {
  if (context.estateId) {
    try {
      const resp = await api.post<ValoraAnswerResult>('/api/v1/analytics/intelligence/ask', {
        question,
        estate_id: context.estateId,
      })
      if (resp && typeof resp.summary === 'string' && resp.summary.trim()) {
        return {
          summary: resp.summary,
          evidence: Array.isArray(resp.evidence) ? resp.evidence.map(String) : [],
          recommendation: typeof resp.recommendation === 'string' ? resp.recommendation : '',
          related: Array.isArray(resp.related) ? resp.related.map(String) : [],
          source: (resp.source as 'n8n' | 'estate-domain') ?? 'estate-domain',
        }
      }
    } catch {
      // Backend unavailable or offline: fallback to direct webhook or domain
    }
  }

  if (N8N_URL) {
    try {
      const response = await fetch(`${N8N_URL}/valora/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          question,
          estate_id: context.estateId,
          estate_name: context.estateName ?? null,
        }),
      })
      if (response.ok) {
        const payload = (await response.json()) as Partial<ValoraAnswer>
        if (typeof payload.summary === 'string' && payload.summary.trim()) {
          return {
            summary: payload.summary,
            evidence: Array.isArray(payload.evidence) ? payload.evidence.map(String) : [],
            recommendation: typeof payload.recommendation === 'string' ? payload.recommendation : '',
            related: Array.isArray(payload.related) ? payload.related.map(String) : [],
            source: 'n8n',
          }
        }
      }
    } catch {
      // Unreachable service: answer from the domain instead of failing the panel.
    }
  }

  await new Promise((resolve) => window.setTimeout(resolve, 900))
  const answer = domainAnswers[question] ?? genericAnswer(question, context.estateName)
  return { ...answer, source: 'estate-domain' }
}

/* -------------------------------------------- tolerance for live payloads */

function toEvidence(value: unknown): RecommendationEvidence[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    // A live service may send evidence as plain strings; keep both shapes usable.
    if (typeof item === 'string') return [{ label: item, detail: '', source: '' }]
    if (item && typeof item === 'object') {
      const entry = item as Record<string, unknown>
      return [
        {
          label: String(entry.label ?? entry.title ?? ''),
          detail: String(entry.detail ?? entry.description ?? ''),
          source: String(entry.source ?? ''),
        },
      ]
    }
    return []
  })
}

/**
 * Read a recommendations payload from the intelligence service.
 *
 * Tolerant by design: the service may return evidence as strings or objects, and
 * a finding that does not parse is dropped rather than rendered half-formed.
 */
export function parseRecommendations(payload: unknown): PriorityRecommendation[] {
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray((payload as { recommendations?: unknown })?.recommendations)
      ? ((payload as { recommendations: unknown[] }).recommendations ?? [])
      : []

  return list.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const row = item as Record<string, unknown>
    if (!row.id || !row.title) return []
    return [
      {
        id: String(row.id),
        kind: (row.kind as RecommendationKind) ?? 'PREVENTIVE MAINTENANCE',
        title: String(row.title),
        summary: String(row.summary ?? ''),
        evidence: toEvidence(row.evidence),
        confidence: (row.confidence as Confidence) ?? 'Medium',
        confidenceValue: Number(row.confidenceValue ?? 0),
        impact: String(row.impact ?? ''),
        savingsZar: Number(row.savingsZar ?? 0),
        suggestedAction: String(row.suggestedAction ?? ''),
        workOrderDefaults: (row.workOrderDefaults as WorkOrderDefaults) ?? { title: String(row.title), priority: 'medium' },
      },
    ]
  })
}
