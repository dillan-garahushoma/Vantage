import { ArrowRight, FileSearch, Layers, ShieldCheck, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { RequireEstate } from '../components/RequireEstate';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { ErrorState } from '../components/ui';
import { AskValora } from '../components/valora/AskValora';
import { CreateWorkOrderDialog } from '../components/valora/CreateWorkOrderDialog';
import { DetailDrawer } from '../components/valora/DetailDrawer';
import { RecommendationCard } from '../components/valora/RecommendationCard';
import { SignalField } from '../components/valora/SignalField';
import { StatusChip } from '../components/valora/StatusChip';
import { Surface } from '../components/valora/Surface';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api } from '../lib/api';
import { zar } from '../lib/format';
import { useAsync } from '../lib/useAsync';
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
function IntelligenceBody() {
    const { estateId, estate } = useEstateScope();
    const { user } = useAuth();
    const isAdmin = user?.role === 'hoa_admin' && estate?.is_estate_admin === true;
    const [reviewing, setReviewing] = useState(null);
    const [workOrderDraft, setWorkOrderDraft] = useState(null);
    const [accepted, setAccepted] = useState([]);
    const [generating, setGenerating] = useState(false);
    const [generationError, setGenerationError] = useState(null);
    const intelligenceQuery = useAsync(() => estateId === null
        ? Promise.resolve(null)
        : api.get('/api/v1/analytics/intelligence', { estate_id: estateId }), [estateId]);
    const activeBriefing = intelligenceQuery.data?.briefing;
    const activeRecommendations = intelligenceQuery.data?.recommendations ?? [];
    const signals = signalNodes(intelligenceQuery.data?.operational_signals);
    function openWorkOrder(recommendation) {
        setReviewing(null);
        setWorkOrderDraft({
            title: recommendation.title,
            asset: recommendation.workOrderDefaults.asset,
            location: recommendation.workOrderDefaults.location,
            priority: recommendation.workOrderDefaults.priority,
            costZar: recommendation.workOrderDefaults.costZar,
            description: recommendation.workOrderDefaults.description,
        });
    }
    if (intelligenceQuery.loading) return <p role="status">Loading stored estate intelligence…</p>;
    if (intelligenceQuery.error || !activeBriefing) return <ErrorState title="Intelligence unavailable" message={intelligenceQuery.error?.message ?? 'No briefing was returned.'} action={<Button onClick={intelligenceQuery.reload}>Try again</Button>}/>;
    return (<div className="space-y-6">
      {/* ------------------------------------------------ weekly briefing hero */}
      <div className="relative overflow-hidden rounded-3xl border border-line bg-surface">
        <SignalField className="absolute inset-x-0 top-0 h-[280px] rounded-none border-0"/>

        <div className="relative px-6 py-9 sm:px-10 sm:py-12">
          <Badge variant="default" className="gap-2 bg-surface/80 px-3.5 py-1.5 tracking-[0.16em] backdrop-blur">
            <Sparkles className="h-3.5 w-3.5"/>
            VALORA Intelligence
            {intelligenceQuery.data?.source === 'n8n' ? (<span className="ml-1 rounded-full bg-mint-wash px-2 py-0.5 text-[0.68rem] font-bold text-mint-ink">
                Live n8n
              </span>) : null}
          </Badge>

          <h1 className="mt-6 max-w-3xl font-heading text-[1.9rem] leading-[1.12] font-extrabold tracking-[-0.025em] text-ink sm:text-[2.5rem]">
            {activeBriefing.headline}
          </h1>
          <p className="mt-4 max-w-2xl text-[1rem] leading-relaxed text-ink/62">
            {activeBriefing.body}
          </p>
          <p className="mt-3 text-sm text-ink/55">
            {intelligenceQuery.data?.briefing_id ? 'Saved briefing' : 'Current preview'} · {intelligenceQuery.data?.as_of ? new Date(intelligenceQuery.data.as_of).toLocaleString('en-ZA') : 'Date unavailable'}
          </p>
          {intelligenceQuery.data?.briefing_id ? <p className="mt-1 text-xs text-ink/50">Counts are frozen at the briefing date. Ask VALORA reads current records.</p> : null}
          {isAdmin ? <Button className="mt-3" disabled={generating} onClick={async () => {
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
          }}>{generating ? 'Saving…' : 'Save current briefing'}</Button> : null}
          {generationError ? <p role="alert">{generationError}</p> : null}
          {intelligenceQuery.data?.limitations?.map((limitation) => <p key={limitation} className="mt-1 text-xs text-ink/50">{limitation}</p>)}

          <div className="mt-8 flex flex-wrap items-center gap-x-7 gap-y-2.5">
            <span className="text-[0.78rem] font-medium text-ink/45">
              Briefing window · {activeBriefing.windowLabel}
            </span>
            <span className="text-[0.78rem] font-medium text-ink/45">
              {activeBriefing.signalsReviewed.toLocaleString('en-ZA')} signals reviewed across{' '}
              {activeBriefing.sources} sources
            </span>
            <span className="inline-flex items-center gap-1.5 text-[0.78rem] font-semibold text-mint-ink">
              <ShieldCheck className="h-3.5 w-3.5"/>
              Every finding traceable to source
            </span>
          </div>
        </div>
      </div>

      {signals.length > 0 ? (<SignalField signals={signals} label="Operational counts at the briefing date"/>) : null}

      <div className="grid gap-5 xl:grid-cols-[1fr_400px]">
        <div className="space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-heading text-[1.1rem] font-bold tracking-[-0.01em] text-ink">
                This week’s priority recommendations
              </h2>
              <p className="mt-1 text-[0.85rem] text-ink/55">
                Ordered by expected impact. Each one shows its evidence, confidence and suggested
                action.
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-wash px-3 py-1.5 text-[0.72rem] font-semibold text-brand-ink">
              <Layers className="h-3.5 w-3.5"/> {activeRecommendations.length} recommendations
            </span>
          </div>

          <div className="grid gap-5 2xl:grid-cols-2">
            {activeRecommendations.length === 0 ? (<div className="col-span-full rounded-2xl border border-dashed border-line bg-canvas/60 p-8 text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-wash text-brand-ink">
                  <Sparkles className="h-6 w-6"/>
                </div>
                <h3 className="mt-4 font-heading text-base font-bold text-ink">
                  No Priority Recommendations Yet
                </h3>
                <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink/60">
                  Stored counts are available. Asset failure predictions and verified cost savings require additional evidence.
                </p>
                <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1 text-xs font-medium text-ink/60">
                  <ShieldCheck className="h-3.5 w-3.5 text-mint-ink"/>
                  Stored operational records
                </div>
              </div>) : (activeRecommendations.map((recommendation, index) => (<RecommendationCard key={recommendation.id} recommendation={recommendation} index={index} onReview={setReviewing} onAction={openWorkOrder} canAction={isAdmin}/>)))}
          </div>

          <Surface className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-canvas text-brand">
                <FileSearch className="h-4 w-4"/>
              </span>
              <div>
                <p className="text-[0.88rem] font-semibold text-ink">
                  Recommendations are clearly separated from measured results
                </p>
                <p className="mt-1 text-[0.82rem] leading-relaxed text-ink/55">
                  Estate health scores, financial figures and incident counts come from measured
                  signals. Everything on this screen is a recommendation until you act on it.
                </p>
              </div>
            </div>
            {accepted.length > 0 ? (<span className="shrink-0 rounded-full bg-mint-wash px-3 py-1.5 text-[0.72rem] font-semibold text-mint-ink">
                {accepted.length} accepted this session
              </span>) : null}
          </Surface>

          {!isAdmin ? (<p className="text-[0.78rem] text-ink/45">
              Raising the work order for a recommendation is an estate administrator action — the API
              refuses it for any other role, so the button is hidden rather than shown and rejected.
            </p>) : null}
        </div>

        <Surface className="h-fit overflow-hidden xl:sticky xl:top-24" padded={false}>
          <div className="h-[620px]">
            <AskValora key={estateId}/>
          </div>
        </Surface>
      </div>

      {/* ------------------------------------------------------- review drawer */}
      <DetailDrawer open={reviewing !== null} onOpenChange={(open) => {
            if (!open)
                setReviewing(null);
        }} title={reviewing?.title} subtitle={reviewing ? `${reviewing.id} · ${reviewing.kind}` : ''} badge={reviewing ? (<StatusChip status={reviewing.confidence} size="sm"/>) : null} width="sm:max-w-[600px]" footer={reviewing ? (<div className="flex flex-wrap justify-end gap-2">
              <Button variant="outline" onClick={() => setReviewing(null)} className="h-10 rounded-full px-5">
                Close
              </Button>
              {isAdmin ? (<Button variant="ink" onClick={() => openWorkOrder(reviewing)} className="h-10 rounded-full px-5">
                  Create work order
                  <ArrowRight className="h-3.5 w-3.5"/>
                </Button>) : null}
            </div>) : null}>
        {reviewing ? (<div className="space-y-6">
            <p className="text-[0.9rem] leading-relaxed text-ink/70">{reviewing.summary}</p>

            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { label: 'Confidence', value: `${reviewing.confidence} · ${reviewing.confidenceValue}%` },
                { label: 'Expected saving', value: zar(reviewing.savingsZar) },
                { label: 'Category', value: reviewing.kind },
            ].map((row) => (<div key={row.label} className="rounded-xl border border-line p-3.5">
                  <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink/40 uppercase">
                    {row.label}
                  </p>
                  <p className="mt-1.5 text-[0.85rem] font-bold text-ink">{row.value}</p>
                </div>))}
            </div>

            <div>
              <p className="text-[0.68rem] font-semibold tracking-[0.14em] text-ink/40 uppercase">
                Source signals
              </p>
              <ul className="mt-3 divide-y divide-line-soft rounded-2xl border border-line">
                {reviewing.evidence.map((item) => (<li key={item.label} className="px-4 py-3.5">
                    <p className="text-[0.85rem] font-semibold text-ink">{item.label}</p>
                    {item.detail ? (<p className="mt-0.5 text-[0.78rem] text-ink/50">{item.detail}</p>) : null}
                    {item.source ? (<p className="mt-1.5 inline-flex rounded-full bg-canvas px-2.5 py-1 text-[0.68rem] font-medium text-ink/45">
                        {item.source}
                      </p>) : null}
                  </li>))}
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
          </div>) : null}
      </DetailDrawer>

      {/* --------------------------------------------- work order from finding */}
      <CreateWorkOrderDialog open={workOrderDraft !== null} onOpenChange={(open) => {
            if (!open)
                setWorkOrderDraft(null);
        }} defaults={workOrderDraft ?? undefined} onCreated={() => {
            if (reviewing)
                setAccepted((current) => [...current, reviewing.id]);
            intelligenceQuery.reload();
        }}/>

      {estateId === null ? (<ErrorState title="No estate selected" message="Intelligence reads one estate at a time. Choose an estate from the switcher to scope the signals."/>) : null}

      <p className="text-[0.72rem] text-ink/35">
        Scope: {estate?.estate_name ?? 'no estate selected'} · recommendations are advisory and never
        written back to the estate’s records without a work order.
      </p>
    </div>);
}
export function Intelligence() {
    const { estateId } = useEstateScope();
    return (<RequireEstate>
      <IntelligenceBody key={estateId}/>
    </RequireEstate>);
}
