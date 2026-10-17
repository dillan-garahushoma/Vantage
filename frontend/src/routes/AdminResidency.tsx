import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { RequireEstate } from '../components/RequireEstate'
import { IconCheck, IconClose, IconReport, IconSearch } from '../components/Icons'
import {
  Button,
  Card,
  Chip,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  SectionTitle,
  Select,
  TableShell,
  Td,
  Th,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useEstateScope } from '../context/EstateContext'
import { ApiError } from '../lib/api'
import { fullDate, relativeDays } from '../lib/format'
import {
  approveResidencyRequest,
  asResidencyStatus,
  listResidencyRequests,
  pendingResidencyCount,
  rejectResidencyRequest,
  RESIDENCY_STATUS,
} from '../lib/residency'
import type { ResidencyRequest } from '../lib/contract'
import { useAsync } from '../lib/useAsync'

function toApiError(cause: unknown, fallback: string): ApiError {
  return cause instanceof ApiError ? cause : new ApiError(0, fallback)
}

/** A tiny pending-count badge for the header, muted while it loads. */
function PendingBadge({ count, loading }: { count: number | null; loading: boolean }) {
  if (loading) return <Chip>checking…</Chip>
  if (count === null) return null
  return count > 0 ? (
    <Chip tone="warn">{count} awaiting review</Chip>
  ) : (
    <Chip tone="good">nothing pending</Chip>
  )
}

/* ------------------------------------------------------------------ detail */

