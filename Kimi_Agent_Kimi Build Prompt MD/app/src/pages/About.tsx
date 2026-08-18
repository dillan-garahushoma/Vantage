import { Link } from "react-router";
import { site } from "@/config/site";
import { useDocumentMeta } from "@/hooks/useDocumentMeta";

export default function About() {
  useDocumentMeta({
    title: "About | FibreHood",
    description: "Who FibreHood is and what we do — fibre connectivity for Zimbabwe.",
  });

  return (
    <div className="container-site max-w-3xl py-10 sm:py-14">
      <h1 className="text-3xl font-extrabold text-navy sm:text-4xl">About FibreHood</h1>

      <div className="mt-6 space-y-5 leading-relaxed text-ink/80">
        <p>
          FibreHood is a Zimbabwe-focused fibre connectivity company. We work on bringing
          fibre internet into neighbourhoods, buildings and businesses — so that fast,
          reliable connectivity is something you can simply check for and request, rather
          than chase.
        </p>
        <p>
          This website is built around one simple idea: you should be able to enter your
          address, find out whether fibre reaches you, see your options, and talk to a real
          person — in a couple of minutes.
        </p>

        <h2 className="pt-2 text-xl font-bold text-navy">What we do</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>Fibre connectivity for residential homes and apartment buildings.</li>
          <li>Fibre connectivity for businesses.</li>
          <li>Coverage discovery — check your address before you commit to anything.</li>
          <li>Connection requests and support through short forms and WhatsApp.</li>
        </ul>

        <h2 className="pt-2 text-xl font-bold text-navy">For homes and businesses</h2>
        <p>
          Whether you're a remote worker who needs a dependable connection, a property
          manager looking to connect a whole building, or a business that relies on being
          online — the process starts the same way:{" "}
          <Link to="/coverage" className="font-semibold text-navy underline underline-offset-4">
            check your coverage
          </Link>
          .
        </p>

        {!site.openAccessClaimConfirmed && (
          <p className="rounded-lg bg-fog p-4 text-sm text-ink/60">
            Note: details about FibreHood's operating model (including any open-access
            network and partner-ISP arrangements) will be published here once confirmed by
            the business.
          </p>
        )}
      </div>
    </div>
  );
}
