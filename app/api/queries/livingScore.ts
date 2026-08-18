import { and, gte, eq } from "drizzle-orm";
import { getDb } from "./connection";
import { complaints } from "../../db/schema";
import type { ScoreComponentKey } from "@contracts/constants";

export type ScoreBreakdown = Record<
  ScoreComponentKey,
  { score: number; explanation: string }
>;

export interface LivingScoreResult {
  score: number;
  breakdown: ScoreBreakdown;
  avgResolutionDays: number;
  complaintsLast90d: number;
  windowDays: number;
}

function clamp(n: number) {
  return Math.max(0, Math.min(100, Math.round(n)));
}

/**
 * 90-day rolling Living Score (0-100).
 * Components: resolution time, complaint frequency, security incidents,
 * resident satisfaction, maintenance resolution rate.
 */
export async function computeLivingScore(
  estateName: string,
): Promise<LivingScoreResult> {
  const db = getDb();
  const since = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000);
  const rows = await db
    .select()
    .from(complaints)
    .where(and(eq(complaints.estateName, estateName), gte(complaints.createdAt, since)));

  const total = rows.length;
  const resolved = rows.filter((c) => c.resolvedAt);
  const resolutionDays = resolved.map(
    (c) => (c.resolvedAt!.getTime() - c.createdAt.getTime()) / 86400000,
  );
  const avgResolutionDays =
    resolutionDays.length > 0
      ? resolutionDays.reduce((a, b) => a + b, 0) / resolutionDays.length
      : 0;
  const securityIncidents = rows.filter((c) => c.category === "security").length;
  const ratings = rows.filter((c) => c.rating != null).map((c) => c.rating!);
  const avgRating =
    ratings.length > 0 ? ratings.reduce((a, b) => a + b, 0) / ratings.length : null;
  const maintenanceRows = rows.filter((c) => c.category === "maintenance");
  const maintenanceResolved = maintenanceRows.filter((c) => c.resolvedAt).length;

  const perMonth = total / 3;

  const resolutionScore = clamp(100 - Math.max(0, avgResolutionDays - 3) * (100 / 11));
  const frequencyScore = clamp(100 - perMonth * 10);
  const securityScore = clamp(100 - securityIncidents * 15);
  const satisfactionScore =
    avgRating == null ? 70 : clamp(((avgRating - 1) / 4) * 100);
  const maintenanceScore =
    maintenanceRows.length === 0
      ? 90
      : clamp((maintenanceResolved / maintenanceRows.length) * 100);

  const breakdown: ScoreBreakdown = {
    resolutionTime: {
      score: resolutionScore,
      explanation:
        resolved.length === 0
          ? "No complaints resolved in the last 90 days to measure."
          : `Average resolution time is ${avgResolutionDays.toFixed(1)} days (target: 3 days).`,
    },
    complaintFrequency: {
      score: frequencyScore,
      explanation: `${total} complaints logged in 90 days (~${perMonth.toFixed(1)}/month).`,
    },
    security: {
      score: securityScore,
      explanation:
        securityIncidents === 0
          ? "No security incidents reported in 90 days."
          : `Score reduced by ${securityIncidents} recent security incident${securityIncidents > 1 ? "s" : ""}.`,
    },
    satisfaction: {
      score: satisfactionScore,
      explanation:
        avgRating == null
          ? "No resident ratings yet — neutral baseline applied."
          : `Residents rate resolutions ${avgRating.toFixed(1)}/5 on average.`,
    },
    maintenance: {
      score: maintenanceScore,
      explanation:
        maintenanceRows.length === 0
          ? "No maintenance issues reported in 90 days."
          : `${maintenanceResolved} of ${maintenanceRows.length} maintenance issues resolved.`,
    },
  };

  const score = clamp(
    resolutionScore * 0.25 +
      frequencyScore * 0.2 +
      securityScore * 0.2 +
      satisfactionScore * 0.2 +
      maintenanceScore * 0.15,
  );

  return {
    score,
    breakdown,
    avgResolutionDays: Math.round(avgResolutionDays * 10) / 10,
    complaintsLast90d: total,
    windowDays: 90,
  };
}
