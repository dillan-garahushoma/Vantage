import type { Provider } from "@/types";

/**
 * MOCK development fixtures — NOT real partner data.
 * The two partner ISPs referenced in the PRD are unnamed (research open
 * question). Replace these with real providers via plansService once confirmed.
 */
export const mockProviders: Provider[] = [
  { id: "prov-placeholder-a", name: "Provider A (placeholder)", slug: "provider-a", placeholder: true },
  { id: "prov-placeholder-b", name: "Provider B (placeholder)", slug: "provider-b", placeholder: true },
];
