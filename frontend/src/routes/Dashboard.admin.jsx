import { useMemo, useState } from 'react';
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, CalendarDays, CheckCircle2, CircleAlert, Clock3, FileText, HeartPulse, ShieldAlert, Wrench } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Chip, EmptyState, ErrorState, LoadingState } from '../components/ui';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api, ApiError } from '../lib/api';
import { getLivingScore, getLivingScoreHistory, recalculateLivingScore } from '../lib/analytics';
import { complaintStatus, pillarBand, workOrderStatus } from '../lib/display';
import { displayLabel, durationHours, relativeDays, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';

const OPEN_STATUSES = new Set(['submitted', 'reviewed', 'assigned', 'in_progress']);
const CLOSED_STATUSES = new Set(['resolved', 'rated', 'closed']);

function EstateContextHero({ estate }) {
  return (
    <section className="grid overflow-hidden border-y border-line bg-brand-wash/45 md:grid-cols-[1fr_0.88fr]" aria-label="Estate context">
      <div className="flex min-h-[230px] flex-col justify-between p-6 sm:p-8 lg:p-9">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-ink">Estate operations</p>
          <h2 className="mt-3 max-w-2xl font-heading text-3xl font-semibold leading-tight tracking-[-0.035em] text-ink sm:text-4xl">
            {estate?.estate_name ?? 'Your estate'}.
            <span className="block text-brand-ink">What needs attention today?</span>
          </h2>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-soft">
            Review outstanding work, keep residents informed, and follow operational issues through to resolution.
          </p>
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-muted">
          {estate?.suburb || estate?.city ? (
            <span className="inline-flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              {[estate.suburb, estate.city, estate.province].filter(Boolean).join(', ')}
            </span>
          ) : null}
          <span>{estate?.property_ids?.length ?? 0} linked units</span>
          <Link to="/admin/settings" className="font-semibold text-brand-ink hover:underline">Estate profile <ArrowRight className="ml-1 inline h-3.5 w-3.5" /></Link>
        </div>
      </div>
      <div className="relative min-h-[210px] overflow-hidden md:min-h-full">
        <img
          src="/estate-hero.jpg"
          alt="Residential estate architecture"
          width="960"
          height="640"
          fetchPriority="high"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#24153f]/80 via-[#24153f]/10 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 p-5 sm:p-7">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/75">Management workspace</p>
          <p className="mt-1 max-w-md font-heading text-xl font-semibold leading-snug text-white">
            Clear priorities. Accountable action. A healthier estate.
          </p>
        </div>
      </div>
    </section>
  );
}

function PriorityRow({ complaint, onSelect }) {
  const priority = (complaint.priority ?? 'normal').toLowerCase();
  const critical = priority === 'urgent';
  const high = priority === 'high';
  const status = complaintStatus[complaint.status ?? 'submitted'];
  return (
    <li className="border-b border-line/80 last:border-b-0">
      <button
        type="button"
        onClick={() => onSelect(complaint)}
        className="group grid w-full gap-3 py-4 text-left transition-colors hover:bg-brand-wash/35 focus-visible:outline-2 focus-visible:outline-brand sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-3"
        aria-label={`Review complaint ${complaint.id}: ${complaint.description}`}
      >
        <span className="flex min-w-0 items-start gap-3.5">
          <span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center ${critical ? 'bg-signal-wash text-signal-ink' : high ? 'bg-ochre-wash text-ochre-ink' : 'bg-brand-wash text-brand-ink'}`}>
            {critical || high ? <CircleAlert className="h-4 w-4" /> : <Wrench className="h-4 w-4" />}
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-ink">{complaint.description}</span>
              <span className={`text-[10px] font-bold uppercase tracking-[0.08em] ${critical ? 'text-signal-ink' : high ? 'text-ochre-ink' : 'text-ink-muted'}`}>
                {displayLabel(priority)}
              </span>
            </span>
            <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-muted">
              <span>#{complaint.id}</span><span aria-hidden="true">·</span>
              <span>{displayLabel(complaint.category)}</span>
              {complaint.unit_id ? <><span aria-hidden="true">·</span><span>Unit {complaint.unit_id}</span></> : null}
              <span aria-hidden="true">·</span><span>Logged {relativeDays(complaint.created_at)}</span>
            </span>
          </span>
        </span>
        <span className="flex items-center justify-between gap-3 pl-[3.15rem] sm:justify-end sm:pl-0">
          <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>{status?.label ?? complaint.status}</Chip>
          <ArrowRight className="h-4 w-4 shrink-0 text-ink-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
        </span>
      </button>
    </li>
  );
}

function ScoreSummary({ snapshot, history, loading, error, onRecalculate, recalculating, recalculateError }) {
  const scored = snapshot?.status === 'scored' && snapshot?.overall_score !== null && snapshot?.overall_score !== undefined;
  const score = scored ? Number(snapshot.overall_score) : null;
  const band = scored ? pillarBand(score) : null;
  const snapshots = [...(history?.snapshots ?? [])].reverse().filter((item) => item.overall_score !== null && item.overall_score !== undefined);
  const change = snapshots.length > 1 ? Number(snapshots.at(-1).overall_score) - Number(snapshots.at(-2).overall_score) : null;

  return (
    <section className="border-l-2 border-brand pl-4 sm:pl-5" aria-labelledby="estate-health-summary">
      <div className="flex items-center gap-2 text-brand-ink">
        <HeartPulse className="h-4 w-4" />
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em]">Estate health</p>
      </div>
      <div className="mt-3 flex items-end gap-3">
        {loading ? <LoadingState label="Loading Living Score" /> : error ? (
          <p className="text-sm text-ink-muted">Estate health is temporarily unavailable.</p>
        ) : scored ? (
          <>
            <p className="num font-heading text-4xl font-semibold leading-none tracking-tight text-brand-ink">
              {score.toLocaleString('en-ZA', { maximumFractionDigits: 1 })}
              <span className="ml-1 text-sm font-medium text-ink-muted">/100</span>
            </p>
            <Chip tone={band?.tone === 'positive' ? 'good' : 'warn'}>{band?.label ?? 'Published score'}</Chip>
          </>
        ) : <p className="font-heading text-3xl font-semibold text-ink">Not scored yet</p>}
      </div>
      {scored ? (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
          {change !== null ? <span className={`inline-flex items-center gap-1 font-semibold ${change > 0 ? 'text-mint-ink' : change < 0 ? 'text-signal-ink' : 'text-ink-muted'}`}>
            {change > 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : change < 0 ? <ArrowDownRight className="h-3.5 w-3.5" /> : null}
            {change > 0 ? '+' : ''}{change.toLocaleString('en-ZA', { maximumFractionDigits: 1 })} points vs previous snapshot
          </span> : null}
          <span>Updated {shortDate(snapshot.as_of ?? snapshot.calculated_at)}</span>
        </div>
      ) : (
        <p className="mt-2 max-w-md text-sm leading-relaxed text-ink-soft">A score appears when the estate has enough measured operational data for a stored calculation.</p>
      )}
      {recalculateError ? <p role="alert" className="mt-2 text-xs text-signal-ink">{recalculateError.message}</p> : null}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link to="/app/health" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">
          Explore Estate Health <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <button type="button" onClick={onRecalculate} disabled={recalculating} className="text-xs font-medium text-ink-muted underline-offset-4 hover:text-brand-ink hover:underline disabled:opacity-50">
          {recalculating ? 'Recalculating…' : 'Recalculate score'}
        </button>
      </div>
    </section>
  );
}

function ComplaintDetail({ complaint, onClose }) {
  if (!complaint) return null;
  const status = complaintStatus[complaint.status ?? 'submitted'];
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <button className="absolute inset-0 cursor-default bg-ink/35" aria-label="Close issue details" onClick={onClose} />
      <aside role="dialog" aria-modal="true" aria-labelledby="issue-drawer-title" className="relative flex h-full w-full max-w-lg flex-col overflow-y-auto border-l border-line bg-surface shadow-lift animate-in slide-in-from-right duration-200">
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-5 sm:px-7">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-brand-ink">Complaint #{complaint.id}</p>
            <h2 id="issue-drawer-title" className="mt-2 font-heading text-xl font-semibold tracking-tight text-ink">{complaint.description}</h2>
            <p className="mt-1 text-sm text-ink-muted">{displayLabel(complaint.category)}{complaint.unit_id ? ` · Unit ${complaint.unit_id}` : ''}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close issue details" className="flex h-9 w-9 shrink-0 items-center justify-center text-ink-muted hover:bg-brand-wash hover:text-brand-ink focus-visible:outline-2 focus-visible:outline-brand">×</button>
        </div>
        <div className="flex-1 space-y-6 px-5 py-6 sm:px-7">
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>{status?.label ?? complaint.status}</Chip>
            <span className={`text-xs font-semibold uppercase ${complaint.priority === 'urgent' ? 'text-signal-ink' : complaint.priority === 'high' ? 'text-ochre-ink' : 'text-ink-muted'}`}>{displayLabel(complaint.priority ?? 'normal')} priority</span>
          </div>
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-muted">Record</h3>
            <dl className="mt-3 divide-y divide-line">
              <div className="flex justify-between gap-4 py-3 text-sm"><dt className="text-ink-muted">Created</dt><dd className="text-right font-medium text-ink">{shortDate(complaint.created_at)}</dd></div>
              <div className="flex justify-between gap-4 py-3 text-sm"><dt className="text-ink-muted">Last updated</dt><dd className="text-right font-medium text-ink">{shortDate(complaint.updated_at ?? complaint.created_at)}</dd></div>
              <div className="flex justify-between gap-4 py-3 text-sm"><dt className="text-ink-muted">Unit</dt><dd className="text-right font-medium text-ink">{complaint.unit_id ?? 'Not recorded'}</dd></div>
            </dl>
          </section>
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-muted">Description</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">{complaint.description}</p>
          </section>
          <p className="text-xs leading-relaxed text-ink-muted">This view shows the recorded complaint. Use the complaint workspace to assign work, update its lifecycle, and review additional information.</p>
        </div>
        <div className="border-t border-line p-5 sm:px-7">
          <Link to="/app/complaints" onClick={onClose} className="inline-flex w-full items-center justify-center gap-2 bg-brand px-4 py-3 text-sm font-semibold text-white hover:bg-brand-ink">
            Open complaint workspace <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </aside>
    </div>
  );
}

function ActivityList({ complaints, workOrders }) {
  const records = [
    ...complaints.map((item) => ({
      key: `complaint-${item.id}`,
      icon: <FileText className="h-4 w-4" />,
      title: item.description,
      detail: `Complaint #${item.id} · ${displayLabel(item.status ?? 'submitted')}`,
      date: item.updated_at ?? item.created_at,
    })),
    ...workOrders.map((item) => ({
      key: `work-order-${item.id}`,
      icon: <Wrench className="h-4 w-4" />,
      title: `Work order #${item.id}`,
      detail: `${displayLabel(item.status ?? 'assigned')} · Complaint #${item.complaint_id}`,
      date: item.updated_at ?? item.created_at,
    })),
  ].sort((a, b) => new Date(b.date ?? 0).getTime() - new Date(a.date ?? 0).getTime()).slice(0, 4);

  if (records.length === 0) return <p className="py-4 text-sm text-ink-muted">Recent activity will appear here as estate work is recorded.</p>;
  return (
    <ul className="divide-y divide-line/80">
      {records.map((item) => (
        <li key={item.key} className="flex items-start gap-3 py-3.5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center bg-brand-wash text-brand-ink">{item.icon}</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-ink">{item.title}</p>
            <p className="mt-1 text-xs text-ink-muted">{item.detail}</p>
          </div>
          <time className="shrink-0 pt-0.5 text-xs text-ink-muted">{shortDate(item.date)}</time>
        </li>
      ))}
    </ul>
  );
}

