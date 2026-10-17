import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useEstateScope } from '../../context/EstateContext'
import { api, ApiError } from '../../lib/api'
import { createWorkOrder, listEstateProviders } from '../../lib/estateAdmin'
import { relativeDays } from '../../lib/format'
import type { ServiceProvider, WorkOrder } from '../../lib/contract'
import type { Complaint, Page } from '../../lib/types'
import { Button } from '../ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Label } from '../ui/label'
import { toast } from '../ui/toast'
import { ErrorState } from '../ui'
import { StatusChip } from './StatusChip'

/** The complaints a work order can still be raised against. */
const OPEN_STATUSES = new Set(['submitted', 'reviewed', 'assigned', 'in_progress'])

const controlClass =
  'mt-2 h-11 w-full rounded-xl border border-line bg-surface px-3 text-[0.88rem] text-ink transition-colors duration-200 focus:border-brand focus:outline-none'

export interface WorkOrderDraft {
  complaintId?: number
  providerId?: number
  costZar?: number
  /** Context from the finding or row that opened the dialog. */
  title?: string
  asset?: string
  location?: string
  priority?: string
  description?: string
}

export interface CreateWorkOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaults?: WorkOrderDraft
  onCreated?: (order: WorkOrder) => void
}

/**
 * Raise a work order.
 *
 * This dialog submits the API's real contract: a work order in VALORA is the
 * *assignment of a provider to a complaint* (`POST /api/v1/work-orders` with
 * `complaint_id` + `provider_id`), not a free-standing job record. So it asks
 * which complaint the work resolves and which estate provider takes it, and shows
 * the finding it was opened from as context rather than inventing fields the
 * backend does not accept.
 *
 * Both the complaint list and the provider directory are estate-scoped server
 * responses, and the endpoint is administrator-only; a caller the server would
 * refuse never sees the form.
 */
