import type { ReactNode } from 'react'

import type { ApiError } from '../lib/api'
import { displayLabel, fullDate, ratio } from '../lib/format'
import type { LivingScoreComponent, LivingScoreSnapshot } from '../lib/contract'
import { scoreBand } from '../lib/display'
import { Button, Card, Chip, ErrorState, LoadingState, Meter, cx } from './ui'
import { IconSparkle } from './Icons'

/**
 * The documented Living Score weights, from the PRD (§8.1).
 *
 * These are *published model parameters*, not a calculation. React never
 * computes a score — it only explains the one the backend published. They are
 * shown in the "no score yet" state so an administrator can see what the engine
 * will weigh before it has enough evidence to publish anything.
 */
export const LIVING_SCORE_FACTORS = [
  { key: 'resolution', label: 'Complaint resolution time', weight: 0.3, signal: 'How fast issues reach closed' },
  { key: 'frequency', label: 'Complaint frequency', weight: 0.25, signal: 'Issues logged per unit' },
  { key: 'security', label: 'Security incidents', weight: 0.2, signal: 'Incidents normalised by estate size' },
  { key: 'satisfaction', label: 'Resident satisfaction', weight: 0.15, signal: 'Ratings on completed work orders' },
  { key: 'infrastructure', label: 'Infrastructure maintenance', weight: 0.1, signal: 'Resolved vs open work orders' },
] as const

