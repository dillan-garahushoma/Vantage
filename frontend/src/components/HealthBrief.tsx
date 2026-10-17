import { Fragment, useState } from 'react'

import {
  generateHealthBrief,
  readHealthBrief,
  sendHealthBriefFeedback,
} from '../lib/ai'
import type { BriefComponent, HealthBrief as HealthBriefPayload } from '../lib/ai'
import { ApiError } from '../lib/api'
import { displayLabel, fullDate } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { Button, Card, Chip, EmptyState, ErrorState, Field, LoadingState, Textarea } from './ui'
import type { Tone } from '../lib/display'

/**
 * The estate's health brief.
 *
 * It *displays* what the API returns and nothing else: no score is computed
 * here, no figure is reconciled, no label is guessed. Where the words come from
 * matters — an AI-written brief says so, and the deterministic template never
 * claims to be AI.
 */
const AI_WORDING = 'Written by AI from the figures below'

const DIRECTION_TONE: Record<string, Tone> = {
  improving: 'good',
  declining: 'alert',
  stable: 'neutral',
}

const DIRECTION_GLYPH: Record<string, string> = {
  improving: '↑',
  declining: '↓',
  stable: '·',
}

/** Formatting only: an absent figure is shown as absent, never as a zero. */
function fact(value: string | number | null | undefined): string {
  return value === null || value === undefined ? '—' : String(value)
}

function inputsText(inputs: BriefComponent['inputs'] | undefined): string {
  const entries = Object.entries(inputs ?? {})
  if (entries.length === 0) return 'none recorded'
  return entries.map(([key, value]) => `${key}: ${fact(value)}`).join(' · ')
}

