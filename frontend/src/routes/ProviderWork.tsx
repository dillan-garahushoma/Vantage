import { useState } from 'react'
import { RequireEstate } from '../components/RequireEstate'
import { IconWrench } from '../components/Icons'
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Select,
  Textarea,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useEstateScope } from '../context/EstateContext'
import { ApiError } from '../lib/api'
import { workOrderStatus } from '../lib/display'
import { listMyWorkOrders, updateWorkOrder } from '../lib/estateAdmin'
import { fullDate, money, relativeDays } from '../lib/format'
import type { WorkOrder } from '../lib/contract'
import { useAsync } from '../lib/useAsync'

/**
 * The provider's own work, and the only two transitions the API lets a provider
 * make: `assigned → in_progress → completed`. Nothing is invented here — the
 * buttons offered match the server's state machine exactly, and a rejected
 * transition is shown as the server's own message.
 */
function ProviderWorkOrderRow({
  order,
  estateId,
  onChanged,
}: {
  order: WorkOrder
  estateId: number
  onChanged: () => void
}) {
  const status = workOrderStatus[order.status ?? 'assigned']
  const [notes, setNotes] = useState(order.completion_notes ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [expanded, setExpanded] = useState(false)

  const isCompleted = order.status === 'completed'
  const isCancelled = order.status === 'cancelled'

  async function send(changes: { status?: string; completion_notes?: string }) {
    setBusy(true)
    setError(null)
    try {
      await updateWorkOrder(estateId, order.id, changes)
      setExpanded(false)
      onChanged()
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not update that job.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="hairline rounded-xs bg-surface p-4">
      <div className="flex flex-wrap items-center gap-3">
        <IconWrench size={17} className="shrink-0 text-ink-muted" />
        <span className="num text-[13px] font-medium">WO-{String(order.id).padStart(4, '0')}</span>
        <span className="num text-[12.5px] text-ink-muted">complaint #{order.complaint_id}</span>
        <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
          {status?.label ?? order.status ?? '—'}
        </Chip>
        <span className="num ml-auto text-[12.5px] text-ink-muted">
          assigned {relativeDays(order.assigned_at)}
        </span>
      </div>

      <dl className="mt-3 grid gap-x-6 gap-y-1.5 text-[12.5px] sm:grid-cols-2">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-ink-soft">Job cost</dt>
          <dd className="num font-medium">{money(order.job_cost)}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-ink-soft">Resident rating</dt>
          <dd className="num font-medium">
            {order.resident_rating ? `${order.resident_rating} / 5` : 'Not rated yet'}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-ink-soft">Due</dt>
          <dd className="num font-medium">
            {order.estimated_completion_date ? fullDate(order.estimated_completion_date) : '—'}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-ink-soft">Completed</dt>
          <dd className="num font-medium">
            {order.actual_completion_date ? fullDate(order.actual_completion_date) : '—'}
          </dd>
        </div>
      </dl>

      {order.completion_notes ? (
        <p className="mt-3 border-t border-ink/15 pt-3 text-[13px] text-ink-soft">
          {order.completion_notes}
        </p>
      ) : null}

      {error ? (
        <div className="mt-3">
          <ErrorState
            title={
              error.status === 409
                ? 'That step is not allowed from where this job is'
                : 'Could not update that job'
            }
            message={error.message}
            requestId={error.requestId}
          />
        </div>
      ) : null}

      {!isCompleted && !isCancelled ? (
        <div className="mt-3.5 border-t border-ink/15 pt-3.5">
          {order.status === 'assigned' ? (
            <Button variant="primary" disabled={busy} onClick={() => send({ status: 'in_progress' })}>
              {busy ? 'Starting…' : 'Start this work'}
            </Button>
          ) : (
            <>
              {!expanded ? (
                <Button variant="primary" onClick={() => setExpanded(true)}>
                  Mark as completed
                </Button>
              ) : (
                <div className="space-y-3">
                  <Field
                    label="What was done"
                    hint="This note is recorded against the complaint as the resolution — write it for the resident who logged the issue."
                  >
                    <Textarea
                      name={`completion_notes_${order.id}`}
                      value={notes}
                      maxLength={5000}
                      onChange={(event) => setNotes(event.target.value)}
                      placeholder="Replaced the seized valve and refilled the line. Pressure tested; no leaks."
                    />
                  </Field>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="primary"
                      disabled={busy}
                      onClick={() =>
                        send({
                          status: 'completed',
                          ...(notes.trim() ? { completion_notes: notes.trim() } : {}),
                        })
                      }
                    >
                      {busy ? 'Completing…' : 'Complete this job'}
                    </Button>
                    <Button variant="ghost" disabled={busy} onClick={() => setExpanded(false)}>
                      Cancel
                    </Button>
                  </div>
                  <p className="text-[12px] text-ink-muted">
                    Completing is final: the API does not allow a completed job to be re-opened, and
                    the complaint moves to <span className="font-medium">resolved</span> so the
                    resident can rate it.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        <p className="mt-3 border-t border-ink/15 pt-3 text-[12.5px] text-ink-muted">
          {isCompleted
            ? 'Closed on the estate’s record. The resident can still rate it.'
            : 'This job was cancelled.'}
        </p>
      )}
    </li>
  )
}

function ProviderWorkBody() {
  const { estateId } = useEstateScope()
  const { user } = useAuth()
  const scope = estateId ?? 0
  const isProvider = user?.role === 'service_provider'

  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const workOrders = useAsync(
    () =>
      isProvider && scope
        ? listMyWorkOrders(scope, { page, size: 20 })
        : Promise.resolve(null),
    [scope, page, isProvider],
  )

  if (!isProvider) {
    return (
      <ErrorState
        title="This is the service provider’s own work list"
        message="Administrators see every work order in the estate from Work orders. This screen shows only what is assigned to the signed-in provider’s profile."
      />
    )
  }

  const items = (workOrders.data?.items ?? []).filter((order) =>
    status ? order.status === status : true,
  )
  const pages = workOrders.data?.pages ?? 0

  return (
    <div className="space-y-5">
      <header>
        <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
          Assigned work
        </p>
        <h1 className="mt-2 text-[26px] leading-tight font-semibold">My work</h1>
        <p className="mt-1 max-w-2xl text-[13.5px] text-ink-muted">
          Jobs the estate’s administrators have assigned to your profile. Starting and completing them
          is what moves the estate’s operational record forward — completion also resolves the
          resident’s complaint.
        </p>
      </header>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <label className="min-w-[12rem] flex-1">
          <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Status
          </span>
          <Select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All statuses</option>
            {Object.entries(workOrderStatus).map(([key, meta]) => (
              <option key={key} value={key}>
                {meta.label}
              </option>
            ))}
          </Select>
        </label>
        <p className="num pb-2 text-[12.5px] text-ink-muted">
          {workOrders.data?.total ?? 0} assigned
        </p>
      </Card>

      {workOrders.loading ? (
        <LoadingState label="Loading your work" />
      ) : workOrders.error ? (
        <ErrorState
          title="Could not load your work"
          message={workOrders.error.message}
          requestId={workOrders.error.requestId}
          action={
            <Button variant="secondary" onClick={workOrders.reload}>
              Try again
            </Button>
          }
        />
      ) : (workOrders.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="Nothing assigned to you yet"
          body="An administrator has to add your email to their estate and then assign a complaint to your provider profile. Both steps are theirs; there is nothing to do from here but check again."
          action={
            <Button variant="secondary" onClick={workOrders.reload}>
              Check again
            </Button>
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="No job with that status"
          body="Clear the status filter to see everything assigned to you."
          action={
            <Button variant="secondary" onClick={() => setStatus('')}>
              Clear the filter
            </Button>
          }
        />
      ) : (
        <>
          <ul className="space-y-3">
            {items.map((order) => (
              <ProviderWorkOrderRow
                key={order.id}
                order={order}
                estateId={scope}
                onChanged={workOrders.reload}
              />
            ))}
          </ul>

          <div className="flex items-center justify-between gap-3">
            <p className="num text-[12px] text-ink-muted">
              page {workOrders.data?.page ?? 1} of {Math.max(pages, 1)}
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={page >= Math.max(pages, 1)}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export function ProviderWork() {
  return (
    <RequireEstate>
      <ProviderWorkBody />
    </RequireEstate>
  )
}
