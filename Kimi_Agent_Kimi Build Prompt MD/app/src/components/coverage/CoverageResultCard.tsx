import { CheckCircle2, MapPin, AlertCircle } from "lucide-react";
import type { CoverageResult } from "@/types";
import { PlanCard } from "@/components/plans/PlanCard";
import { LeadForm } from "@/components/leads/LeadForm";
import { WhatsAppButton } from "@/components/brand/WhatsAppButton";
import { site } from "@/config/site";

export function CoverageResultCard({ result }: { result: CoverageResult }) {
  const address = result.queriedAddress;

  return (
    <section aria-live="polite" aria-label="Coverage result" className="mt-8 space-y-6">
      {result.status === "covered" && (
        <>
          <div className="rounded-xl border border-[#1FA855]/40 bg-[#1FA855]/10 p-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-1 h-7 w-7 shrink-0 text-[#1FA855]" aria-hidden="true" />
              <div>
                <h2 className="text-2xl font-extrabold text-navy">You're covered</h2>
                <p className="mt-1 text-ink/70">
                  Fibre is available at {address ? <strong>{address}</strong> : "this address"}.
                </p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-bold text-navy">Available providers</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {result.providers.map((p) => (
                <li key={p.id} className="rounded-full bg-navy-50 px-4 py-1.5 text-sm font-semibold text-navy">
                  {p.name}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-bold text-navy">Available plans</h3>
            <PlaceholderNote />
            <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {result.plans.map((plan) => (
                <PlanCard key={plan.id} plan={plan} />
              ))}
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-white p-6">
              <LeadForm
                source="coverage_check"
                heading="Request a connection"
                submitLabel="Request a Connection"
                defaultAddress={address}
                coverageStatus={result.status}
                coordinates={result.coordinates}
              />
            </div>
            <div className="flex flex-col justify-center rounded-xl bg-navy p-6 text-white">
              <h3 className="text-lg font-bold">Prefer to chat?</h3>
              <p className="mt-2 text-sm text-white/75">
                Message us on WhatsApp and we'll take it from there — your address is prefilled.
              </p>
              <WhatsAppButton className="mt-4 self-start" address={address} />
            </div>
          </div>
        </>
      )}

      {result.status === "near_coverage" && (
        <>
          <div className="rounded-xl border border-gold-500/50 bg-gold-100/60 p-6">
            <div className="flex items-start gap-3">
              <MapPin className="mt-1 h-7 w-7 shrink-0 text-gold-600" aria-hidden="true" />
              <div>
                <h2 className="text-2xl font-extrabold text-navy">You're almost covered</h2>
                <p className="mt-1 text-ink/70">
                  Fibre infrastructure is nearby
                  {result.distanceM != null && ` (roughly ${result.distanceM} m from ${result.matchedPolygonName ?? "the nearest coverage area"})`},
                  but availability at this exact address needs confirmation.
                </p>
              </div>
            </div>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-white p-6">
              <LeadForm
                source="survey_request"
                heading="Request a survey"
                submitLabel="Request a Survey"
                defaultAddress={address}
                coverageStatus={result.status}
                coordinates={result.coordinates}
              />
            </div>
            <div className="flex flex-col justify-center rounded-xl bg-navy p-6 text-white">
              <h3 className="text-lg font-bold">Ask us directly</h3>
              <p className="mt-2 text-sm text-white/75">
                Send us your address on WhatsApp and we'll confirm availability.
              </p>
              <WhatsAppButton className="mt-4 self-start" address={address} />
            </div>
          </div>
        </>
      )}

      {result.status === "not_covered" && (
        <div className="rounded-xl border border-border bg-white p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-1 h-7 w-7 shrink-0 text-navy-300" aria-hidden="true" />
            <div className="flex-1">
              <h2 className="text-2xl font-extrabold text-navy">
                Fibre isn't available at this address yet
              </h2>
              <p className="mt-1 text-ink/70">
                Leave your details and we'll let you know when coverage becomes available.
              </p>
              <div className="mt-6">
                <LeadForm
                  source="coverage_request"
                  heading="Request coverage"
                  submitLabel="Request Coverage"
                  defaultAddress={address}
                  coverageStatus={result.status}
                  coordinates={result.coordinates}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export function PlaceholderNote() {
  if (!site.usingPlaceholderPlans) return null;
  return (
    <p className="mt-2 rounded-lg bg-fog px-3 py-2 text-xs text-ink/60">
      Development preview: provider names, plans and pricing are placeholders until FibreHood
      confirms its partner ISPs and plan details.
    </p>
  );
}