export function LivingScoreDial({ score, size = 168 }: { score: number; size?: number }) {
  const band = scoreBand(score)
  const radius = size / 2 - 12
  const circumference = Math.PI * radius * 1.5 // 270° arc
  const clamped = Math.max(0, Math.min(100, score))
  const filled = (clamped / 100) * circumference

  return (
    <div className="relative" style={{ width: size, height: size * 0.82 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <g transform={`rotate(135 ${size / 2} ${size / 2})`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            className="text-ink/12"
            strokeWidth="10"
            strokeDasharray={`${circumference} 999`}
            strokeLinecap="butt"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className={band.textClass}
            stroke="currentColor"
            strokeWidth="10"
            strokeDasharray={`${filled} 999`}
            strokeLinecap="butt"
          />
        </g>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-3">
        {/* The stored value, formatted — never re-derived. */}
        <span className={cx('num text-[40px] leading-none font-semibold', band.textClass)}>
          {ratio(score)}
        </span>
        <span className="num mt-1 text-[11px] text-ink-muted">/ 100</span>
      </div>
    </div>
  )
}

/** The dashed dial the panel shows when the engine has published no number. */
function EmptyDial() {
  return (
    <div className="survey-grid flex h-[138px] w-[168px] shrink-0 items-center justify-center border border-dashed border-ink/25">
      <div className="text-center">
        <span className="num block text-[34px] leading-none font-semibold text-ink-muted">——</span>
        <span className="num mt-1 block text-[11px] text-ink-muted">/ 100</span>
      </div>
    </div>
  )
}

/**
 * One stored component, exactly as the engine described it.
 *
 * `score` is a string or absent — absent means "not enough evidence for this
 * factor", which is why it renders as words rather than as a zero. The weight is
 * the engine's published weight, read from the response and never re-derived.
 */
function ComponentMeter({ component }: { component: LivingScoreComponent }) {
  const measured = component.score !== null && component.score !== undefined
  const value = measured ? Number(component.score) : 0
  const weightPct = Math.round(Number(component.weight) * 100)

  return (
    <div>
      <Meter
        label={component.label}
        value={value}
        caption={
          measured
            ? ratio(component.score, ' / 100')
            : component.status === 'insufficient_data'
              ? 'no evidence yet'
              : 'not measured'
        }
        barClass={measured ? 'bg-accent' : 'bg-ink/15'}
      />
      <p className="mt-1 text-[11.5px] text-ink-muted">
        {weightPct}% of the score
        {measured ? '' : ' · left out until there is enough data'}
      </p>
    </div>
  )
}

/**
 * The dashboard hero.
 *
 * It renders the *stored* snapshot and nothing else: the overall score, the
 * status the engine recorded, the five components with their own status, the
 * engine version and when the calculation was made. There is no arithmetic here
 * — when the API sends no score, or sends `insufficient_data`, the panel says so
 * in words instead of showing a number nobody computed.
 */
export function LivingScorePanel({
  snapshot,
  loading,
  error,
  onRetry,
  onRecalculate,
  recalculating = false,
  recalculateError = null,
}: {
  snapshot: LivingScoreSnapshot | null
  loading: boolean
  error: ApiError | null
  onRetry?: () => void
  /** Present only for an HOA administrator of this estate: the server checks again. */
  onRecalculate?: () => void
  recalculating?: boolean
  recalculateError?: ApiError | null
}) {
  const recalculateButton = onRecalculate ? (
    <Button variant="secondary" onClick={onRecalculate} disabled={recalculating}>
      {recalculating ? 'Recalculating…' : 'Recalculate now'}
    </Button>
  ) : null

  const recalculateFailure = recalculateError ? (
    <ErrorState
      title="The recalculation was refused"
      message={recalculateError.message}
      requestId={recalculateError.requestId}
    />
  ) : null
  if (loading) {
    return (
      <Card as="section" className="min-w-0 p-5">
        <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
          Living Score
        </p>
        <LoadingState label="Loading the Living Score" />
      </Card>
    )
  }

  if (error && error.status !== 404) {
    return (
      <Card as="section" className="min-w-0 p-5">
        <p className="mb-3 text-[11px] font-medium tracking-wider text-ink-muted uppercase">
          Living Score
        </p>
        <ErrorState
          title="Could not load the Living Score"
          message={error.message}
          requestId={error.requestId}
          action={
            onRetry ? (
              <Button variant="secondary" onClick={onRetry}>
                Try again
              </Button>
            ) : null
          }
        />
      </Card>
    )
  }

  const scored =
    snapshot !== null &&
    snapshot.status === 'scored' &&
    snapshot.overall_score !== null &&
    snapshot.overall_score !== undefined

  if (!scored) {
    return (
      <NoScoreYet
        snapshot={snapshot}
        onRetry={onRetry}
        action={recalculateButton}
        failure={recalculateFailure}
      />
    )
  }

  const score = Number(snapshot.overall_score)
  const band = scoreBand(score)
  const components = snapshot.components ?? []
  const advice = (snapshot.drivers ?? []).filter((driver) => driver.recommendation).slice(0, 3)

  return (
    <Card as="section" className="min-w-0 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Living Score
          </p>
          <h2 className="mt-1 text-[17px] font-semibold">Estate quality of life</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {snapshot.is_demo ? (
            <Chip tone="warn" glyph="◷">
              Demo data
            </Chip>
          ) : null}
          <Chip
            tone={band.key === 'high' ? 'good' : band.key === 'mid' ? 'warn' : 'alert'}
            glyph="●"
          >
            {band.label}
          </Chip>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-center">
        <div className="shrink-0">
          <LivingScoreDial score={score} />
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          {components.map((component) => (
            <ComponentMeter key={component.key} component={component} />
          ))}
        </div>
      </div>

      <dl className="mt-4 grid gap-3 border-t border-ink/15 pt-3 text-[12.5px] sm:grid-cols-3">
        <div>
          <dt className="text-ink-muted">Calculated for</dt>
          <dd className="num mt-0.5 font-medium">{fullDate(snapshot.as_of)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Engine version</dt>
          <dd className="num mt-0.5 font-medium">{snapshot.engine_version}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Stored</dt>
          <dd className="num mt-0.5 font-medium">{fullDate(snapshot.calculated_at)}</dd>
        </div>
      </dl>

      {advice.length > 0 ? (
        <div className="mt-4 border-t border-ink/15 pt-3">
          <p className="text-[12px] font-medium text-ink-soft">Where to look next</p>
          <ul className="mt-2 space-y-1.5">
            {advice.map((driver) => (
              <li key={driver.key} className="flex items-start gap-2.5 text-[12.5px] text-ink-soft">
                <IconSparkle size={15} className="mt-0.5 shrink-0 text-ochre-ink" />
                <span>
                  <span className="font-medium">{driver.label}</span>
                  {driver.recommendation ? ` — ${driver.recommendation}` : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {recalculateFailure ? <div className="mt-3">{recalculateFailure}</div> : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-ink/15 pt-3">
        <p className="max-w-xl text-[12px] text-ink-muted">
          A stored calculation over a rolling 90-day window, produced by engine version{' '}
          {snapshot.engine_version}. It is never recalculated on read, so this figure cannot move on
          its own.
        </p>
        {recalculateButton}
      </div>
    </Card>
  )
}

/**
 * The state the estate is in before there is a number: never scored, or scored
 * with too little of the estate measurable to justify one. The engine's own
 * explanation is shown when the API sent one; the published factors are shown so
 * the panel is still useful while it waits.
 */
function NoScoreYet({
  snapshot,
  onRetry,
  action,
  failure,
}: {
  snapshot: LivingScoreSnapshot | null
  onRetry?: () => void
  action?: ReactNode
  failure?: ReactNode
}) {
  const measuredShare =
    snapshot && snapshot.measured_weight !== null && snapshot.measured_weight !== undefined
      ? Math.round(Number(snapshot.measured_weight) * 100)
      : null

  return (
    <Card as="section" className="min-w-0 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Living Score
          </p>
          <h2 className="mt-1 text-[17px] font-semibold">Estate quality of life</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {snapshot?.is_demo ? (
            <Chip tone="warn" glyph="◷">
              Demo data
            </Chip>
          ) : null}
          <Chip tone="warn" glyph="◷">
            Not enough data yet
          </Chip>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-center">
        <EmptyDial />

        <div className="min-w-0 flex-1 space-y-3">
          {snapshot && (snapshot.components ?? []).length > 0
            ? (snapshot.components ?? []).map((component) => (
                <ComponentMeter key={component.key} component={component} />
              ))
            : LIVING_SCORE_FACTORS.map((factor) => (
                <Meter
                  key={factor.key}
                  label={factor.label}
                  value={0}
                  caption="awaiting data"
                  barClass="bg-ink/15"
                />
              ))}
        </div>
      </div>

      <div className="mt-4 flex items-start gap-2.5 border-l-2 border-l-ochre bg-ochre-wash px-3.5 py-3">
        <IconSparkle size={16} className="mt-0.5 shrink-0 text-ochre-ink" />
        <div className="min-w-0 text-[12.5px] text-ink-soft">
          {snapshot ? (
            <>
              <p>
                {displayLabel(snapshot.status)} — the engine will not publish a number from a sliver
                of the estate&rsquo;s operations
                {measuredShare !== null ? ` (${measuredShare}% of the score's weight is measurable)` : ''}
                .
              </p>
              {snapshot.components?.[0]?.explanation ? (
                <p className="mt-1.5">{snapshot.components[0].explanation}</p>
              ) : null}
            </>
          ) : (
            <p>
              This estate has not been scored yet. Every operational action — a logged complaint, a
              completed work order, a resident rating — feeds the five weighted factors above, and
              the score appears here once there is a rolling 90-day window to work from.
            </p>
          )}
        </div>
      </div>

      {failure ? <div className="mt-3">{failure}</div> : null}

      {onRetry || action ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {onRetry ? (
            <Button variant="secondary" onClick={onRetry}>
              Check again
            </Button>
          ) : null}
          {action}
        </div>
      ) : null}
    </Card>
  )
}

/** The published weights, shown as evidence rather than a black box. */
export function LivingScoreFactors() {
  return (
    <ul className="divide-y divide-ink/10">
      {LIVING_SCORE_FACTORS.map((factor) => (
        <li key={factor.key} className="flex items-baseline gap-4 py-3">
          <span className="num w-14 shrink-0 text-[15px] font-semibold text-accent-ink">
            {Math.round(factor.weight * 100)}%
          </span>
          <span className="min-w-0">
            <span className="block text-[14px] font-medium">{factor.label}</span>
            <span className="block text-[12.5px] text-ink-muted">{factor.signal}</span>
          </span>
        </li>
      ))}
    </ul>
  )
}
