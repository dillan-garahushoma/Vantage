import type { Coordinates, CoverageResult } from "@/types";
import {
  MOCK_COVERAGE_VERSION,
  haversineM,
  mockAddressBook,
  mockPolygons,
  pointInRing,
  ringCentroid,
} from "@/lib/mock/coverage";
import { mockProviders } from "@/lib/mock/providers";
import { mockPlans } from "@/lib/mock/plans";
import { analytics } from "./analytics";

/**
 * Coverage service.
 *
 * Backend contract (future):
 *   GET /api/v1/coverage/lookup?address=
 *   GET /api/v1/coverage/lookup?lat=&lon=
 *
 * For now this resolves against clearly-labelled MOCK development polygons.
 * UI components must depend on this interface only — never on mock files.
 */

export class UnknownAddressError extends Error {
  readonly address: string;
  constructor(address: string) {
    super(`Could not verify address: ${address}`);
    this.address = address;
  }
}

const NETWORK_DELAY_MS = 500;
const NEAR_COVERAGE_THRESHOLD_M = 800;

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function plansForPolygon(_polygonId: string) {
  // With real data, the backend returns the providers serving the matched
  // polygon and their plans. In mock mode all placeholder providers serve
  // every mock polygon.
  return { providers: mockProviders, plans: mockPlans };
}

function buildResult(
  status: CoverageResult["status"],
  coordinates: Coordinates | undefined,
  queriedAddress: string | undefined,
  matched?: (typeof mockPolygons)[number],
  distanceM?: number,
): CoverageResult {
  const { providers, plans } =
    status === "covered" || status === "near_coverage"
      ? plansForPolygon(matched?.id ?? "")
      : { providers: [], plans: [] };
  return {
    status,
    providers,
    plans,
    matchedPolygonId: matched?.id,
    matchedPolygonName: matched?.name,
    coverageVersion: MOCK_COVERAGE_VERSION,
    distanceM,
    coordinates,
    queriedAddress,
    mock: true,
  };
}

function evaluatePoint(point: Coordinates, queriedAddress?: string): CoverageResult {
  for (const polygon of mockPolygons) {
    if (pointInRing(point.lon, point.lat, polygon.ring)) {
      return buildResult("covered", point, queriedAddress, polygon);
    }
  }
  // Near coverage: distance to nearest polygon centroid (mock approximation
  // of the future PostGIS ST_DWithin query).
  let nearest: (typeof mockPolygons)[number] | undefined;
  let nearestM = Infinity;
  for (const polygon of mockPolygons) {
    const d = haversineM(point, ringCentroid(polygon.ring));
    if (d < nearestM) {
      nearestM = d;
      nearest = polygon;
    }
  }
  if (nearest && nearestM <= NEAR_COVERAGE_THRESHOLD_M) {
    return buildResult("near_coverage", point, queriedAddress, nearest, Math.round(nearestM));
  }
  return buildResult("not_covered", point, queriedAddress);
}

export const coverageService = {
  /** GET /api/v1/coverage/lookup?address= */
  async lookupByAddress(address: string): Promise<CoverageResult> {
    analytics.track("coverageCheck.start", { source: "address" });
    await delay(NETWORK_DELAY_MS);
    const query = address.trim().toLowerCase();
    if (query.length < 3) {
      throw new UnknownAddressError(address);
    }
    const match = mockAddressBook.find((entry) =>
      entry.keywords.some((k) => query.includes(k)),
    );
    if (!match) {
      throw new UnknownAddressError(address);
    }
    const result = evaluatePoint(match.coordinates, match.label);
    analytics.track("coverageCheck.result", {
      status: result.status,
      provider_count: result.providers.length,
    });
    return result;
  },

  /** GET /api/v1/coverage/lookup?lat=&lon= */
  async lookupByCoordinates(coords: Coordinates): Promise<CoverageResult> {
    analytics.track("coverageCheck.start", { source: "map_pin" });
    await delay(NETWORK_DELAY_MS);
    const result = evaluatePoint(coords);
    analytics.track("coverageCheck.result", {
      status: result.status,
      provider_count: result.providers.length,
    });
    return result;
  },

  /** Polygons for map display (mock development data). */
  async getCoveragePolygons() {
    return mockPolygons;
  },
};

export type CoverageService = typeof coverageService;
