import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { triageCategories, triagePriorities, triageTrades } from '../api/generated/enums'
import {
  decideTriageSuggestion,
  isAiUnavailable,
  readTriageSuggestion,
  requestTriageSuggestion,
} from '../lib/ai'
import type { TriageDecisionRequest, TriageSuggestion as TriagePayload } from '../lib/ai'
import { ApiError } from '../lib/api'
import { displayLabel, fullDate } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { Button, Chip, ErrorState, Field, LoadingState, Select } from './ui'

/**
 * The HOA's advisory triage review for one complaint.
 *
 * It shows what the AI layer suggested and records the HOA's decision on it. It
 * never changes the complaint, never infers a category itself, and never implies
 * urgency handling or automatic action — the labels it offers are the contract's
 * vocabularies (`src/api/generated/enums.ts`), not a hand-written list.
 *
 * Only an HOA admin sees this: the parent renders it solely for admins, and the
 * endpoints are admin-only anyway.
 */
const ANONYMOUS_MESSAGE = 'AI triage is not available for anonymous complaints.'
const UNAVAILABLE_MESSAGE = 'AI triage is unavailable right now. No triage was generated.'

function decidedLabel(decision: string | null): string {
  return decision === null ? 'Not decided' : displayLabel(decision)
}

/** The labels a decision settled on. A dismissal carries none. */
function decidedSummary(suggestion: TriagePayload): string {
  if (suggestion.decision === null) return ''
  if (suggestion.decided_category === null && suggestion.decided_priority === null && suggestion.decided_trade === null) {
    return 'no labels'
  }
  return [suggestion.decided_category, suggestion.decided_priority, suggestion.decided_trade]
    .filter((value) => value !== null)
    .map((value) => displayLabel(value))
    .join(' · ')
}

