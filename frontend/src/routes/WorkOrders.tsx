import { useState } from 'react'
import { IconSearch, IconWrench } from '../components/Icons'
import { RequireEstate } from '../components/RequireEstate'
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Select,
  TableShell,
  Td,
  Textarea,
  Th,
  cx,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useEstateScope } from '../context/EstateContext'
import { api, ApiError } from '../lib/api'
import { workOrderStatus } from '../lib/display'
import { fullDate, money, relativeDays, titleCase } from '../lib/format'
import type { Page, WorkOrder } from '../lib/types'
import { useAsync } from '../lib/useAsync'

/* ------------------------------------------------------------ admin view */

function AdminWorkOrders() {
  const { estateId } = useEstateScope()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const workOrders = useAsync(
    () =>
      api.get<Page<WorkOrder>>('/api/v1/work-orders', {
        estate_id: estateId,
        page,
        size: 20,
        sort: '-created_at',
        status: status || undefined,
      }),
    [estateId, page, status],
  )

  const items = workOrders.data?.items ?? []
  const pages = workOrders.data?.pages ?? 0

  return (
    <>
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
        <p className="text-[12.5px] text-ink-muted">
          Assigned providers update progress from their own account. Administrators see the record;
          they do not edit it.
        </p>
      </Card>

      {workOrders.loading ? (
        <LoadingState label="Loading work orders" />
      ) : workOrders.error ? (
        <ErrorState message={workOrders.error.message} requestId={workOrders.error.requestId} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No work orders match these filters"
          body="A work order is raised from a complaint that is under review. Assign a verified provider there and it appears here."
        />
      ) : (
        <>
          <TableShell>
            <thead>
              <tr>
                <Th className="w-24">Ref</Th>
                <Th className="w-28">Complaint</Th>
                <Th className="w-28">Provider</Th>
                <Th className="w-36">Status</Th>
                <Th className="w-32 text-right">Job cost</Th>
                <Th className="w-28 text-right">Rating</Th>
                <Th className="w-32 text-right">Assigned</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((order) => {
                const meta = workOrderStatus[order.status ?? 'assigned']
                return (
                  <tr key={order.id}>
                    <Td className="num font-medium">WO-{String(order.id).padStart(4, '0')}</Td>
                    <Td className="num">#{order.complaint_id}</Td>
                    <Td className="num">#{order.provider_id}</Td>
                    <Td>
                      <Chip tone={meta?.tone ?? 'neutral'} glyph={meta?.glyph}>
                        {meta?.label ?? order.status}
                      </Chip>
                    </Td>
                    <Td className="num text-right">{money(order.job_cost)}</Td>
                    <Td className="num text-right">
                      {order.resident_rating ? `${order.resident_rating} / 5` : '—'}
                    </Td>
                    <Td className="num text-right text-ink-muted">
                      {relativeDays(order.assigned_at)}
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </TableShell>

          <div className="flex items-center justify-between gap-3">
            <p className="num text-[12px] text-ink-muted">
              {workOrders.data?.total ?? 0} work orders · page {workOrders.data?.page ?? 1} of{' '}
              {Math.max(pages, 1)}
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
    </>
  )
}

/* --------------------------------------------------------- provider view */

function ProviderWorkOrders() {
  const { estateId } = useEstateScope()
  const [reference, setReference] = useState('')
  const [order, setOrder] = useState<WorkOrder | null>(null)
  const [lookupError, setLookupError] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)

  const [status, setStatus] = useState('in_progress')
  const [cost, setCost] = useState('')
  const [notes, setNotes] = useState('')
  const [estimated, setEstimated] = useState('')
  const [saveError, setSaveError] = useState<ApiError | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  async function lookup() {
    const id = Number(reference.replace(/\D/g, ''))
    if (!id) {
      setLookupError(new ApiError(0, 'Enter the numeric reference from your assignment.'))
      return
    }
    setBusy(true)
    setLookupError(null)
    setSaved(false)
    try {
      const found = await api.get<WorkOrder>(`/api/v1/work-orders/${id}`, { estate_id: estateId })
      setOrder(found)
      setStatus(found.status ?? 'in_progress')
      setCost(found.job_cost ?? '')
      setNotes(found.completion_notes ?? '')
      setEstimated(found.estimated_completion_date ? found.estimated_completion_date.slice(0, 10) : '')
    } catch (cause) {
      setOrder(null)
      setLookupError(
        cause instanceof ApiError
          ? cause
          : new ApiError(0, 'Could not look up that work order.'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    if (!order) return
    setSaving(true)
    setSaveError(null)
    setSaved(false)
    try {
      const updated = await api.patch<WorkOrder>(
        `/api/v1/work-orders/${order.id}`,
        {
          status,
          job_cost: cost === '' ? null : Number(cost),
          completion_notes: notes.trim() || null,
          estimated_completion_date: estimated ? new Date(estimated).toISOString() : null,
        },
        { estate_id: estateId },
      )
      setOrder(updated)
      setSaved(true)
    } catch (cause) {
      setSaveError(
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not update the work order.'),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
      <Card className="p-5">
        <h2 className="text-[15px] font-semibold">Find your assignment</h2>
        <p className="mt-1.5 text-[13px] text-ink-soft">
          Enter the work order reference from your assignment notification. You can only open work
          assigned to your provider profile.
        </p>
        <div className="mt-4 flex gap-2">
          <Input
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && lookup()}
            placeholder="WO-0002 or 2"
            aria-label="Work order reference"
          />
          <Button variant="primary" onClick={lookup} disabled={busy}>
            <IconSearch size={16} />
            {busy ? 'Looking…' : 'Open'}
          </Button>
        </div>

        {lookupError ? (
          <div className="mt-4">
            <ErrorState message={lookupError.message} requestId={lookupError.requestId} />
          </div>
        ) : null}

        <div className="mt-5 border-t border-ink/15 pt-4">
          <p className="text-[12px] text-ink-muted">
            Assignments are scoped to the estate you are a member of, and to your own provider
            profile. A work order belonging to another provider returns forbidden, not a record.
          </p>
        </div>
      </Card>

      <Card className="p-5">
        {order ? (
          <>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="num text-[15px] font-semibold">
                  WO-{String(order.id).padStart(4, '0')}
                </h2>
                <p className="num mt-1 text-[12px] text-ink-muted">
                  complaint #{order.complaint_id} · provider #{order.provider_id}
                </p>
              </div>
              <Chip
                tone={workOrderStatus[order.status ?? 'assigned']?.tone ?? 'neutral'}
                glyph={workOrderStatus[order.status ?? 'assigned']?.glyph}
              >
                {workOrderStatus[order.status ?? 'assigned']?.label ?? order.status}
              </Chip>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-3 border-y border-ink/15 py-3">
              <div>
                <dt className="text-[11px] tracking-wider text-ink-muted uppercase">Assigned</dt>
                <dd className="num mt-0.5 text-[13px]">{fullDate(order.assigned_at)}</dd>
              </div>
              <div>
                <dt className="text-[11px] tracking-wider text-ink-muted uppercase">Current cost</dt>
                <dd className="num mt-0.5 text-[13px]">{money(order.job_cost)}</dd>
              </div>
            </dl>

            <div className="mt-4 space-y-4">
              {saveError ? (
                <ErrorState message={saveError.message} requestId={saveError.requestId} />
              ) : null}
              {saved ? (
                <div className="border-l-2 border-l-accent bg-accent-wash px-3.5 py-2.5 text-[13px] text-accent-ink">
                  Work order updated. The estate's maintenance record now reflects this change.
                </div>
              ) : null}

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Status">
                  <Select value={status} onChange={(event) => setStatus(event.target.value)}>
                    {Object.entries(workOrderStatus).map(([key, meta]) => (
                      <option key={key} value={key}>
                        {meta.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Job cost (ZAR)">
                  <Input
                    inputMode="decimal"
                    value={cost}
                    onChange={(event) => setCost(event.target.value)}
                    placeholder="2400.00"
                  />
                </Field>
              </div>

              <Field label="Estimated completion">
                <Input
                  type="date"
                  value={estimated}
                  onChange={(event) => setEstimated(event.target.value)}
                />
              </Field>

              <Field
                label="Completion notes"
                hint="What was done, parts used, anything the next contractor should know."
              >
                <Textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Replaced the failed section of pipe and pressure-tested the line."
                />
              </Field>

              <Button variant="primary" onClick={save} disabled={saving}>
                <IconWrench size={16} />
                {saving ? 'Saving…' : 'Save update'}
              </Button>
            </div>
          </>
        ) : (
          <div className="flex h-full min-h-48 flex-col items-center justify-center text-center">
            <span className="text-ink-muted">
              <IconWrench size={26} />
            </span>
            <p className="mt-3 text-[14px] font-medium">No work order open</p>
            <p className="mt-1 max-w-sm text-[13px] text-ink-muted">
              Open an assignment to update its status, cost and completion evidence.
            </p>
          </div>
        )}
      </Card>
    </div>
  )
}

export function WorkOrders() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'hoa_admin'

  return (
    <RequireEstate>
      <div className="space-y-5">
        <header>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Maintenance intelligence
          </p>
          <h1 className="mt-2 text-[26px] leading-tight font-semibold">Work orders</h1>
          <p className="mt-1 text-[13.5px] text-ink-muted">
            {isAdmin
              ? 'Resolution time, cost and provider performance — the operational quality behind the estate’s health.'
              : 'Update the status, cost and completion evidence for work assigned to you.'}
          </p>
        </header>

        <div className={cx(isAdmin ? '' : '')}>
          {isAdmin ? <AdminWorkOrders /> : <ProviderWorkOrders />}
        </div>

        {!isAdmin ? (
          <p className="text-[12px] text-ink-muted">
            Note for the pilot: {titleCase('service_provider')} accounts cannot list all work orders
            yet — assignments are opened by reference. A “my assignments” feed is part of the next
            build.
          </p>
        ) : null}
      </div>
    </RequireEstate>
  )
}
