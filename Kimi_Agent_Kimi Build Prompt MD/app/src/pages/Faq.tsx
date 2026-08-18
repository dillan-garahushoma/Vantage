import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useDocumentMeta } from "@/hooks/useDocumentMeta";

/**
 * FAQ — answers are limited to what the confirmed source material supports.
 * Categories exist for confirmed content to slot into; nothing here invents
 * technical policy (installation timelines, fault SLAs, etc.).
 */
const categories: { name: string; items: { q: string; a: React.ReactNode }[] }[] = [
  {
    name: "Coverage",
    items: [
      {
        q: "How do I check if fibre is available at my address?",
        a: (
          <>
            Use the <a href="/coverage" className="font-semibold text-navy underline underline-offset-4">coverage checker</a>{" "}
            — enter your address or click the map. You'll get one of three results: covered,
            almost covered (infrastructure nearby, needs confirmation), or not covered yet.
          </>
        ),
      },
      {
        q: "What if my address isn't covered?",
        a: "It isn't a dead end. Leave your details on the result page and we'll let you know when coverage becomes available. Demand helps decide where fibre goes next.",
      },
      {
        q: "What does 'almost covered' mean?",
        a: "Fibre infrastructure is nearby, but availability at your exact address needs to be confirmed. Request a survey and we'll verify it for you.",
      },
    ],
  },
  {
    name: "Plans",
    items: [
      {
        q: "Which providers and plans are available?",
        a: "Where fibre coverage exists, available providers and plans are shown on your coverage result and on the plans page. Provider names and pricing are being finalised with partners and will be published once confirmed.",
      },
    ],
  },
  {
    name: "Installation",
    items: [
      {
        q: "How do I request an installation?",
        a: "Check your coverage first. If you're covered, use the 'Request a connection' form on your result or chat to us on WhatsApp — your address will be prefilled.",
      },
    ],
  },
  {
    name: "Moving house",
    items: [
      {
        q: "I'm moving — what should I do?",
        a: "Check coverage at your new address and contact us on WhatsApp so we can advise on the options there.",
      },
    ],
  },
  {
    name: "Contacting support",
    items: [
      {
        q: "What's the fastest way to get help?",
        a: "WhatsApp. Tap the WhatsApp button anywhere on this site and your message goes straight to the team.",
      },
    ],
  },
];

export default function Faq() {
  useDocumentMeta({
    title: "FAQ | FibreHood",
    description: "Frequently asked questions about FibreHood coverage, plans and installation.",
  });

  return (
    <div className="container-site max-w-3xl py-10 sm:py-14">
      <h1 className="text-3xl font-extrabold text-navy sm:text-4xl">Frequently asked questions</h1>
      <p className="mt-3 text-ink/70">
        Quick answers about coverage, plans and getting connected.
      </p>

      <div className="mt-8 space-y-8">
        {categories.map((cat, i) => (
          <section key={cat.name} aria-labelledby={`faq-cat-${i}`}>
            <h2 id={`faq-cat-${i}`} className="text-lg font-bold text-navy">{cat.name}</h2>
            <Accordion type="single" collapsible className="mt-3">
              {cat.items.map((item, j) => (
                <AccordionItem key={j} value={`${i}-${j}`} className="rounded-lg border border-border bg-white px-4 data-[state=open]:shadow-xs mb-2">
                  <AccordionTrigger className="text-left text-sm font-semibold text-navy">
                    {item.q}
                  </AccordionTrigger>
                  <AccordionContent className="text-sm leading-relaxed text-ink/75">
                    {item.a}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </section>
        ))}
      </div>
    </div>
  );
}
