import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Clock, Megaphone, Plus, Wrench } from 'lucide-react';
import { IconArrowRight, IconMegaphone, IconReport } from '../components/Icons';
import { Chip, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui';
import { SectionHeading } from '../components/valora/SectionHeading';
import { Surface } from '../components/valora/Surface';
import { useEstateScope } from '../context/EstateContext';
import { getLivingScore } from '../lib/analytics';
import { api } from '../lib/api';
import { complaintStatus, pillarBand } from '../lib/display';
import { relativeDays, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';

export function ResidentDashboard() {
  const { estateId, estate } = useEstateScope();

  const complaints = useAsync(
    () => api.get('/api/v1/complaints', { estate_id: estateId, size: 6, sort: '-created_at' }),
    [estateId],
  );
  const announcements = useAsync(
    () => api.get('/api/v1/announcements', { estate_id: estateId, size: 4 }),
    [estateId],
  );

  // The stored snapshot — exactly as the engine wrote it. A 404 (never scored)
  // and an `insufficient_data` snapshot are both "not enough data yet", never zero.
  const livingScoreSnapshot = useAsync(
    () => (estateId === null ? Promise.resolve(null) : getLivingScore(estateId)),
    [estateId],
  );

  const snapshot = livingScoreSnapshot.data;
  const scored =
    snapshot !== null &&
    snapshot?.status === 'scored' &&
    snapshot?.overall_score !== null &&
    snapshot?.overall_score !== undefined;

  // Pillars — engine's own components, never re-derived
  const pillars = (snapshot?.components ?? []).map((component) => ({
    key: component.key,
    name: component.label,
    score:
      component.score === null || component.score === undefined ? 0 : Number(component.score),
    weight: Number(component.weight) * 100,
    summary: component.explanation || undefined,
    measured: component.status === 'measured' && component.score !== null,
  }));

  const band = scored ? pillarBand(Number(snapshot?.overall_score)) : null;
  const flagged = pillars.filter(
    (pillar) => pillar.measured && pillarBand(pillar.score).tone !== 'positive',
  );
  const statusLabel = !scored
    ? 'Not enough data yet'
    : `${band?.label ?? 'Healthy'}${flagged.length === 0 ? '' : ', with watch areas'}`;

  const openComplaints = (complaints.data?.items ?? []).filter(
    (item) => !['resolved', 'closed', 'rated'].includes(item.status ?? '')
  );

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------- Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <SectionHeading
          eyebrow="Resident portal"
          title={estate ? estate.estate_name : 'Estate dashboard'}
          description={
            estate?.suburb
              ? `${estate.suburb}, ${estate.city ?? ''} · ${estate?.property_ids?.length ?? 0} unit${(estate?.property_ids?.length ?? 0) !== 1 ? 's' : ''} linked to your profile`
              : 'Authorized resident overview and maintenance requests.'
          }
        />
        <div className="flex items-center gap-2">
          <Link
            to="/app/complaints"
            className="inline-flex items-center gap-1.5 rounded-sm bg-brand px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition-opacity hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" />
            Report issue
          </Link>
        </div>
      </div>

      {/* ------------------------------------------- Hero Maintenance CTA */}
      <div className="rounded-lg border border-brand/20 bg-gradient-to-r from-brand-wash/50 via-surface to-surface p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-1.5 text-[0.68rem] font-semibold tracking-wider text-brand-ink uppercase">
              <Wrench className="h-3.5 w-3.5" />
              Maintenance & Repairs
            </span>
            <h2 className="mt-1 font-heading text-lg font-bold text-ink sm:text-xl">
              Report a maintenance issue
            </h2>
            <p className="mt-1 text-[0.85rem] leading-relaxed text-ink-soft">
              Notice a leak, electrical fault, or access gate issue? Log it here — your estate office will
              dispatch an approved contractor and keep you updated at every step.
            </p>
          </div>
          <Link
            to="/app/complaints"
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-sm bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-xs transition-all hover:bg-brand/90 hover:shadow-soft"
          >
            <IconReport size={16} />
            <span>Log an issue</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* ----------------------------------------- Two-column Resident Grid */}
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* Left Column: Active Requests */}
        <Surface>
          <SectionTitle
            title="Your active requests"
            hint="Real-time progress on maintenance logged for your property"
            action={
              <Link
                to="/app/complaints"
                className="inline-flex items-center gap-1 text-[0.8rem] font-medium text-brand-ink hover:underline"
              >
                All complaints
                <IconArrowRight size={14} />
              </Link>
            }
          />

          <div className="mt-4">
            {complaints.loading ? (
              <LoadingState label="Loading your maintenance requests" />
            ) : complaints.error ? (
              <ErrorState message={complaints.error.message} requestId={complaints.error.requestId} />
            ) : (complaints.data?.items?.length ?? 0) === 0 ? (
              <EmptyState
                title="No active requests"
                body="You don't have any open maintenance issues. Use the report button above whenever something in your unit or common property requires repair."
              />
            ) : (
              <ul className="divide-y divide-line">
                {(complaints.data?.items ?? []).map((item) => {
                  const status = complaintStatus[item.status ?? 'submitted'];
                  return (
                    <li key={item.id} className="py-3.5 first:pt-0 last:pb-0">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-[0.88rem] text-ink truncate">
                            {item.description}
                          </p>
                          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.74rem] text-ink-muted">
                            <span className="font-mono">#{item.id}</span>
                            <span className="h-1 w-1 rounded-full bg-line" />
                            <span>Unit {item.unit_id}</span>
                            <span className="h-1 w-1 rounded-full bg-line" />
                            <span>{item.category}</span>
                            <span className="h-1 w-1 rounded-full bg-line" />
                            <span className="inline-flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {relativeDays(item.created_at)}
                            </span>
                          </div>
                        </div>
                        <Chip tone={status?.tone ?? 'neutral'} glyph={status?.glyph}>
                          {status?.label ?? item.status}
                        </Chip>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Surface>

        {/* Right Column: Estate Health Teaser + Announcements */}
        <div className="space-y-6">
          {/* Compact Living Score Teaser */}
          <Surface>
            <SectionTitle
              title="Estate health"
              hint="Operational health calculated from estate records"
              action={
                <Link
                  to="/app/health"
                  className="inline-flex items-center gap-1 text-[0.8rem] font-medium text-brand-ink hover:underline"
                >
                  Full health breakdown
                  <IconArrowRight size={14} />
                </Link>
              }
            />

            <div className="mt-3">
              {livingScoreSnapshot.loading ? (
                <LoadingState label="Loading estate health" />
              ) : scored ? (
                <div className="space-y-3">
                  <div className="flex items-baseline gap-3">
                    <p className="num font-heading text-[2.2rem] leading-none font-bold text-ink">
                      {Number(snapshot.overall_score).toLocaleString('en-ZA', {
                        minimumFractionDigits: 1,
                        maximumFractionDigits: 1,
                      })}
                      <span className="ml-1 text-[1rem] font-normal text-ink-muted">/ 100</span>
                    </p>
                    <Chip tone={band?.tone === 'positive' ? 'good' : 'warn'}>{statusLabel}</Chip>
                  </div>
                  <p className="text-[0.78rem] leading-relaxed text-ink-muted">
                    Stored for a rolling 90-day window by engine {snapshot.engine_version}; this dashboard does not recalculate it.
                  </p>
                </div>
              ) : (
                <p className="text-[0.82rem] leading-relaxed text-ink-muted">
                  Not enough data yet. VALORA will show a score only once the estate has a stored, publishable calculation.
                </p>
              )}
            </div>
          </Surface>

          {/* Estate Announcements */}
          <Surface>
            <SectionTitle
              title="Estate announcements"
              hint="Official notices from your HOA management"
              action={
                <Link
                  to="/app/announcements"
                  className="inline-flex items-center gap-1 text-[0.8rem] font-medium text-brand-ink hover:underline"
                >
                  All
                  <IconArrowRight size={14} />
                </Link>
              }
            />

            <div className="mt-3">
              {announcements.loading ? (
                <LoadingState label="Loading announcements" />
              ) : announcements.error ? (
                <ErrorState
                  message={announcements.error.message}
                  requestId={announcements.error.requestId}
                />
              ) : (announcements.data?.items?.length ?? 0) === 0 ? (
                <p className="py-2 text-[0.82rem] text-ink-muted">No announcements yet.</p>
              ) : (
                <ul className="divide-y divide-line">
                  {(announcements.data?.items ?? []).slice(0, 3).map((item) => (
                    <li key={item.id} className="py-3 first:pt-0 last:pb-0">
                      <div className="flex items-baseline justify-between gap-3">
                        <h4 className="text-[0.85rem] font-medium text-ink">{item.title}</h4>
                        <span className="num shrink-0 text-[0.72rem] text-ink-muted">
                          {shortDate(item.created_at)}
                        </span>
                      </div>
                      <p className="mt-1 line-clamp-2 text-[0.8rem] leading-relaxed text-ink-soft">
                        {item.message}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Surface>
        </div>
      </div>
    </div>
  );
}
