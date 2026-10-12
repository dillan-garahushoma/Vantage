import { useState } from 'react'
import { useEstateScope } from '../context/EstateContext'
import { useAuth } from '../context/AuthContext'
import { api, ApiError } from '../lib/api'
import { complaintStatus, priorityMeta, workOrderStatus } from '../lib/display'
import {
  getComplaintWorkOrder,
  listEstateProviders,
  rateWorkOrder,
} from '../lib/estateAdmin'
import { displayLabel, fullDate, money, relativeDays, titleCase } from '../lib/format'
import type { Complaint, ComplaintEvent, Page, WorkOrder } from '../lib/types'
import { useAsync } from '../lib/useAsync'
import { IconWrench } from './Icons'
import { TriageSuggestion } from './TriageSuggestion'
import { Button, Chip, Drawer, ErrorState, Field, Input, LoadingState, Select, Textarea } from './ui'

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-ink/8 py-2">
      <span className="text-[12.5px] text-ink-muted">{label}</span>
      <span className="num text-right text-[12.5px] font-medium">{children}</span>
    </div>
  )
}

function Lifecycle({ events, status }: { events: ComplaintEvent[]; status: string | null }) {
  if (events.length === 0) {
    return <p className="text-[13px] text-ink-muted">No lifecycle events recorded yet.</p>
  }

  return (
    <ol className="relative ml-1.5 border-l border-ink/20 pl-5">
      {events.map((event) => {
        const meta = complaintStatus[event.to_status ?? ''] ?? complaintStatus.submitted
        return (
          <li key={event.id} className="relative pb-5 last:pb-0">
            <span className="absolute top-1 -left-[26px] flex h-3 w-3 items-center justify-center bg-paper">
              <span className="h-2 w-2 bg-accent" />
            </span>
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="text-[13.5px] font-medium">
                {event.event_type === 'submitted' ? 'Logged' : meta.label}
              </span>
              <span className="num text-[11.5px] text-ink-muted">
                {fullDate(event.occurred_at)}
              </span>
            </div>
            <p className="num mt-0.5 text-[11.5px] text-ink-muted">
              {event.from_status ? `${event.from_status} → ` : ''}
              {event.to_status ?? '—'}
              {event.actor_user_id ? ` · actor #${event.actor_user_id}` : ''}
            </p>
            {event.note ? <p className="mt-1 text-[12.5px] text-ink-soft">{event.note}</p> : null}
          </li>
        )
      })}
      {status ? (
        <li className="relative pt-1">
          <span className="absolute top-2 -left-[26px] h-3 w-3 border border-ink/25 bg-paper" />
          <span className="num text-[11.5px] text-ink-muted">
            Current stage: {complaintStatus[status]?.label ?? status}
          </span>
        </li>
      ) : null}
    </ol>
  )
}

function AssignProviderForm({
  complaintId,
  onDone,
}: {
  complaintId: number
  onDone: () => void
}) {
  const { estateId } = useEstateScope()
  // The provider directory is estate-scoped: the server returns only providers
  // who are members of *this* estate, to an administrator of it, so the estate is
  // part of the request rather than implied by the session.
  const providers = useAsync(
    () =>
      estateId === null
        ? Promise.resolve(null)
        : listEstateProviders(estateId, { size: 100 }),
    [estateId],
  )
  const [providerId, setProviderId] = useState('')
  const [cost, setCost] = useState('')
  const [error, setError] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!providerId) return
    setBusy(true)
    setError(null)
    try {
      await api.post<WorkOrder>(
        '/api/v1/work-orders',
        {
          complaint_id: complaintId,
          provider_id: Number(providerId),
          job_cost: cost === '' ? null : Number(cost),
        },
        { estate_id: estateId },
      )
      onDone()
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not create the work order.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}
      {providers.loading ? (
        <LoadingState label="Loading the provider directory" />
      ) : providers.error ? (
        <ErrorState message={providers.error.message} requestId={providers.error.requestId} />
      ) : (
        <>
          <Field label="Verified provider">
            <Select value={providerId} onChange={(event) => setProviderId(event.target.value)}>
              <option value="">Select a provider…</option>
              {(providers.data?.items ?? []).map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.full_name} · {titleCase(provider.trade)}
                  {provider.verified ? ' · verified' : ' · unverified'}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Quoted cost (optional)" hint="Recorded against the work order for audit.">
            <Input
              inputMode="decimal"
              value={cost}
              onChange={(event) => setCost(event.target.value)}
              placeholder="2400.00"
            />
          </Field>
          <Button variant="primary" onClick={submit} disabled={busy || !providerId}>
            {busy ? 'Assigning…' : 'Assign provider'}
          </Button>
        </>
      )}
    </div>
  )
}

