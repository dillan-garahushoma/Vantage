import { mockPlans } from "@/lib/mock/plans";
import { mockProviders } from "@/lib/mock/providers";
import type { Plan, Provider } from "@/types";

/**
 * Plans service.
 * Backend contract (future): GET /api/v1/plans
 * Currently serves clearly-labelled placeholder fixtures.
 */
export const plansService = {
  async listPlans(): Promise<Plan[]> {
    await new Promise((r) => setTimeout(r, 150));
    return mockPlans;
  },

  async listProviders(): Promise<Provider[]> {
    return mockProviders;
  },

  providerById(id: string): Provider | undefined {
    return mockProviders.find((p) => p.id === id);
  },
};
