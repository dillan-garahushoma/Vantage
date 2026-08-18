import { useNavigate } from "react-router";
import { ShieldCheck, MapPinned, GitBranch, ChevronRight } from "lucide-react";
import { AddressSearchForm } from "@/components/coverage/AddressSearchForm";
import { PlanCard } from "@/components/plans/PlanCard";
import { PlaceholderNote } from "@/components/coverage/CoverageResultCard";
import { WhatsAppButton } from "@/components/brand/WhatsAppButton";
import { mockPlans } from "@/lib/mock/plans";
import { site } from "@/config/site";
import { useDocumentMeta } from "@/hooks/useDocumentMeta";

export default function Home() {
  const navigate = useNavigate();
  useDocumentMeta({
    title: "FibreHood — Fibre connectivity built for Zimbabwe",
    description: site.description,
  });

  return (
    <>
      {/* Hero — coverage checker is the dominant interaction */}
      <section className="bg-navy text-white">
        <div className="hero-grid">
          <div className="container-site py-16 sm:py-24">
            <p className="text-sm font-semibold uppercase tracking-widest text-gold">
              Fibre connectivity built for Zimbabwe
            </p>
            <h1 className="mt-4 max-w-2xl text-4xl font-extrabold leading-tight sm:text-5xl">
              Fast, reliable fibre.
              <br />
              Connected to what matters.
            </h1>
            <p className="mt-4 max-w-xl text-lg text-white/80">
              Check whether fibre is available at your address and discover the plans
              available to you.
            </p>

            <div className="mt-8 max-w-xl rounded-xl bg-white p-4 text-ink shadow-lg sm:p-5">
              <AddressSearchForm
                autoFocus={false}
                onSearch={(address) => navigate(`/coverage?address=${encodeURIComponent(address)}`)}
              />
            </div>

            <div className="mt-5">
              <WhatsAppButton variant="outline" className="border-gold text-gold hover:bg-gold/10">
                WhatsApp us
              </WhatsAppButton>
            </div>
          </div>
        </div>
      </section>

      {/* Value propositions */}
      <section className="container-site py-14 sm:py-20" aria-labelledby="value-props">
        <h2 id="value-props" className="sr-only">Why FibreHood</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {[
            {
              icon: ShieldCheck,
              title: "Reliable fibre infrastructure",
              body: "Fibre connectivity designed and built for real neighbourhoods — homes, buildings and businesses.",
            },
            {
              icon: MapPinned,
              title: "Simple coverage checking",
              body: "Enter your address, see your result in seconds, and know exactly what your options are.",
            },
            {
              icon: GitBranch,
              title: "Flexible provider options",
              body: "Where coverage exists, compare available plans and providers and choose what fits.",
            },
          ].map((item) => (
            <article key={item.title} className="rounded-xl border border-border bg-white p-6 shadow-xs">
              <item.icon className="h-8 w-8 text-gold-600" aria-hidden="true" />
              <h3 className="mt-4 text-lg font-bold text-navy">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/70">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-fog" aria-labelledby="how-it-works">
        <div className="container-site py-14 sm:py-20">
          <h2 id="how-it-works" className="text-2xl font-extrabold text-navy sm:text-3xl">
            How it works
          </h2>
          <ol className="mt-8 grid gap-6 md:grid-cols-3">
            {[
              { step: 1, title: "Check your address", body: "Search your address or drop a pin on the map." },
              { step: 2, title: "View available options", body: "See whether you're covered and which plans and providers are available." },
              { step: 3, title: "Request your connection", body: "Send a short request — or chat to us on WhatsApp — and we'll take it from there." },
            ].map((item) => (
              <li key={item.step} className="relative rounded-xl bg-white p-6 shadow-xs">
                <span
                  aria-hidden="true"
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-gold text-lg font-extrabold text-navy"
                >
                  {item.step}
                </span>
                <h3 className="mt-4 text-lg font-bold text-navy">{item.title}</h3>
                <p className="mt-2 text-sm text-ink/70">{item.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Coverage CTA */}
      <section className="container-site py-14 sm:py-20" aria-labelledby="coverage-cta">
        <div className="rounded-2xl bg-navy p-8 text-center text-white sm:p-14">
          <h2 id="coverage-cta" className="text-3xl font-extrabold sm:text-4xl">
            Not sure if you're covered?
          </h2>
          <p className="mx-auto mt-3 max-w-md text-white/80">
            Enter your address and find out in seconds.
          </p>
          <button
            type="button"
            onClick={() => navigate("/coverage")}
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-gold px-8 py-3.5 text-base font-bold text-navy transition-colors hover:bg-gold-300"
          >
            Check Coverage
            <ChevronRight className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
      </section>

      {/* Plans teaser */}
      <section className="container-site pb-14 sm:pb-20" aria-labelledby="plans-teaser">
        <div className="flex items-end justify-between">
          <h2 id="plans-teaser" className="text-2xl font-extrabold text-navy sm:text-3xl">
            Example plans
          </h2>
          <button
            type="button"
            onClick={() => navigate("/plans")}
            className="text-sm font-bold text-navy underline-offset-4 hover:underline"
          >
            View all plans →
          </button>
        </div>
        <PlaceholderNote />
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mockPlans.slice(0, 3).map((plan) => (
            <PlanCard key={plan.id} plan={plan} onSelect={() => navigate("/plans")} />
          ))}
        </div>
      </section>

      {/* WhatsApp CTA */}
      <section className="bg-navy" aria-labelledby="whatsapp-cta">
        <div className="container-site flex flex-col items-start gap-6 py-14 text-white sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 id="whatsapp-cta" className="text-2xl font-extrabold sm:text-3xl">
              Talk to a real person
            </h2>
            <p className="mt-2 max-w-md text-white/80">
              Questions about coverage, plans or installation? WhatsApp is the fastest way to reach us.
            </p>
          </div>
          <WhatsAppButton className="shrink-0" />
        </div>
      </section>
    </>
  );
}
