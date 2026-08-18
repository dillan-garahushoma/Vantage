import { ArrowDown, ArrowUp, Check } from "lucide-react";
import type { Plan } from "@/types";
import { plansService } from "@/lib/services/plansService";
import { cn } from "@/lib/utils";

export function formatPrice(plan: Plan): string {
  if (plan.monthlyPriceCents == null) return "Price on request";
  return `${plan.currency} ${(plan.monthlyPriceCents / 100).toFixed(0)} / month`;
}

export function PlanCard({
  plan,
  selected = false,
  onToggleCompare,
  onSelect,
  compareDisabled = false,
}: {
  plan: Plan;
  selected?: boolean;
  onToggleCompare?: (plan: Plan) => void;
  onSelect?: (plan: Plan) => void;
  compareDisabled?: boolean;
}) {
  const provider = plansService.providerById(plan.providerId);
  return (
    <article
      className={cn(
        "flex h-full flex-col rounded-xl border bg-white p-5 shadow-xs transition-shadow hover:shadow-md",
        selected ? "border-gold ring-2 ring-gold" : "border-border",
      )}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-ink/50">
        {provider?.name ?? "Provider"}
      </p>
      <h3 className="mt-1 text-lg font-bold text-navy">{plan.name}</h3>

      <div className="mt-4 flex items-center gap-6">
        <p className="flex items-center gap-1.5 text-navy">
          <ArrowDown className="h-4 w-4 text-gold-600" aria-hidden="true" />
          <span className="text-xl font-extrabold">{plan.downloadMbps}</span>
          <span className="text-xs text-ink/50">Mbps ↓</span>
        </p>
        <p className="flex items-center gap-1.5 text-navy">
          <ArrowUp className="h-4 w-4 text-gold-600" aria-hidden="true" />
          <span className="text-xl font-extrabold">{plan.uploadMbps}</span>
          <span className="text-xs text-ink/50">Mbps ↑</span>
        </p>
      </div>

      <p className="mt-4 text-xl font-extrabold text-navy">{formatPrice(plan)}</p>
      <dl className="mt-2 space-y-1 text-sm text-ink/60">
        <div className="flex gap-2">
          <dt className="font-medium">Installation:</dt>
          <dd>{plan.installationFeeCents != null ? `${plan.currency} ${(plan.installationFeeCents / 100).toFixed(0)}` : "To be confirmed"}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="font-medium">Contract:</dt>
          <dd>{plan.contractMonths != null ? `${plan.contractMonths} months` : "To be confirmed"}</dd>
        </div>
      </dl>

      <ul className="mt-4 space-y-1.5 text-sm text-ink/75">
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#1FA855]" aria-hidden="true" />
            {f}
          </li>
        ))}
      </ul>

      <div className="mt-auto flex flex-col gap-2 pt-5">
        {onSelect && (
          <button
            type="button"
            onClick={() => onSelect(plan)}
            className="h-11 rounded-lg bg-navy text-sm font-bold text-white transition-colors hover:bg-navy-600"
          >
            Select
          </button>
        )}
        {onToggleCompare && (
          <button
            type="button"
            onClick={() => onToggleCompare(plan)}
            disabled={compareDisabled && !selected}
            aria-pressed={selected}
            className={cn(
              "h-11 rounded-lg border-2 text-sm font-semibold transition-colors",
              selected
                ? "border-gold bg-gold-100 text-navy"
                : "border-navy/20 text-navy hover:border-navy disabled:cursor-not-allowed disabled:opacity-40",
            )}
          >
            {selected ? "Remove from compare" : compareDisabled ? "Compare (max 3)" : "Add to compare"}
          </button>
        )}
      </div>
    </article>
  );
}
