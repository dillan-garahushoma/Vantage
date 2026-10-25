import {
  ArrowRight,
  CheckCircle2,
  ShieldCheck,
} from 'lucide-react';
import { useState } from 'react';
import { RequireEstate } from '../components/RequireEstate';
import { Button } from '../components/ui/button';
import { ErrorState } from '../components/ui';
import { AskValora } from '../components/valora/AskValora';
import { CreateWorkOrderDialog } from '../components/valora/CreateWorkOrderDialog';
import { DetailDrawer } from '../components/valora/DetailDrawer';
import { RecommendationCard } from '../components/valora/RecommendationCard';
import { SignalField } from '../components/valora/SignalField';
import { StatusChip } from '../components/valora/StatusChip';
import { Surface } from '../components/valora/Surface';
import { useEstateScope } from '../context/EstateContext';
import { api } from '../lib/api';
import { zar } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { cn } from '../lib/utils';

/**
 * The signal tiles are the estate's *measured* counts, fetched for this screen —
 * nothing on them is invented. When a read fails the tile is simply absent rather
 * than showing a stand-in number.
 */
function signalNodes(counts) {
  const nodes = [];
  if (counts) {
    const open = counts.open_complaints;
    nodes.push({
      id: 'complaints',
      label: 'Complaints awaiting resolution',
      value: String(open),
      tone: open === 0 ? 'positive' : open > 5 ? 'critical' : 'attention',
      source: 'Complaint records',
    });
  }
  if (counts) {
    const inFlight = counts.work_orders_in_flight;
    nodes.push({
      id: 'work-orders',
      label: 'Work orders in flight',
      value: String(inFlight),
      tone: inFlight === 0 ? 'positive' : 'brand',
      source: 'Work order records',
    });
  }
  if (counts) {
    const open = counts.unresolved_incidents;
    nodes.push({
      id: 'incidents',
      label: 'Incidents not yet resolved',
      value: String(open),
      tone: open === 0 ? 'positive' : 'attention',
      source: 'Incident records',
    });
  }
  return nodes;
}

function sourceActionFor(recommendation) {
  const overdue = /^overdue_work_order-(\d+)$/.exec(recommendation?.id ?? '');
  if (overdue) {
    return {
      type: 'work_order',
      recordId: Number(overdue[1]),
      label: 'Open work order',
      to: '/app/work-orders',
      state: { focusWorkOrderId: Number(overdue[1]) },
    };
  }

  const complaint = /^unassigned_complaint-(\d+)$/.exec(recommendation?.id ?? '');
  if (complaint) {
    return {
      type: 'complaint',
      recordId: Number(complaint[1]),
      label: 'Open complaint',
      to: '/app/complaints',
      state: { focusComplaintId: Number(complaint[1]) },
    };
  }

  return null;
}

