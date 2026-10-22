import { Area, AreaChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from 'recharts';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { IconAlert, IconArrowRight, IconClock, IconMegaphone, IconReport, IconWrench } from '../components/Icons';
import { HealthBrief } from '../components/HealthBrief';
import { RequireEstate } from '../components/RequireEstate';
import { Chip, EmptyState, ErrorState, LoadingState, SectionTitle, cx } from '../components/ui';
import { Button } from '../components/ui/button';
import { HealthPillars } from '../components/valora/HealthPillars';
import { MetricCard } from '../components/valora/MetricCard';
import { ScoreCard } from '../components/valora/ScoreCard';
import { SectionHeading } from '../components/valora/SectionHeading';
import { Surface } from '../components/valora/Surface';
import { AttentionPanel } from '../components/valora/AttentionPanel';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api, ApiError } from '../lib/api';
import { getLivingScore, getLivingScoreHistory, recalculateLivingScore } from '../lib/analytics';
import { complaintStatus, pillarBand, workOrderStatus } from '../lib/display';
import { durationHours, displayLabel, ratio, relativeDays, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';

const OPEN_STATUSES = new Set(['submitted', 'reviewed', 'assigned', 'in_progress']);

function EstateCard() {
  const { estate } = useEstateScope();
  if (!estate) return null;
  return (
    <Surface>
      <p className="text-[0.66rem] font-semibold tracking-[0.14em] text-ink/40 uppercase">Estate</p>
      <h2 className="mt-1 font-heading text-[1.05rem] font-bold text-ink">{estate.estate_name}</h2>
      <p className="num mt-1 text-[0.78rem] text-ink-muted">
        {estate.suburb}, {estate.city}, {estate.province}
      </p>

      <dl className="mt-4 space-y-2.5">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[0.82rem] text-ink-soft">Your role here</dt>
          <dd className="num text-[0.82rem] font-medium">
            {estate.is_estate_admin
              ? 'HOA administrator'
              : estate.is_estate_provider
              ? 'Service provider'
              : (estate.membership_roles[0] ?? 'member')}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[0.82rem] text-ink-soft">Units linked to you</dt>
          <dd className="num text-[0.82rem] font-medium">{estate.property_ids.length}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[0.82rem] text-ink-soft">Estate reference</dt>
          <dd className="num text-[0.82rem] font-medium">#{estate.estate_id}</dd>
        </div>
      </dl>

      <p className="mt-4 border-t border-line pt-3 text-[0.75rem] text-ink-muted">
        This identifier is resolved on the server from your membership. Supplying an estate number is
        never treated as proof of access.
      </p>
    </Surface>
  );
}

function NeedsAttention({ complaints }) {
  const open = complaints.filter((item) => OPEN_STATUSES.has(item.status ?? '')).slice(0, 5);
  const items =
    open.length > 0
      ? open.map((item) => ({
          id: item.id,
          title: item.description,
          detail: `Unit ${item.unit_id} · ${displayLabel(item.category)} · logged ${relativeDays(item.created_at)}`,
          area: `Unit ${item.unit_id}`,
          eta: item.priority === 'urgent' ? 'Immediate SLA' : 'Standard SLA',
          impact: `Priority: ${displayLabel(item.priority)}`,
          urgency:
            item.priority === 'urgent'
              ? 'Critical'
              : item.priority === 'high'
              ? 'At Risk'
              : 'Watch',
        }))
      : [];
  return <AttentionPanel items={items} />;
}

function AnnouncementList({ announcements }) {
  if (announcements.length === 0) {
    return (
      <EmptyState
        title="No announcements yet"
        body="When your HOA publishes a notice — an outage, an AGM, a security upgrade — it appears here for every member of the estate."
      />
    );
  }
  return (
    <ul className="divide-y divide-line">
      {announcements.map((item) => (
        <li key={item.id} className="py-3.5">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-[0.88rem] font-medium">{item.title}</h3>
            <span className="num shrink-0 text-[0.75rem] text-ink-muted">
              {shortDate(item.created_at)}
            </span>
          </div>
          <p className="mt-1 line-clamp-2 text-[0.83rem] text-ink-soft">{item.message}</p>
        </li>
      ))}
    </ul>
  );
}

export function AdminDashboard() {
  const { estateId, estate } = useEstateScope();
  const { user } = useAuth();
  const isAdmin = user?.role === 'hoa_admin';
  const announcements = useAsync(
    () => api.get('/api/v1/announcements', { estate_id: estateId, size: 4 }),
    [estateId]
  );
  const complaints = useAsync(
    () =>
      api.get('/api/v1/complaints', {
        estate_id: estateId,
        size: 12,
        sort: '-created_at',
      }),
    [estateId]
  );
  const stats = useAsync(
    () =>
      isAdmin
        ? api.get('/api/v1/complaints/stats', { estate_id: estateId })
        : Promise.resolve(null),
    [estateId, isAdmin]
  );
  const workOrders = useAsync(
    () =>
      isAdmin
        ? api.get('/api/v1/work-orders', { estate_id: estateId, size: 100 })
        : Promise.resolve(null),
    [estateId, isAdmin]
  );
  const properties = useAsync(
    () => api.get('/api/v1/properties', { estate_id: estateId, size: 100 }),
    [estateId]
  );

  // The stored snapshot, exactly as the engine wrote it: this screen never
  // calculates a score. A 404 (never scored) and an `insufficient_data` snapshot
  // are both rendered as "not enough data yet", never as a zero.
  const livingScoreSnapshot = useAsync(
    () => (estateId === null ? Promise.resolve(null) : getLivingScore(estateId)),
    [estateId]
  );
  const livingScoreHistory = useAsync(
    () => (estateId === null ? Promise.resolve(null) : getLivingScoreHistory(estateId, 12)),
    [estateId]
  );

  // The one action on this panel. The server decides whether the caller may
  // calculate; a refusal is shown verbatim and nothing is recalculated locally.
  const [recalculating, setRecalculating] = useState(false);
  const [recalculateError, setRecalculateError] = useState(null);

  async function recalculateScore() {
    if (estateId === null || recalculating) return;
    setRecalculating(true);
    setRecalculateError(null);
    try {
      await recalculateLivingScore(estateId);
      livingScoreSnapshot.reload();
      livingScoreHistory.reload();
    } catch (cause) {
      setRecalculateError(
        cause instanceof ApiError
          ? cause
          : new ApiError(0, cause instanceof Error ? cause.message : 'Something went wrong.')
      );
    } finally {
      setRecalculating(false);
    }
  }

  const snapshot = livingScoreSnapshot.data;
  const scored =
    snapshot !== null &&
    snapshot.status === 'scored' &&
    snapshot.overall_score !== null &&
    snapshot.overall_score !== undefined;

  // The engine's own pillars, with the weights it published — never re-derived.
  const pillars = (snapshot?.components ?? []).map((component) => ({
    key: component.key,
    name: component.label,
    score:
      component.score === null || component.score === undefined ? 0 : Number(component.score),
    weight: Number(component.weight) * 100,
    summary: component.explanation || undefined,
    measured: component.status === 'measured' && component.score !== null,
  }));

  // Stored snapshots, oldest first: a trajectory of published numbers.
  const trajectory = [...(livingScoreHistory.data?.snapshots ?? [])]
    .reverse()
    .filter((row) => row.overall_score !== null)
    .map((row) => ({ date: shortDate(row.as_of), score: Number(row.overall_score) }));

  // The written status and the movement come from the snapshots this screen
  // fetched — the band is a *label* for the published number, and the change is
  // the difference between two stored figures. Neither is a score calculation.
  const storedValues = trajectory.map((point) => point.score);
  const band = scored ? pillarBand(Number(snapshot?.overall_score)) : null;
  const trend =
    storedValues.length > 1
      ? Math.round((storedValues[storedValues.length - 1] - storedValues[storedValues.length - 2]) * 10) /
        10
      : null;

  // “Healthy, with watch areas” — the composite band, qualified by the pillars
  // the engine measured below the healthy band.
  const flagged = pillars.filter(
    (pillar) => pillar.measured && pillarBand(pillar.score).tone !== 'positive'
  );
  const statusLabel = !scored
    ? 'Not enough data yet'
    : `${band?.label ?? 'Healthy'}${flagged.length === 0 ? '' : ', with watch areas'}`;

  const openCount = (complaints.data?.items ?? []).filter((item) =>
    OPEN_STATUSES.has(item.status ?? '')
  ).length;
  const unitCount = properties.data?.total ?? null;
  const averageResolution = stats.data?.avg_resolution_hours;
  const workOrdersInFlight = (workOrders.data?.items ?? []).filter((order) =>
    ['assigned', 'in_progress'].includes(order.status ?? '')
  ).length;

  const operationalTimeline = [
    ...(complaints.data?.items ?? []).map((item) => ({
      id: `complaint-${item.id}`,
      date: shortDate(item.updated_at ?? item.created_at),
      title: `Complaint #${item.id}: ${displayLabel(item.status ?? 'submitted')}`,
      description: item.description,
      meta: `Unit ${item.unit_id} · ${displayLabel(item.category)}`,
      status: OPEN_STATUSES.has(item.status ?? '') ? 'current' : 'completed',
      occurredAt: item.updated_at ?? item.created_at,
    })),
    ...(isAdmin
      ? (workOrders.data?.items ?? []).map((order) => ({
          id: `work-order-${order.id}`,
          date: shortDate(order.updated_at ?? order.created_at),
          title: `Work order #${order.id}: ${displayLabel(order.status ?? 'assigned')}`,
          description:
            order.completion_notes ?? `Complaint #${order.complaint_id} · provider #${order.provider_id}`,
          meta: `Work order #${order.id}`,
          status: ['assigned', 'in_progress'].includes(order.status ?? '') ? 'current' : 'completed',
          occurredAt: order.updated_at ?? order.created_at,
        }))
      : []),
  ]
    .sort(
      (left, right) =>
        new Date(right.occurredAt ?? 0).getTime() - new Date(left.occurredAt ?? 0).getTime()
    )
    .slice(0, 8);

  // ADD: triage banner computation
  const unassignedComplaints = (complaints.data?.items ?? []).filter(
    (c) => c.status === 'submitted' || c.status === 'reviewed'
  );

  return (
    <div className="space-y-5">
      {/* ---- Triage banners (NEW — leads the view) ---- */}
      {unassignedComplaints.length > 0 ? (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-signal/30 border-l-4 border-l-signal bg-signal-wash px-4 py-3.5">
          <div>
            <p className="text-[13.5px] font-semibold text-signal-ink">
              {unassignedComplaints.length} complaint{unassignedComplaints.length !== 1 ? 's' : ''} need{unassignedComplaints.length === 1 ? 's' : ''} review
            </p>
            <p className="text-[12px] text-ink-soft">
              Unassigned — no contractor has been assigned yet.
            </p>
          </div>
          <Link
            to="/app/complaints"
            className="shrink-0 rounded-xs border border-signal/30 bg-white px-3 py-1.5 text-[12.5px] font-medium text-signal-ink transition-colors hover:bg-signal-wash"
          >
            Review →
          </Link>
        </div>
      ) : null}

      {/* ---- All existing DashboardBody JSX below, unchanged ---- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <SectionHeading
          eyebrow={isAdmin ? 'Governance overview' : 'Estate overview'}
          title="Property health at a glance"
          description="Operational data as recorded by the estate. Each score shows its own calculation date."
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <ScoreCard
          empty={!scored}
          value={scored ? ratio(snapshot?.overall_score) : undefined}
          status={statusLabel}
          change={scored ? (trend ?? undefined) : undefined}
          spark={scored ? storedValues : undefined}
          label="Living Score"
          description={
            scored
              ? `Stored for a rolling 90-day window by engine ${snapshot?.engine_version}. The figure is read, never recalculated on this screen.`
              : 'This estate has no publishable score yet. Every operational action — a logged complaint, a completed work order, a resident rating — feeds the five weighted pillars below.'
          }
          action={
            <div className="space-y-3">
              {recalculateError ? (
                <ErrorState
                  title="The recalculation was refused"
                  message={recalculateError.message}
                  requestId={recalculateError.requestId}
                />
              ) : null}
              <div className="flex flex-wrap items-center gap-2">
                {isAdmin ? (
                  <Button variant="secondary" onClick={recalculateScore} disabled={recalculating}>
                    {recalculating ? 'Recalculating…' : 'Recalculate now'}
                  </Button>
                ) : null}
                <Link
                  to="/app/health"
                  className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium text-brand-ink hover:underline"
                >
                  Full health breakdown
                  <IconArrowRight size={15} />
                </Link>
              </div>
            </div>
          }
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
            <MetricCard
              label="Complaints logged"
              value={String(stats.data.total)}
              hint={`${stats.data.total - (stats.data.by_status.resolved ?? 0) - (stats.data.by_status.rated ?? 0) - (stats.data.by_status.closed ?? 0)} still open`}
              icon={<IconReport size={17} />}
            />
            <MetricCard
              label="Resolution rate"
              value={`${Number(stats.data.resolution_rate_pct).toFixed(0)}%`}
              deltaTone="positive"
              hint="Share of complaints that reached resolved"
              icon={<IconClock size={17} />}
            />
            <MetricCard
              label="Average resolution"
              value={durationHours(averageResolution)}
              deltaTone={
                averageResolution && Number(averageResolution) > 24 * 5 ? 'attention' : 'positive'
              }
              hint="Benchmark: 5 business days"
              icon={<IconWrench size={17} />}
            />
            <MetricCard
              label="Work orders in flight"
              value={String(workOrdersInFlight)}
              hint="Assigned or in progress right now"
              icon={<IconWrench size={17} />}
              deltaTone={workOrdersInFlight > 0 ? 'brand' : 'positive'}
            />
          </div>
        ) : null
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard
            label={user?.role === 'resident' ? 'Your open complaints' : 'Open complaints'}
            value={String(openCount)}
            deltaTone={openCount > 0 ? 'attention' : 'positive'}
            hint={user?.role === 'resident' ? 'Issues you have logged' : 'Across the estate'}
            icon={<IconReport size={17} />}
          />
          <MetricCard
            label="Estate units"
            value={unitCount === null ? '—' : String(unitCount)}
            hint="Registered in VALORA"
            icon={<IconClock size={17} />}
          />
          <MetricCard
            label="Announcements"
            value={String(announcements.data?.total ?? 0)}
            hint="Published by the HOA"
            icon={<IconMegaphone size={17} />}
          />
        </div>
      )}

      {/* ----------------------------------------------- pillars + trajectory */}
      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <Surface>
          <SectionTitle
            title="Health pillars"
            hint="The engine’s five weighted components, exactly as stored"
          />
          {livingScoreSnapshot.loading ? (
            <LoadingState label="Loading the pillar breakdown" />
          ) : (
            <HealthPillars pillars={pillars} expandedDefault={false} showWeights />
          )}
        </Surface>

        <Surface>
          <SectionTitle
            title="Stored trajectory"
            hint="Each point is a snapshot the engine wrote"
          />
          {trajectory.length > 1 ? (
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={trajectory}
                  margin={{ top: 8, right: 8, bottom: 0, left: -20 }}
                >
                  <defs>
                    <linearGradient id="dashboardHealthFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: '#6B6480' }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: '#6B6480' }}
                  />
                  <ChartTooltip
                    contentStyle={{
                      borderRadius: 12,
                      border: '1px solid #E9E3FF',
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="#7C3AED"
                    strokeWidth={2}
                    fill="url(#dashboardHealthFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="py-3 text-[0.83rem] text-ink-muted">
              A trajectory appears once there are at least two stored snapshots. Until then there is
              nothing honest to plot.
            </p>
          )}
        </Surface>
      </div>

      {/* ------------------------------------------------ estate health brief */}
      {estateId !== null ? <HealthBrief estateId={estateId} canGenerate={isAdmin} /> : null}

      {/* ------------------------------------------------ lower grid */}
      <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        {isAdmin ? (
          complaints.loading ? (
            <LoadingState label="Loading complaints" />
          ) : complaints.error ? (
            <ErrorState
              message={complaints.error.message}
              requestId={complaints.error.requestId}
            />
          ) : (
            <NeedsAttention complaints={complaints.data?.items ?? []} />
          )
        ) : (
          <Surface>
            <SectionTitle
              title={user?.role === 'resident' ? 'Your complaints' : 'Your activity'}
              hint="Only issues you logged are visible to you"
              action={
                user?.role === 'resident' ? (
                  <Link
                    to="/app/complaints"
                    className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium text-brand-ink hover:underline"
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
              <ErrorState
                message={complaints.error.message}
                requestId={complaints.error.requestId}
              />
            ) : (complaints.data?.items.length ?? 0) === 0 ? (
              <p className="py-4 text-[0.83rem] text-ink-muted">
                {user?.role === 'resident'
                  ? 'You have not logged any complaints yet.'
                  : 'Nothing logged against your membership.'}
              </p>
            ) : (
              <ul className="divide-y divide-line">
                {(complaints.data?.items ?? []).slice(0, 5).map((item) => {
                  const status = complaintStatus[item.status ?? 'submitted'];
                  return (
                    <li key={item.id} className="flex items-start gap-3 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[0.86rem]">{item.description}</p>
                        <p className="num mt-0.5 text-[0.75rem] text-ink-muted">
                          #{item.id} · {item.category} · {relativeDays(item.created_at)}
                        </p>
                      </div>
                      <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
                        {status?.label ?? item.status}
                      </Chip>
                    </li>
                  );
                })}
              </ul>
            )}
          </Surface>
        )}

        <Surface>
          <SectionTitle
            title="Latest announcements"
            hint="Governance activity is itself a health signal"
            action={
              <Link
                to="/app/announcements"
                className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium text-brand-ink hover:underline"
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
        </Surface>
      </div>

      {isAdmin ? (
        <Surface>
          <SectionTitle
            title="Maintenance in flight"
            hint="Work orders measure operational quality, not just cost"
            action={
              <Link
                to="/app/work-orders"
                className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium text-brand-ink hover:underline"
              >
                All work orders
                <IconArrowRight size={15} />
              </Link>
            }
          />
          {workOrders.loading ? (
            <LoadingState label="Loading work orders" />
          ) : workOrders.error ? (
            <ErrorState
              message={workOrders.error.message}
              requestId={workOrders.error.requestId}
            />
          ) : (workOrders.data?.items.length ?? 0) === 0 ? (
            <p className="py-4 text-[0.83rem] text-ink-muted">
              No work orders have been raised yet.
            </p>
          ) : (
            <ul className="divide-y divide-line">
              {(workOrders.data?.items ?? []).slice(0, 6).map((order) => {
                const status = workOrderStatus[order.status ?? 'assigned'];
                return (
                  <li key={order.id} className="flex flex-wrap items-center gap-3 py-3">
                    <IconWrench size={16} className="shrink-0 text-ink-muted" />
                    <span className="num text-[0.8rem]">
                      WO-{String(order.id).padStart(4, '0')}
                    </span>
                    <span className="num text-[0.8rem] text-ink-muted">
                      complaint #{order.complaint_id}
                    </span>
                    <span className="num text-[0.8rem] text-ink-muted">
                      provider #{order.provider_id}
                    </span>
                    <span className="ml-auto">
                      <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
                        {status?.label ?? order.status}
                      </Chip>
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </Surface>
      ) : null}

      {/* --------------------------------------------------- operational timeline */}
      <Surface>
        <SectionTitle
          title="Recent estate operations"
          hint="Authorized complaint and work-order records, newest first"
        />
        <div className="mt-4">
          {complaints.loading || (isAdmin && workOrders.loading) ? (
            <LoadingState label="Loading recent operations" />
          ) : complaints.error ? (
            <ErrorState
              message={complaints.error.message}
              requestId={complaints.error.requestId}
            />
          ) : isAdmin && workOrders.error ? (
            <ErrorState
              message={workOrders.error.message}
              requestId={workOrders.error.requestId}
            />
          ) : operationalTimeline.length === 0 ? (
            <EmptyState
              title="No recent operational activity"
              body="Logged complaints and work-order updates will appear here once the estate has records."
            />
          ) : (
            <ul className="divide-y divide-line">
              {operationalTimeline.map((item) => (
                <li key={item.id} className="py-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-3">
                    <p className="text-[13px] font-medium">{item.title}</p>
                    <span className="num text-[11.5px] text-ink-muted">{item.date}</span>
                  </div>
                  <p className="mt-1 text-[12.5px] text-ink-soft">{item.description}</p>
                  <p className="mt-1 text-[11.5px] text-ink-muted">{item.meta}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Surface>

      {/* --------------------------------------------------- next steps */}
      {!livingScoreSnapshot.loading && livingScoreSnapshot.data === null ? (
        <Surface className="bg-ink text-white">
          <div className="flex flex-wrap items-start gap-4">
            <IconAlert size={20} className="mt-0.5 shrink-0 text-white/70" />
            <div className="min-w-0 flex-1">
              <h2 className="font-heading text-[1rem] font-semibold text-white">
                What the Living Score needs
              </h2>
              <p className="mt-1.5 max-w-2xl text-[0.83rem] text-white/75">
                Every figure above is a signal. The engine normalises, weights and combines them
                into a 0–100 Living Score over a rolling 90-day window — and the score is always
                shown next to the factors that produced it.
              </p>
            </div>
            <div className="flex gap-2">
              <span className="rounded-full bg-white/10 px-3 py-1.5 text-[0.72rem] font-semibold text-white">
                ◷ Awaiting data
              </span>
            </div>
          </div>
        </Surface>
      ) : null}

      <div className={cx('grid gap-4 sm:grid-cols-3')}>
        {[
          { icon: <IconReport size={17} />, label: 'Log an issue', to: '/app/complaints' },
          {
            icon: <IconMegaphone size={17} />,
            label: 'Read announcements',
            to: '/app/announcements',
          },
          { icon: <IconClock size={17} />, label: 'Estate health', to: '/app/health' },
        ]
          .filter((shortcut) => user?.role !== 'service_provider' || shortcut.to !== '/app/complaints')
          .map((shortcut) => (
            <Link
              key={shortcut.to}
              to={shortcut.to}
              className="flex items-center gap-3 rounded-2xl border border-line bg-surface px-4 py-3 text-[0.86rem] font-medium transition-colors duration-200 hover:border-brand-soft hover:bg-canvas"
            >
              <span className="text-brand">{shortcut.icon}</span>
              {shortcut.label}
              <IconArrowRight size={15} className="ml-auto text-ink-muted" />
            </Link>
          ))}
      </div>

      <p className="text-[0.72rem] text-ink/35">
        Scope: {estate?.estate_name ?? 'no estate selected'} ·{' '}
        {stats.data ? `${stats.data.total} complaints on record` : 'estate metrics unavailable'}
      </p>
    </div>
  );
}

// Re-export as DashboardBody for backwards compatibility
export { AdminDashboard as DashboardBody };
