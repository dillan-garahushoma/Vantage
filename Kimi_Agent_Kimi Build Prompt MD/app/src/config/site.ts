/**
 * Centralized site & brand configuration.
 * Replace values here — components must not hard-code business facts.
 * Anything marked `confirmed: false` is an unverified placeholder pending
 * confirmation by the business (see FibreHood-research.md open questions).
 */
export const site = {
  name: "FibreHood",
  domain: "fibrehood.co.zw", // currently reported suspended — confirm ownership
  tagline: "Fibre connectivity built for Zimbabwe",
  description:
    "FibreHood builds fibre connectivity for homes, buildings and businesses in Zimbabwe. Check whether fibre is available at your address and discover the plans available to you.",

  brand: {
    navy: "#072248",
    yellow: "#FFCC00",
    background: "#F7F9FB",
    neutral: "#ECEFF4",
    text: "#0B1B2A",
  },

  whatsapp: {
    // Referenced in research (+263 78 071 1337) — REQUIRES CONFIRMATION before launch.
    numberE164: "263780711337",
    display: "+263 78 071 1337",
    confirmed: false as const,
    defaultMessage: "Hi FibreHood, I'd like to enquire about fibre connectivity." as string,
  },

  contact: {
    // No verified public email/phone beyond the WhatsApp reference above.
    email: null as string | null,
    phone: null as string | null,
    address: null as string | null,
  },

  /**
   * Open-access model and partner ISP names are UNVERIFIED (research open
   * questions). Keep this flag false until the business confirms the claim,
   * then provider names can replace the placeholders in lib/mock.
   */
  openAccessClaimConfirmed: false as const,

  /**
   * When true, plan/provider data shown on the site is clearly-labelled
   * development placeholder content, not real pricing.
   */
  usingPlaceholderPlans: true as const,

  /**
   * Real coverage data (KML/GeoJSON/shapefile/address list) has not been
   * supplied yet. The coverage checker currently runs against clearly
   * labelled mock development polygons.
   */
  usingMockCoverage: true as const,
} as const;

export type SiteConfig = typeof site;