function RequestDrawer({
  request,
  estateName,
  onClose,
  onDecided,
}: {
  request: ResidencyRequest
  estateName: string
  onClose: () => void
  onDecided: () => void
}) {
  const { estateId } = useEstateScope()
  const scope = estateId ?? 0
  const [confirming, setConfirming] = useState<'approve' | 'reject' | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [done, setDone] = useState<string | null>(null)

  const status = asResidencyStatus(request.status)
  const meta = RESIDENCY_STATUS[status]
  const decided = status !== 'pending'

  async function decide(decision: 'approve' | 'reject') {
    if (!scope) return
    setBusy(true)
    setError(null)
    try {
      if (decision === 'approve') {
        await approveResidencyRequest(scope, request.request_id)
        setDone(`${request.applicant_name} now has resident access to unit ${request.unit_no}.`)
      } else {
        await rejectResidencyRequest(scope, request.request_id, note)
        setDone(`${request.applicant_name} was declined. They were told the outcome by email.`)
      }
      setConfirming(null)
      onDecided()
    } catch (cause) {
      setError(toApiError(cause, 'Could not record that decision.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Drawer
      open
      onClose={onClose}
      title={request.applicant_name}
      subtitle={`unit ${request.unit_no} · request #${request.request_id}`}
    >
      <div className="space-y-6">
        {error ? (
          <ErrorState
            title={error.status === 409 ? 'Someone already decided this' : 'Could not record that decision'}
            message={error.message}
            requestId={error.requestId}
          />
        ) : null}
        {done ? (
          <div className="hairline rounded-xs border-l-2 border-l-accent bg-accent-wash px-3.5 py-3">
            <p className="text-[13.5px] text-accent-ink">{done}</p>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={meta.tone}>{meta.label}</Chip>
          <Chip>Submitted {relativeDays(request.created_at)}</Chip>
        </div>

        <dl className="space-y-3">
          {(
            [
              ['Applicant', request.applicant_name],
              ['Email', request.applicant_email],
              ['Phone', request.applicant_phone ?? 'not supplied'],
              ['Estate', estateName],
              ['Unit', request.unit_no],
              ['Submitted', fullDate(request.created_at)],
              ['Decided', request.decided_at ? fullDate(request.decided_at) : '—'],
            ] as Array<[string, string]>
          ).map(([label, value]) => (
            <div key={label} className="flex items-baseline justify-between gap-4 border-b border-ink/10 pb-2">
              <dt className="text-[12.5px] text-ink-muted">{label}</dt>
              <dd className="min-w-0 truncate text-right text-[13px] font-medium">{value}</dd>
            </div>
          ))}
        </dl>

        {request.note ? (
          <div className="hairline rounded-xs bg-paper px-3.5 py-3">
            <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
              Note from the applicant
            </p>
            <p className="mt-1.5 text-[13px] text-ink-soft">{request.note}</p>
          </div>
        ) : null}

        {decided ? (
          <div className="text-[13px] text-ink-soft">
            <p>{meta.hint}</p>
            {request.decision_note ? (
              <p className="mt-1.5">
                <span className="font-medium">Note recorded:</span> {request.decision_note}
              </p>
            ) : null}
          </div>
        ) : confirming === null ? (
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" onClick={() => setConfirming('approve')}>
              <IconCheck size={16} />
              Approve
            </Button>
            <Button variant="danger" onClick={() => setConfirming('reject')}>
              <IconClose size={16} />
              Reject
            </Button>
          </div>
        ) : confirming === 'approve' ? (
          <div className="hairline rounded-xs bg-accent-wash/50 p-4">
            <p className="text-[13.5px] font-medium">Approve {request.applicant_name}?</p>
            <p className="mt-1 text-[12.5px] text-ink-soft">
              This grants resident access to unit {request.unit_no} of {estateName} and records you
              as the deciding administrator. It cannot be undone from here.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="primary" onClick={() => decide('approve')} disabled={busy}>
                {busy ? 'Approving…' : 'Yes, approve access'}
              </Button>
              <Button variant="ghost" onClick={() => setConfirming(null)} disabled={busy}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="hairline rounded-xs bg-signal-wash/60 p-4">
            <p className="text-[13.5px] font-medium">Reject {request.applicant_name}?</p>
            <p className="mt-1 text-[12.5px] text-ink-soft">
              No access is granted and the applicant is told the outcome. The reason below is
              optional and shown to the applicant.
            </p>
            <div className="mt-3">
              <Field label="Reason (optional)" hint="Max 500 characters.">
                <Input
                  value={note}
                  maxLength={500}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Not on the lease"
                />
              </Field>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="danger" onClick={() => decide('reject')} disabled={busy}>
                {busy ? 'Recording…' : 'Yes, reject the request'}
              </Button>
              <Button variant="ghost" onClick={() => setConfirming(null)} disabled={busy}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>
    </Drawer>
  )
}

/* ------------------------------------------------------------------ screen */

const STATUS_FILTERS = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'Awaiting review' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Not approved' },
] as const

function AdminResidencyBody() {
  const { estateId, estate } = useEstateScope()
  const { user } = useAuth()
  const scope = estateId ?? 0
  const isAdmin = user?.role === 'hoa_admin'

  const [params, setParams] = useSearchParams()
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [committed, setCommitted] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<ResidencyRequest | null>(null)

  const count = useAsync(
    () => (isAdmin && scope ? pendingResidencyCount(scope) : Promise.resolve(null)),
    [scope, isAdmin],
  )
  const queue = useAsync(
    () =>
      isAdmin && scope
        ? listResidencyRequests(scope, {
            status: (status as 'pending' | 'approved' | 'rejected' | '') || '',
            search: committed,
            page,
            page_size: 20,
          })
        : Promise.resolve(null),
    [scope, isAdmin, status, committed, page],
  )

  const items = queue.data?.items ?? []
  const pages = queue.data?.pages ?? 0

  // A notification email links straight to a request, so open it when present.
  const deepLinkedId = params.get('request')
  useEffect(() => {
    if (!deepLinkedId || selected) return
    const match = items.find((item) => String(item.request_id) === deepLinkedId)
    if (match) setSelected(match)
  }, [deepLinkedId, items, selected])

  function submitSearch(event: FormEvent) {
    event.preventDefault()
    setCommitted(search.trim())
    setPage(1)
  }

  function reloadAll() {
    queue.reload()
    count.reload()
  }

  function closeDrawer() {
    setSelected(null)
    if (deepLinkedId) {
      // Drop the deep-link param so the drawer does not immediately reopen.
      const next = new URLSearchParams(params)
      next.delete('request')
      setParams(next, { replace: true })
    }
  }

  if (!isAdmin) {
    return (
      <ErrorState
        title="Approving residents is an HOA administrator’s task"
        message="You are a member of this estate, but not its administrator. Residents' registration requests name and identify people, so only the estate office can decide them."
      />
    )
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Estate administration
          </p>
          <h1 className="mt-2 text-[26px] leading-tight font-semibold">Resident approvals</h1>
          <p className="mt-1 max-w-2xl text-[13.5px] text-ink-muted">
            People who asked to join {estate?.estate_name ?? 'this estate'}. Approving grants resident
            access to a unit; rejecting grants nothing. A join code still admits a resident
            immediately, so if someone you are about to approve already joined with a code, the
            request is approved without creating a second membership.
          </p>
        </div>
        <PendingBadge count={count.data?.pending ?? null} loading={count.loading} />
      </header>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <form onSubmit={submitSearch} className="flex min-w-[16rem] flex-1 items-end gap-2">
          <label className="min-w-0 flex-1">
            <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
              Search
            </span>
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Name, email or unit"
              aria-label="Search requests by name, email or unit"
            />
          </label>
          <Button type="submit" variant="secondary">
            <IconSearch size={16} />
            Search
          </Button>
        </form>
        <label className="min-w-[12rem]">
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
            {STATUS_FILTERS.map((option) => (
              <option key={option.value || 'all'} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </label>
        <p className="num pb-2 text-[12.5px] text-ink-muted">
          {queue.data?.total ?? 0} {queue.data?.total === 1 ? 'request' : 'requests'}
        </p>
      </Card>

      {queue.loading ? (
        <LoadingState label="Loading registration requests" />
      ) : queue.error ? (
        <ErrorState
          title="Could not read the approval queue"
          message={queue.error.message}
          requestId={queue.error.requestId}
          action={
            <Button variant="secondary" onClick={queue.reload}>
              Try again
            </Button>
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          title={committed || status ? 'No requests match' : 'No registration requests yet'}
          body={
            committed || status
              ? 'Clear the search or the status filter to see everything.'
              : 'When a resident asks to join this estate, the request appears here for you to approve or reject.'
          }
        />
      ) : (
        <>
          <TableShell>
            <thead>
              <tr>
                <Th>Applicant</Th>
                <Th className="w-24">Unit</Th>
                <Th className="w-40">Submitted</Th>
                <Th className="w-40">Status</Th>
                <Th className="w-28 text-right">Review</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((request) => {
                const meta = RESIDENCY_STATUS[asResidencyStatus(request.status)]
                return (
                  <tr
                    key={request.request_id}
                    onClick={() => setSelected(request)}
                    className="cursor-pointer transition-colors hover:bg-accent-wash/40"
                  >
                    <Td>
                      <span className="font-medium">{request.applicant_name}</span>
                      <span className="num mt-0.5 block text-[11.5px] text-ink-muted">
                        {request.applicant_email}
                      </span>
                    </Td>
                    <Td className="num">{request.unit_no}</Td>
                    <Td>
                      <span className="block text-[13px]">{fullDate(request.created_at)}</span>
                      <span className="num block text-[11.5px] text-ink-muted">
                        {relativeDays(request.created_at)}
                      </span>
                    </Td>
                    <Td>
                      <Chip tone={meta.tone}>{meta.label}</Chip>
                    </Td>
                    <Td className="text-right">
                      <span className="inline-flex items-center gap-1 text-[12.5px] font-medium text-accent-ink">
                        <IconReport size={14} />
                        {asResidencyStatus(request.status) === 'pending' ? 'Decide' : 'View'}
                      </span>
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </TableShell>

          <div className="flex items-center justify-between gap-3">
            <p className="num text-[12px] text-ink-muted">
              page {queue.data?.page ?? 1} of {Math.max(pages, 1)}
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

      <Card as="section" className="p-5">
        <SectionTitle title="What a decision does" />
        <ul className="space-y-1.5 text-[13px] text-ink-soft">
          <li>
            <span className="font-medium">Approve</span> creates the resident’s membership of the
            unit and records you as the deciding administrator, with the time. If they already joined
            with a code, the request is approved without creating a duplicate membership.
          </li>
          <li>
            <span className="font-medium">Reject</span> grants nothing and stores your optional
            reason. The applicant may ask to join again later.
          </li>
          <li>
            Every decision is final from this screen. A resident who should be removed after being
            approved is removed from <span className="font-medium">Members</span>.
          </li>
        </ul>
      </Card>

      {selected ? (
        <RequestDrawer
          request={selected}
          estateName={estate?.estate_name ?? 'this estate'}
          onClose={closeDrawer}
          onDecided={reloadAll}
        />
      ) : null}
    </div>
  )
}

export function AdminResidency() {
  return (
    <RequireEstate>
      <AdminResidencyBody />
    </RequireEstate>
  )
}
