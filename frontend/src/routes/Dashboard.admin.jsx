import { useMemo, useState } from 'react';
import { ArrowRight, Bell, CalendarDays, CheckCircle2, CircleAlert, Clock3, FileText, HeartPulse, ShieldAlert, Wrench } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Chip, ErrorState, LoadingState } from '../components/ui';
import { ComplaintDrawer } from '../components/ComplaintDrawer';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api, ApiError } from '../lib/api';
import { getLivingScore, getLivingScoreHistory, recalculateLivingScore } from '../lib/analytics';
import { complaintStatus, pillarBand, workOrderStatus } from '../lib/display';
import { displayLabel, relativeDays, shortDate } from '../lib/format';
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
  const firstName = user?.full_name?.trim().split(' ').filter(Boolean)[0] || 'there';
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <div className="space-y-6 pb-6">
      <header className="flex flex-col justify-between gap-3 border-b border-brand/10 pb-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] text-brand-ink">Welcome back</p>
          <h1 className="mt-1 font-heading text-3xl font-semibold leading-tight tracking-[-0.045em] text-ink sm:text-[2.65rem]">
            {greeting}, <span className="text-brand-ink">{firstName}</span>
          </h1>
          <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-ink/55">
            Here's the current status for {estate?.estate_name ?? 'your estate'}.
          </p>
        </div>
      </header>

      <section className="grid gap-0 overflow-hidden border border-brand/10 bg-white md:grid-cols-[1.12fr_0.88fr]" aria-label="Estate summary">
        <EstateContextHero estate={estate} />
        <div className="flex items-center px-5 py-5 sm:px-6">
          <ScoreSummary
            snapshot={score.data}
            history={scoreHistory.data}
            loading={score.loading || scoreHistory.loading}
            error={score.error || scoreHistory.error}
            onRecalculate={recalculateScore}
            recalculating={recalculating}
            recalculateError={recalculateError}
          />
        </div>
      </section>

      <section className="grid gap-8 xl:grid-cols-[minmax(0,1.55fr)_minmax(250px,0.72fr)] xl:gap-9">
        <div className="min-w-0">
          <div className="flex flex-wrap items-end justify-between gap-3 border-b border-brand/15 pb-3">
            <div>
              <h2 className="font-heading text-xl font-semibold tracking-tight text-ink sm:text-2xl">What needs your attention today?</h2>
              <p className="mt-1 text-xs text-ink/50">Priority issues and open items requiring action.</p>
            </div>
            <Link to="/app/complaints" className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-ink hover:underline">
              All complaints <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>

          {urgentCount > 0 ? (
            <div className="my-3 flex items-start gap-2.5 border-l-2 border-signal bg-signal-wash/55 px-3.5 py-2.5">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-signal-ink" aria-hidden="true" />
              <div>
                <p className="text-xs font-semibold text-signal-ink">{urgentCount} high-priority issue{urgentCount === 1 ? '' : 's'} in the latest records</p>
                <p className="mt-0.5 text-[0.7rem] leading-relaxed text-ink/60">Open an issue to inspect the record and continue the workflow.</p>
              </div>
            </div>
          ) : null}

          <div className="hidden grid-cols-[minmax(0,1.6fr)_100px_minmax(90px,0.7fr)_140px] gap-4 border-b border-brand/10 px-2 py-2.5 text-[0.6rem] font-bold uppercase tracking-[0.13em] text-ink/40 sm:grid">
            <span>Issue</span><span>Priority</span><span>Owner</span><span>Next action</span>
          </div>

          {complaints.loading ? <div className="py-5"><LoadingState label="Loading priority issues" /></div> : complaints.error ? (
            <div className="py-4">
              <ErrorState title="Issues could not be loaded" message={complaints.error.message} requestId={complaints.error.requestId} action={<button onClick={complaints.reload} type="button" className="text-sm font-semibold text-brand-ink underline">Try again</button>} />
            </div>
          ) : activeComplaints.length === 0 ? (
            <div className="flex items-start gap-3 py-7">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-mint-ink" aria-hidden="true" />
              <div><p className="font-semibold text-ink">No open complaints on record.</p><p className="mt-1 text-sm text-ink/55">New submissions will appear here for review.</p></div>
            </div>
          ) : (
            <ul>{activeComplaints.slice(0, 7).map((item) => <PriorityRow key={item.id} complaint={item} onSelect={setSelectedComplaint} />)}</ul>
          )}
          {activeComplaints.length > 7 ? <Link to="/app/complaints" className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-brand-ink hover:underline">View all {activeComplaints.length} open items <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link> : null}

          <section className="mt-7 border-t border-brand/10 pt-5" aria-labelledby="operational-pulse-heading">
            <div className="flex items-baseline justify-between gap-3">
              <div>
                <h2 id="operational-pulse-heading" className="font-heading text-lg font-semibold text-ink">Operational pulse</h2>
                <p className="mt-1 text-xs text-ink/50">Latest measurements from stored estate records.</p>
              </div>
              <Link to="/app/health" className="text-xs font-semibold text-brand-ink hover:underline">Estate health <ArrowRight className="ml-1 inline h-3 w-3" aria-hidden="true" /></Link>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-4 border-y border-brand/10 py-4 sm:grid-cols-4 sm:gap-0">
              <div className="sm:border-r sm:border-brand/10 sm:pr-4">
                <p className="flex items-center gap-2 text-[0.68rem] text-ink/55"><span className="h-2 w-2 rounded-full bg-signal" />Open complaints</p>
                <p className="num mt-1 text-2xl font-semibold text-ink">{stats.loading || stats.error ? '—' : openComplaintCount}</p>
              </div>
              <div className="sm:border-r sm:border-brand/10 sm:px-4">
                <p className="flex items-center gap-2 text-[0.68rem] text-ink/55"><span className="h-2 w-2 rounded-full bg-brand" />Work in progress</p>
                <p className="num mt-1 text-2xl font-semibold text-ink">{workOrders.loading || workOrders.error ? '—' : workOrdersInFlight.length}</p>
              </div>
              <div className="sm:border-r sm:border-brand/10 sm:px-4">
                <p className="flex items-center gap-2 text-[0.68rem] text-ink/55"><span className="h-2 w-2 rounded-full bg-ochre" />Awaiting review</p>
                <p className="num mt-1 text-2xl font-semibold text-ink">{stats.loading || stats.error ? '—' : needsReview}</p>
              </div>
              <div className="sm:pl-4">
                <p className="flex items-center gap-2 text-[0.68rem] text-ink/55"><span className="h-2 w-2 rounded-full bg-mint" />Resolution rate</p>
                <p className="num mt-1 text-2xl font-semibold text-ink">{stats.loading || stats.error || resolutionRate == null ? '—' : String(Number(resolutionRate).toFixed(0)) + '%'}</p>
              </div>
            </div>
            {complaints.loading || workOrders.loading ? <div className="mt-3"><LoadingState label="Loading recent activity" /></div> : complaints.error && workOrders.error ? (
              <p className="py-3 text-xs text-ink/50">Recent activity is unavailable.</p>
            ) : (
              <div className="mt-2"><ActivityList complaints={allComplaints.slice(0, 6)} workOrders={workOrderItems.slice(0, 6)} /></div>
            )}
          </section>
        </div>

        <aside className="min-w-0">
          <section className="border border-brand/10 bg-white" aria-labelledby="estate-profile-heading">
            <img src="/estate-hero.jpg" alt="Contemporary residential architecture" width="720" height="320" loading="lazy" className="h-[118px] w-full object-cover sm:h-[140px]" />
            <div className="p-4">
              <p className="text-[0.6rem] font-bold uppercase tracking-[0.15em] text-brand-ink">Selected estate</p>
              <h2 id="estate-profile-heading" className="mt-1 font-heading text-lg font-semibold text-ink">{estate?.estate_name ?? 'Estate profile'}</h2>
              <p className="mt-0.5 text-xs text-ink/50">{[estate?.suburb, estate?.city, estate?.province].filter(Boolean).join(', ') || 'Location not recorded'}</p>
              <p className="mt-1 text-xs text-ink/50">{estate?.property_ids?.length ?? 0} units linked to your account</p>
              <div className="mt-4 divide-y divide-brand/10 border-t border-brand/10">
                <Link to="/admin/settings" className="flex items-center justify-between gap-3 py-3 text-xs font-semibold text-ink/70 hover:text-brand-ink">Estate profile <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>
                <Link to="/admin/members" className="flex items-center justify-between gap-3 py-3 text-xs font-semibold text-ink/70 hover:text-brand-ink">Residents and access <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>
                <Link to="/intelligence" className="flex items-center justify-between gap-3 py-3 text-xs font-semibold text-ink/70 hover:text-brand-ink">Reports and intelligence <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>
              </div>
            </div>
          </section>

          <section className="mt-6 border-t border-brand/10 pt-5" aria-labelledby="latest-notices">
            <div className="flex items-start justify-between gap-3">
              <div><h2 id="latest-notices" className="font-heading text-lg font-semibold text-ink">Community updates</h2><p className="mt-1 text-xs text-ink/50">Keep residents informed.</p></div>
              <Link to="/app/announcements" aria-label="View all announcements" className="flex h-8 w-8 items-center justify-center text-brand-ink hover:bg-brand-wash"><ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>
            </div>
            {announcements.loading ? <div className="mt-3"><LoadingState label="Loading notices" /></div> : announcements.error ? (
              <p className="mt-3 text-xs text-ink/55">Notices are temporarily unavailable.</p>
            ) : notices.length === 0 ? (
              <div className="mt-3 flex items-start gap-2.5 bg-brand-wash/40 px-3 py-3"><Bell className="mt-0.5 h-4 w-4 shrink-0 text-brand-ink" aria-hidden="true" /><p className="text-xs text-ink/55">No notices have been published yet.</p></div>
            ) : (
              <ul className="mt-3 divide-y divide-brand/10">
                {notices.slice(0, 2).map((notice, index) => <li key={notice.id} className={index === 0 ? 'bg-brand-wash/45 px-3 py-3' : 'py-3'}>
                  <div className="flex items-start gap-2.5">
                    <CalendarDays className="mt-0.5 h-4 w-4 shrink-0 text-brand-ink" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline justify-between gap-2"><p className="text-xs font-semibold text-ink">{notice.title}</p><time className="text-[0.64rem] text-ink/40">{shortDate(notice.created_at)}</time></div>
                      <p className="mt-1 line-clamp-2 text-[0.7rem] leading-relaxed text-ink/55">{notice.message}</p>
                    </div>
                  </div>
                </li>)}
              </ul>
            )}
            <Link to="/app/announcements" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-brand-ink hover:underline">Manage announcements <ArrowRight className="h-3 w-3" aria-hidden="true" /></Link>
          </section>

          <section className="mt-6 border-t border-brand/10 pt-5" aria-labelledby="work-orders-heading">
            <div className="flex items-center justify-between gap-3">
              <div><h2 id="work-orders-heading" className="font-heading text-lg font-semibold text-ink">Work in motion</h2><p className="mt-1 text-xs text-ink/50">Assigned and active repairs.</p></div>
              <Link to="/app/work-orders" aria-label="View all work orders" className="flex h-8 w-8 items-center justify-center text-brand-ink hover:bg-brand-wash"><ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>
            </div>
            {workOrders.loading ? <div className="mt-3"><LoadingState label="Loading work orders" /></div> : workOrders.error ? (
              <p className="mt-3 text-xs text-ink/55">Work orders are temporarily unavailable.</p>
            ) : workOrdersInFlight.length === 0 ? (
              <p className="py-4 text-xs text-ink/50">No active work orders are recorded.</p>
            ) : (
              <ul className="mt-2 divide-y divide-brand/10">
                {workOrdersInFlight.slice(0, 3).map((order) => {
                  const status = workOrderStatus[order.status ?? 'assigned'];
                  return <li key={order.id} className="flex items-start gap-2.5 py-3">
                    <Wrench className="mt-0.5 h-4 w-4 shrink-0 text-brand-ink" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-ink">Work order #{order.id}</p>
                      <p className="mt-0.5 text-[0.68rem] text-ink/50">Complaint #{order.complaint_id}</p>
                      <p className="mt-1 text-[0.68rem] text-ink/60">{status?.label ?? displayLabel(order.status ?? 'assigned')}</p>
                    </div>
                  </li>;
                })}
              </ul>
            )}
          </section>
        </aside>
      </section>

      <section className="border-t border-brand/10 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[0.7rem] text-ink/45">Figures reflect records returned for this estate. Living Score details and supporting history are in Estate Health.</p>
          <Link to="/app/health" className="inline-flex items-center gap-1 text-[0.7rem] font-semibold text-brand-ink hover:underline">Explore Estate Health <ArrowRight className="h-3 w-3" aria-hidden="true" /></Link>
        </div>
      </section>
      {selectedComplaint ? (
        <ComplaintDrawer
          complaintId={selectedComplaint.id}
          onClose={() => setSelectedComplaint(null)}
          onChanged={() => {
            complaints.reload();
            stats.reload();
            workOrders.reload();
            score.reload();
            scoreHistory.reload();
          }}
        />
      ) : null}
    </div>
  );
}

export { AdminDashboard as DashboardBody };