function OverrideForm({
  suggestion,
  busy,
  onCancel,
  onSubmit,
}: {
  suggestion: TriagePayload
  busy: boolean
  onCancel: () => void
  onSubmit: (payload: TriageDecisionRequest) => void
}) {
  const [category, setCategory] = useState<string>(suggestion.suggested_category)
  const [priority, setPriority] = useState<string>(suggestion.suggested_priority)
  const [trade, setTrade] = useState<string>(suggestion.suggested_trade ?? '')
  const first = useRef<HTMLSelectElement>(null)

  // The form replaces the button row, so move focus into it: a keyboard user
  // lands on the first control instead of being dropped back at the top.
  useEffect(() => {
    first.current?.focus()
  }, [])

  // Only what actually changed is sent: the server refuses an override that
  // changes nothing, and it refuses labels on an accept or a dismiss.
  const payload: TriageDecisionRequest = { decision: 'overridden' }
  let changed = false
  if (category !== suggestion.suggested_category) {
    payload.category = category as TriageDecisionRequest['category']
    changed = true
  }
  if (priority !== suggestion.suggested_priority) {
    payload.priority = priority as TriageDecisionRequest['priority']
    changed = true
  }
  if (trade !== (suggestion.suggested_trade ?? '')) {
    payload.trade = (trade === '' ? null : (trade as TriageDecisionRequest['trade']))
    changed = true
  }

  return (
    <div className="mt-3 space-y-3">
      <Field label="Override category">
        <Select
          ref={first}
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          {triageCategories.map((value) => (
            <option key={value} value={value}>
              {displayLabel(value)}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Override priority">
        <Select value={priority} onChange={(event) => setPriority(event.target.value)}>
          {triagePriorities.map((value) => (
            <option key={value} value={value}>
              {displayLabel(value)}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Override trade">
        <Select value={trade} onChange={(event) => setTrade(event.target.value)}>
          <option value="">No trade</option>
          {triageTrades.map((value) => (
            <option key={value} value={value}>
              {displayLabel(value)}
            </option>
          ))}
        </Select>
      </Field>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          disabled={!changed || busy}
          onClick={() => onSubmit(payload)}
        >
          {busy ? 'Saving…' : 'Save override'}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
      {!changed ? (
        <p className="text-[12px] text-ink-muted">Change at least one label to override.</p>
      ) : null}
    </div>
  )
}

export function TriageSuggestion({
  estateId,
  complaintId,
  isAnonymous,
}: {
  estateId: number
  complaintId: number
  isAnonymous: boolean
}) {
  const stored = useAsync(() => readTriageSuggestion(estateId, complaintId), [
    estateId,
    complaintId,
  ])
  const [current, setCurrent] = useState<TriagePayload | null>(null)
  const [overriding, setOverriding] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [announcement, setAnnouncement] = useState('')

  const suggestion = current ?? stored.data
  // A 404 on the initial read means "not asked for yet", not a failure.
  const noneYet = stored.error?.status === 404
  const forbidden = stored.error?.status === 403
  const readFailure = stored.error && !noneYet && !forbidden ? stored.error : null

  async function request() {
    if (busy) return
    setBusy(true)
    setError(null)
    setNote(null)
    try {
      const fetched = await requestTriageSuggestion(estateId, complaintId)
      setCurrent(fetched)
      setAnnouncement('Triage suggestion ready for review.')
    } catch (cause) {
      const failure =
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not fetch a suggestion.')
      // The AI layer being unavailable is a quiet, ordinary state.
      if (isAiUnavailable(failure)) setNote(UNAVAILABLE_MESSAGE)
      else setError(failure)
      setAnnouncement('No suggestion was produced.')
    } finally {
      setBusy(false)
    }
  }

  async function decide(payload: TriageDecisionRequest) {
    if (busy) return
    setBusy(true)
    setError(null)
    setNote(null)
    try {
      setCurrent(await decideTriageSuggestion(estateId, complaintId, payload))
      setOverriding(false)
      setAnnouncement(`Suggestion ${payload.decision}.`)
    } catch (cause) {
      const failure =
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not record the decision.')
      if (failure.status === 409) {
        setNote(failure.message)
        // Someone else decided between our read and our write: drop our copy so
        // the reloaded row (with its decision and decider) wins.
        setCurrent(null)
        stored.reload()
      } else {
        setError(failure)
      }
    } finally {
      setBusy(false)
    }
  }

  if (isAnonymous) {
    return (
      <section className="mt-2">
        <h4 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
          AI triage
        </h4>
        <p className="mt-2 text-[13px] text-ink-soft">{ANONYMOUS_MESSAGE}</p>
      </section>
    )
  }

  return (
    <section>
      <h4 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
        AI triage
      </h4>
      <p className="mt-1.5 text-[12.5px] text-ink-soft">
        Uses this complaint's current estate record only when requested. A suggestion for the HOA's review;
        nothing is assigned or changed automatically, and this is not an emergency channel.
      </p>

      <p role="status" aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {stored.loading && !suggestion ? <LoadingState label="Checking for a suggestion" /> : null}

      {forbidden ? (
        <div className="mt-3">
          <ErrorState message={stored.error?.message ?? 'Not permitted.'} />
        </div>
      ) : null}

      {/* One failure banner at a time: a request failure supersedes a stale read failure. */}
      {readFailure && !error ? (
        <div className="mt-3 space-y-2">
          <ErrorState
            message={readFailure.message}
            requestId={readFailure.requestId}
            action={
              <Button variant="secondary" onClick={stored.reload}>
                Try again
              </Button>
            }
          />
        </div>
      ) : null}

      {note ? <p className="mt-3 text-[12.5px] text-ink-soft">{note}</p> : null}

      {error ? (
        <div className="mt-3">
          <ErrorState
            message={error.message}
            requestId={error.requestId}
            action={
              <Button variant="secondary" onClick={request}>
                Try again
              </Button>
            }
          />
        </div>
      ) : null}

      {!suggestion && !forbidden ? (
        <div className="mt-3">
          {noneYet ? (
            <p className="mb-2 text-[12.5px] text-ink-muted">{stored.error?.message}</p>
          ) : null}
          <Button variant="secondary" onClick={request} disabled={busy}>
            {busy ? 'Requesting…' : 'Suggest triage with AI'}
          </Button>
        </div>
      ) : null}

      {suggestion ? (
        <div className="mt-3 space-y-3">
          {suggestion.decision === null ? (
            <>
              <div className="hairline rounded-xs bg-surface p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <Chip tone="progress" glyph="◐">
                    Suggested
                  </Chip>
                  <span className="num text-[11.5px] text-ink-muted">
                    {`${suggestion.provider} · ${suggestion.model} · ${suggestion.prompt_version}`}
                  </span>
                </div>
                <dl className="mt-2.5 grid gap-1.5 sm:grid-cols-3">
                  <div>
                    <dt className="text-[11px] tracking-wider text-ink-muted uppercase">Category</dt>
                    <dd className="text-[13.5px] font-medium">
                      {displayLabel(suggestion.suggested_category)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-wider text-ink-muted uppercase">Priority</dt>
                    <dd className="text-[13.5px] font-medium">
                      {displayLabel(suggestion.suggested_priority)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-wider text-ink-muted uppercase">Trade</dt>
                    <dd className="text-[13.5px] font-medium">
                      {suggestion.suggested_trade ? displayLabel(suggestion.suggested_trade) : '—'}
                    </dd>
                  </div>
                </dl>
              </div>

              {suggestion.suggested_trade ? (
                <p className="text-[12.5px]">
                  <Link
                    className="text-accent-ink underline decoration-dotted underline-offset-2"
                    to={`/app/providers?trade=${suggestion.suggested_trade}`}
                  >
                    {`Find ${displayLabel(suggestion.suggested_trade)} providers`}
                  </Link>
                </p>
              ) : null}

              {overriding ? (
                <OverrideForm
                  suggestion={suggestion}
                  busy={busy}
                  onCancel={() => setOverriding(false)}
                  onSubmit={decide}
                />
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Button variant="primary" onClick={() => decide({ decision: 'accepted' })} disabled={busy}>
                    Accept
                  </Button>
                  <Button variant="secondary" onClick={() => setOverriding(true)} disabled={busy}>
                    Override
                  </Button>
                  <Button variant="ghost" onClick={() => decide({ decision: 'dismissed' })} disabled={busy}>
                    Dismiss
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div className="hairline rounded-xs bg-surface p-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <Chip tone={suggestion.decision === 'dismissed' ? 'neutral' : 'good'} glyph="✓">
                  {decidedLabel(suggestion.decision)}
                </Chip>
                <span className="num text-[11.5px] text-ink-muted">
                  {`${
                    suggestion.decided_by === null ? 'by an administrator' : `by user #${suggestion.decided_by}`
                  } · ${fullDate(suggestion.decided_at)}`}
                </span>
              </div>
              <p className="mt-2 text-[13px]">
                {suggestion.decision === 'accepted'
                  ? 'Suggestion accepted as-is'
                  : `Decided labels: ${decidedSummary(suggestion)}`}
              </p>
            </div>
          )}
        </div>
      ) : null}
    </section>
  )
}
