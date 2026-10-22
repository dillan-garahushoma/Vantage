import { Link } from 'react-router-dom';
import { IconAlert, IconArrowRight, IconMegaphone, IconReport } from '../components/Icons';
import { Chip, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui';
import { HealthPillars } from '../components/valora/HealthPillars';
import { ScoreCard } from '../components/valora/ScoreCard';
import { SectionHeading } from '../components/valora/SectionHeading';
import { Surface } from '../components/valora/Surface';
import { useEstateScope } from '../context/EstateContext';
import { getLivingScore } from '../lib/analytics';
import { api } from '../lib/api';
import { complaintStatus, pillarBand } from '../lib/display';
import { ratio, relativeDays, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';

export function ResidentDashboard() {
  const { estateId, estate } = useEstateScope();

  const complaints = useAsync(
    () => api.get('/api/v1/complaints', { estate_id: estateId, size: 5, sort: '-created_at' }),
    [estateId],
  );
  const announcements = useAsync(
    () => api.get('/api/v1/announcements', { estate_id: estateId, size: 3 }),
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

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------- heading */}
      <SectionHeading
        eyebrow="Your estate"
        title={estate ? estate.estate_name : 'Estate dashboard'}
        description={
          estate?.suburb
            ? `${estate.suburb} · ${estate?.property_ids?.length ?? 0} unit${(estate?.property_ids?.length ?? 0) !== 1 ? 's' : ''} linked to you`
            : undefined
        }
      />

      {/* ------------------------------------------- primary CTA */}
      <Surface className="border-l-2 border-l-accent bg-accent-wash/40">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] text-accent-ink uppercase">
              Maintenance
            </p>
            <h2 className="mt-1 text-[17px] font-semibold text-ink">
              Report a maintenance issue
            </h2>
            <p className="mt-1 text-[13px] text-ink-soft">
              Something broken or unsafe? Log it here — your estate office will assign a
              contractor and you'll be notified when it's resolved.
            </p>
          </div>
          <IconReport size={22} className="mt-1 shrink-0 text-accent-ink" />
        </div>
        <Link
          to="/app/complaints"
          className="mt-4 inline-flex items-center gap-2 rounded-xs bg-accent px-4 py-2 text-[13.5px] font-medium text-white transition-opacity hover:opacity-90"
        >
          Log an issue
          <IconArrowRight size={15} />
        </Link>
      </Surface>

      {/* ---------------------------------------- living score card */}
      <ScoreCard
        empty={!scored}
        value={scored ? ratio(snapshot?.overall_score) : undefined}
        status={statusLabel}
        label="Living Score"
        description={
          scored
            ? `Stored for a rolling 90-day window by engine ${snapshot?.engine_version}. The figure is read, never recalculated on this screen.`
            : 'This estate has no publishable score yet. Every operational action — a logged complaint, a completed work order, a resident rating — feeds the five weighted pillars below.'
        }
        action={
          <Link
            to="/app/health"
            className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium text-brand-ink hover:underline"
          >
            Full health breakdown
            <IconArrowRight size={15} />
          </Link>
        }
      />

      {/* -------------------------------------------- health pillars */}
      <Surface>
        <SectionTitle
          title="Health pillars"
          hint="The engine's five weighted components, exactly as stored"
        />
        {livingScoreSnapshot.loading ? (
          <LoadingState label="Loading the pillar breakdown" />
        ) : (
          <HealthPillars pillars={pillars} expandedDefault={false} showWeights />
        )}
      </Surface>

      {/* ----------------------------- engine-pending strip (404 state) */}
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

      {/* ----------------------------------------- open complaints */}
      <Surface>
        <SectionTitle
          title="Your open issues"
          hint="Only complaints you logged"
          action={
            <Link
              to="/app/complaints"
              className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium text-brand-ink hover:underline"
            >
              All complaints
              <IconArrowRight size={14} />
            </Link>
          }
        />
        {complaints.loading ? (
          <LoadingState label="Loading your complaints" />
        ) : complaints.error ? (
          <ErrorState message={complaints.error.message} requestId={complaints.error.requestId} />
        ) : (complaints.data?.items?.length ?? 0) === 0 ? (
          <EmptyState
            title="No open issues"
            body="When you log a complaint it will appear here with its current status."
          />
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

      {/* ------------------------------------------ announcements */}
      <Surface>
        <SectionTitle
          title="Estate announcements"
          hint="Notices published by your HOA"
          action={
            <Link
              to="/app/announcements"
              className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium text-brand-ink hover:underline"
            >
              All
              <IconArrowRight size={14} />
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
        ) : (announcements.data?.items?.length ?? 0) === 0 ? (
          <p className="py-4 text-[0.83rem] text-ink-muted">No announcements yet.</p>
        ) : (
          <ul className="divide-y divide-line">
            {(announcements.data?.items ?? []).slice(0, 3).map((item) => (
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
        )}
      </Surface>
    </div>
  );
}
