import { ArrowRight, Bell, CalendarDays, CheckCircle2, Clock3, HeartPulse, Plus, Wrench } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Chip, EmptyState, ErrorState, LoadingState } from '../components/ui';
import { useEstateScope } from '../context/EstateContext';
import { useAuth } from '../context/AuthContext';
import { getLivingScore } from '../lib/analytics';
import { api } from '../lib/api';
import { complaintStatus, pillarBand } from '../lib/display';
import { relativeDays, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';

const TERMINAL_STATUSES = new Set(['resolved', 'closed', 'rated']);

function EstateHero({ estate, firstName }) {
  return (
    <section className="grid overflow-hidden border-y border-line bg-brand-wash/45 md:grid-cols-[1.08fr_0.92fr]" aria-label="Your estate">
      <div className="flex min-h-[250px] flex-col justify-between p-6 sm:p-8 lg:p-10">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-ink">Your place, your community</p>
          <h2 className="mt-3 max-w-xl font-heading text-3xl font-semibold leading-tight tracking-[-0.035em] text-ink sm:text-4xl">
            Welcome home, {firstName}.
          </h2>
          <p className="mt-3 max-w-lg text-sm leading-relaxed text-ink-soft sm:text-base">
            Keep up with what is happening at {estate?.estate_name ?? 'your estate'} and the requests that matter to you.
          </p>
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-muted">
          {estate?.suburb || estate?.city ? (
            <span className="inline-flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              {[estate.suburb, estate.city, estate.province].filter(Boolean).join(', ')}
            </span>
          ) : null}
          <Link to="/app/announcements" className="inline-flex items-center gap-1.5 font-semibold text-brand-ink hover:underline">
            Estate notices <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
      <div className="relative min-h-[220px] overflow-hidden md:min-h-full">
        <img
          src="/estate-hero.jpg"
          alt="Residential community architecture"
          width="960"
          height="640"
          className="absolute inset-0 h-full w-full object-cover"
          fetchPriority="high"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#24153f]/70 via-[#24153f]/10 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 p-5 text-white sm:p-7">
          <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-white/75">A community that works</p>
          <p className="mt-1 max-w-md font-heading text-lg font-medium leading-snug sm:text-xl">
            Clear updates. Visible progress. Better everyday living.
          </p>
        </div>
      </div>
    </section>
  );
}

function RequestRow({ item }) {
  const status = complaintStatus[item.status ?? 'submitted'];
  const isOpen = !TERMINAL_STATUSES.has(item.status ?? '');
  return (
    <li className="group grid gap-3 border-b border-line/80 py-4 first:pt-1 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <div className="flex min-w-0 items-start gap-3.5">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center bg-brand-wash text-brand-ink">
          {isOpen ? <Wrench className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{item.description}</p>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-muted">
            <span>#{item.id}</span>
            <span aria-hidden="true">·</span>
            <span>{item.category}</span>
            {item.unit_id ? <><span aria-hidden="true">·</span><span>Unit {item.unit_id}</span></> : null}
            <span aria-hidden="true">·</span>
            <span>{relativeDays(item.created_at)}</span>
          </p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 pl-[3.35rem] sm:justify-end sm:pl-0">
        <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>{status?.label ?? item.status}</Chip>
        <Link to="/app/complaints" aria-label={`View request ${item.id}`} className="inline-flex h-8 w-8 items-center justify-center text-ink-muted transition-colors hover:bg-brand-wash hover:text-brand-ink focus-visible:outline-2 focus-visible:outline-brand">
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </li>
  );
}

function EstateHealthSummary({ snapshot, loading, error }) {
  const scoreAvailable = snapshot?.status === 'scored' && snapshot?.overall_score !== null && snapshot?.overall_score !== undefined;
  const score = scoreAvailable ? Number(snapshot.overall_score) : null;
  const band = scoreAvailable ? pillarBand(score) : null;

  return (
    <section className="border-l-2 border-brand pl-4 sm:pl-5" aria-labelledby="resident-health-heading">
      <div className="flex items-center gap-2 text-brand-ink">
        <HeartPulse className="h-4 w-4" />
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em]">Estate health</p>
      </div>
      <h2 id="resident-health-heading" className="mt-2 text-lg font-semibold text-ink">How your estate is doing</h2>
      {loading ? <div className="mt-3"><LoadingState label="Loading published estate health" /></div> : error ? (
        <p className="mt-2 text-sm text-ink-muted">Estate health is temporarily unavailable.</p>
      ) : scoreAvailable ? (
        <div className="mt-3 flex items-end gap-3">
          <p className="num font-heading text-4xl font-semibold leading-none tracking-tight text-brand-ink">
            {score.toLocaleString('en-ZA', { maximumFractionDigits: 1 })}
            <span className="ml-1 text-sm font-medium text-ink-muted">/100</span>
          </p>
          <Chip tone={band?.tone === 'positive' ? 'good' : 'warn'}>{band?.label ?? 'Published score'}</Chip>
        </div>
      ) : (
        <p className="mt-2 max-w-md text-sm leading-relaxed text-ink-soft">
          Not enough data yet for a published Living Score. The score appears when there is sufficient measured operational information.
        </p>
      )}
      <Link to="/app/health" className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">
        Explore Estate Health <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </section>
  );
}

export function ResidentDashboard() {
  const { estateId, estate, loading: estateLoading } = useEstateScope();
  const { user } = useAuth();
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

  const firstName = user?.full_name?.trim().split(/\\s+/)[0] || 'there';
  const openRequests = (complaints.data?.items ?? []).filter((item) => !TERMINAL_STATUSES.has(item.status ?? ''));
  const notices = announcements.data?.items ?? [];

  return (
    <div className="space-y-9 pb-6">
      <header className="flex flex-col justify-between gap-4 border-b border-line pb-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.17em] text-brand-ink">Resident home</p>
          <h1 className="mt-2 font-heading text-3xl font-semibold tracking-[-0.035em] text-ink sm:text-4xl">
            Your estate, in view.
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
            Your requests, important updates, and the next thing you need to know.
          </p>
        </div>
        <Link to="/app/complaints" className="inline-flex min-h-11 items-center justify-center gap-2 self-start bg-brand px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand sm:self-auto">
          <Plus className="h-4 w-4" /> Report an issue
        </Link>
      </header>

      {estateLoading ? <LoadingState label="Loading your estate" /> : null}
      <EstateHero estate={estate} firstName={firstName} />

      <section aria-labelledby="requests-heading">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-ink">Your home</p>
            <h2 id="requests-heading" className="mt-1 font-heading text-xl font-semibold tracking-tight text-ink sm:text-2xl">
              Your requests
              {openRequests.length > 0 ? <span className="ml-2 align-middle text-sm font-medium text-ink-muted">{openRequests.length} active</span> : null}
            </h2>
          </div>
          <Link to="/app/complaints" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-ink hover:underline">
            View all requests <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="mt-2">
          {complaints.loading ? <LoadingState label="Loading your requests" /> : complaints.error ? (
            <ErrorState title="Your requests could not be loaded" message={complaints.error.message} requestId={complaints.error.requestId} action={<button type="button" onClick={complaints.reload} className="text-sm font-semibold text-brand-ink underline">Try again</button>} />
          ) : openRequests.length === 0 ? (
            <div className="flex flex-col items-start gap-3 py-7 sm:flex-row sm:items-center">
              <span className="flex h-10 w-10 items-center justify-center bg-brand-wash text-brand-ink"><CheckCircle2 className="h-5 w-5" /></span>
              <div className="flex-1">
                <p className="font-semibold text-ink">Nothing needs your attention right now.</p>
                <p className="mt-1 text-sm text-ink-soft">When something needs fixing, report it here and follow its progress from this list.</p>
              </div>
              <Link to="/app/complaints" className="text-sm font-semibold text-brand-ink hover:underline">Report an issue <ArrowRight className="ml-1 inline h-3.5 w-3.5" /></Link>
            </div>
          ) : (
            <ul>{openRequests.slice(0, 5).map((item) => <RequestRow key={item.id} item={item} />)}</ul>
          )}
        </div>
      </section>

      <section className="grid gap-8 border-t border-line pt-7 lg:grid-cols-[1fr_0.72fr] lg:gap-12">
        <div>
          <div className="flex items-center justify-between gap-3 border-b border-line pb-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-brand-ink">From your estate</p>
              <h2 className="mt-1 font-heading text-xl font-semibold text-ink">Important notices</h2>
            </div>
            <Link to="/app/announcements" aria-label="View all estate notices" className="inline-flex h-9 w-9 items-center justify-center text-brand-ink hover:bg-brand-wash">
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          {announcements.loading ? <div className="mt-4"><LoadingState label="Loading estate notices" /></div> : announcements.error ? (
            <div className="mt-4"><ErrorState title="Notices unavailable" message={announcements.error.message} requestId={announcements.error.requestId} action={<button type="button" onClick={announcements.reload} className="text-sm font-semibold text-brand-ink underline">Try again</button>} /></div>
          ) : notices.length === 0 ? (
            <div className="flex gap-3 py-5">
              <Bell className="mt-0.5 h-4 w-4 shrink-0 text-brand-ink" />
              <div><p className="text-sm font-medium text-ink">No new notices</p><p className="mt-1 text-sm text-ink-muted">Official updates from your estate will appear here.</p></div>
            </div>
          ) : (
            <ul className="divide-y divide-line/80">
              {notices.slice(0, 3).map((notice) => (
                <li key={notice.id} className="py-4 first:pt-4">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center bg-brand-wash text-brand-ink"><CalendarDays className="h-4 w-4" /></span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                        <h3 className="text-sm font-semibold text-ink">{notice.title}</h3>
                        <time className="text-xs text-ink-muted">{shortDate(notice.created_at)}</time>
                      </div>
                      <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-ink-soft">{notice.message}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-7">
          <EstateHealthSummary snapshot={score.data} loading={score.loading} error={score.error} />
          <div className="border-l-2 border-brand-soft pl-4 sm:pl-5">
            <div className="flex items-center gap-2 text-brand-ink">
              <Clock3 className="h-4 w-4" /><p className="text-[11px] font-semibold uppercase tracking-[0.14em]">How it works</p>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">
              Every request has a recorded status. When the estate team acts, progress is visible here—so you can follow what happens next.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
