import { useState } from 'react'
import { Link } from 'react-router-dom'
import { IconAlert, IconArrowRight, IconClock, IconMegaphone, IconReport, IconWrench } from '../components/Icons'
import { HealthBrief } from '../components/HealthBrief'
import { LivingScorePanel } from '../components/LivingScore'
import { RequireEstate } from '../components/RequireEstate'
import { Card, Chip, EmptyState, ErrorState, LoadingState, SectionTitle, StatTile, cx } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useEstateScope } from '../context/EstateContext'
import { api, ApiError } from '../lib/api'
import { getLivingScore, recalculateLivingScore } from '../lib/analytics'
import { complaintStatus, priorityMeta, workOrderStatus } from '../lib/display'
import { durationHours, displayLabel, fullDate, money, relativeDays, shortDate } from '../lib/format'
import type { Announcement, Complaint, ComplaintStats, Page, Property, WorkOrder } from '../lib/types'
import { useAsync } from '../lib/useAsync'

const OPEN_STATUSES = new Set(['submitted', 'reviewed', 'assigned', 'in_progress'])

function EstateCard() {
  const { estate } = useEstateScope()
  if (!estate) return null

  return (
    <Card as="section" className="min-w-0 p-5">
      <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">Estate</p>
      <h2 className="mt-1 text-[17px] font-semibold">{estate.estate_name}</h2>
      <p className="num mt-1 text-[12.5px] text-ink-muted">
        {estate.suburb}, {estate.city}, {estate.province}
      </p>

      <dl className="mt-4 space-y-2.5">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[13px] text-ink-soft">Your role here</dt>
          <dd className="num text-[13px] font-medium">
            {estate.is_estate_admin
              ? 'HOA administrator'
              : estate.is_estate_provider
                ? 'Service provider'
                : (estate.membership_roles[0] ?? 'member')}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[13px] text-ink-soft">Units linked to you</dt>
          <dd className="num text-[13px] font-medium">{estate.property_ids.length}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[13px] text-ink-soft">Estate reference</dt>
          <dd className="num text-[13px] font-medium">#{estate.estate_id}</dd>
        </div>
      </dl>

      <p className="mt-4 border-t border-ink/15 pt-3 text-[12px] text-ink-muted">
        This identifier is resolved on the server from your membership. Supplying an estate number is
        never treated as proof of access.
      </p>
    </Card>
  )
}

