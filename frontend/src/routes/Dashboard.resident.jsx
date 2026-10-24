import { useMemo } from 'react';
import { ArrowRight, Bell, CalendarDays, CheckCircle2, Clock3, HeartPulse, Plus, Wrench } from 'lucide-react';
import { Link, useOutletContext } from 'react-router-dom';
import { Chip, EmptyState, ErrorState, LoadingState } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { getLivingScore } from '../lib/analytics';
import { api } from '../lib/api';
import { complaintStatus, pillarBand } from '../lib/display';
import { shortDate, relativeDays } from '../lib/format';
import { useAsync } from '../lib/useAsync';

const TERMINAL_STATUSES = new Set(['resolved', 'closed', 'rated']);

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function statusGuidance(status) {
  switch (status) {
    case 'submitted': return 'Awaiting estate review';
    case 'reviewed': return 'Under review by the estate team';
    case 'assigned': return 'A provider has been assigned';
    case 'in_progress': return 'Repair work is underway';
    case 'resolved': return 'Marked resolved by the estate team';
    case 'rated': return 'Completed and rated';
    case 'closed': return 'This request has been closed';
    default: return 'See the request for its latest status';
  }
}

function CommunityHero({ estate }) {
  const estateName = estate?.estate_name ?? 'Your residential community';
  const location = [estate?.suburb, estate?.city, estate?.province].filter(Boolean).join(' · ');

  return (
    <section className="relative isolate h-[190px] overflow-hidden bg-brand-wash sm:h-[230px] lg:h-[248px]" aria-label="Your residential community">
      <img
        src="/estate-hero.jpg"
        alt="Contemporary residential architecture and landscaped grounds"
        width="1200"
        height="520"
        fetchPriority="high"
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-[#21152f]/75 via-[#21152f]/10 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 p-5 text-white sm:p-7">
        <p className="text-[0.64rem] font-semibold uppercase tracking-[0.17em] text-white/75">Your community, in view</p>
        <h2 className="mt-1 font-heading text-xl font-semibold tracking-[-0.025em] sm:text-2xl">{estateName}</h2>
        {location ? <p className="mt-0.5 text-xs text-white/80">{location}</p> : null}
      </div>
    </section>
  );
}

function RequestRow({ item }) {
  const status = complaintStatus[item.status ?? 'submitted'];
  const isOpen = !TERMINAL_STATUSES.has(item.status ?? '');
  return (
    <li className="group border-b border-brand/10 last:border-b-0">
      <Link
        to="/app/complaints"
        state={{ focusComplaintId: item.id }}
        aria-label={`View request ${item.id}: ${item.description}`}
        className="grid min-w-0 grid-cols-[38px_minmax(0,1fr)_auto] items-center gap-3 py-3.5 transition-colors hover:bg-brand-wash/35 sm:gap-4 sm:px-2"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-wash text-brand-ink">
          {isOpen ? <Wrench className="h-4 w-4" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-[0.84rem] font-semibold text-ink">{item.description}</span>
          <span className="mt-0.5 block truncate text-xs text-ink/50">
            {item.category ? `${item.category} · ` : ''}Unit {item.unit_id} · {relativeDays(item.created_at)}
          </span>
          <span className="mt-1 hidden text-xs text-ink/60 sm:block">{statusGuidance(item.status)}</span>
        </span>
        <span className="flex items-center gap-2">
          <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>{status?.label ?? item.status}</Chip>
          <ArrowRight className="h-4 w-4 shrink-0 text-ink/35 transition-transform group-hover:translate-x-0.5 group-hover:text-brand" aria-hidden="true" />
        </span>
      </Link>
    </li>
  );
}

function EstateHealthSummary({ snapshot, loading, error }) {
  const scoreAvailable = snapshot?.status === 'scored' && snapshot?.overall_score !== null && snapshot?.overall_score !== undefined;
  const score = scoreAvailable ? Number(snapshot.overall_score) : null;
  const band = scoreAvailable ? pillarBand(score) : null;
  const percentage = score === null ? 0 : Math.max(0, Math.min(100, score));

  return (
    <section className="flex flex-col gap-4 border-t border-brand/10 py-5 sm:flex-row sm:items-center sm:justify-between" aria-labelledby="resident-health-heading">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-wash text-brand-ink">
          <HeartPulse className="h-4 w-4" aria-hidden="true" />
        </span>
        <div>
          <h2 id="resident-health-heading" className="font-heading text-base font-semibold text-ink">Estate health</h2>
          <p className="mt-0.5 text-xs leading-relaxed text-ink/55">A measured view of how the estate is being maintained.</p>
          {loading ? <div className="mt-2"><LoadingState label="Loading estate health" /></div> : error ? (
            <p className="mt-2 text-xs text-ink/60">Estate health is temporarily unavailable.</p>
          ) : scoreAvailable ? (
            <p className="mt-1.5 text-xs text-ink/60">Updated {shortDate(snapshot.as_of ?? snapshot.calculated_at)} · {band?.label ?? 'Published score'}</p>
          ) : (
            <p className="mt-1.5 max-w-md text-xs leading-relaxed text-ink/60">Not enough data yet for a published Living Score. The score appears when the estate has sufficient measured operational history.</p>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between gap-4 sm:justify-end">
        {scoreAvailable ? (
          <div
            role="img"
            aria-label={`Living Score ${score.toLocaleString('en-ZA', { maximumFractionDigits: 1 })} out of 100`}
            className="flex h-[66px] w-[66px] shrink-0 items-center justify-center rounded-full"
            style={{ background: `conic-gradient(#7041D8 ${percentage}%, #e9e1f6 ${percentage}% 100%)` }}
          >
            <div className="flex h-[52px] w-[52px] flex-col items-center justify-center rounded-full bg-white">
              <span className="num text-base font-bold leading-none text-brand-ink">{score.toLocaleString('en-ZA', { maximumFractionDigits: 1 })}</span>
              <span className="mt-0.5 text-[0.55rem] text-ink/40">/ 100</span>
            </div>
          </div>
        ) : null}
        <Link to="/app/health" className="inline-flex min-h-9 items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">
          View details <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>
    </section>
  );
}

export function ResidentDashboard() {
  const { estateId, estate, loading: estateLoading } = useEstateScope();
  const { user } = useAuth();
  const { onLogComplaint } = useOutletContext() ?? {};
  const complaints = useAsync(
    () => estateId === null ? Promise.resolve({ items: [], total: 0 }) : api.get('/api/v1/complaints', { estate_id: estateId, size: 10, sort: '-created_at' }),
    [estateId],
  );
  const announcements = useAsync(
    () => estateId === null ? Promise.resolve({ items: [], total: 0 }) : api.get('/api/v1/announcements', { estate_id: estateId, size: 4 }),
    [estateId],
  );
  const score = useAsync(
    () => estateId === null ? Promise.resolve(null) : getLivingScore(estateId).catch((error) => {
      if (error?.status === 404) return null;
      throw error;
    }),
    [estateId],
  );

  const firstName = user?.full_name?.trim().split(/\s+/)[0] || 'there';
  const allRequests = complaints.data?.items ?? [];
  const openRequests = useMemo(
    () => allRequests.filter((item) => !TERMINAL_STATUSES.has(item.status ?? '')),
    [allRequests],
  );
  const notices = announcements.data?.items ?? [];

  return (
    <div className="space-y-7 pb-5">
      {estateLoading ? <LoadingState label="Loading your estate" /> : null}

      <section className="grid gap-5 lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)] lg:items-stretch" aria-label="Resident welcome">
        <header className="flex min-w-0 flex-col items-start justify-center gap-4 border-b border-brand/10 pb-5 lg:border-b-0 lg:py-5">
          <div>
            <p className="text-[0.65rem] font-bold uppercase tracking-[0.17em] text-brand-ink">{greeting()}</p>
            <h1 className="mt-1 font-heading text-3xl font-semibold leading-tight tracking-[-0.045em] text-ink sm:text-[2.7rem]">
              {firstName}
            </h1>
            <p className="mt-2 max-w-md text-sm leading-relaxed text-ink/60">
              Your estate, your home. Here's what's happening at {estate?.estate_name ?? 'your community'}.
            </p>
          </div>
          <button
            type="button"
            onClick={onLogComplaint}
            disabled={!onLogComplaint}
            className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 bg-brand px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-ink disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <Plus className="h-4 w-4" aria-hidden="true" /> Report an issue <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </header>
        <CommunityHero estate={estate} />
      </section>

      <section className="grid gap-4 border-y border-brand/15 py-4 sm:grid-cols-3 sm:gap-0" aria-label="Estate at a glance">
        <div className="sm:border-r sm:border-brand/10 sm:pr-5">
          <p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-brand-ink">Your open requests</p>
          <p className="num mt-1 text-2xl font-semibold leading-none text-ink">{complaints.loading ? '—' : openRequests.length}</p>
          <Link to="/app/complaints" className="mt-1 inline-flex min-h-8 items-center text-xs font-semibold text-brand-ink hover:underline">Track progress <ArrowRight className="ml-1 h-3 w-3" aria-hidden="true" /></Link>
        </div>
        <div className="sm:border-r sm:border-brand/10 sm:px-5">
          <p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-brand-ink">Estate health</p>
          <p className="num mt-1 text-2xl font-semibold leading-none text-ink">{score.loading || score.error ? '—' : (score.data?.overall_score ?? '—')}</p>
          <Link to="/app/health" className="mt-1 inline-flex min-h-8 items-center text-xs font-semibold text-brand-ink hover:underline">View measured health <ArrowRight className="ml-1 h-3 w-3" aria-hidden="true" /></Link>
        </div>
        <div className="sm:pl-5">
          <p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-brand-ink">Latest community update</p>
          <p className="mt-1 line-clamp-1 text-sm font-semibold text-ink">{notices[0]?.title ?? 'No updates yet'}</p>
          <Link to="/app/announcements" className="mt-1 inline-flex min-h-8 items-center text-xs font-semibold text-brand-ink hover:underline">Read announcements <ArrowRight className="ml-1 h-3 w-3" aria-hidden="true" /></Link>
        </div>
      </section>

      <section aria-labelledby="requests-heading">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-brand/15 pb-3">
          <div>
            <h2 id="requests-heading" className="font-heading text-xl font-semibold tracking-tight text-ink sm:text-2xl">Your requests</h2>
            <p className="mt-1 text-xs text-ink/50">
              {openRequests.length > 0 ? `${openRequests.length} active in your latest requests` : 'Track every issue from report to resolution.'}
            </p>
          </div>
          <Link to="/app/complaints" className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-ink hover:underline">
            View all <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>

        <div className="mt-1">
          {complaints.loading ? <LoadingState label="Loading your requests" /> : complaints.error ? (
            <ErrorState title="Your requests could not be loaded" message={complaints.error.message} requestId={complaints.error.requestId} action={<button type="button" onClick={complaints.reload} className="text-sm font-semibold text-brand-ink underline">Try again</button>} />
          ) : openRequests.length === 0 ? (
            <div className="flex flex-col items-start gap-3 py-6 sm:flex-row sm:items-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-wash text-brand-ink"><CheckCircle2 className="h-5 w-5" aria-hidden="true" /></span>
              <div className="flex-1">
                <p className="font-semibold text-ink">Nothing needs your attention right now.</p>
                <p className="mt-1 text-sm text-ink/55">When something needs fixing, report it here and follow its progress from this list.</p>
              </div>
              <button type="button" onClick={onLogComplaint} disabled={!onLogComplaint} className="text-sm font-semibold text-brand-ink hover:underline disabled:opacity-50">Report an issue <ArrowRight className="ml-1 inline h-3.5 w-3.5" aria-hidden="true" /></button>
            </div>
          ) : (
            <ul>{openRequests.slice(0, 5).map((item) => <RequestRow key={item.id} item={item} />)}</ul>
          )}
        </div>
      </section>

      <section aria-labelledby="notices-heading" className="border-t border-brand/10 pt-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Bell className="h-4 w-4 text-brand-ink" aria-hidden="true" />
            <h2 id="notices-heading" className="font-heading text-lg font-semibold text-ink">Important announcements</h2>
          </div>
          <Link to="/app/announcements" className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-ink hover:underline">
            View all <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>
        {announcements.loading ? <div className="mt-3"><LoadingState label="Loading announcements" /></div> : announcements.error ? (
          <div className="mt-3"><ErrorState title="Announcements unavailable" message={announcements.error.message} requestId={announcements.error.requestId} action={<button type="button" onClick={announcements.reload} className="text-sm font-semibold text-brand-ink underline">Try again</button>} /></div>
        ) : notices.length === 0 ? (
          <div className="mt-3 flex items-start gap-3 bg-brand-wash/45 px-4 py-4">
            <CalendarDays className="mt-0.5 h-4 w-4 shrink-0 text-brand-ink" aria-hidden="true" />
            <div><p className="text-sm font-semibold text-ink">No announcements yet</p><p className="mt-1 text-xs text-ink/55">Official updates from your estate will appear here when published.</p></div>
          </div>
        ) : (
          <ul className="mt-3 divide-y divide-brand/10">
            {notices.slice(0, 3).map((notice, index) => (
              <li key={notice.id} className={index === 0 ? 'bg-brand-wash/50 px-4 py-4' : 'px-1 py-4'}>
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-brand-ink"><CalendarDays className="h-4 w-4" aria-hidden="true" /></span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                      <h3 className="text-sm font-semibold text-ink">{notice.title}</h3>
                      <time className="text-xs text-ink/45">{shortDate(notice.created_at)}</time>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-ink/60">{notice.message}</p>
                    <Link to="/app/announcements" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-ink hover:underline">View details <ArrowRight className="h-3 w-3" aria-hidden="true" /></Link>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <EstateHealthSummary snapshot={score.data} loading={score.loading} error={score.error} />
      <p className="flex items-start gap-2 border-t border-brand/10 pt-3 text-[0.7rem] leading-relaxed text-ink/45">
        <Clock3 className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        Request statuses reflect the latest records returned by VALORA. The full history remains in My requests.
      </p>
    </div>
  );
}
