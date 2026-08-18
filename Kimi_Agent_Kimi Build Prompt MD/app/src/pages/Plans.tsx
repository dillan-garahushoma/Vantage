import { useMemo, useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import type { Plan } from "@/types";
import { mockPlans } from "@/lib/mock/plans";
import { mockProviders } from "@/lib/mock/providers";
import { plansService } from "@/lib/services/plansService";
import { PlanCard } from "@/components/plans/PlanCard";
import { CompareView } from "@/components/plans/CompareView";
import { LeadForm } from "@/components/leads/LeadForm";
import { PlaceholderNote } from "@/components/coverage/CoverageResultCard";
import { WhatsAppButton } from "@/components/brand/WhatsAppButton";
import { analytics } from "@/lib/services/analytics";
import { useDocumentMeta } from "@/hooks/useDocumentMeta";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type SortKey = "speed_desc" | "speed_asc" | "price_asc" | "price_desc";
const MAX_COMPARE = 3;

export default function Plans() {
  useDocumentMeta({
    title: "Plans | FibreHood",
    description: "Compare fibre plans available through FibreHood coverage areas.",
  });

  const [providerFilter, setProviderFilter] = useState<string>("all");
  const [minSpeed, setMinSpeed] = useState<number>(0);
  const [sort, setSort] = useState<SortKey>("speed_desc");
  const [compare, setCompare] = useState<Plan[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

  const filtered = useMemo(() => {
    let list = mockPlans.filter(
      (p) =>
        (providerFilter === "all" || p.providerId === providerFilter) &&
        p.downloadMbps >= minSpeed,
    );
    const nullsLast = (v: number | null) => (v == null ? Number.MAX_SAFE_INTEGER : v);
    list = [...list].sort((a, b) => {
      switch (sort) {
        case "speed_desc": return b.downloadMbps - a.downloadMbps;
        case "speed_asc": return a.downloadMbps - b.downloadMbps;
        case "price_asc": return nullsLast(a.monthlyPriceCents) - nullsLast(b.monthlyPriceCents);
        case "price_desc": return nullsLast(b.monthlyPriceCents) - nullsLast(a.monthlyPriceCents);
      }
    });
    return list;
  }, [providerFilter, minSpeed, sort]);

  function toggleCompare(plan: Plan) {
    setCompare((current) => {
      if (current.some((p) => p.id === plan.id)) return current.filter((p) => p.id !== plan.id);
      if (current.length >= MAX_COMPARE) return current;
      const next = [...current, plan];
      analytics.track("plan.compare", { plan_ids: next.map((p) => p.id).join(",") });
      return next;
    });
  }

  return (
    <div className="container-site py-10 sm:py-14">
      <header className="max-w-2xl">
        <h1 className="text-3xl font-extrabold text-navy sm:text-4xl">Fibre plans</h1>
        <p className="mt-3 text-ink/70">
          Compare the fibre options available through FibreHood coverage areas. Select up to{" "}
          {MAX_COMPARE} plans to compare side by side.
        </p>
        <PlaceholderNote />
      </header>

      {/* Filters */}
      <section aria-label="Plan filters" className="mt-8 rounded-xl border border-border bg-white p-4 shadow-xs">
        <div className="flex items-center gap-2 text-sm font-bold text-navy">
          <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
          Filter & sort
        </div>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="filter-provider" className="mb-1 block text-sm font-semibold text-ink">Provider</label>
            <select
              id="filter-provider"
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="h-11 w-full rounded-lg border border-input bg-white px-3 text-sm"
            >
              <option value="all">All providers</option>
              {mockProviders.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-speed" className="mb-1 block text-sm font-semibold text-ink">
              Minimum download speed
            </label>
            <select
              id="filter-speed"
              value={minSpeed}
              onChange={(e) => setMinSpeed(Number(e.target.value))}
              className="h-11 w-full rounded-lg border border-input bg-white px-3 text-sm"
            >
              <option value={0}>Any speed</option>
              <option value={25}>25+ Mbps</option>
              <option value={50}>50+ Mbps</option>
              <option value={100}>100+ Mbps</option>
              <option value={200}>200+ Mbps</option>
            </select>
          </div>
          <div>
            <label htmlFor="sort" className="mb-1 block text-sm font-semibold text-ink">Sort by</label>
            <select
              id="sort"
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="h-11 w-full rounded-lg border border-input bg-white px-3 text-sm"
            >
              <option value="speed_desc">Speed: high to low</option>
              <option value="speed_asc">Speed: low to high</option>
              <option value="price_asc">Price: low to high</option>
              <option value="price_desc">Price: high to low</option>
            </select>
          </div>
        </div>
      </section>

      {/* Compare tray */}
      {compare.length > 0 && (
        <div className="sticky bottom-4 z-30 mt-6 flex items-center justify-between gap-4 rounded-xl border border-gold bg-white p-4 shadow-lg">
          <p className="text-sm font-semibold text-navy">
            {compare.length} of {MAX_COMPARE} plans selected
          </p>
          <button
            type="button"
            onClick={() => setCompareOpen(true)}
            disabled={compare.length < 2}
            className="h-11 rounded-lg bg-navy px-6 text-sm font-bold text-white hover:bg-navy-600 disabled:opacity-40"
          >
            Compare now
          </button>
        </div>
      )}

      {/* Plan grid */}
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            selected={compare.some((p) => p.id === plan.id)}
            onToggleCompare={toggleCompare}
            onSelect={setSelectedPlan}
            compareDisabled={compare.length >= MAX_COMPARE}
          />
        ))}
        {filtered.length === 0 && (
          <p className="col-span-full rounded-xl border border-border bg-white p-8 text-center text-ink/60">
            No plans match these filters. Try widening your selection.
          </p>
        )}
      </div>

      {/* Bottom CTA */}
      <section className="mt-12 rounded-2xl bg-navy p-8 text-white sm:p-10" aria-labelledby="plans-help">
        <h2 id="plans-help" className="text-2xl font-extrabold">Not sure which plan fits?</h2>
        <p className="mt-2 max-w-lg text-white/80">
          Tell us how you use the internet and we'll point you in the right direction.
        </p>
        <WhatsAppButton className="mt-5" />
      </section>

      {compareOpen && (
        <CompareView
          plans={compare}
          onRemove={(id) => setCompare((c) => c.filter((p) => p.id !== id))}
          onClose={() => setCompareOpen(false)}
        />
      )}

      {/* Plan selection → lead dialog */}
      <Dialog open={!!selectedPlan} onOpenChange={(open) => !open && setSelectedPlan(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-navy">
              Request {selectedPlan?.name ?? "this plan"}
            </DialogTitle>
          </DialogHeader>
          {selectedPlan && (
            <>
              <p className="text-sm text-ink/60">
                {plansService.providerById(selectedPlan.providerId)?.name} ·{" "}
                {selectedPlan.downloadMbps}/{selectedPlan.uploadMbps} Mbps
              </p>
              <LeadForm
                source="plans_page"
                heading="Your details"
                submitLabel="Request this plan"
                planId={selectedPlan.id}
              />
              <div className="mt-2">
                <WhatsAppButton variant="outline" planName={selectedPlan.name} className="w-full" />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