/**
 * The resident's side of a repair: the work order raised for their complaint (the
 * new per-complaint endpoint), and the rating control once the work is completed.
 *
 * The order shown is the server's, and the rating posted is the resident's own —
 * nothing is inferred locally. A complaint with no work order is a real state, not
 * an error: the endpoint answers 404 and the panel says so in words.
 */
function ResidentWorkOrder({
  complaintId,
  onDone,
}: {
  complaintId: number
  onDone: () => void
}) {
  const { estateId } = useEstateScope()
  const [error, setError] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)
  const order = useAsync(
    () =>
      estateId === null
        ? Promise.resolve(null)
        : getComplaintWorkOrder(estateId, complaintId),
    [estateId, complaintId],
  )

  async function rate(value: number) {
    if (estateId === null || !order.data || busy) return
    setBusy(true)
    setError(null)
    try {
      await rateWorkOrder(estateId, order.data.id, value)
      order.reload()
      onDone()
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause
          : new ApiError(0, 'Could not record your rating.'),
      )
    } finally {
      setBusy(false)
    }
  }

  if (order.loading) return <LoadingState label="Loading the repair" />

  if (order.error) {
    if (order.error.status === 404) {
      return (
        <p className="text-[13px] text-ink-muted">
          No work order has been raised for this complaint yet. Your HOA assigns a provider first;
          the repair, and the rating below it, appear here from that point on.
        </p>
      )
    }
    return <ErrorState message={order.error.message} requestId={order.error.requestId} />
  }

  const active = order.data
  if (!active) return null
  const status = workOrderStatus[active.status ?? 'assigned']

  return (
    <div className="hairline rounded-xs bg-surface p-3.5">
      <div className="flex items-center justify-between gap-3">
        <span className="num flex items-center gap-2 text-[13px] font-medium">
          <IconWrench size={15} className="text-accent-ink" />
          WO-{String(active.id).padStart(4, '0')}
        </span>
        <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
          {status?.label ?? active.status}
        </Chip>
      </div>
      <div className="mt-2.5">
        <Row label="Assigned">{fullDate(active.assigned_at)}</Row>
        <Row label="Completed">{fullDate(active.resolved_at)}</Row>
      </div>
      {active.completion_notes ? (
        <p className="mt-2.5 border-t border-ink/10 pt-2.5 text-[12.5px] text-ink-soft">
          {active.completion_notes}
        </p>
      ) : null}

      {error ? (
        <div className="mt-3">
          <ErrorState message={error.message} requestId={error.requestId} />
        </div>
      ) : null}

      {active.status === 'completed' ? (
        active.resident_rating ? (
          <p className="num mt-3 border-t border-ink/10 pt-3 text-[12.5px] text-ink-soft">
            You rated this repair {active.resident_rating} out of 5.
          </p>
        ) : (
          <div className="mt-3 border-t border-ink/10 pt-3">
            <p className="text-[12.5px] text-ink-soft">How was the repair?</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {[1, 2, 3, 4, 5].map((value) => (
                <Button
                  key={value}
                  variant="secondary"
                  disabled={busy}
                  aria-label={`Rate the repair ${value} out of 5`}
                  onClick={() => rate(value)}
                >
                  {value}
                </Button>
              ))}
            </div>
            <p className="mt-2 text-[11.5px] text-ink-muted">
              A rating is recorded against the work order and feeds the estate's Living Score. It
              cannot be changed afterwards.
            </p>
          </div>
        )
      ) : null}
    </div>
  )
}