export function CreateWorkOrderDialog({
  open,
  onOpenChange,
  defaults,
  onCreated,
}: CreateWorkOrderDialogProps) {
  const { estateId, estate } = useEstateScope()
  const { user } = useAuth()
  const isAdmin = user?.role === 'hoa_admin'

  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [providers, setProviders] = useState<ServiceProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<ApiError | null>(null)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const [saving, setSaving] = useState(false)

  const [complaintId, setComplaintId] = useState('')
  const [providerId, setProviderId] = useState('')
  const [cost, setCost] = useState('')
  const [estimated, setEstimated] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!open || !isAdmin || estateId === null) return
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    setSubmitError(null)
    setErrors({})
    setCost(defaults?.costZar ? String(defaults.costZar) : '')
    setEstimated('')

    Promise.all([
      api.get<Page<Complaint>>('/api/v1/complaints', {
        estate_id: estateId,
        size: 100,
        sort: '-created_at',
      }),
      listEstateProviders(estateId, { size: 100 }),
    ])
      .then(([complaintPage, providerPage]) => {
        if (cancelled) return
        const openComplaints = complaintPage.items.filter((item) =>
          OPEN_STATUSES.has(item.status ?? ''),
        )
        setComplaints(openComplaints)
        setProviders(providerPage.items)
        setComplaintId(
          defaults?.complaintId
            ? String(defaults.complaintId)
            : openComplaints.length === 1
              ? String(openComplaints[0].id)
              : '',
        )
        setProviderId(defaults?.providerId ? String(defaults.providerId) : '')
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setLoadError(
          cause instanceof ApiError
            ? cause
            : new ApiError(0, 'Could not load the estate’s complaints and providers.'),
        )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [open, isAdmin, estateId, defaults])

  async function submit() {
    const nextErrors: Record<string, string> = {}
    if (!complaintId) nextErrors.complaint = 'Choose the complaint this work order resolves.'
    if (!providerId) nextErrors.provider = 'Choose the provider who will do the work.'
    if (cost !== '' && Number.isNaN(Number(cost))) {
      nextErrors.cost = 'Enter a cost in rand, or leave it blank.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0 || estateId === null || saving) return

    setSaving(true)
    setSubmitError(null)
    try {
      const order = await createWorkOrder(estateId, {
        complaint_id: Number(complaintId),
        provider_id: Number(providerId),
        job_cost: cost === '' ? null : Number(cost),
        estimated_completion_date: estimated
          ? new Date(`${estimated}T12:00:00Z`).toISOString()
          : null,
      })
      toast({
        title: 'Work order raised',
        description: `WO-${String(order.id).padStart(4, '0')} is assigned and its SLA clock has started.`,
      })
      onCreated?.(order)
      onOpenChange(false)
    } catch (cause) {
      setSubmitError(
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not raise the work order.'),
      )
    } finally {
      setSaving(false)
    }
  }

  const contextRows = (
    [
      defaults?.title ? { label: 'Finding', value: defaults.title } : null,
      defaults?.asset ? { label: 'Asset', value: defaults.asset } : null,
      defaults?.location ? { label: 'Location', value: defaults.location } : null,
      defaults?.priority ? { label: 'Suggested priority', value: defaults.priority } : null,
    ] as ({ label: string; value: string } | null)[]
  ).filter((row): row is { label: string; value: string } => row !== null)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="scrollbar-slim max-h-[92vh] overflow-y-auto rounded-3xl p-0 sm:max-w-[620px]">
        <DialogHeader className="border-b border-line px-6 py-5">
          <DialogTitle>Create work order</DialogTitle>
          <DialogDescription>
            A work order assigns an estate provider to a complaint, so the repair keeps its evidence:
            who did the work, what it cost and how long it took.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 px-6 py-5">
          {!isAdmin ? (
            <ErrorState
              title="Only an estate administrator can raise a work order"
              message="Your account can follow a complaint and rate the completed work, but assigning a provider is an administrator action. The server enforces this too."
            />
          ) : loadError ? (
            <ErrorState message={loadError.message} requestId={loadError.requestId} />
          ) : loading ? (
            <p className="text-[0.85rem] text-ink-muted">
              Loading the estate’s complaints and providers…
            </p>
          ) : (
            <>
              {submitError ? (
                <ErrorState
                  title={
                    submitError.isForbidden
                      ? 'The server refused this assignment'
                      : 'The work order was not created'
                  }
                  message={submitError.message}
                  requestId={submitError.requestId}
                />
              ) : null}

              {contextRows.length > 0 ? (
                <div className="rounded-xl bg-canvas p-4">
                  <p className="text-[0.66rem] font-semibold tracking-[0.14em] text-brand-ink uppercase">
                    Raised from the finding
                  </p>
                  <dl className="mt-2.5 space-y-1.5">
                    {contextRows.map((row) => (
                      <div key={row.label} className="flex gap-3 text-[0.78rem]">
                        <dt className="w-32 shrink-0 text-ink/45">{row.label}</dt>
                        <dd className="min-w-0 font-medium text-ink/80">{row.value}</dd>
                      </div>
                    ))}
                  </dl>
                  {defaults?.description ? (
                    <p className="mt-3 border-t border-line pt-3 text-[0.78rem] leading-relaxed text-ink/60">
                      {defaults.description}
                    </p>
                  ) : null}
                </div>
              ) : null}

              <div>
                <Label htmlFor="work-order-complaint">Which complaint does this resolve?</Label>
                <select
                  id="work-order-complaint"
                  value={complaintId}
                  onChange={(event) => setComplaintId(event.target.value)}
                  className={controlClass}
                >
                  <option value="">Select an open complaint…</option>
                  {complaints.map((item) => (
                    <option key={item.id} value={item.id}>
                      #{item.id} · {item.description.slice(0, 60)} · {relativeDays(item.created_at)}
                    </option>
                  ))}
                </select>
                {errors.complaint ? (
                  <p className="mt-1.5 text-[0.75rem] font-medium text-signal-ink">
                    {errors.complaint}
                  </p>
                ) : complaints.length === 0 ? (
                  <p className="mt-1.5 text-[0.75rem] text-ink-muted">
                    There is no open complaint in {estate?.estate_name ?? 'this estate'} to attach a
                    work order to. Log the issue first, then assign a provider to it.
                  </p>
                ) : null}
              </div>

              <div>
                <Label htmlFor="work-order-provider">Provider</Label>
                <select
                  id="work-order-provider"
                  value={providerId}
                  onChange={(event) => setProviderId(event.target.value)}
                  className={controlClass}
                >
                  <option value="">Select a provider…</option>
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.full_name} · {provider.trade}
                      {provider.verified ? ' · verified' : ' · unverified'}
                    </option>
                  ))}
                </select>
                {errors.provider ? (
                  <p className="mt-1.5 text-[0.75rem] font-medium text-signal-ink">
                    {errors.provider}
                  </p>
                ) : providers.length === 0 ? (
                  <p className="mt-1.5 text-[0.75rem] text-ink-muted">
                    No provider is a member of this estate yet. Add one from Members before assigning
                    work.
                  </p>
                ) : (
                  <p className="mt-1.5 text-[0.75rem] text-ink-muted">
                    Only providers who are members of this estate appear here.
                  </p>
                )}
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <Label htmlFor="work-order-cost">Quoted cost (ZAR)</Label>
                  <input
                    id="work-order-cost"
                    inputMode="decimal"
                    value={cost}
                    onChange={(event) => setCost(event.target.value)}
                    placeholder="9800"
                    className={`num ${controlClass}`}
                  />
                  {errors.cost ? (
                    <p className="mt-1.5 text-[0.75rem] font-medium text-signal-ink">{errors.cost}</p>
                  ) : null}
                </div>
                <div>
                  <Label htmlFor="work-order-eta">Estimated completion</Label>
                  <input
                    id="work-order-eta"
                    type="date"
                    value={estimated}
                    onChange={(event) => setEstimated(event.target.value)}
                    className={controlClass}
                  />
                </div>
              </div>

              <div className="flex items-start gap-2.5 rounded-xl bg-canvas p-4">
                <StatusChip status={defaults?.priority ?? 'High'} size="sm" />
                <p className="text-[0.78rem] leading-relaxed text-ink/55">
                  The SLA window starts when the provider accepts the job, and the resolution time it
                  produces feeds this estate’s Living Score. A recommendation is not recorded as an
                  outcome until this work order exists.
                </p>
              </div>
            </>
          )}
        </div>

        <DialogFooter className="gap-2 border-t border-line px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="h-11 px-6">
            Cancel
          </Button>
          <Button
            variant="ink"
            onClick={() => void submit()}
            disabled={!isAdmin || loading || saving || loadError !== null}
            className="h-11 px-6"
          >
            {saving ? 'Creating…' : 'Create work order'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
