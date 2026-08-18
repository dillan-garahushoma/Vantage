import { z } from "zod";
import type { Lead, LeadInput, LeadResult } from "@/types";
import { analytics } from "./analytics";

/**
 * Lead service.
 * Backend contract (future): POST /api/v1/leads
 *
 * There is no backend yet: leads are stored in this browser's localStorage
 * only. They are NOT sent to any server and will not sync across devices.
 */

export const leadSchema = z.object({
  name: z.string().trim().min(2, "Please enter your name"),
  phone: z
    .string()
    .trim()
    .min(7, "Please enter a valid phone number")
    .regex(/^[+0-9][0-9\s-]{6,}$/, "Please enter a valid phone number"),
  email: z
    .string()
    .trim()
    .email("Please enter a valid email address")
    .optional()
    .or(z.literal("")),
  address: z.string().trim().optional().or(z.literal("")),
  planId: z.string().optional(),
  source: z.enum([
    "coverage_check",
    "plans_page",
    "contact_form",
    "coverage_request",
    "survey_request",
  ]),
  consent: z.boolean().refine((v) => v === true, "Please consent so we can respond to your request"),
  coverageStatus: z.enum(["covered", "near_coverage", "not_covered", "unknown"]).optional(),
  lat: z.number().optional(),
  lon: z.number().optional(),
  utm: z.record(z.string(), z.string()).optional(),
});

const STORAGE_KEY = "fibrehood.leads.v1";

function readLeads(): Lead[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as Lead[];
  } catch {
    return [];
  }
}

export function collectUtm(): Record<string, string> {
  const params = new URLSearchParams(window.location.search);
  const utm: Record<string, string> = {};
  for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]) {
    const value = params.get(key);
    if (value) utm[key] = value;
  }
  return utm;
}

export const leadService = {
  async create(input: LeadInput): Promise<LeadResult> {
    const parsed = leadSchema.safeParse(input);
    if (!parsed.success) {
      return { ok: false, error: parsed.error.issues[0]?.message ?? "Invalid input" };
    }
    await new Promise((r) => setTimeout(r, 400));
    try {
      const leads = readLeads();
      const lead: Lead = {
        ...parsed.data,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
      };
      leads.push(lead);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(leads));
      analytics.track("lead.created", { source: lead.source, plan_id: lead.planId });
      return { ok: true, leadId: lead.id };
    } catch {
      return {
        ok: false,
        error: "We couldn't save your request in this browser. Please try WhatsApp instead.",
      };
    }
  },
};

export type LeadService = typeof leadService;
