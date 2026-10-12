import { useState } from 'react'
import { ComplaintDrawer } from '../components/ComplaintDrawer'
import { IconPlus, IconSearch } from '../components/Icons'
import { RequireEstate } from '../components/RequireEstate'
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
  Select,
  TableShell,
  Td,
  Textarea,
  Th,
  cx,
} from '../components/ui'
import { complaintCategories, complaintPriorities } from '../api/generated/enums'
import { useAuth } from '../context/AuthContext'
import { useEstateScope } from '../context/EstateContext'
import { api, ApiError } from '../lib/api'
import { complaintStatus, priorityMeta } from '../lib/display'
import { displayLabel, relativeDays } from '../lib/format'
import type { Complaint, Page, Property } from '../lib/types'
import { useAsync } from '../lib/useAsync'

export function LogComplaintDrawer({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { estateId, estate } = useEstateScope()
  const { user } = useAuth()
  const isAdmin = user?.role === 'hoa_admin'

  const properties = useAsync(
    () => api.get<Page<Property>>('/api/v1/properties', { estate_id: estateId, size: 100 }),
    [estateId],
  )

  const [unitId, setUnitId] = useState('')
  const [category, setCategory] = useState<string>(complaintCategories[0])
  const [priority, setPriority] = useState('normal')
  const [description, setDescription] = useState('')
  const [anonymous, setAnonymous] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)

  const ownedUnits = estate?.property_ids ?? []
  const units = (properties.data?.items ?? []).filter(
    (property) => isAdmin || ownedUnits.includes(property.id),
  )

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      await api.post<Complaint>(
        '/api/v1/complaints',
        {
          unit_id: Number(unitId),
          category,
          description: description.trim(),
          priority,
          is_anonymous: anonymous,
        },
        { estate_id: estateId },
      )
      onDone()
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not log the complaint.'))
    } finally {
      setBusy(false)
    }
  }

  const invalid = !unitId || description.trim().length < 5

  return (
    <Drawer
      open
      onClose={onClose}
      title="Log a complaint"
      subtitle={estate ? estate.estate_name : undefined}
      footer={
        <div className="flex items-center justify-between gap-3">
          <span className="text-[12px] text-ink-muted">
            {description.trim().length}/5000 characters
          </span>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" onClick={submit} disabled={busy || invalid}>
              {busy ? 'Logging…' : 'Log complaint'}
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}

        <p className="border-l-2 border-l-accent bg-accent-wash px-3.5 py-3 text-[12.5px] text-ink-soft">
          Your complaint starts the resolution clock. Every status change is retained as evidence, and
          the resolution time it produces feeds the estate's Living Score.
        </p>

        {properties.loading ? (
          <LoadingState label="Loading units" />
        ) : properties.error ? (
          <ErrorState message={properties.error.message} requestId={properties.error.requestId} />
        ) : units.length === 0 ? (
          <ErrorState
            title="No unit linked to your account"
            message="You can only log a complaint against a unit you are a member of. Ask your HOA to link your unit."
          />
        ) : (
          <Field label="Which unit?" hint={isAdmin ? 'Admins may log on behalf of any estate unit.' : undefined}>
            <Select value={unitId} onChange={(event) => setUnitId(event.target.value)}>
              <option value="">Select a unit…</option>
              {units.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.unit_no} — {property.street_address}
                </option>
              ))}
            </Select>
          </Field>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Category">
            <Select value={category} onChange={(event) => setCategory(event.target.value)}>
              {complaintCategories.map((item) => (
                <option key={item} value={item}>
                  {displayLabel(item)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Priority">
            <Select value={priority} onChange={(event) => setPriority(event.target.value)}>
              {complaintPriorities.map((value) => (
                <option key={value} value={value}>
                  {displayLabel(value)}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field
          label="What is wrong?"
          hint="Be specific: location, when it started, and what you have already tried."
          error={description.length > 0 && description.trim().length < 5 ? 'Describe the issue in at least 5 characters.' : null}
        >
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            maxLength={5000}
            placeholder="Sewage overflow at the Block C boundary — started last night and is pooling near the pedestrian gate."
          />
        </Field>

        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={anonymous}
            onChange={(event) => setAnonymous(event.target.checked)}
            className="mt-1 h-4 w-4 accent-[#1F6F5C]"
          />
          <span className="text-[13px] text-ink-soft">
            Report anonymously
            <span className="mt-0.5 block text-[12px] text-ink-muted">
              Your name is hidden from other members, including the HOA. You can still see your own
              complaint and its progress.
            </span>
          </span>
        </label>
      </div>
    </Drawer>
  )
}

function ComplaintsBody() {
  const { estateId } = useEstateScope()
  const { user } = useAuth()
  const isAdmin = user?.role === 'hoa_admin'

  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<number | null>(null)
  const [logging, setLogging] = useState(false)

  const complaints = useAsync(
    () =>
      api.get<Page<Complaint>>('/api/v1/complaints', {
        estate_id: estateId,
        page,
        size: 20,
        sort: '-created_at',
        status: status || undefined,
        category: category || undefined,
      }),
    [estateId, page, status, category],
  )

  const items = complaints.data?.items ?? []
  const pages = complaints.data?.pages ?? 0
  const canLog = user?.role === 'resident' || isAdmin

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Operational signals
          </p>
          <h1 className="mt-2 text-[26px] leading-tight font-semibold">
            {isAdmin ? 'Complaints' : 'Your complaints'}
          </h1>
          <p className="mt-1 text-[13.5px] text-ink-muted">
            {isAdmin
              ? 'Every complaint logged in this estate, with its lifecycle evidence.'
              : 'Issues you have logged. Your HOA sees them; other residents do not.'}
          </p>
        </div>
        {canLog ? (
          <Button variant="primary" onClick={() => setLogging(true)}>
            <IconPlus size={16} />
            Log a complaint
          </Button>
        ) : null}
      </header>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <label className="min-w-[11rem] flex-1">
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
            {Object.entries(complaintStatus)
              .filter(([key]) => key !== 'closed')
              .map(([key, meta]) => (
                <option key={key} value={key}>
                  {meta.label}
                </option>
              ))}
          </Select>
        </label>

        <label className="min-w-[11rem] flex-1">
          <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Category
          </span>
          <Select
            value={category}
            onChange={(event) => {
              setCategory(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All categories</option>
            {complaintCategories.map((item) => (
              <option key={item} value={item}>
                {displayLabel(item)}
              </option>
            ))}
          </Select>
        </label>

        <div className="flex items-center gap-2">
          <Input
            className="hidden sm:block"
            placeholder="Search the table below"
            onKeyDown={(event) => {
              if (event.key !== 'Enter') return
              const term = (event.target as HTMLInputElement).value.trim().toLowerCase()
              if (!term) return
              const match = items.find(
                (item) =>
                  item.description.toLowerCase().includes(term) ||
                  String(item.id) === term ||
                  item.category.includes(term),
              )
              if (match) setOpenId(match.id)
            }}
          />
          <span className="text-ink-muted" aria-hidden="true">
            <IconSearch size={17} />
          </span>
        </div>
      </Card>

      {complaints.loading ? (
        <LoadingState label="Loading complaints" />
      ) : complaints.error ? (
        <ErrorState
          message={complaints.error.message}
          requestId={complaints.error.requestId}
          action={
            <Button variant="secondary" onClick={complaints.reload}>
              Try again
            </Button>
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          title={isAdmin ? 'No complaints match these filters' : 'You have not logged any complaints'}
          body={
            isAdmin
              ? 'Clear the filters, or wait for residents to log an issue. Every complaint becomes a health signal.'
              : 'When something in your estate needs fixing, log it here. You will be able to follow it to resolution.'
          }
          action={canLog ? <Button variant="primary" onClick={() => setLogging(true)}>Log a complaint</Button> : undefined}
        />
      ) : (
        <>
          <TableShell>
            <thead>
              <tr>
                <Th className="w-20">Ref</Th>
                <Th>Issue</Th>
                <Th className="w-28">Category</Th>
                <Th className="w-28">Priority</Th>
                <Th className="w-36">Status</Th>
                <Th className="w-24 text-right">Logged</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const statusMeta = complaintStatus[item.status ?? 'submitted']
                const priority = priorityMeta[item.priority] ?? priorityMeta.normal
                return (
                  <tr
                    key={item.id}
                    onClick={() => setOpenId(item.id)}
                    className={cx(
                      'cursor-pointer transition-colors hover:bg-accent-wash/40',
                      openId === item.id && 'bg-accent-wash/60',
                    )}
                  >
                    <Td className="num font-medium">#{item.id}</Td>
                    <Td>
                      <span className="line-clamp-1 max-w-[38rem]">{item.description}</span>
                      <span className="num mt-0.5 block text-[11.5px] text-ink-muted">
                        unit {item.unit_id}
                        {item.is_anonymous ? ' · anonymous' : ''}
                      </span>
                    </Td>
                    <Td className="text-ink-soft">{displayLabel(item.category)}</Td>
                    <Td>
                      <Chip tone={priority.tone} glyph={priority.glyph}>
                        {displayLabel(item.priority)}
                      </Chip>
                    </Td>
                    <Td>
                      <Chip tone={statusMeta?.tone ?? 'neutral'} glyph={statusMeta?.glyph}>
                        {statusMeta?.label ?? item.status}
                      </Chip>
                    </Td>
                    <Td className="num text-right text-ink-muted">
                      {relativeDays(item.created_at)}
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </TableShell>

          <div className="flex items-center justify-between gap-3">
            <p className="num text-[12px] text-ink-muted">
              {complaints.data?.total ?? 0} complaints · page {complaints.data?.page ?? 1} of{' '}
              {Math.max(pages, 1)}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={page >= Math.max(pages, 1)}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}

      {openId !== null ? (
        <ComplaintDrawer
          complaintId={openId}
          onClose={() => setOpenId(null)}
          onChanged={complaints.reload}
        />
      ) : null}

      {logging ? (
        <LogComplaintDrawer
          onClose={() => setLogging(false)}
          onDone={() => {
            setLogging(false)
            complaints.reload()
          }}
        />
      ) : null}
    </div>
  )
}

export function Complaints() {
  return (
    <RequireEstate>
      <ComplaintsBody />
    </RequireEstate>
  )
}