function NeedsAttention({ complaints }: { complaints: Complaint[] }) {
  const open = complaints.filter((item) => OPEN_STATUSES.has(item.status ?? '')).slice(0, 5)

  return (
    <Card as="section" className="min-w-0 p-5">
      <SectionTitle
        title="Needs attention"
        hint="Unresolved complaints, newest operational risk first"
        action={
          <Link
            to="/app/complaints"
            className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-accent-ink hover:underline"
          >
            All complaints
            <IconArrowRight size={15} />
          </Link>
        }
      />
      {open.length === 0 ? (
        <p className="py-4 text-[13px] text-ink-muted">
          Nothing open. Every logged complaint has progressed past resolution.
        </p>
      ) : (
        <ul className="divide-y divide-ink/10">
          {open.map((item) => {
            const status = complaintStatus[item.status ?? 'submitted']
            const priority = priorityMeta[item.priority] ?? priorityMeta.normal
            return (
              <li key={item.id} className="flex items-start gap-3 py-3">
                <span className="mt-0.5 shrink-0">
                  <Chip tone={priority.tone} glyph={priority.glyph}>
                    {displayLabel(item.priority)}
                  </Chip>
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13.5px] text-ink">{item.description}</p>
                  <p className="num mt-0.5 text-[11.5px] text-ink-muted">
                    #{item.id} · {displayLabel(item.category)} · unit {item.unit_id} · logged {relativeDays(item.created_at)}
                  </p>
                </div>
                <span className="shrink-0">
                  <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
                    {status?.label ?? item.status ?? '—'}
                  </Chip>
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

function AnnouncementList({ announcements }: { announcements: Announcement[] }) {
  if (announcements.length === 0) {
    return (
      <EmptyState
        title="No announcements yet"
        body="When your HOA publishes a notice — an outage, an AGM, a security upgrade — it appears here for every member of the estate."
      />
    )
  }

  return (
    <ul className="divide-y divide-ink/10">
      {announcements.map((item) => (
        <li key={item.id} className="py-3.5">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-[14px] font-medium">{item.title}</h3>
            <span className="num shrink-0 text-[11.5px] text-ink-muted">
              {shortDate(item.created_at)}
            </span>
          </div>
          <p className="mt-1 line-clamp-2 text-[13px] text-ink-soft">{item.message}</p>
        </li>
      ))}
    </ul>
  )
}

function DashboardBody() {
  const { estateId } = useEstateScope()
  const { user } = useAuth()
  const isAdmin = user?.role === 'hoa_admin'

  const announcements = useAsync(
    () => api.get<Page<Announcement>>('/api/v1/announcements', { estate_id: estateId, size: 4 }),
    [estateId],
  )
  const complaints = useAsync(
    () =>
      api.get<Page<Complaint>>('/api/v1/complaints', {
        estate_id: estateId,
        size: 12,
        sort: '-created_at',
      }),
    [estateId],
  )
  const stats = useAsync(
    () =>
      isAdmin
        ? api.get<ComplaintStats>('/api/v1/complaints/stats', { estate_id: estateId })
        : Promise.resolve(null),
    [estateId, isAdmin],
  )
  const workOrders = useAsync(
    () =>
      isAdmin
        ? api.get<Page<WorkOrder>>('/api/v1/work-orders', { estate_id: estateId, size: 4 })
        : Promise.resolve(null),
    [estateId, isAdmin],
  )
  const properties = useAsync(
    () => api.get<Page<Property>>('/api/v1/properties', { estate_id: estateId, size: 100 }),
    [estateId],
  )
  // The stored snapshot, exactly as the engine wrote it: this screen never
  // calculates a score. A 404 (never scored) and an `insufficient_data` snapshot
  // are both rendered as "not enough data yet", never as a zero.
  const livingScore = useAsync(
    () => (estateId === null ? Promise.resolve(null) : getLivingScore(estateId)),
    [estateId],
  )
  // The one action on this panel. The server decides whether the caller may
  // calculate; a refusal is shown verbatim and nothing is recalculated locally.
  const [recalculating, setRecalculating] = useState(false)
  const [recalculateError, setRecalculateError] = useState<ApiError | null>(null)

  async function recalculateScore() {
    if (estateId === null || recalculating) return
    setRecalculating(true)
    setRecalculateError(null)
    try {
      await recalculateLivingScore(estateId)
      livingScore.reload()
    } catch (cause: unknown) {
      setRecalculateError(
        cause instanceof ApiError
          ? cause
          : new ApiError(0, cause instanceof Error ? cause.message : 'Something went wrong.'),
      )
    } finally {
      setRecalculating(false)
    }
  }

  const openCount = (complaints.data?.items ?? []).filter((item) =>
    OPEN_STATUSES.has(item.status ?? ''),
  ).length
  const unitCount = properties.data?.total ?? null
  const premierResolution = stats.data?.avg_resolution_hours

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            {isAdmin ? 'Governance overview' : 'Estate overview'}
          </p>
          <h1 className="mt-2 text-[26px] leading-tight font-semibold">Property health at a glance</h1>
          <p className="mt-1 text-[13.5px] text-ink-muted">
            Operational data as recorded by the estate. Updated {fullDate(new Date().toISOString())}.
          </p>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <LivingScorePanel
          snapshot={livingScore.data}
          loading={livingScore.loading}
          error={livingScore.error}
          onRetry={livingScore.reload}
          onRecalculate={isAdmin ? recalculateScore : undefined}
          recalculating={recalculating}
          recalculateError={recalculateError}
        />
        <EstateCard />
      </div>

      {/* ------------------------------------------------ KPI row */}
      {isAdmin ? (
        stats.loading ? (
          <LoadingState label="Loading estate metrics" />
        ) : stats.error ? (
          <ErrorState message={stats.error.message} requestId={stats.error.requestId} />
        ) : stats.data ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label="Complaints logged"
              value={String(stats.data.total)}
              hint={`${stats.data.total - (stats.data.by_status.resolved ?? 0) - (stats.data.by_status.rated ?? 0) - (stats.data.by_status.closed ?? 0)} still open`}
            />
            <StatTile
              label="Resolution rate"
              value={`${Number(stats.data.resolution_rate_pct).toFixed(0)}%`}
              tone="progress"
              hint="Share of complaints that reached resolved"
            />
            <StatTile
              label="Average resolution"
              value={durationHours(premierResolution)}
              tone={
                premierResolution && Number(premierResolution) > 24 * 5 ? 'warn' : 'good'
              }
              hint="Benchmark: 5 business days"
            />
            <StatTile
              label="Units on record"
              value={unitCount === null ? '—' : String(unitCount)}
              hint="Estate units registered in VALORA"
            />
          </div>
        ) : null
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatTile
            label={user?.role === 'resident' ? 'Your open complaints' : 'Open complaints'}
            value={String(openCount)}
            tone={openCount > 0 ? 'warn' : 'good'}
            hint={user?.role === 'resident' ? 'Issues you have logged' : 'Across the estate'}
          />
          <StatTile
            label="Estate units"
            value={unitCount === null ? '—' : String(unitCount)}
            hint="Registered in VALORA"
          />
          <StatTile
            label="Announcements"
            value={String(announcements.data?.total ?? 0)}
            hint="Published by the HOA"
          />
        </div>
      )}

      {/* ------------------------------------------------ estate health brief */}
      {estateId !== null ? <HealthBrief estateId={estateId} canGenerate={isAdmin} /> : null}

      {/* ------------------------------------------------ lower grid */}
      <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        {isAdmin ? (
          complaints.loading ? (
            <LoadingState label="Loading complaints" />
          ) : complaints.error ? (
            <ErrorState message={complaints.error.message} requestId={complaints.error.requestId} />
          ) : (
            <NeedsAttention complaints={complaints.data?.items ?? []} />
          )
        ) : (
          <Card as="section" className="min-w-0 p-5">
            <SectionTitle
              title={user?.role === 'resident' ? 'Your complaints' : 'Your activity'}
              hint="Only issues you logged are visible to you"
              action={
                user?.role === 'resident' ? (
                  <Link
                    to="/app/complaints"
                    className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-accent-ink hover:underline"
                  >
                    Open complaints
                    <IconArrowRight size={15} />
                  </Link>
                ) : null
              }
            />
            {complaints.loading ? (
              <LoadingState label="Loading complaints" />
            ) : complaints.error ? (
              <ErrorState message={complaints.error.message} requestId={complaints.error.requestId} />
            ) : (complaints.data?.items.length ?? 0) === 0 ? (
              <p className="py-4 text-[13px] text-ink-muted">
                {user?.role === 'resident'
                  ? 'You have not logged any complaints yet.'
                  : 'Nothing logged against your membership.'}
              </p>
            ) : (
              <ul className="divide-y divide-ink/10">
                {(complaints.data?.items ?? []).slice(0, 5).map((item) => {
                  const status = complaintStatus[item.status ?? 'submitted']
                  return (
                    <li key={item.id} className="flex items-start gap-3 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13.5px]">{item.description}</p>
                        <p className="num mt-0.5 text-[11.5px] text-ink-muted">
                          #{item.id} · {item.category} · {relativeDays(item.created_at)}
                        </p>
                      </div>
                      <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
                        {status?.label ?? item.status}
                      </Chip>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>
        )}

        <Card as="section" className="min-w-0 p-5">
          <SectionTitle
            title="Latest announcements"
            hint="Governance activity is itself a health signal"
            action={
              <Link
                to="/app/announcements"
                className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-accent-ink hover:underline"
              >
                All
                <IconArrowRight size={15} />
              </Link>
            }
          />
          {announcements.loading ? (
            <LoadingState label="Loading announcements" />
          ) : announcements.error ? (
            <ErrorState
              message={announcements.error.message}
              requestId={announcements.error.requestId}
            />
          ) : (
            <AnnouncementList announcements={announcements.data?.items ?? []} />
          )}
        </Card>
      </div>

      {isAdmin ? (
        <Card as="section" className="min-w-0 p-5">
          <SectionTitle
            title="Maintenance in flight"
            hint="Work orders measure operational quality, not just cost"
            action={
              <Link
                to="/app/work-orders"
                className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-accent-ink hover:underline"
              >
                All work orders
                <IconArrowRight size={15} />
              </Link>
            }
          />
          {workOrders.loading ? (
            <LoadingState label="Loading work orders" />
          ) : workOrders.error ? (
            <ErrorState message={workOrders.error.message} requestId={workOrders.error.requestId} />
          ) : (workOrders.data?.items.length ?? 0) === 0 ? (
            <p className="py-4 text-[13px] text-ink-muted">No work orders have been raised yet.</p>
          ) : (
            <ul className="divide-y divide-ink/10">
              {(workOrders.data?.items ?? []).map((order) => {
                const status = workOrderStatus[order.status ?? 'assigned']
                return (
                  <li key={order.id} className="flex flex-wrap items-center gap-3 py-3">
                    <IconWrench size={16} className="shrink-0 text-ink-muted" />
                    <span className="num text-[12.5px]">WO-{String(order.id).padStart(4, '0')}</span>
                    <span className="num text-[12.5px] text-ink-muted">
                      complaint #{order.complaint_id}
                    </span>
                    <span className="num text-[12.5px] text-ink-muted">
                      provider #{order.provider_id}
                    </span>
                    <span className="num ml-auto text-[12.5px]">{money(order.job_cost)}</span>
                    <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
                      {status?.label ?? order.status}
                    </Chip>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
      ) : null}

      {/* --------------------------------------------------- next steps */}
      {/* Only while there is nothing stored to show: once a snapshot exists the
          panel above carries its own explanation and this strip would repeat it. */}
      {!livingScore.loading && livingScore.data === null ? (
        <Card as="section" className="bg-ink p-5 text-paper">
          <div className="flex flex-wrap items-start gap-4">
            <IconAlert size={20} className="mt-0.5 shrink-0 text-paper/70" />
            <div className="min-w-0 flex-1">
              <h2 className="text-[15px] font-semibold text-paper">What the Living Score needs</h2>
              <p className="mt-1.5 max-w-2xl text-[13px] text-paper/75">
                Every figure above is a signal. The engine normalises, weights and combines them
                into a 0–100 Living Score over a rolling 90-day window — and the score is always
                shown next to the factors that produced it.
              </p>
            </div>
            <div className="flex gap-2">
              <Chip className="bg-paper/10 text-paper" glyph="◷">
                Awaiting data
              </Chip>
            </div>
          </div>
        </Card>
      ) : null}

      <div className={cx('grid gap-4 sm:grid-cols-3')}>
        {[
          { icon: <IconReport size={17} />, label: 'Log an issue', to: '/app/complaints' },
          { icon: <IconMegaphone size={17} />, label: 'Read announcements', to: '/app/announcements' },
          { icon: <IconClock size={17} />, label: 'Estate properties', to: '/app/properties' },
        ]
          .filter((shortcut) => user?.role !== 'service_provider' || shortcut.to !== '/app/properties')
          .map((shortcut) => (
            <Link
              key={shortcut.to}
              to={shortcut.to}
              className="hairline flex items-center gap-3 rounded-xs bg-surface px-4 py-3 text-[13.5px] font-medium transition-colors hover:border-ink/40"
            >
              <span className="text-accent-ink">{shortcut.icon}</span>
              {shortcut.label}
              <IconArrowRight size={15} className="ml-auto text-ink-muted" />
            </Link>
          ))}
      </div>
    </div>
  )
}

export function Dashboard() {
  return (
    <RequireEstate>
      <DashboardBody />
    </RequireEstate>
  )
}
