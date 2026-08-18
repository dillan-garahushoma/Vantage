import { lazy, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { Loader2 } from "lucide-react";
import { AddressSearchForm } from "@/components/coverage/AddressSearchForm";
import { CoverageResultCard } from "@/components/coverage/CoverageResultCard";
import { LeadForm } from "@/components/leads/LeadForm";
import { useCoverageLookup } from "@/hooks/useCoverageLookup";
import { useDocumentMeta } from "@/hooks/useDocumentMeta";
import { site } from "@/config/site";

// Map library loads only when the coverage page is opened.
const CoverageMap = lazy(() =>
  import("@/components/coverage/CoverageMap").then((m) => ({ default: m.CoverageMap })),
);

export default function Coverage() {
  useDocumentMeta({
    title: "Check Coverage | FibreHood",
    description: "Check whether FibreHood fibre is available at your address in Zimbabwe.",
  });
  const { state, lookupAddress, lookupCoordinates, reset } = useCoverageLookup();
  const [params, setParams] = useSearchParams();
  const [geoError, setGeoError] = useState<string | null>(null);

  // Support ?address= deep links from the homepage hero.
  useEffect(() => {
    const address = params.get("address");
    if (address) {
      void lookupAddress(address);
      params.delete("address");
      setParams(params, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const result = state.phase === "result" ? state.result : undefined;
  const loading = state.phase === "loading";

  function useMyLocation() {
    setGeoError(null);
    if (!navigator.geolocation) {
      setGeoError("Your browser doesn't support location. Please enter your address instead.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => lookupCoordinates({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => setGeoError("We couldn't access your location. Please enter your address instead."),
      { timeout: 10000 },
    );
  }

  return (
    <div className="container-site py-10 sm:py-14">
      <header className="max-w-2xl">
        <h1 className="text-3xl font-extrabold text-navy sm:text-4xl">Check your coverage</h1>
        <p className="mt-3 text-ink/70">
          Enter your address, use your location, or click anywhere on the map. We'll tell you
          whether fibre is available there and what your options are.
        </p>
        {site.usingMockCoverage && (
          <p className="mt-3 rounded-lg bg-gold-100 px-3 py-2 text-xs font-medium text-navy">
            Development preview: coverage areas on this map are mock data until real coverage
            files are supplied.
          </p>
        )}
      </header>

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        <div>
          <div className="rounded-xl border border-border bg-white p-5 shadow-xs">
            <AddressSearchForm
              onSearch={(a) => lookupAddress(a)}
              onUseLocation={useMyLocation}
              loading={loading}
            />
            {geoError && (
              <p role="alert" className="mt-3 text-sm text-destructive">
                {geoError}
              </p>
            )}
            <p className="mt-4 text-xs text-ink/50">
              Tip for this preview: try “Avondale” (covered), “Highlands” (near coverage),
              “Bulawayo” (not covered), or any unrecognised address (error state).
            </p>
          </div>

          {state.phase === "unknown_address" && (
            <div role="alert" className="mt-6 rounded-xl border border-border bg-white p-6">
              <h2 className="text-xl font-extrabold text-navy">We couldn't verify this address</h2>
              <p className="mt-1 text-ink/70">
                Check the address and try again, or request a coverage survey and we'll
                confirm availability for you.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={reset}
                  className="h-11 rounded-lg bg-navy px-6 text-sm font-bold text-white hover:bg-navy-600"
                >
                  Try Again
                </button>
              </div>
              <div className="mt-6 border-t border-border pt-6">
                <LeadForm
                  source="survey_request"
                  heading="Request a survey"
                  submitLabel="Request Survey"
                  defaultAddress={state.address}
                />
              </div>
            </div>
          )}
        </div>

        <div>
          <Suspense
            fallback={
              <div className="flex h-72 items-center justify-center rounded-xl border border-border bg-fog sm:h-96" role="status" aria-label="Loading map">
                <Loader2 className="h-8 w-8 animate-spin text-navy-300" aria-hidden="true" />
              </div>
            }
          >
            <CoverageMap
              pin={result?.coordinates}
              highlightPolygonId={result?.matchedPolygonId}
              onMapClick={(coords) => lookupCoordinates(coords)}
            />
          </Suspense>
          {loading && (
            <div role="status" className="mt-4 flex items-center gap-3 rounded-xl border border-border bg-white p-4">
              <Loader2 className="h-5 w-5 animate-spin text-navy" aria-hidden="true" />
              <p className="text-sm font-medium text-ink/70">Checking coverage…</p>
            </div>
          )}
        </div>
      </div>

      {result && <CoverageResultCard result={result} />}
    </div>
  );
}
