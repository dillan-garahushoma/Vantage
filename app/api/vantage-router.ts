import { z } from "zod";
import { desc, eq, like, or, and, gte, sql } from "drizzle-orm";
import { createRouter, publicQuery, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import {
  announcements,
  complaints,
  properties,
  serviceProviders,
  users,
} from "../db/schema";
import { computeLivingScore } from "./queries/livingScore";
import { COMPLAINT_CATEGORIES, COMPLAINT_STATUSES, USER_ROLES } from "@contracts/constants";
import { TRPCError } from "@trpc/server";

const ADMIN_ROLES = ["hoa_admin", "admin"] as const;

function requireHoa(role: string) {
  if (!(ADMIN_ROLES as readonly string[]).includes(role)) {
    throw new TRPCError({ code: "FORBIDDEN", message: "HOA admin access required" });
  }
}

export const vantageRouter = createRouter({
  // ---- Role selection (MVP: user picks their role after sign-in) ----
  setRole: authedQuery
    .input(z.object({ role: z.enum(USER_ROLES) }))
    .mutation(async ({ ctx, input }) => {
      const db = getDb();
      await db.update(users).set({ role: input.role }).where(eq(users.id, ctx.user.id));
      return { success: true, role: input.role };
    }),

  // ---- Properties / valuation ----
  searchProperties: publicQuery
    .input(z.object({ query: z.string().min(1) }))
    .query(async ({ input }) => {
      const db = getDb();
      const q = `%${input.query}%`;
      return db
        .select()
        .from(properties)
        .where(or(like(properties.address, q), like(properties.suburb, q), like(properties.estateName, q)))
        .limit(10);
    }),

  listProperties: publicQuery.query(async () => {
    const db = getDb();
    return db.select().from(properties).limit(50);
  }),

  propertyValuation: publicQuery
    .input(z.object({ propertyId: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const [prop] = await db.select().from(properties).where(eq(properties.id, input.propertyId));
      if (!prop) throw new TRPCError({ code: "NOT_FOUND", message: "Property not found" });
      const living = await computeLivingScore(prop.estateName);
      // AI valuation: baseline adjusted by Living Score (±12% band around 60 baseline)
      const adjustment = (living.score - 60) / 100;
      const estimatedValue = Math.round(prop.baseValue * (1 + adjustment * 0.3));
      const annualYield = 0.055 + (living.score - 50) * 0.0004;
      const roi10yr = Math.round(
        prop.baseValue * (Math.pow(1 + 0.045 + adjustment * 0.03, 10) - 1) +
          estimatedValue * annualYield * 10,
      );
      return {
        property: prop,
        livingScore: living,
        estimatedValue,
        rentalYieldPct: Math.round(annualYield * 1000) / 10,
        roi10yr,
        explainers: [
          `Baseline market value R ${prop.baseValue.toLocaleString()} for ${prop.propertyType} in ${prop.suburb}.`,
          `Living Score of ${living.score}/100 ${living.score >= 60 ? "adds" : "subtracts"} a ${Math.abs(Math.round(adjustment * 30))}% community-health ${living.score >= 60 ? "premium" : "discount"}.`,
          `Rental yield estimate reflects estate desirability at current score.`,
        ],
      };
    }),

  // ---- Living Score ----
  livingScore: publicQuery
    .input(z.object({ estateName: z.string().min(1) }))
    .query(({ input }) => computeLivingScore(input.estateName)),

  complaintTrend: publicQuery
    .input(z.object({ estateName: z.string().min(1) }))
    .query(async ({ input }) => {
      const db = getDb();
      const since = new Date(Date.now() - 180 * 86400000);
      const rows = await db
        .select({
          month: sql<string>`DATE_FORMAT(${complaints.createdAt}, '%Y-%m')`,
          count: sql<number>`COUNT(*)`,
          resolved: sql<number>`SUM(CASE WHEN ${complaints.resolvedAt} IS NOT NULL THEN 1 ELSE 0 END)`,
        })
        .from(complaints)
        .where(and(eq(complaints.estateName, input.estateName), gte(complaints.createdAt, since)))
        .groupBy(sql`DATE_FORMAT(${complaints.createdAt}, '%Y-%m')`)
        .orderBy(sql`DATE_FORMAT(${complaints.createdAt}, '%Y-%m')`);
      return rows;
    }),

  // ---- Complaints ----
  createComplaint: authedQuery
    .input(
      z.object({
        title: z.string().min(3).max(255),
        description: z.string().max(2000).optional(),
        category: z.enum(COMPLAINT_CATEGORIES),
        estateName: z.string().min(1),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const db = getDb();
      const [result] = await db.insert(complaints).values({
        userId: ctx.user.id,
        title: input.title,
        description: input.description,
        category: input.category,
        estateName: input.estateName,
      });
      return { success: true, id: result.insertId };
    }),

  myComplaints: authedQuery.query(async ({ ctx }) => {
    const db = getDb();
    return db
      .select()
      .from(complaints)
      .where(eq(complaints.userId, ctx.user.id))
      .orderBy(desc(complaints.createdAt))
      .limit(50);
  }),

  allComplaints: authedQuery
    .input(z.object({ estateName: z.string().optional() }).optional())
    .query(async ({ ctx, input }) => {
      requireHoa(ctx.user.role);
      const db = getDb();
      const where = input?.estateName ? eq(complaints.estateName, input.estateName) : undefined;
      return db.select().from(complaints).where(where).orderBy(desc(complaints.createdAt)).limit(100);
    }),

  updateComplaintStatus: authedQuery
    .input(z.object({ id: z.number(), status: z.enum(COMPLAINT_STATUSES) }))
    .mutation(async ({ ctx, input }) => {
      requireHoa(ctx.user.role);
      const db = getDb();
      const resolvedAt = input.status === "resolved" || input.status === "closed" ? new Date() : null;
      await db
        .update(complaints)
        .set({ status: input.status, ...(resolvedAt ? { resolvedAt } : {}) })
        .where(eq(complaints.id, input.id));
      return { success: true };
    }),

  assignComplaint: authedQuery
    .input(z.object({ id: z.number(), providerId: z.number() }))
    .mutation(async ({ ctx, input }) => {
      requireHoa(ctx.user.role);
      const db = getDb();
      await db
        .update(complaints)
        .set({ providerId: input.providerId, status: "assigned" })
        .where(eq(complaints.id, input.id));
      return { success: true };
    }),

  rateComplaint: authedQuery
    .input(z.object({ id: z.number(), rating: z.number().min(1).max(5) }))
    .mutation(async ({ ctx, input }) => {
      const db = getDb();
      const [row] = await db.select().from(complaints).where(eq(complaints.id, input.id));
      if (!row || row.userId !== ctx.user.id) {
        throw new TRPCError({ code: "FORBIDDEN", message: "Not your complaint" });
      }
      await db.update(complaints).set({ rating: input.rating, status: "closed" }).where(eq(complaints.id, input.id));
      return { success: true };
    }),

  // ---- Announcements ----
  listAnnouncements: publicQuery
    .input(z.object({ estateName: z.string().optional() }).optional())
    .query(async ({ input }) => {
      const db = getDb();
      const where = input?.estateName ? eq(announcements.estateName, input.estateName) : undefined;
      return db.select().from(announcements).where(where).orderBy(desc(announcements.createdAt)).limit(20);
    }),

  createAnnouncement: authedQuery
    .input(z.object({ title: z.string().min(3).max(255), content: z.string().min(3), estateName: z.string().min(1) }))
    .mutation(async ({ ctx, input }) => {
      requireHoa(ctx.user.role);
      const db = getDb();
      await db.insert(announcements).values({ ...input, authorId: ctx.user.id });
      return { success: true };
    }),

  // ---- Service providers ----
  listProviders: publicQuery.query(async () => {
    const db = getDb();
    return db.select().from(serviceProviders).orderBy(desc(serviceProviders.rating));
  }),

  verifyProvider: authedQuery
    .input(z.object({ id: z.number(), verified: z.boolean() }))
    .mutation(async ({ ctx, input }) => {
      requireHoa(ctx.user.role);
      const db = getDb();
      await db.update(serviceProviders).set({ verified: input.verified }).where(eq(serviceProviders.id, input.id));
      return { success: true };
    }),
});
