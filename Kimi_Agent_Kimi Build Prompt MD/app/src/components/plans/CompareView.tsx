import { X } from "lucide-react";
import type { Plan } from "@/types";
import { plansService } from "@/lib/services/plansService";
import { formatPrice } from "./PlanCard";

function fmt(cents: number | null, currency: string, suffix = ""): string {
  return cents != null ? `${currency} ${(cents / 100).toFixed(0)}${suffix}` : "To be confirmed";
}

/**
 * Responsive plan comparison: table on desktop, stacked cards on mobile.
 */
export function CompareView({
  plans,
  onRemove,
  onClose,
}: {
  plans: Plan[];
  onRemove: (id: string) => void;
  onClose: () => void;
}) {
  const rows: { label: string; value: (p: Plan) => string }[] = [
    { label: "Provider", value: (p) => plansService.providerById(p.providerId)?.name ?? "—" },
    { label: "Download", value: (p) => `${p.downloadMbps} Mbps` },
    { label: "Upload", value: (p) => `${p.uploadMbps} Mbps` },
    { label: "Monthly price", value: (p) => formatPrice(p) },
    { label: "Contract", value: (p) => (p.contractMonths != null ? `${p.contractMonths} months` : "To be confirmed") },
    { label: "Installation", value: (p) => fmt(p.installationFeeCents, p.currency) },
    { label: "Features", value: (p) => p.features.join(" · ") },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Plan comparison"
      className="fixed inset-0 z-50 flex items-end justify-center bg-navy-900/60 p-0 sm:items-center sm:p-6"
    >
      <div className="max-h-[92vh] w-full max-w-4xl overflow-auto rounded-t-2xl bg-white p-5 sm:rounded-2xl sm:p-8">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-extrabold text-navy">Comparing {plans.length} plans</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close comparison"
            className="rounded-md p-2 text-ink/60 hover:bg-fog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Desktop table */}
        <div className="mt-5 hidden overflow-x-auto md:block">
          <table className="w-full border-collapse text-left text-sm">
            <caption className="sr-only">Side-by-side comparison of selected plans</caption>
            <thead>
              <tr>
                <th scope="col" className="p-3 text-ink/50">Attribute</th>
                {plans.map((p) => (
                  <th key={p.id} scope="col" className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-bold text-navy">{p.name}</span>
                      <button
                        type="button"
                        onClick={() => onRemove(p.id)}
                        aria-label={`Remove ${p.name} from comparison`}
                        className="rounded p-1 text-ink/40 hover:bg-fog hover:text-ink"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label} className="border-t border-border">
                  <th scope="row" className="p-3 font-semibold text-ink/60">
                    {row.label}
                  </th>
                  {plans.map((p) => (
                    <td key={p.id} className="p-3 text-ink">
                      {row.value(p)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile stacked cards */}
        <div className="mt-5 space-y-4 md:hidden">
          {plans.map((p) => (
            <section key={p.id} className="rounded-xl border border-border p-4" aria-label={p.name}>
              <div className="flex items-start justify-between">
                <h3 className="font-bold text-navy">{p.name}</h3>
                <button
                  type="button"
                  onClick={() => onRemove(p.id)}
                  aria-label={`Remove ${p.name} from comparison`}
                  className="rounded p-1 text-ink/40 hover:bg-fog"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <dl className="mt-3 space-y-2 text-sm">
                {rows.map((row) => (
                  <div key={row.label} className="flex justify-between gap-4">
                    <dt className="text-ink/50">{row.label}</dt>
                    <dd className="text-right font-medium text-ink">{row.value(p)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
