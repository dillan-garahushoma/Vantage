import { MessageCircle } from "lucide-react";
import { LeadForm } from "@/components/leads/LeadForm";
import { WhatsAppButton } from "@/components/brand/WhatsAppButton";
import { site } from "@/config/site";
import { whatsappService } from "@/lib/services/whatsappService";
import { useDocumentMeta } from "@/hooks/useDocumentMeta";

export default function Contact() {
  useDocumentMeta({
    title: "Contact | FibreHood",
    description: "Contact FibreHood — WhatsApp is the fastest way to reach us.",
  });

  return (
    <div className="container-site py-10 sm:py-14">
      <header className="max-w-2xl">
        <h1 className="text-3xl font-extrabold text-navy sm:text-4xl">Contact us</h1>
        <p className="mt-3 text-ink/70">
          WhatsApp is the fastest way to reach FibreHood. Prefer writing it down? Use the
          form below and we'll get back to you.
        </p>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl bg-navy p-6 text-white sm:p-8" aria-labelledby="wa-heading">
          <MessageCircle className="h-9 w-9 text-gold" aria-hidden="true" />
          <h2 id="wa-heading" className="mt-4 text-xl font-extrabold">Chat on WhatsApp</h2>
          <p className="mt-2 text-sm text-white/80">
            {site.whatsapp.display}
          </p>
          {whatsappService.confirmationNotice && (
            <p className="mt-1 text-xs text-white/50">{whatsappService.confirmationNotice}</p>
          )}
          <p className="mt-4 text-sm text-white/80">
            Tell us your address and what you're looking for — coverage, plans, installation
            or support — and we'll take it from there.
          </p>
          <WhatsAppButton className="mt-6" />
        </section>

        <section className="rounded-xl border border-border bg-white p-6 sm:p-8" aria-labelledby="form-heading">
          <h2 id="form-heading" className="text-xl font-extrabold text-navy">Send an enquiry</h2>
          <div className="mt-5">
            <LeadForm
              source="contact_form"
              heading="Your details"
              submitLabel="Send enquiry"
            />
          </div>
        </section>
      </div>

      {!site.contact.email && !site.contact.phone && (
        <p className="mt-6 rounded-lg bg-fog p-4 text-sm text-ink/60">
          Additional contact channels (phone, email, office address) will be published here
          once confirmed by the business.
        </p>
      )}
    </div>
  );
}
