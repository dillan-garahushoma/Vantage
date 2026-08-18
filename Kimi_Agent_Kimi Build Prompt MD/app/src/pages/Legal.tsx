import { useDocumentMeta } from "@/hooks/useDocumentMeta";

const REVIEW_NOTICE =
  "DRAFT — This legal text is a structural placeholder. It requires review and approval by FibreHood and legal counsel before the site goes live. It does not claim compliance with any specific regulation.";

export function Privacy() {
  useDocumentMeta({ title: "Privacy Policy | FibreHood" });
  return (
    <div className="container-site max-w-3xl py-10 sm:py-14">
      <h1 className="text-3xl font-extrabold text-navy sm:text-4xl">Privacy Policy</h1>
      <p role="note" className="mt-4 rounded-lg border border-gold-500/50 bg-gold-100/60 p-4 text-sm font-medium text-navy">
        {REVIEW_NOTICE}
      </p>
      <div className="mt-6 space-y-5 text-sm leading-relaxed text-ink/80">
        <h2 className="text-lg font-bold text-navy">What we collect</h2>
        <p>
          When you use this site we may collect: your name, phone number, email address,
          the address you check for coverage, approximate coordinates, and referral (UTM)
          tags. We collect the minimum needed to respond to your request.
        </p>
        <h2 className="text-lg font-bold text-navy">Consent</h2>
        <p>
          We only store your details when you explicitly consent (the checkbox on our
          forms). Consent is recorded with the time and context of your request.
        </p>
        <h2 className="text-lg font-bold text-navy">How we use it</h2>
        <p>
          To respond to coverage, plan and installation enquiries; to notify you when
          coverage becomes available at your address; and to improve this service.
        </p>
        <h2 className="text-lg font-bold text-navy">Third parties</h2>
        <p>
          This site links to WhatsApp (Meta) for messaging. Map tiles are provided by
          OpenStreetMap contributors. A final list of processors (including analytics and
          geocoding providers) will be published here before launch.
        </p>
        <h2 className="text-lg font-bold text-navy">Your rights</h2>
        <p>
          You may request access to, correction of, or deletion of your personal data at
          any time by contacting us on WhatsApp. Retention periods will be confirmed in
          the final policy.
        </p>
      </div>
    </div>
  );
}

export function Terms() {
  useDocumentMeta({ title: "Terms of Service | FibreHood" });
  return (
    <div className="container-site max-w-3xl py-10 sm:py-14">
      <h1 className="text-3xl font-extrabold text-navy sm:text-4xl">Terms of Service</h1>
      <p role="note" className="mt-4 rounded-lg border border-gold-500/50 bg-gold-100/60 p-4 text-sm font-medium text-navy">
        {REVIEW_NOTICE}
      </p>
      <div className="mt-6 space-y-5 text-sm leading-relaxed text-ink/80">
        <h2 className="text-lg font-bold text-navy">The service</h2>
        <p>
          This website lets you check fibre coverage at an address, view available plans,
          and submit connection or coverage requests to FibreHood.
        </p>
        <h2 className="text-lg font-bold text-navy">Coverage results</h2>
        <p>
          Coverage results are indicative. Availability at a specific address is confirmed
          only after a survey or provider confirmation. Submitting a request does not
          guarantee installation or a specific timeline.
        </p>
        <h2 className="text-lg font-bold text-navy">Plans and pricing</h2>
        <p>
          Plan details, providers and pricing shown on this site are subject to
          confirmation by the relevant provider. Final terms are agreed directly when you
          sign up.
        </p>
        <h2 className="text-lg font-bold text-navy">Acceptable use</h2>
        <p>
          Do not misuse this site, attempt to disrupt it, or submit false or misleading
          information.
        </p>
      </div>
    </div>
  );
}
