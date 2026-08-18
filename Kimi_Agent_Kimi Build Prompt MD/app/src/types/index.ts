export type CoverageStatus = "covered" | "near_coverage" | "not_covered" | "unknown";

export type Coordinates = { lat: number; lon: number };

export interface Provider {
  id: string;
  name: string;
  slug: string;
  /** true while this is development placeholder content */
  placeholder: boolean;
}

export interface Plan {
  id: string;
  providerId: string;
  name: string;
  downloadMbps: number;
  uploadMbps: number;
  /** null = price not yet confirmed; UI renders "Price on request" */
  monthlyPriceCents: number | null;
  currency: string;
  contractMonths: number | null;
  installationFeeCents: number | null;
  features: string[];
  placeholder: boolean;
}

export interface CoverageResult {
  status: Exclude<CoverageStatus, "unknown">;
  providers: Provider[];
  plans: Plan[];
  matchedPolygonId?: string;
  matchedPolygonName?: string;
  coverageVersion?: number;
  distanceM?: number;
  coordinates?: Coordinates;
  queriedAddress?: string;
  /** true while coverage data is mock development data */
  mock: boolean;
}

export interface LeadInput {
  name: string;
  phone: string;
  email?: string;
  address?: string;
  planId?: string;
  source: "coverage_check" | "plans_page" | "contact_form" | "coverage_request" | "survey_request";
  consent: boolean;
  coverageStatus?: CoverageStatus;
  lat?: number;
  lon?: number;
  utm?: Record<string, string>;
}

export interface Lead extends LeadInput {
  id: string;
  createdAt: string;
}

export type LeadResult = { ok: true; leadId: string } | { ok: false; error: string };
