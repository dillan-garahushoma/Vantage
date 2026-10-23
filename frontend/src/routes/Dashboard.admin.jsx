import { useMemo, useState } from 'react';
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, CalendarDays, CheckCircle2, CircleAlert, Clock3, FileText, HeartPulse, ShieldAlert, Wrench } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Chip, ErrorState, LoadingState } from '../components/ui';
import { Drawer } from '../components/ui/drawer';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api, ApiError } from '../lib/api';
import { getLivingScore, getLivingScoreHistory, recalculateLivingScore } from '../lib/analytics';
import { complaintStatus, pillarBand, workOrderStatus } from '../lib/display';
import { displayLabel, durationHours, relativeDays, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';

const OPEN_STATUSES = new Set(['submitted', 'reviewed', 'assigned', 'in_progress']);

function EstateContextHero({ estate }) {
  const location = [estate?.suburb, estate?.city, estate?.province].filter(Boolean).join(' · ');
  return (
    <section className="relative min-h-[154px] overflow-hidden bg-brand-wash sm:min-h-[174px]" aria-label="Selected estate">
      <img
        src="/estate-hero.jpg"
        alt="Contemporary residential architecture and landscaped grounds"
        width="960"
        height="420"
        fetchPriority="high"
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-r from-[#241532]/80 via-[#241532]/35 to-transparent" />
      <div className="relative flex min-h-[154px] max-w-xl flex-col justify-end p-5 text-white sm:min-h-[174px] sm:p-6">
        <p className="text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-white/75">Your estate</p>
        <h2 className="mt-1 font-heading text-xl font-semibold tracking-tight sm:text-2xl">{estate?.estate_name ?? 'Selected estate'}</h2>
        {location ? <p className="mt-1 text-xs text-white/80">{location}</p> : null}
      </div>
    </section>
  );
}

function nextAction(status) {
  switch (status) {
    case 'submitted': return 'Review issue';
    case 'reviewed': return 'Assign provider';
    case 'assigned': return 'Confirm work start';
    case 'in_progress': return 'Follow repair';
    default: return 'Open record';
  }
}

function PriorityRow({ complaint, onSelect }) {
  const priority = (complaint.priority ?? 'normal').toLowerCase();
  const critical = priority === 'urgent';
  const high = priority === 'high';
  const status = complaintStatus[complaint.status ?? 'submitted'];
  return (
    <li className="border-b border-brand/10 last:border-b-0">
      <button
        type="button"
        onClick={() => onSelect(complaint)}
        className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 py-3.5 text-left transition-colors hover:bg-brand-wash/35 focus-visible:outline-2 focus-visible:outline-brand sm:grid-cols-[minmax(0,1.6fr)_100px_minmax(90px,0.7fr)_140px] sm:gap-4 sm:px-2"
        aria-label={`Open issue details for complaint ${complaint.id}: ${complaint.description}`}
      >
        <span className="flex min-w-0 items-start gap-3">
          <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${critical ? 'bg-signal-wash text-signal-ink' : high ? 'bg-ochre-wash text-ochre-ink' : 'bg-brand-wash text-brand-ink'}`}>
            {critical || high ? <CircleAlert className="h-3.5 w-3.5" aria-hidden="true" /> : <Wrench className="h-3.5 w-3.5" aria-hidden="true" />}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block line-clamp-2 text-[0.82rem] font-semibold leading-snug text-ink">{complaint.description}</span>
            <span className="mt-1 block truncate text-[0.68rem] text-ink/50">
              {displayLabel(complaint.category)} · Unit {complaint.unit_id} · #{complaint.id}
            </span>
            <span className="mt-1 block text-[0.68rem] text-ink/45 sm:hidden">
              {status?.label ?? displayLabel(complaint.status ?? 'submitted')} · {relativeDays(complaint.created_at)}
            </span>
          </span>
        </span>

        <span className={`inline-flex w-fit items-center rounded-full px-2 py-1 text-[0.62rem] font-semibold ${critical ? 'bg-signal-wash text-signal-ink' : high ? 'bg-ochre-wash text-ochre-ink' : priority === 'low' ? 'bg-mint-wash text-mint-ink' : 'bg-brand-wash text-brand-ink'}`}>
          {displayLabel(priority)}
        </span>

        <span className="hidden min-w-0 truncate text-[0.74rem] text-ink/60 sm:block">
          {complaint.assigned_to?.trim() || 'Not assigned'}
        </span>

        <span className="col-span-2 flex items-center justify-between gap-2 border-t border-brand/5 pt-2 text-[0.72rem] font-semibold text-brand-ink sm:col-span-1 sm:border-0 sm:pt-0">
          <span className="flex min-w-0 items-center gap-2">
            <span className="hidden text-[0.68rem] font-normal text-ink/45 sm:inline">{status?.label ?? displayLabel(complaint.status ?? 'submitted')}</span>
            <span className="truncate">{nextAction(complaint.status)}</span>
          </span>
          <ArrowRight className="h-3.5 w-3.5 shrink-0 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
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
  const percentage = score === null ? 0 : Math.max(0, Math.min(100, score));

  return (
    <section className="flex min-w-0 items-center gap-4" aria-labelledby="estate-health-summary">
      <div
        className="flex h-[74px] w-[74px] shrink-0 items-center justify-center rounded-full"
        style={{ background: `conic-gradient(#7041D8 ${percentage}%, #e9e1f6 ${percentage}% 100%)` }}
        role={scored ? 'img' : undefined}
        aria-label={scored ? `Living Score ${score.toLocaleString('en-ZA', { maximumFractionDigits: 1 })} out of 100` : undefined}
      >
        <div className="flex h-[58px] w-[58px] flex-col items-center justify-center rounded-full bg-white">
          <span className="num text-lg font-bold leading-none text-brand-ink">{loading ? '—' : scored ? score.toLocaleString('en-ZA', { maximumFractionDigits: 1 }) : '—'}</span>
          <span className="mt-1 text-[0.55rem] text-ink/40">/ 100</span>
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-brand-ink">
          <HeartPulse className="h-4 w-4 shrink-0" aria-hidden="true" />
          <p id="estate-health-summary" className="text-[0.65rem] font-bold uppercase tracking-[0.13em]">Estate health</p>
        </div>
        {loading ? <div className="mt-2"><LoadingState label="Loading Living Score" /></div> : error ? (
          <p className="mt-1 text-xs text-ink/55">Estate health is temporarily unavailable.</p>
        ) : scored ? (
          <>
            <p className="mt-1 text-[0.78rem] font-semibold text-ink">{band?.label ?? 'Published score'}</p>
            <p className="mt-0.5 text-[0.66rem] text-ink/50">Updated {shortDate(snapshot.as_of ?? snapshot.calculated_at)}</p>
            {change !== null ? <p className={`mt-1 text-[0.65rem] font-semibold ${change > 0 ? 'text-mint-ink' : change < 0 ? 'text-signal-ink' : 'text-ink/45'}`}>{change > 0 ? '+' : ''}{change.toLocaleString('en-ZA', { maximumFractionDigits: 1 })} points vs previous snapshot</p> : null}
          </>
        ) : (
          <p className="mt-1 text-[0.74rem] leading-relaxed text-ink/55">Not enough data for a published Living Score yet.</p>
        )}

        {recalculateError ? <div role="alert" className="mt-2 border-l-2 border-signal bg-signal-wash/60 px-2.5 py-2 text-[0.68rem] text-signal-ink"><p className="font-semibold">Recalculation refused</p><p className="mt-1">{recalculateError.message}</p>{recalculateError.requestId ? <p className="mt-1">Reference: {recalculateError.requestId}</p> : null}</div> : null}

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          <Link to="/app/health" className="inline-flex items-center gap-1 text-[0.72rem] font-semibold text-brand-ink hover:underline">
            Explore Estate Health <ArrowRight className="h-3 w-3" aria-hidden="true" />
          </Link>
          <button type="button" onClick={onRecalculate} disabled={recalculating} className="text-[0.66rem] font-medium text-ink/45 underline-offset-4 hover:text-brand-ink hover:underline disabled:opacity-50">
            {recalculating ? 'Recalculating…' : 'Recalculate'}
          </button>
        </div>
      </div>
    </section>
  );
}

function ComplaintDetail({ complaint, onClose }) {
  const status = complaint ? complaintStatus[complaint.status ?? 'submitted'] : null;
  return (
    <Drawer
      open={Boolean(complaint)}
      onOpenChange={(open) => { if (!open) onClose(); }}
      side="right"
      width="sm:max-w-[560px]"
      title={complaint ? `Complaint #${complaint.id}` : ''}
      subtitle={complaint ? `${displayLabel(complaint.category ?? 'General')}${complaint.unit_id ? ` · Unit ${complaint.unit_id}` : ''}` : ''}
      badge={complaint ? <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>{status?.label ?? complaint.status}</Chip> : null}
      footer={complaint ? (
        <Link to="/app/complaints" onClick={onClose} className="inline-flex w-full items-center justify-center gap-2 bg-brand px-4 py-3 text-sm font-semibold text-white hover:bg-brand-ink">
          Open complaint workspace <ArrowRight className="h-4 w-4" />
        </Link>
      ) : null}
    >
      {complaint ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`text-xs font-semibold uppercase ${complaint.priority === 'urgent' ? 'text-signal-ink' : complaint.priority === 'high' ? 'text-ochre-ink' : 'text-ink-muted'}`}>
              {displayLabel(complaint.priority ?? 'normal')} priority
            </span>
            <span className="text-xs text-ink-muted">Logged {relativeDays(complaint.created_at)}</span>
          </div>
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-muted">Record details</h3>
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
          <div className="border-l-2 border-brand bg-brand-wash/50 px-4 py-3">
            <p className="text-sm font-semibold text-ink">Next step</p>
            <p className="mt-1 text-sm leading-relaxed text-ink-soft">Open the complaint workspace to inspect the full record, assign a provider, and continue the complaint lifecycle.</p>
          </div>
        </div>
      ) : null}
    </Drawer>
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

  const openComplaintCount = stats.data
    ? Math.max(
        0,
        Number(stats.data.total ?? 0) -
          Number(stats.data.by_status?.resolved ?? 0) -
          Number(stats.data.by_status?.rated ?? 0) -
          Number(stats.data.by_status?.closed ?? 0),
      )
    : activeComplaints.length;
  const needsReview = stats.data
    ? Number(stats.data.by_status?.submitted ?? 0) + Number(stats.data.by_status?.reviewed ?? 0)
    : activeComplaints.filter((item) => ['submitted', 'reviewed'].includes(item.status ?? '')).length;
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
          <div><p className="text-xs text-ink-muted">Open complaints</p><p className="num mt-1 font-heading text-3xl font-semibold text-ink">{stats.loading || stats.error ? '—' : openComplaintCount}</p><p className="mt-1 text-xs text-ink-muted">{stats.error ? 'Count unavailable' : `${needsReview} awaiting review`}</p></div>
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
              <h2 className="mt-1 font-heading text-xl font-semibold tracking-tight text-ink sm:text-2xl">Priority issues <span className="ml-1 text-sm font-medium text-ink-muted">{stats.error ? '' : openComplaintCount}</span></h2>
            </div>
            <Link to="/app/complaints" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">Open complaints <ArrowRight className="h-3.5 w-3.5" /></Link>
          </div>

          {urgentCount > 0 ? (
            <div className="my-4 flex items-start gap-3 border-l-2 border-signal bg-signal-wash/60 px-4 py-3">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-signal-ink" />
              <div><p className="text-sm font-semibold text-signal-ink">{urgentCount} high-priority item{urgentCount === 1 ? '' : 's'} in the latest records need attention</p><p className="mt-0.5 text-xs leading-relaxed text-ink-soft">Review the recorded details and decide the next action.</p></div>
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
        {complaints.loading || workOrders.loading ? <div className="mt-3"><LoadingState label="Loading recent activity" /></div> : complaints.error && workOrders.error ? <p className="py-3 text-sm text-ink-muted">Recent activity is unavailable.</p> : <div className="mt-2"><ActivityList complaints={allComplaints.slice(0, 6)} workOrders={workOrderItems.slice(0, 6)} /></div>}
      </section>

      <p className="border-t border-line pt-4 text-xs text-ink-muted">
        Operational figures reflect records currently returned by VALORA. Deeper score history, calculation details, and intelligence evidence live in their dedicated workspaces.
      </p>
      <ComplaintDetail complaint={selectedComplaint} onClose={() => setSelectedComplaint(null)} />
    </div>
  );
}

export { AdminDashboard as DashboardBody };