export function AdminDashboard() {
  const { estateId, estate } = useEstateScope();
  const { user } = useAuth();
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [recalculating, setRecalculating] = useState(false);
  const [recalculateError, setRecalculateError] = useState(null);

  const announcements = useAsync(
    () => estateId === null ? Promise.resolve({ items: [], total: 0 }) : api.get('/api/v1/announcements', { estate_id: estateId, size: 4 }),
    [estateId],
  );
  const complaints = useAsync(
    () => estateId === null ? Promise.resolve({ items: [], total: 0 }) : api.get('/api/v1/complaints', { estate_id: estateId, size: 50, sort: '-created_at' }),
    [estateId],
  );
  const stats = useAsync(
    () => user?.role === 'hoa_admin' && estateId !== null ? api.get('/api/v1/complaints/stats', { estate_id: estateId }) : Promise.resolve(null),
    [estateId, user?.role],
  );
  const workOrders = useAsync(
    () => user?.role === 'hoa_admin' && estateId !== null ? api.get('/api/v1/work-orders', { estate_id: estateId, size: 50 }) : Promise.resolve({ items: [], total: 0 }),
    [estateId, user?.role],
  );
  const score = useAsync(
    () => estateId === null ? Promise.resolve(null) : getLivingScore(estateId).catch((error) => {
      if (error?.status === 404) return null;
      throw error;
    }),
    [estateId],
  );
  const scoreHistory = useAsync(
    () => estateId === null ? Promise.resolve(null) : getLivingScoreHistory(estateId, 12).catch((error) => {
      if (error?.status === 404) return { snapshots: [] };
      throw error;
    }),
    [estateId],
  );

  const allComplaints = complaints.data?.items ?? [];
  const activeComplaints = useMemo(
    () => allComplaints.filter((item) => OPEN_STATUSES.has(item.status ?? '')).sort((a, b) => {
      const priorityRank = (value) => value === 'urgent' ? 0 : value === 'high' ? 1 : value === 'normal' ? 2 : 3;
      const priorityDifference = priorityRank(a.priority) - priorityRank(b.priority);
      return priorityDifference || new Date(a.created_at ?? 0).getTime() - new Date(b.created_at ?? 0).getTime();
    }),
    [allComplaints],
  );
  const workOrderItems = workOrders.data?.items ?? [];
  const workOrdersInFlight = workOrderItems.filter((item) => ['assigned', 'in_progress'].includes(item.status ?? ''));
  const openIncidents = null; // Incidents are intentionally not fabricated; only show a metric when a real incident endpoint is wired.
  const averageResolution = stats.data?.avg_resolution_hours;
  const resolutionRate = stats.data?.resolution_rate_pct;
  const notices = announcements.data?.items ?? [];

  async function recalculateScore() {
    if (estateId === null || recalculating) return;
    setRecalculating(true);
    setRecalculateError(null);
    try {
      await recalculateLivingScore(estateId);
      score.reload();
      scoreHistory.reload();
    } catch (cause) {
      setRecalculateError(cause instanceof ApiError ? cause : new ApiError(0, cause instanceof Error ? cause.message : 'Could not recalculate the score.'));
    } finally {
      setRecalculating(false);
    }
  }

  const needsReview = activeComplaints.filter((item) => ['submitted', 'reviewed'].includes(item.status ?? '')).length;
  const urgentCount = activeComplaints.filter((item) => ['urgent', 'high'].includes((item.priority ?? '').toLowerCase())).length;

  return (
    <div className="space-y-9 pb-6">
      <header className="flex flex-col justify-between gap-4 border-b border-line pb-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.17em] text-brand-ink">HOA workspace</p>
          <h1 className="mt-2 font-heading text-3xl font-semibold tracking-[-0.035em] text-ink sm:text-4xl">The operating picture.</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">Start with the issues that need a decision. The rest of the estate's record is one step away.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/app/complaints" className="inline-flex min-h-10 items-center justify-center gap-2 border border-line px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-brand-wash">
            <FileText className="h-4 w-4" /> Complaints
          </Link>
          <Link to="/app/work-orders" className="inline-flex min-h-10 items-center justify-center gap-2 bg-brand px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-ink">
            <Wrench className="h-4 w-4" /> Work orders <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <EstateContextHero estate={estate} />

      <section aria-label="Operational overview" className="grid gap-5 border-y border-line py-5 sm:grid-cols-2 xl:grid-cols-4">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-signal-ink"><CircleAlert className="h-4 w-4" /></span>
          <div><p className="text-xs text-ink-muted">Open complaints</p><p className="num mt-1 font-heading text-3xl font-semibold text-ink">{complaints.loading ? '—' : activeComplaints.length}</p><p className="mt-1 text-xs text-ink-muted">{needsReview} awaiting review</p></div>
        </div>
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-brand-ink"><Wrench className="h-4 w-4" /></span>
          <div><p className="text-xs text-ink-muted">Work orders in flight</p><p className="num mt-1 font-heading text-3xl font-semibold text-ink">{workOrders.loading ? '—' : workOrdersInFlight.length}</p><p className="mt-1 text-xs text-ink-muted">Assigned or in progress</p></div>
        </div>
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-ochre-ink"><Activity className="h-4 w-4" /></span>
          <div><p className="text-xs text-ink-muted">Resolution rate</p><p className="num mt-1 font-heading text-3xl font-semibold text-ink">{stats.loading || resolutionRate == null ? '—' : `${Number(resolutionRate).toFixed(0)}%`}</p><p className="mt-1 text-xs text-ink-muted">From recorded complaints</p></div>
        </div>
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-brand"><Clock3 className="h-4 w-4" /></span>
          <div><p className="text-xs text-ink-muted">Average resolution</p><p className="num mt-1 font-heading text-3xl font-semibold text-ink">{stats.loading || averageResolution == null ? '—' : durationHours(averageResolution)}</p><p className="mt-1 text-xs text-ink-muted">For resolved records</p></div>
        </div>
      </section>

      <section className="grid gap-9 xl:grid-cols-[minmax(0,1.45fr)_minmax(290px,0.72fr)] xl:gap-12">
        <div>
          <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-ink">Needs a decision</p>
              <h2 className="mt-1 font-heading text-xl font-semibold tracking-tight text-ink sm:text-2xl">Priority issues <span className="ml-1 text-sm font-medium text-ink-muted">{activeComplaints.length}</span></h2>
            </div>
            <Link to="/app/complaints" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">Open complaints <ArrowRight className="h-3.5 w-3.5" /></Link>
          </div>

          {urgentCount > 0 ? (
            <div className="my-4 flex items-start gap-3 border-l-2 border-signal bg-signal-wash/60 px-4 py-3">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-signal-ink" />
              <div><p className="text-sm font-semibold text-signal-ink">{urgentCount} high-priority issue{urgentCount === 1 ? '' : 's'} need attention</p><p className="mt-0.5 text-xs leading-relaxed text-ink-soft">Review the recorded details and decide the next action.</p></div>
            </div>
          ) : null}

          {complaints.loading ? <LoadingState label="Loading priority issues" /> : complaints.error ? (
            <ErrorState title="Issues could not be loaded" message={complaints.error.message} requestId={complaints.error.requestId} action={<button onClick={complaints.reload} type="button" className="text-sm font-semibold text-brand-ink underline">Try again</button>} />
          ) : activeComplaints.length === 0 ? (
            <div className="flex items-start gap-3 py-7">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-mint-ink" />
              <div><p className="font-semibold text-ink">No open complaints on record.</p><p className="mt-1 text-sm text-ink-soft">New submissions will appear here for review.</p></div>
            </div>
          ) : (
            <ul className="divide-y divide-line/80">
              {activeComplaints.slice(0, 6).map((item) => <PriorityRow key={item.id} complaint={item} onSelect={setSelectedComplaint} />)}
            </ul>
          )}
          {activeComplaints.length > 6 ? <Link to="/app/complaints" className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">View all {activeComplaints.length} open issues <ArrowRight className="h-3.5 w-3.5" /></Link> : null}
        </div>

        <aside className="space-y-8">
          <ScoreSummary
            snapshot={score.data}
            history={scoreHistory.data}
            loading={score.loading || scoreHistory.loading}
            error={score.error || scoreHistory.error}
            onRecalculate={recalculateScore}
            recalculating={recalculating}
            recalculateError={recalculateError}
          />

          <section aria-labelledby="latest-notices">
            <div className="flex items-center justify-between gap-3 border-b border-line pb-3">
              <div><p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-ink">Keep residents informed</p><h2 id="latest-notices" className="mt-1 font-heading text-lg font-semibold text-ink">Latest notices</h2></div>
              <Link to="/app/announcements" aria-label="View all announcements" className="flex h-9 w-9 items-center justify-center text-brand-ink hover:bg-brand-wash"><ArrowRight className="h-4 w-4" /></Link>
            </div>
            {announcements.loading ? <div className="mt-3"><LoadingState label="Loading notices" /></div> : announcements.error ? (
              <p className="mt-3 text-sm text-ink-muted">Notices are temporarily unavailable.</p>
            ) : notices.length === 0 ? (
              <div className="flex gap-3 py-4"><Bell className="mt-0.5 h-4 w-4 shrink-0 text-brand-ink" /><p className="text-sm text-ink-muted">No notices have been published yet.</p></div>
            ) : (
              <ul className="divide-y divide-line/80">
                {notices.slice(0, 3).map((notice) => <li key={notice.id} className="py-3.5">
                  <div className="flex items-start gap-2"><CalendarDays className="mt-0.5 h-4 w-4 shrink-0 text-brand-ink" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-baseline justify-between gap-2"><p className="text-sm font-semibold text-ink">{notice.title}</p><time className="text-xs text-ink-muted">{shortDate(notice.created_at)}</time></div><p className="mt-1 line-clamp-2 text-sm leading-relaxed text-ink-soft">{notice.message}</p></div></div>
                </li>)}
              </ul>
            )}
            <Link to="/app/announcements" className="mt-1 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">Manage notices <ArrowRight className="h-3.5 w-3.5" /></Link>
          </section>
        </aside>
      </section>

      <section aria-labelledby="work-orders-heading" className="border-t border-line pt-6">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3">
          <div><p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-ink">Operational follow-through</p><h2 id="work-orders-heading" className="mt-1 font-heading text-xl font-semibold text-ink sm:text-2xl">Work in motion</h2><p className="mt-1 text-sm text-ink-soft">Assigned work and in-progress repairs.</p></div>
          <Link to="/app/work-orders" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">All work orders <ArrowRight className="h-3.5 w-3.5" /></Link>
        </div>
        {workOrders.loading ? <div className="mt-3"><LoadingState label="Loading work orders" /></div> : workOrders.error ? (
          <div className="mt-3"><ErrorState title="Work orders are unavailable" message={workOrders.error.message} requestId={workOrders.error.requestId} action={<button type="button" onClick={workOrders.reload} className="text-sm font-semibold text-brand-ink underline">Try again</button>} /></div>
        ) : workOrdersInFlight.length === 0 ? (
          <p className="py-5 text-sm text-ink-muted">No active work orders are recorded.</p>
        ) : (
          <ul className="divide-y divide-line/80">
            {workOrdersInFlight.slice(0, 4).map((order) => {
              const status = workOrderStatus[order.status ?? 'assigned'];
              return <li key={order.id} className="grid gap-2 py-3.5 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
                <div className="flex min-w-0 items-center gap-3"><Wrench className="h-4 w-4 shrink-0 text-brand-ink" /><div className="min-w-0"><p className="truncate text-sm font-semibold text-ink">Work order #{order.id}</p><p className="mt-0.5 text-xs text-ink-muted">Complaint #{order.complaint_id}{order.provider_id ? ` · Provider #${order.provider_id}` : ''}</p></div></div>
                <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>{status?.label ?? order.status}</Chip>
                <Link to="/app/work-orders" className="inline-flex items-center gap-1 text-sm font-semibold text-brand-ink hover:underline">Review <ArrowRight className="h-3.5 w-3.5" /></Link>
              </li>;
            })}
          </ul>
        )}
      </section>

      <section aria-labelledby="recent-activity-heading" className="border-t border-line pt-6">
        <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-ink">Record of action</p><h2 id="recent-activity-heading" className="mt-1 font-heading text-lg font-semibold text-ink">Recent activity</h2></div><p className="text-xs text-ink-muted">{estate?.estate_name ?? 'Selected estate'}</p></div>
        {complaints.loading || workOrders.loading ? <div className="mt-3"><LoadingState label="Loading recent activity" /></div> : complaints.error && workOrders.error ? <p className="py-3 text-sm text-ink-muted">Recent activity is unavailable.</p> : <div className="mt-2"><ActivityList complaints={allComplaints.filter((item) => !CLOSED_STATUSES.has(item.status ?? '')).slice(0, 6)} workOrders={workOrderItems.slice(0, 6)} /></div>}
      </section>

      <p className="border-t border-line pt-4 text-xs text-ink-muted">
        Operational figures reflect records currently returned by VALORA. Deeper score history, calculation details, and intelligence evidence live in their dedicated workspaces.
      </p>
      <ComplaintDetail complaint={selectedComplaint} onClose={() => setSelectedComplaint(null)} />
    </div>
  );
}

export { AdminDashboard as DashboardBody };
