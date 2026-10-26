import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck2,
  FileText,
  HelpCircle,
  Layers,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
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
  const { estateId, estate, livingScore } = useEstateScope();

  const [reviewing, setReviewing] = useState(null);
  const [workOrderDraft, setWorkOrderDraft] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);
  const [generationStatus, setGenerationStatus] = useState(null);
  const [historyBriefingId, setHistoryBriefingId] = useState(null);
  const [activeTab, setActiveTab] = useState('evidence'); // 'context' | 'evidence' | 'related'
  const [chatKey, setChatKey] = useState(0);

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
    <div className="space-y-6">
      {/* -------------------- Top Hero Banner -------------------- */}
      <section className="relative overflow-hidden rounded-2xl border border-line bg-surface p-5 sm:p-6 shadow-soft">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3.5">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-brand text-white shadow-sm">
              <Sparkles className="h-5 w-5" />
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="font-heading text-xl font-bold tracking-tight text-ink sm:text-2xl">
                  VALORA Intelligence
                </h1>
                <span className="inline-flex items-center gap-1 rounded-full border border-brand/25 bg-brand-wash px-2.5 py-0.5 text-[10px] font-bold text-brand-ink uppercase">
                  <Sparkles className="h-2.5 w-2.5" />
                  Powered by AI
                </span>
              </div>
              <p className="mt-1 text-xs text-ink/70 sm:text-sm">
                Ask questions. Get clear, actionable insights about your estate.
              </p>
            </div>
          </div>

          {/* Right side: Estate dossier preview */}
          <div className="flex items-center gap-3 rounded-xl border border-line/80 bg-canvas/60 p-2 sm:max-w-xs">
            <div className="h-10 w-14 shrink-0 overflow-hidden rounded-lg bg-line">
              <img
                src="/estates/willowbrook-mews-01-hero.jpg"
                alt={estate?.estate_name ?? 'Estate view'}
                className="h-full w-full object-cover"
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            </div>
            <div className="min-w-0 pr-1">
              <p className="truncate text-xs font-semibold text-ink">
                {estate?.estate_name ?? intelligence?.estate_name ?? 'Active estate'}
              </p>
              <div className="flex items-center gap-1.5 text-[11px] text-ink-muted">
                <span className="h-1.5 w-1.5 rounded-full bg-mint" />
                <span>Live estate record</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Loading & Error States */}
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

      {/* -------------------- Main 3-Column Grid -------------------- */}
      <div className={cn("grid gap-6 items-start", isResident ? "grid-cols-1" : isHoaAdmin ? "xl:grid-cols-[240px_minmax(0,1fr)_320px]" : "grid-cols-1")}>
        {/* ==================== LEFT COLUMN (Recent & History) ==================== */}
        {isHoaAdmin ? {isHoaAdmin ? <aside className="space-y-4 xl:sticky xl:top-24">
          <Surface className="space-y-4" padded={true}>
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-brand" />
                <h2 className="font-heading text-xs font-bold tracking-wider text-ink uppercase">
                  Saved briefings
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setChatKey((k) => k + 1)}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-brand-ink hover:underline"
              >
                <Plus className="h-3 w-3" />
                New chat
              </button>
            </div>


            {/* Saved Briefings for HOA Admin */}
            {isHoaAdmin ? (
              <div className="pt-2 border-t border-line">
                <div className="flex items-center justify-between pb-2">
                  <h3 className="font-heading text-[11px] font-bold text-ink uppercase tracking-wider">
                    Briefing history
                  </h3>
                  {historyBriefingId !== null ? (
                    <button
                      type="button"
                      onClick={() => setHistoryBriefingId(null)}
                      className="text-[11px] text-brand-ink hover:underline"
                    >
                      Current
                    </button>
                  ) : null}
                </div>

                {history.loading ? (
                  <p className="text-xs text-ink-muted py-2">Loading saved briefings…</p>
                ) : history.error ? (
                  <p className="text-xs text-rose-700 py-2">History unavailable</p>
                ) : (history.data?.items ?? []).length === 0 ? (
                  <p className="text-xs text-ink-muted py-2">No saved briefings yet.</p>
                ) : (
                  <ul className="space-y-1.5 divide-y-0">
                    {history.data.items.map((entry) => (
                      <li key={entry.briefing_id} className="flex items-center justify-between gap-1 py-1">
                        <span className="text-[11px] text-ink-soft truncate">
                          #{entry.briefing_id} · {new Date(entry.as_of).toLocaleDateString('en-ZA')}
                        </span>
                        <Button
                          variant="secondary"
                          size="sm"
                          className="h-7 text-[11px] px-2"
                          disabled={historicalBriefing.loading && historyBriefingId === entry.briefing_id}
                          onClick={() => setHistoryBriefingId(entry.briefing_id)}
                          aria-label={`View saved briefing ${entry.briefing_id}`}
                          name={`View saved briefing ${entry.briefing_id}`}
                        >
                          {historicalBriefing.loading && historyBriefingId === entry.briefing_id
                            ? 'Loading…'
                            : `View saved briefing ${entry.briefing_id}`}
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}

          </Surface>
        </aside> : null}

        {/* ==================== CENTER COLUMN (AI Conversation Workbench) ==================== */}
        <main className="space-y-4">
          <Surface className={cn("overflow-hidden", isResident ? "min-h-[420px] md:min-h-[480px]" : "h-[min(680px,80vh)] min-h-[500px]")} padded={false}>
            <AskValora key={`${estateId}-${chatKey}`} estateId={estateId} role={resolvedRole} />
          </Surface>
        </main>

        {/* ==================== RIGHT COLUMN (Context, Evidence, Related) ==================== */}
        <aside className="space-y-4 xl:sticky xl:top-24">
          <Surface className="space-y-4" padded={true}>
            {/* 3 Tab Switcher */}
            <div className="flex rounded-xl border border-line bg-canvas p-1" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'evidence'}
                onClick={() => setActiveTab('evidence')}
                className={cn(
                  'flex-1 rounded-lg py-1.5 text-xs font-semibold transition-all',
                  activeTab === 'evidence'
                    ? 'bg-surface text-ink shadow-xs border border-line/60'
                    : 'text-ink-muted hover:text-ink'
                )}
              >
                Evidence
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'context'}
                onClick={() => setActiveTab('context')}
                className={cn(
                  'flex-1 rounded-lg py-1.5 text-xs font-semibold transition-all',
                  activeTab === 'context'
                    ? 'bg-surface text-ink shadow-xs border border-line/60'
                    : 'text-ink-muted hover:text-ink'
                )}
              >
                Context
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'related'}
                onClick={() => setActiveTab('related')}
                className={cn(
                  'flex-1 rounded-lg py-1.5 text-xs font-semibold transition-all',
                  activeTab === 'related'
                    ? 'bg-surface text-ink shadow-xs border border-line/60'
                    : 'text-ink-muted hover:text-ink'
                )}
              >
                Related
              </button>
            </div>

            {/* ---------- TAB 1: EVIDENCE (Default) ---------- */}
            {activeTab === 'evidence' && (
              <div className="space-y-4">
                {activeBriefing ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-brand-ink">
                        Weekly Briefing
                      </span>
                      {isHoaAdmin ? (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          disabled={generating}
                          onClick={async () => {
                            setGenerating(true);
                            setGenerationError(null);
                            setGenerationStatus(null);
                            try {
                              await api.post('/api/v1/analytics/intelligence/briefing/generate', {}, { estate_id: estateId });
                              intelligenceQuery.reload();
                              history.reload();
                              setGenerationStatus('Briefing saved.');
                            } catch (cause) {
                              setGenerationError(cause instanceof Error ? cause.message : 'Could not save the briefing.');
                            } finally {
                              setGenerating(false);
                            }
                          }}
                        >
                          {generating ? 'Saving…' : 'Save current briefing'}
                        </Button>
                      ) : null}
                    </div>

                    <h2 className="font-heading text-base font-semibold leading-snug text-ink">
                      {activeBriefing.headline}
                    </h2>
                    <p className="text-xs leading-relaxed text-ink/75">
                      {activeBriefing.body}
                    </p>

                    {generationError ? <p role="alert" className="text-xs text-rose-700">{generationError}</p> : null}
                    {generationStatus ? <p role="status" className="text-xs text-mint-ink font-medium">{generationStatus}</p> : null}
                  </div>
                ) : null}

                {/* Measured operational signals */}
                {signals.length > 0 ? (
                  <div className="pt-2 border-t border-line">
                    <SignalField signals={signals} label="Measured operational signals" />
                  </div>
                ) : null}

                {/* Management recommendations */}
                <div className="pt-2 border-t border-line space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-heading text-xs font-bold tracking-wider uppercase text-ink">
                      Findings & Actions
                    </h3>
                    <span className="text-[11px] text-ink-muted">
                      {activeRecommendations.length} findings
                    </span>
                  </div>
                  <p className="text-[10px] font-semibold tracking-wider text-brand-ink uppercase">
                    Every finding traceable to source
                  </p>

                  <div className="space-y-2.5">
                    {activeRecommendations.length === 0 ? (
                      <p className="text-xs text-ink-muted py-2">
                        No overdue work orders or high-priority complaints.
                      </p>
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
              </div>
            )}

            {/* ---------- TAB 2: CONTEXT ---------- */}
            {activeTab === 'context' && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-ink/40">Selected community</p>
                  <h3 className="font-heading text-sm font-bold text-ink">
                    {estate?.estate_name ?? intelligence?.estate_name ?? 'Selected estate'}
                  </h3>
                  <p className="text-xs text-ink-muted">Intelligence is scoped to the selected estate and your current role.</p>
                </div>
                {livingScore?.value != null ? (
                  <div className="border-t border-line pt-3">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-ink/40">Living Score</p>
                    <p className="mt-1 text-xl font-semibold tabular-nums text-ink">{livingScore.value}<span className="ml-1 text-xs font-normal text-ink-muted">/100</span></p>
                    {livingScore.label ? <p className="mt-1 text-xs text-ink-muted">{livingScore.label}</p> : null}
                  </div>
                ) : null}
                {signals.length ? (
                  <div className="border-t border-line pt-3">
                    <SignalField signals={signals} label="Measured operational signals" />
                  </div>
                ) : null}
                <div className="border-t border-line pt-3 space-y-2">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-ink/40">Explore records</p>
                  <Link to="/app/health" className="flex items-center justify-between rounded-lg border border-line p-2 text-xs text-ink/80 hover:border-brand-soft hover:text-brand-ink">
                    <span>Estate health</span><ArrowRight className="h-3 w-3" />
                  </Link>
                  {isHoaAdmin ? (
                    <>
                      <Link to="/app/complaints" className="flex items-center justify-between rounded-lg border border-line p-2 text-xs text-ink/80 hover:border-brand-soft hover:text-brand-ink">
                        <span>Complaints</span><ArrowRight className="h-3 w-3" />
                      </Link>
                      <Link to="/app/work-orders" className="flex items-center justify-between rounded-lg border border-line p-2 text-xs text-ink/80 hover:border-brand-soft hover:text-brand-ink">
                        <span>Work orders</span><ArrowRight className="h-3 w-3" />
                      </Link>
                    </>
                  ) : null}
                </div>
                <button type="button" onClick={() => setChatKey((k) => k + 1)} className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-line bg-canvas py-2 text-xs font-semibold text-ink hover:bg-surface">
                  <RefreshCw className="h-3.5 w-3.5 text-brand" /> Start a new chat
                </button>
              </div>
            )}

            {/* ---------- TAB 3: RELATED ---------- */}
            {activeTab === 'related' && (
              <div className="space-y-3">
                <p className="text-[11px] font-bold uppercase tracking-wider text-ink/40">Related to this briefing</p>
                {activeRecommendations.length ? (
                  <div className="divide-y divide-line">
                    {activeRecommendations.map((recommendation) => (
                      <div key={recommendation.id} className="py-3">
                        <p className="text-xs font-semibold text-ink">{recommendation.title}</p>
                        <p className="mt-1 text-xs leading-relaxed text-ink/65">{recommendation.summary}</p>
                        {recommendation.evidence?.length ? (
                          <p className="mt-1 text-[11px] text-ink-muted">{recommendation.evidence.length} supporting source{recommendation.evidence.length === 1 ? '' : 's'}</p>
                        ) : null}
                        <button type="button" onClick={() => { setReviewing(recommendation); setActiveTab('evidence'); }} className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-brand-ink hover:underline">
                          Review finding <ArrowRight className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs leading-relaxed text-ink-muted">No related findings were returned for this view. VALORA will not invent records to fill this panel.</p>
                )}
              </div>
            )}

          </Surface>
        </aside> : null}
      </div>

      {/* -------------------- Resident Scoped Extra Info -------------------- */}
      {isResident ? (
        <div className="grid gap-5 md:grid-cols-2 pt-4 border-t border-line">
          <Surface>
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h2 className="font-heading text-sm font-bold text-ink">
                Your maintenance requests
              </h2>
              <span className="rounded-full bg-brand-wash px-2.5 py-0.5 text-xs font-semibold text-brand-ink">
                {intelligence?.resident_view?.unit_issues?.length ?? 0} tracked
              </span>
            </div>
            {(intelligence?.resident_view?.unit_issues ?? []).length === 0 ? (
              <div className="py-6 text-center text-ink/60">
                <CheckCircle2 className="mx-auto h-6 w-6 text-mint-ink" />
                <p className="mt-2 text-xs font-medium">No maintenance requests are recorded for your account.</p>
                <Link to="/app/complaints" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-brand-ink hover:underline">
                  Report a maintenance issue <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            ) : (
              <div className="mt-2 divide-y divide-line-soft">
                {intelligence.resident_view.unit_issues.map((issue) => (
                  <div key={issue.id} className="flex items-center justify-between py-2 text-xs">
                    <div>
                      <p className="font-semibold text-ink">{issue.title}</p>
                      <p className="text-[11px] text-ink-muted">{issue.category}</p>
                    </div>
                    <StatusChip status={issue.status} size="sm" />
                  </div>
                ))}
              </div>
            )}
          </Surface>

          <Surface>
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-canvas text-brand">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <div>
                <p className="text-sm font-semibold text-ink">
                  Community health
                </p>
                <p className="mt-1 text-xs leading-relaxed text-ink/65">
                  {intelligence?.resident_view?.living_score_summary || 'A Living Score has not been published for this estate.'}
                </p>
              </div>
            </div>
          </Surface>
        </div>
      ) : null}

      {/* -------------------- Provider Scoped Extra Info -------------------- */}
      {isProvider ? (
        <div className="pt-4 border-t border-line">
          <Surface>
            <h2 className="font-heading text-sm font-bold text-ink border-b border-line pb-2">
              Contractor Site Access Guidelines
            </h2>
            <p className="mt-2 text-xs text-ink/75 leading-relaxed">
              {intelligence?.provider_view?.instructions ?? 'No special access procedures are recorded for your assigned work.'}
            </p>
          </Surface>
        </div>
      ) : null}

      {/* -------------------- Review Drawer -------------------- */}
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
              <Button variant="outline" onClick={() => setReviewing(null)} className="h-9 rounded-full px-4 text-xs">
                Close
              </Button>
              {isHoaAdmin ? (
                <Button variant="ink" onClick={() => openWorkOrder(reviewing)} className="h-9 rounded-full px-4 text-xs">
                  Create work order
                  <ArrowRight className="h-3 w-3" />
                </Button>
              ) : null}
            </div>
          ) : null
        }
      >
        {reviewing ? (
          <div className="space-y-5 text-sm">
            <p className="text-xs leading-relaxed text-ink/75">{reviewing.summary}</p>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ...(reviewing.confidenceValue != null ? [{ label: 'Confidence', value: `${reviewing.confidence} · ${reviewing.confidenceValue}%` }] : []),
                ...(reviewing.savingsZar != null ? [{ label: 'Expected saving', value: zar(reviewing.savingsZar) }] : []),
                { label: 'Category', value: reviewing.kind },
              ].map((row) => (
                <div key={row.label} className="rounded-xl border border-line p-3">
                  <p className="text-[10px] font-bold tracking-wider text-ink/40 uppercase">
                    {row.label}
                  </p>
                  <p className="mt-1 text-xs font-bold text-ink">{row.value}</p>
                </div>
              ))}
            </div>

            <div>
              <p className="text-[11px] font-bold tracking-wider text-ink/40 uppercase">
                Source signals
              </p>
              <ul className="mt-2 divide-y divide-line-soft rounded-xl border border-line">
                {reviewing.evidence.map((item) => (
                  <li key={item.label} className="px-3.5 py-2.5">
                    <p className="text-xs font-semibold text-ink">{item.label}</p>
                    {item.detail ? <p className="mt-0.5 text-[11px] text-ink/50">{item.detail}</p> : null}
                    {item.source ? (
                      <p className="mt-1 inline-flex rounded-full bg-canvas px-2 py-0.5 text-[10px] font-medium text-ink/45">
                        {item.source}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-xl bg-canvas p-3.5">
              <p className="text-[10px] font-bold tracking-wider text-brand-ink uppercase">
                Suggested action
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-ink/80">
                {reviewing.suggestedAction}
              </p>
            </div>

            <p className="text-[11px] leading-relaxed text-ink/45">
              This is a recommendation, not a recorded outcome. Once you create the work order, VALORA
              tracks whether the underlying signal clears.
            </p>
          </div>
        ) : null}
      </DetailDrawer>

      {/* -------------------- Create Work Order Dialog -------------------- */}
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

      <p className="text-[11px] text-ink/40 text-center pt-2">
        {isResident
          ? "VALORA uses your own request records and information published by your estate. It cannot see other residents' private requests."
          : isProvider
            ? "VALORA uses work assigned to your provider account. Confirm site instructions with the assigning estate team when records are incomplete."
            : `Scope: ${estate?.estate_name ?? 'no estate selected'} · recommendations are advisory and never written back to estate records without an authorised action.`}
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