function FeedbackForm({ estateId, insightId }: { estateId: number; insightId: number }) {
  const [helpful, setHelpful] = useState<boolean | null>(null)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [alreadySubmitted, setAlreadySubmitted] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function submit() {
    if (helpful === null || busy) return
    setBusy(true)
    setError(null)
    setAlreadySubmitted(false)
    try {
      await sendHealthBriefFeedback(estateId, insightId, {
        helpful,
        comment: comment.trim() === '' ? null : comment,
      })
      setSent(true)
      setHelpful(null)
      setComment('')
    } catch (cause) {
      const failure =
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not send your feedback.')
      if (failure.status === 409) setAlreadySubmitted(true)
      else setError(failure)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="border-t border-ink/10 pt-4">
      <h4 className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
        Was this useful?
      </h4>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button
          variant={helpful === true ? 'primary' : 'secondary'}
          aria-pressed={helpful === true}
          onClick={() => setHelpful(true)}
        >
          Helpful
        </Button>
        <Button
          variant={helpful === false ? 'primary' : 'secondary'}
          aria-pressed={helpful === false}
          onClick={() => setHelpful(false)}
        >
          Not helpful
        </Button>
      </div>

      <div className="mt-3">
        <Field label="Comment (optional)">
          <Textarea
            value={comment}
            maxLength={500}
            onChange={(event) => setComment(event.target.value)}
            placeholder="What was missing or wrong?"
          />
        </Field>
        <div className="mt-1 flex items-center justify-between gap-3">
          <span className="num text-[11.5px] text-ink-muted">{comment.length}/500</span>
          <Button variant="secondary" onClick={submit} disabled={helpful === null || busy}>
            {busy ? 'Sending…' : 'Send feedback'}
          </Button>
        </div>
      </div>

      {alreadySubmitted ? (
        <p className="mt-2 text-[12.5px] text-ink-soft">Already submitted</p>
      ) : sent ? (
        <p role="status" className="mt-2 text-[12.5px] text-ink-soft">
          Thanks — your feedback was recorded.
        </p>
      ) : null}
      {error ? (
        <p className="mt-2 text-[12.5px] text-signal-ink">
          {error.message}
          {error.requestId ? <span className="num"> · ref {error.requestId}</span> : null}
        </p>
      ) : null}
    </div>
  )
}

function Figures({ brief }: { brief: HealthBriefPayload }) {
  const facts = brief.facts
  const columns = ['Measure', 'Status', 'Score', 'Weight %', 'Δ 30d', 'Δ 30d abs', 'Δ 90d', 'Δ 90d abs']

  return (
    <table className="w-full border-collapse text-left text-[12.5px]">
      <caption className="sr-only">
        The figures behind this brief, exactly as the API returned them
      </caption>
      <thead>
        <tr>
          {columns.map((column) => (
            <th
              key={column}
              scope="col"
              className="border-b border-ink/15 bg-paper px-2 py-1.5 text-[10.5px] font-medium tracking-wider text-ink-muted uppercase"
            >
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row" className="border-b border-ink/8 px-2 py-1.5 font-medium">
            Overall
          </th>
          <td className="border-b border-ink/8 px-2 py-1.5">{displayLabel(facts.overall.status)}</td>
          <td className="num border-b border-ink/8 px-2 py-1.5">{fact(facts.overall.score)}</td>
          <td className="num border-b border-ink/8 px-2 py-1.5">—</td>
          <td className="num border-b border-ink/8 px-2 py-1.5">{fact(facts.overall.delta_30d)}</td>
          <td className="num border-b border-ink/8 px-2 py-1.5">
            {fact(facts.overall.delta_30d_abs)}
          </td>
          <td className="num border-b border-ink/8 px-2 py-1.5">{fact(facts.overall.delta_90d)}</td>
          <td className="num border-b border-ink/8 px-2 py-1.5">
            {fact(facts.overall.delta_90d_abs)}
          </td>
        </tr>
        {facts.components.map((component) => (
          <Fragment key={component.key}>
            <tr>
              <th scope="row" className="border-b border-ink/8 px-2 py-1.5 font-medium">
                {displayLabel(component.key)}
              </th>
              <td className="border-b border-ink/8 px-2 py-1.5">{displayLabel(component.status)}</td>
              <td className="num border-b border-ink/8 px-2 py-1.5">{fact(component.score)}</td>
              <td className="num border-b border-ink/8 px-2 py-1.5">
                {fact(component.weight_pct)}
              </td>
              <td className="num border-b border-ink/8 px-2 py-1.5">{fact(component.delta_30d)}</td>
              <td className="num border-b border-ink/8 px-2 py-1.5">
                {fact(component.delta_30d_abs)}
              </td>
              <td className="num border-b border-ink/8 px-2 py-1.5">{fact(component.delta_90d)}</td>
              <td className="num border-b border-ink/8 px-2 py-1.5">
                {fact(component.delta_90d_abs)}
              </td>
            </tr>
            <tr>
              <td colSpan={8} className="border-b border-ink/8 px-2 py-1.5 text-ink-muted">
                {`Stored inputs: ${inputsText(component.inputs)}`}
              </td>
            </tr>
          </Fragment>
        ))}
        <tr>
          <td colSpan={8} className="px-2 py-1.5 text-ink-muted">
            {`Measured weight ${fact(facts.measured_weight)}% · window ${fact(facts.window_days)} days · engine ${fact(facts.engine_version)}`}
          </td>
        </tr>
      </tbody>
    </table>
  )
}

export function HealthBrief({
  estateId,
  canGenerate,
}: {
  estateId: number
  canGenerate: boolean
}) {
  const brief = useAsync(() => readHealthBrief(estateId), [estateId])
  const [generated, setGenerated] = useState<HealthBriefPayload | null>(null)
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<ApiError | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const [showFigures, setShowFigures] = useState(false)

  // The generated response replaces the panel's data in place: no second read.
  const data = generated ?? brief.data

  async function generate() {
    if (generating) return
    setGenerating(true)
    setGenerateError(null)
    try {
      setGenerated(await generateHealthBrief(estateId))
      setAnnouncement('The brief has been updated.')
    } catch (cause) {
      setGenerateError(
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not generate the brief.'),
      )
      setAnnouncement('The brief could not be generated.')
    } finally {
      setGenerating(false)
    }
  }

  function readFailure(error: ApiError) {
    if (error.status === 403) {
      return (
        <ErrorState
          title="You do not have access to this estate's brief"
          message={error.message}
        />
      )
    }
    if (error.status === 404) {
      return <EmptyState title="No brief yet" body={error.message} />
    }
    return (
      <ErrorState
        message={error.message}
        requestId={error.requestId}
        action={
          <Button variant="secondary" onClick={brief.reload}>
            Try again
          </Button>
        }
      />
    )
  }

  return (
    <Card as="section" className="min-h-[13rem] p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight">Estate health brief</h2>
          {data?.source === 'ai' ? (
            <p className="mt-1 text-[12.5px] text-ink-muted">
              <span>{AI_WORDING}</span>
              <span>{` · as at ${fullDate(data.as_of)}`}</span>
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canGenerate ? (
            <Button variant="secondary" onClick={generate} disabled={generating}>
              {generating ? 'Generating…' : 'Generate AI summary'}
            </Button>
          ) : null}
        </div>
      </header>

      <p role="status" aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {generateError ? (
        <div className="mt-4">
          <ErrorState
            title="The brief could not be generated"
            message={generateError.message}
            requestId={generateError.requestId}
          />
        </div>
      ) : null}

      <div className="mt-4">
        {!data && brief.loading ? (
          <LoadingState label="Loading the estate brief" />
        ) : !data && brief.error ? (
          readFailure(brief.error)
        ) : data?.source === 'ai' ? (
          <div className="space-y-4">
            <div>
              <h3 className="text-[16px] leading-snug font-semibold tracking-tight">
                {data.output.headline}
              </h3>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-soft">
                {data.output.summary}
              </p>
            </div>

            {(data.output.drivers ?? []).length > 0 ? (
              <div>
                <h4 className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                  What is holding the score back
                </h4>
                <ul className="mt-2 space-y-2">
                  {(data.output.drivers ?? []).map((driver) => (
                    <li
                      key={`${driver.component}-${driver.statement}`}
                      className="flex flex-wrap items-baseline gap-2"
                    >
                      <Chip
                        tone={DIRECTION_TONE[driver.direction] ?? 'neutral'}
                        glyph={DIRECTION_GLYPH[driver.direction] ?? '·'}
                      >
                        {displayLabel(driver.direction)}
                      </Chip>
                      <span className="text-[13px] font-medium">
                        {displayLabel(driver.component)}
                      </span>
                      <span className="text-[13px] text-ink-soft">{driver.statement}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {(data.output.actions ?? []).length > 0 ? (
              <div>
                <h4 className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                  What could be done
                </h4>
                <ul className="mt-2 space-y-1.5">
                  {(data.output.actions ?? []).map((action) => (
                    <li key={`${action.component}-${action.action}`} className="flex flex-wrap gap-2">
                      <span className="text-[13px] font-medium">
                        {displayLabel(action.component)}
                      </span>
                      <span className="text-[13px] text-ink-soft">{action.action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div>
              <Button
                variant="ghost"
                aria-expanded={showFigures}
                aria-controls="brief-figures"
                onClick={() => setShowFigures((open) => !open)}
              >
                {showFigures ? 'Hide the figures' : 'Show the figures'}
              </Button>
              {/* The figures scroll inside their own box: eight columns do not fit
                  a phone, and the page itself must never move sideways. */}
              {showFigures ? (
                <div
                  id="brief-figures"
                  className="hairline mt-3 overflow-x-auto rounded-xs bg-surface p-3"
                >
                  <Figures brief={data} />
                </div>
              ) : null}
            </div>

            {data.source === 'ai' && data.insight_id !== null ? (
              <FeedbackForm estateId={estateId} insightId={data.insight_id} />
            ) : null}
          </div>
        ) : (
          <EmptyState
            title={data?.ai_unavailable_reason ? 'AI summary unavailable' : 'No AI summary has been generated yet.'}
            body={
              data?.ai_unavailable_reason
                ? 'No AI summary was created. The Living Score and its supporting figures remain available above; try again after the AI service is configured or available.'
                : 'The Living Score and its supporting figures are calculated from this estate’s recorded data. Select Generate AI summary to request a live explanation when you are ready.'
            }
          />
        )}
      </div>
    </Card>
  )
}
