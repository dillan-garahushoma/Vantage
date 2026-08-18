import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { leadSchema, leadService, collectUtm } from "@/lib/services/leadService";
import type { CoverageStatus, LeadInput } from "@/types";
import { WhatsAppButton } from "@/components/brand/WhatsAppButton";
import { Link } from "react-router";

const inputClass =
  "h-11 w-full rounded-lg border border-input bg-white px-3 text-base text-ink placeholder:text-ink/40 focus-visible:ring-gold";

export function LeadForm({
  source,
  heading = "Request a connection",
  submitLabel = "Submit request",
  defaultAddress,
  planId,
  coverageStatus,
  coordinates,
}: {
  source: LeadInput["source"];
  heading?: string;
  submitLabel?: string;
  defaultAddress?: string;
  planId?: string;
  coverageStatus?: CoverageStatus;
  coordinates?: { lat: number; lon: number };
}) {
  const [values, setValues] = useState({ name: "", phone: "", email: "", address: defaultAddress ?? "" });
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (done) {
    return (
      <div role="status" className="rounded-xl border border-[#1FA855]/40 bg-[#1FA855]/10 p-6 text-center">
        <CheckCircle2 className="mx-auto h-10 w-10 text-[#1FA855]" aria-hidden="true" />
        <h3 className="mt-3 text-lg font-bold text-navy">Request received</h3>
        <p className="mt-1 text-sm text-ink/70">
          Thanks. FibreHood has your request and will be in touch.
        </p>
        <WhatsAppButton
          className="mt-4"
          address={values.address || undefined}
        />
      </div>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    const payload: LeadInput = {
      name: values.name,
      phone: values.phone,
      email: values.email || undefined,
      address: values.address || undefined,
      planId,
      source,
      consent,
      coverageStatus,
      lat: coordinates?.lat,
      lon: coordinates?.lon,
      utm: collectUtm(),
    };
    const parsed = leadSchema.safeParse(payload);
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const key = String(issue.path[0] ?? "form");
        if (!fieldErrors[key]) fieldErrors[key] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    setSubmitting(true);
    const result = await leadService.create(payload);
    setSubmitting(false);
    if (result.ok) {
      setDone(true);
    } else {
      setFormError(result.error);
    }
  }

  function field(
    id: string,
    label: string,
    props: React.InputHTMLAttributes<HTMLInputElement>,
    errorKey: string,
  ) {
    return (
      <div>
        <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink">
          {label}
        </label>
        <input
          id={id}
          className={inputClass}
          aria-invalid={!!errors[errorKey]}
          aria-describedby={errors[errorKey] ? `${id}-error` : undefined}
          {...props}
        />
        {errors[errorKey] && (
          <p id={`${id}-error`} role="alert" className="mt-1 text-sm text-destructive">
            {errors[errorKey]}
          </p>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      <h3 className="text-lg font-bold text-navy">{heading}</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        {field("lead-name", "Name *", {
          value: values.name,
          onChange: (e) => setValues((v) => ({ ...v, name: e.target.value })),
          autoComplete: "name",
          required: true,
        }, "name")}
        {field("lead-phone", "Phone *", {
          value: values.phone,
          onChange: (e) => setValues((v) => ({ ...v, phone: e.target.value })),
          type: "tel",
          inputMode: "tel",
          autoComplete: "tel",
          placeholder: "+263 …",
          required: true,
        }, "phone")}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {field("lead-email", "Email (optional)", {
          value: values.email,
          onChange: (e) => setValues((v) => ({ ...v, email: e.target.value })),
          type: "email",
          autoComplete: "email",
        }, "email")}
        {field("lead-address", "Address (optional)", {
          value: values.address,
          onChange: (e) => setValues((v) => ({ ...v, address: e.target.value })),
          autoComplete: "street-address",
        }, "address")}
      </div>

      <div>
        <label htmlFor="lead-consent" className="flex items-start gap-3 text-sm text-ink/80">
          <input
            id="lead-consent"
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            aria-invalid={!!errors.consent}
            aria-describedby={errors.consent ? "lead-consent-error" : undefined}
            className="mt-0.5 h-5 w-5 shrink-0 rounded border-input accent-navy"
          />
          <span>
            I consent to FibreHood storing my details so the team can respond to this
            request. See the{" "}
            <Link to="/privacy" className="font-semibold text-navy underline underline-offset-4">
              privacy policy
            </Link>
            . *
          </span>
        </label>
        {errors.consent && (
          <p id="lead-consent-error" role="alert" className="mt-1 text-sm text-destructive">
            {errors.consent}
          </p>
        )}
      </div>

      {formError && (
        <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm font-medium text-destructive">
          {formError}
        </p>
      )}

      <Button
        type="submit"
        disabled={submitting}
        className="h-12 w-full bg-navy text-base font-bold text-white hover:bg-navy-600 sm:w-auto sm:px-8"
      >
        {submitting ? "Sending…" : submitLabel}
      </Button>
    </form>
  );
}