function IntelligenceBody() {
  const { estateId, estate } = useEstateScope();

  const [reviewing, setReviewing] = useState(null);
  const [workOrderDraft, setWorkOrderDraft] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);
  const [historyBriefingId, setHistoryBriefingId] = useState(null);

  const intelligenceQuery = useAsync(
    () => (estateId === null ? Promise.resolve(null) : api.get('/api/v1/analytics/intelligence', { estate_id: estateId })),
    [estateId]
  );

  const history = useAsync(
    () =>
      estateId === null || intelligenceQuery.data?.role !== 'hoa_admin'
        ? Promise.resolve(null)
        : api.get('/api/v1/analytics/intelligence/history', { estate_id: estateId, size: 10 }),
    [estateId, intelligenceQuery.data?.role]
  );

  const historicalBriefing = useAsync(
    () =>
      historyBriefingId === null || estateId === null
        ? Promise.resolve(null)
        : api.get(`/api/v1/analytics/intelligence/history/${historyBriefingId}`, { estate_id: estateId }),
    [estateId, historyBriefingId]
  );

  const intelligence = historicalBriefing.data ?? intelligenceQuery.data;
  const activeBriefing = intelligence?.briefing;
  const activeRecommendations = intelligence?.recommendations ?? [];
  const signals = signalNodes(intelligence?.operational_signals);

  // Role resolution
  const resolvedRole = intelligence?.role ?? (
    estate?.is_estate_admin ? 'hoa_admin' : estate?.is_estate_provider ? 'service_provider' : 'resident'
  );
  const isHoaAdmin = resolvedRole === 'hoa_admin';
  const isProvider = resolvedRole === 'service_provider';
  const isResident = resolvedRole === 'resident';

  function openWorkOrder(recommendation) {
    setReviewing(null);
    const sourceAction = sourceActionFor(recommendation);
    setWorkOrderDraft({
      title: recommendation.title,
      complaintId: sourceAction?.type === 'complaint' ? sourceAction.recordId : undefined,
      asset: recommendation.workOrderDefaults.asset,
      location: recommendation.workOrderDefaults.location,
      priority: recommendation.workOrderDefaults.priority,
      costZar: recommendation.workOrderDefaults.costZar,
      description: recommendation.workOrderDefaults.description,
    });
  }

  return (
    <div className="space-y-7">
      {intelligenceQuery.loading ? (
        <p role="status" className="text-sm text-ink-muted">
          Loading your authorized intelligence…
        </p>
      ) : null}
      {intelligenceQuery.error ? (
        <ErrorState
          title="Briefing unavailable"
          message={intelligenceQuery.error.message}
          requestId={intelligenceQuery.error.requestId}
          action={<Button onClick={intelligenceQuery.reload}>Try again</Button>}
        />
      ) : null}
      {activeBriefing ? (
        <section className="border-b border-line pb-6" aria-labelledby="briefing-title">
          <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-3">
            <p className="text-sm font-semibold text-brand-ink">
              {isResident ? 'Personal estate assistant' : isProvider ? 'Assigned work intelligence' : 'Estate operations'}
              <span className="mx-2 text-ink-muted" aria-hidden="true">/</span>
              {estate?.estate_name ?? intelligence?.estate_name}
            </p>
            <p className="text-xs text-ink-muted">
              {intelligence?.briefing_id ? 'Saved briefing' : activeBriefing.windowLabel}
              {' · '}
              {intelligence?.as_of ? new Date(intelligence.as_of).toLocaleString('en-ZA') : 'Date unavailable'}
            </p>
          </div>
          <div className="mt-4 flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-4xl">
              <h1 id="briefing-title" className="font-heading text-2xl font-semibold leading-tight tracking-[-0.025em] text-ink sm:text-[2rem]">
                {activeBriefing.headline}
              </h1>
              <p className="mt-3 max-w-3xl text-[0.95rem] leading-relaxed text-ink/75">
                {activeBriefing.body}
              </p>
              {intelligence?.limitations?.length ? (
                <p className="mt-2 max-w-3xl text-xs leading-relaxed text-ink-muted">
                  {intelligence.limitations[0]}
                  {intelligence?.briefing_id ? ' Counts are frozen at the briefing date.' : ''}
                </p>
              ) : null}
            </div>
            {isHoaAdmin ? (
              <Button
                variant="outline"
                className="shrink-0"
                disabled={generating}
                onClick={async () => {
                  setGenerating(true);
                  setGenerationError(null);
                  try {
                    await api.post('/api/v1/analytics/intelligence/briefing/generate', {}, { estate_id: estateId });
                    intelligenceQuery.reload();
                  } catch (cause) {
                    setGenerationError(cause instanceof Error ? cause.message : 'Could not save the briefing.');
                  } finally {
                    setGenerating(false);
                  }
                }}
              >
                {generating ? 'Saving briefing…' : 'Save current briefing'}
              </Button>
            ) : null}
          </div>
          {generationError ? <p role="alert" className="mt-3 text-sm text-rose-700">{generationError}</p> : null}
        </section>
      ) : null}

      {/* -------------------- Resident View -------------------- */}
      {isResident ? (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.8fr)]">
          <Surface className="order-1 h-[min(560px,70vh)] min-h-[420px] overflow-hidden xl:sticky xl:top-24" padded={false}>
            <AskValora key={estateId} estateId={estateId} role={resolvedRole} />
          </Surface>

          <div className="order-2 space-y-5">
            <Surface>
              <div className="flex items-center justify-between border-b border-line pb-3">
                <h2 className="font-heading text-[1.05rem] font-bold text-ink">
                  Your Logged Requests & Unit Health
                </h2>
                <span className="rounded-full bg-brand-wash px-2.5 py-1 text-xs font-semibold text-brand-ink">
                  {intelligence?.resident_view?.unit_issues?.length ?? 0} tracked
                </span>
              </div>
              {(intelligence?.resident_view?.unit_issues ?? []).length === 0 ? (
                <div className="py-8 text-center text-ink/60">
                  <CheckCircle2 className="mx-auto h-8 w-8 text-mint-ink" />
                  <p className="mt-2 text-sm font-medium">No open maintenance issues logged for your unit.</p>
                  <p className="mt-1 text-xs text-ink/55">Your requests will appear here when submitted.</p>
                </div>
              ) : (
                <div className="mt-3 divide-y divide-line-soft">
                  {intelligence.resident_view.unit_issues.map((issue) => (
                    <div key={issue.id} className="flex items-center justify-between py-3">
                      <div>
                        <p className="text-sm font-semibold text-ink">{issue.title}</p>
                        <p className="text-xs text-ink/40">
                          {issue.category} · Logged {issue.logged_date ? new Date(issue.logged_date).toLocaleDateString('en-ZA') : 'Recently'}
                        </p>
                      </div>
                      <StatusChip status={issue.status} size="sm" />
                    </div>
                  ))}
                </div>
              )}
            </Surface>

            {(intelligence?.resident_view?.community_notices ?? []).length > 0 ? (
              <Surface>
                <div className="border-b border-line pb-3">
                  <h2 className="font-heading text-[1.05rem] font-bold text-ink">
                    Community living notices
                  </h2>
                </div>
                <ul className="mt-3 space-y-2 text-sm text-ink/75">
                  {intelligence.resident_view.community_notices.map((notice, idx) => (
                    <li key={idx} className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-brand-soft" />
                      {notice}
                    </li>
                  ))}
                </ul>
              </Surface>
            ) : null}

            <Surface>
              <div className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-canvas text-brand">
                  <ShieldCheck className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-[0.88rem] font-semibold text-ink">
                    How Living Score Protects Property Values
                  </p>
                  <p className="mt-1 text-[0.82rem] leading-relaxed text-ink/55">
                    {intelligence?.resident_view?.living_score_summary || 'A Living Score has not been published for this estate.'}
                  </p>
                </div>
              </div>
            </Surface>
          </div>
        </div>
      ) : null}

      {/* -------------------- Provider View -------------------- */}
      {isProvider ? (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.8fr)]">
          <Surface className="order-1 h-[min(560px,70vh)] min-h-[420px] overflow-hidden xl:sticky xl:top-24" padded={false}>
            <AskValora key={estateId} estateId={estateId} role={resolvedRole} />
          </Surface>

          <div className="order-2 space-y-5">
            <Surface>
              <div className="flex items-center justify-between border-b border-line pb-3">
                <h2 className="font-heading text-[1.05rem] font-bold text-ink">
                  Assigned Work Orders Queue
                </h2>
                <div className="flex gap-2">
                  <span className="rounded-full bg-brand-wash px-2.5 py-1 text-xs font-semibold text-brand-ink">
                    {intelligence?.provider_view?.assigned_work_orders?.length ?? 0} total
                  </span>
                  {(intelligence?.provider_view?.urgent_count ?? 0) > 0 && (
                    <span className="rounded-full bg-rose-100 text-rose-700 px-2.5 py-1 text-xs font-bold">
                      {intelligence.provider_view.urgent_count} high priority
                    </span>
                  )}
                </div>
              </div>
              {(intelligence?.provider_view?.assigned_work_orders ?? []).length === 0 ? (
                <div className="py-8 text-center text-ink/60">
                  <CheckCircle2 className="mx-auto h-8 w-8 text-mint-ink" />
                  <p className="mt-2 text-sm font-medium">No work orders are currently assigned to your provider account.</p>
                  <p className="mt-1 text-xs text-ink/40">New assignments appear here when recorded.</p>
                </div>
              ) : (
                <div className="mt-3 divide-y divide-line-soft">
                  {intelligence.provider_view.assigned_work_orders.map((wo) => (
                    <div key={wo.id} className="flex items-center justify-between py-3">
                      <div>
                        <p className="text-sm font-semibold text-ink">{wo.title}</p>
                        <p className="text-xs text-ink/40">
                          {wo.location} · Due: {wo.due_date ? new Date(wo.due_date).toLocaleDateString('en-ZA') : 'Due date not recorded'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'text-[11px] font-bold uppercase px-2 py-0.5 rounded',
                            wo.priority === 'urgent' || wo.priority === 'high'
                              ? 'bg-rose-100 text-rose-700'
                              : 'bg-slate-100 text-slate-700'
                          )}
                        >
                          {wo.priority}
                        </span>
                        <StatusChip status={wo.status} size="sm" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Surface>

            <Surface>
              <div className="border-b border-line pb-3">
                <h2 className="font-heading text-[1.05rem] font-bold text-ink">
                  Contractor Site Access Guidelines
                </h2>
              </div>
              {intelligence?.provider_view?.instructions ? (
                <p className="mt-3 text-sm text-ink/75 leading-relaxed">
              {intelligence.provider_view.instructions}
                </p>
              ) : (
                <p className="mt-3 text-sm text-ink/60 leading-relaxed">
              No access procedures are recorded for your assigned work.
                </p>
              )}
            </Surface>
          </div>
        </div>
      ) : null}

      {/* -------------------- HOA Admin View -------------------- */}
      {isHoaAdmin ? (
        <>
          <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.8fr)]">
            <Surface className="h-[min(560px,70vh)] min-h-[420px] overflow-hidden xl:sticky xl:top-24" padded={false}>
              <AskValora key={estateId} estateId={estateId} role={resolvedRole} />
            </Surface>
            <div className="space-y-4">
          <Surface>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="font-heading text-[1rem] font-bold text-ink">Briefing history</h2>
                <p className="mt-1 text-[0.82rem] text-ink-muted">
                  Previous saved estate analyses
                </p>
              </div>
              {historyBriefingId !== null ? (
                <Button variant="outline" onClick={() => setHistoryBriefingId(null)}>
                  View current briefing
                </Button>
              ) : null}
            </div>
            {history.loading ? (
              <p className="mt-4 text-[13px] text-ink-muted">Loading saved briefings…</p>
            ) : history.error ? (
              <div className="mt-4">
                <ErrorState
                  title="Briefing history unavailable"
                  message={history.error.message}
                  requestId={history.error.requestId}
                  action={<Button onClick={history.reload}>Try again</Button>}
                />
              </div>
            ) : (history.data?.items ?? []).length === 0 ? (
              <p className="mt-4 text-[13px] text-ink-muted">
                No saved briefings yet.
              </p>
            ) : (
              <ul className="mt-4 divide-y divide-line-soft">
                {history.data.items.map((entry) => (
                  <li key={entry.briefing_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <span className="text-[13px] text-ink-soft">
                      Briefing #{entry.briefing_id} · {new Date(entry.as_of).toLocaleString('en-ZA')}
                    </span>
                    <Button
                      variant="secondary"
                      disabled={historicalBriefing.loading && historyBriefingId === entry.briefing_id}
                      onClick={() => setHistoryBriefingId(entry.briefing_id)}
                      aria-label={`View saved briefing ${entry.briefing_id}`}
                    >
                      {historicalBriefing.loading && historyBriefingId === entry.briefing_id
                        ? 'Loading…'
                        : `View saved briefing ${entry.briefing_id}`}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {historicalBriefing.error ? (
              <div className="mt-3">
                <ErrorState
                  title="Saved briefing unavailable"
                  message={historicalBriefing.error.message}
                  requestId={historicalBriefing.error.requestId}
                />
              </div>
            ) : null}
          </Surface>

          {signals.length > 0 ? <SignalField signals={signals} label="Measured operational signals" /> : null}
            </div>
          </div>

          <div className="space-y-5">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="font-heading text-[1.1rem] font-bold tracking-[-0.01em] text-ink">Management recommendations</h2>
                  <p className="mt-1 text-[0.85rem] text-ink/65">Review each source record before deciding on action.</p>
                </div>
                <span className="text-sm text-ink-muted">{activeRecommendations.length} findings</span>
              </div>
              <p className="mt-2 text-[0.72rem] font-semibold tracking-[0.12em] text-brand-ink uppercase">
                Every finding traceable to source
              </p>

              <div className="space-y-3">
                {activeRecommendations.length === 0 ? (
                  <div className="rounded-xl bg-surface px-4 py-5">
                    <h3 className="font-heading text-sm font-semibold text-ink">No findings require action</h3>
                    <p className="mt-1 text-sm text-ink-muted">
                      No overdue work orders or unassigned high-priority complaints were returned for this estate.
                    </p>
                  </div>
                ) : (
                  activeRecommendations.map((recommendation) => {
                    const sourceAction = sourceActionFor(recommendation);
                    return (
                      <RecommendationCard
                        key={recommendation.id}
                        recommendation={recommendation}
                        onReview={setReviewing}
                        onAction={openWorkOrder}
                        sourceAction={sourceAction}
                        canAction={isHoaAdmin && sourceAction?.type !== 'work_order'}
                      />
                    );
                  })
                )}
              </div>

          </div>
        </>
      ) : null}

      {/* ------------------------------------------------------- review drawer */}
      <DetailDrawer
        open={reviewing !== null}
        onOpenChange={(open) => {
          if (!open) setReviewing(null);
        }}
        title={reviewing?.title}
        subtitle={reviewing ? `${reviewing.id} · ${reviewing.kind}` : ''}
        badge={reviewing ? <StatusChip status={reviewing.confidence} size="sm" /> : null}
        width="sm:max-w-[600px]"
        footer={
          reviewing ? (
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="outline" onClick={() => setReviewing(null)} className="h-10 rounded-full px-5">
                Close
              </Button>
              {isHoaAdmin ? (
                <Button variant="ink" onClick={() => openWorkOrder(reviewing)} className="h-10 rounded-full px-5">
                  Create work order
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              ) : null}
            </div>
          ) : null
        }
      >
        {reviewing ? (
          <div className="space-y-6">
            <p className="text-[0.9rem] leading-relaxed text-ink/70">{reviewing.summary}</p>

            <div className="grid gap-4 sm:grid-cols-3">
              {[
                ...(reviewing.confidenceValue != null ? [{ label: 'Confidence', value: `${reviewing.confidence} · ${reviewing.confidenceValue}%` }] : []),
                ...(reviewing.savingsZar != null ? [{ label: 'Expected saving', value: zar(reviewing.savingsZar) }] : []),
                { label: 'Category', value: reviewing.kind },
              ].map((row) => (
                <div key={row.label} className="rounded-xl border border-line p-3.5">
                  <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink/40 uppercase">
                    {row.label}
                  </p>
                  <p className="mt-1.5 text-[0.85rem] font-bold text-ink">{row.value}</p>
                </div>
              ))}
            </div>

            <div>
              <p className="text-[0.68rem] font-semibold tracking-[0.14em] text-ink/40 uppercase">
                Source signals
              </p>
              <ul className="mt-3 divide-y divide-line-soft rounded-2xl border border-line">
                {reviewing.evidence.map((item) => (
                  <li key={item.label} className="px-4 py-3.5">
                    <p className="text-[0.85rem] font-semibold text-ink">{item.label}</p>
                    {item.detail ? <p className="mt-0.5 text-[0.78rem] text-ink/50">{item.detail}</p> : null}
                    {item.source ? (
                      <p className="mt-1.5 inline-flex rounded-full bg-canvas px-2.5 py-1 text-[0.68rem] font-medium text-ink/45">
                        {item.source}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl bg-canvas p-4">
              <p className="text-[0.68rem] font-semibold tracking-[0.14em] text-brand-ink uppercase">
                Suggested action
              </p>
              <p className="mt-2 text-[0.86rem] leading-relaxed text-ink/75">
                {reviewing.suggestedAction}
              </p>
            </div>

            <p className="text-[0.75rem] leading-relaxed text-ink/45">
              This is a recommendation, not a recorded outcome. Once you create the work order, VALORA
              tracks whether the underlying signal clears.
            </p>
          </div>
        ) : null}
      </DetailDrawer>

      {/* --------------------------------------------- work order from finding */}
      <CreateWorkOrderDialog
        open={workOrderDraft !== null}
        onOpenChange={(open) => {
          if (!open) setWorkOrderDraft(null);
        }}
        defaults={workOrderDraft ?? undefined}
        onCreated={() => {
          intelligenceQuery.reload();
        }}
      />

      {estateId === null ? (
        <ErrorState
          title="No estate selected"
          message="Intelligence reads one estate at a time. Choose an estate from the switcher to scope the signals."
        />
      ) : null}

      <p className="text-[0.72rem] text-ink/35">
        Scope: {estate?.estate_name ?? 'no estate selected'} · recommendations are advisory and never
        written back to the estate’s records without a work order.
      </p>
    </div>
  );
}

export function Intelligence() {
  const { estateId } = useEstateScope();
  return (
    <RequireEstate>
      <IntelligenceBody key={estateId} />
    </RequireEstate>
  );
}