function ReviewAction({ complaintId, onDone }: { complaintId: number; onDone: () => void }) {
  const { estateId } = useEstateScope()
  const [note, setNote] = useState('')
  const [error, setError] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      await api.patch<Complaint>(
        `/api/v1/complaints/${complaintId}/status`,
        { status: 'reviewed', note: note.trim() || null },
        { estate_id: estateId },
      )
      onDone()
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not update the complaint.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}
      <Field label="Review note (optional)">
        <Textarea
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Confirmed with the resident; assigning a plumber tomorrow."
        />
      </Field>
      <Button variant="primary" onClick={submit} disabled={busy}>
        {busy ? 'Saving…' : 'Mark under review'}
      </Button>
      <p className="text-[12px] text-ink-muted">
        This is the only transition available at this stage: a complaint moves from logged to under
        review here. Assignment, progress and resolution are driven by the work order.
      </p>
    </div>
  )
}

export function ComplaintDrawer({
  complaintId,
  onClose,
  onChanged,
}: {
  complaintId: number
  onClose: () => void
  onChanged: () => void
}) {
  const { estateId } = useEstateScope()
  const { user } = useAuth()

  const detail = useAsync(
    () => api.get<Complaint>(`/api/v1/complaints/${complaintId}`, { estate_id: estateId }),
    [estateId, complaintId],
  )
  const events = useAsync(
    () => api.get<ComplaintEvent[]>(`/api/v1/complaints/${complaintId}/events`, { estate_id: estateId }),
    [estateId, complaintId],
  )
  const isAdmin = user?.role === 'hoa_admin'
  const workOrders = useAsync(
    () =>
      isAdmin
        ? api.get<Page<WorkOrder>>('/api/v1/work-orders', {
            estate_id: estateId,
            complaint_id: complaintId,
            size: 10,
          })
        : Promise.resolve(null),
    [estateId, complaintId, isAdmin],
  )

  const complaint = detail.data
  const status = complaint?.status ?? null
  const activeOrder = (workOrders.data?.items ?? []).find((order) => order.status !== 'cancelled')
  const refresh = () => {
    detail.reload()
    events.reload()
    workOrders.reload()
    onChanged()
  }

  return (
    <Drawer
      open
      onClose={onClose}
      title={complaint ? `Complaint #${complaint.id}` : 'Complaint'}
      subtitle={complaint ? `${displayLabel(complaint.category)} · unit ${complaint.unit_id}` : undefined}
    >
      {detail.loading ? (
        <LoadingState label="Loading complaint" />
      ) : detail.error ? (
        <ErrorState message={detail.error.message} requestId={detail.error.requestId} />
      ) : complaint ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone={complaintStatus[status ?? 'submitted']?.tone ?? 'neutral'} glyph={complaintStatus[status ?? 'submitted']?.glyph}>
              {complaintStatus[status ?? 'submitted']?.label ?? status ?? '—'}
            </Chip>
            <Chip tone={priorityMeta[complaint.priority]?.tone ?? 'neutral'} glyph={priorityMeta[complaint.priority]?.glyph}>
              {displayLabel(complaint.priority)}
            </Chip>
            {complaint.is_anonymous ? <Chip glyph="◍">Anonymous</Chip> : null}
          </div>

          <p className="text-[14px] leading-relaxed text-ink">{complaint.description}</p>

          <div>
            <h3 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
              Record
            </h3>
            <div className="mt-2">
              <Row label="Unit">#{complaint.unit_id}</Row>
              <Row label="Logged">{fullDate(complaint.created_at)}</Row>
              <Row label="Age">{relativeDays(complaint.created_at)}</Row>
              <Row label="Reviewed">{fullDate(complaint.reviewed_at)}</Row>
              <Row label="Assigned">{fullDate(complaint.assigned_at)}</Row>
              <Row label="Started">{fullDate(complaint.started_at)}</Row>
              <Row label="Resolved">{fullDate(complaint.resolved_at)}</Row>
              {complaint.user_id !== null ? (
                <Row label="Resident">user #{complaint.user_id}</Row>
              ) : (
                <Row label="Resident">hidden (anonymous)</Row>
              )}
            </div>
          </div>

          {isAdmin ? (
            <div>
              <h3 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
                Maintenance
              </h3>
              <div className="mt-2">
                {workOrders.loading ? (
                  <LoadingState label="Loading work orders" />
                ) : activeOrder ? (
                  <div className="hairline rounded-xs bg-surface p-3.5">
                    <div className="flex items-center justify-between gap-3">
                      <span className="num flex items-center gap-2 text-[13px] font-medium">
                        <IconWrench size={15} className="text-accent-ink" />
                        WO-{String(activeOrder.id).padStart(4, '0')}
                      </span>
                      <Chip
                        tone={workOrderStatus[activeOrder.status ?? 'assigned']?.tone ?? 'neutral'}
                        glyph={workOrderStatus[activeOrder.status ?? 'assigned']?.glyph}
                      >
                        {workOrderStatus[activeOrder.status ?? 'assigned']?.label}
                      </Chip>
                    </div>
                    <div className="mt-2.5">
                      <Row label="Provider">#{activeOrder.provider_id}</Row>
                      <Row label="Job cost">{money(activeOrder.job_cost)}</Row>
                      <Row label="Assigned">{fullDate(activeOrder.assigned_at)}</Row>
                      <Row label="Estimated completion">
                        {fullDate(activeOrder.estimated_completion_date)}
                      </Row>
                      <Row label="Resident rating">
                        {activeOrder.resident_rating ? `${activeOrder.resident_rating} / 5` : '—'}
                      </Row>
                    </div>
                    {activeOrder.completion_notes ? (
                      <p className="mt-2.5 border-t border-ink/10 pt-2.5 text-[12.5px] text-ink-soft">
                        {activeOrder.completion_notes}
                      </p>
                    ) : null}
                  </div>
                ) : status === 'submitted' ? (
                  <p className="text-[13px] text-ink-muted">
                    Move this complaint under review before assigning a provider.
                  </p>
                ) : (
                  <div className="hairline rounded-xs bg-surface p-4">
                    <p className="mb-3 text-[13px] text-ink-soft">
                      No active work order. Assign a verified provider to start the resolution clock.
                    </p>
                    <AssignProviderForm complaintId={complaint.id} onDone={refresh} />
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {/* Advisory triage review: HOA admins only. The endpoints are
              admin-only too, and residents never see this panel. */}
          {isAdmin && estateId !== null ? (
            <div>
              <h3 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
                AI triage
              </h3>
              <div className="mt-2 hairline rounded-xs bg-surface p-4">
                <TriageSuggestion
                  estateId={estateId}
                  complaintId={complaint.id}
                  isAnonymous={Boolean(complaint.is_anonymous)}
                />
              </div>
            </div>
          ) : null}

          {isAdmin && status === 'submitted' ? (
            <div>
              <h3 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
                HOA action
              </h3>
              <div className="mt-2 hairline rounded-xs bg-surface p-4">
                <ReviewAction complaintId={complaint.id} onDone={refresh} />
              </div>
            </div>
          ) : null}

          {/* The resident who logged the complaint: the repair raised for it, and
              the rating they are the only person entitled to give. */}
          {!isAdmin && estateId !== null ? (
            <div>
              <h3 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
                Repair progress
              </h3>
              <div className="mt-2">
                <ResidentWorkOrder complaintId={complaint.id} onDone={refresh} />
              </div>
            </div>
          ) : null}

          <div>
            <h3 className="text-[12px] font-medium tracking-wider text-ink-muted uppercase">
              Lifecycle evidence (append-only)
            </h3>
            <div className="mt-3">
              {events.loading ? (
                <LoadingState label="Loading history" />
              ) : events.error ? (
                <ErrorState message={events.error.message} requestId={events.error.requestId} />
              ) : (
                <Lifecycle events={events.data ?? []} status={status} />
              )}
            </div>
          </div>
        </div>
      ) : null}
    </Drawer>
  )
}
