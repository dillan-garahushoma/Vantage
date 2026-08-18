import {
  mysqlTable,
  mysqlEnum,
  serial,
  varchar,
  text,
  timestamp,
  bigint,
  int,
  boolean,
} from "drizzle-orm/mysql-core";

export const users = mysqlTable("users", {
  id: serial("id").primaryKey(),
  unionId: varchar("unionId", { length: 255 }).notNull().unique(),
  name: varchar("name", { length: 255 }),
  email: varchar("email", { length: 320 }),
  avatar: text("avatar"),
  role: mysqlEnum("role", ["resident", "investor", "hoa_admin", "admin"])
    .default("resident")
    .notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt")
    .defaultNow()
    .notNull()
    .$onUpdate(() => new Date()),
  lastSignInAt: timestamp("lastSignInAt").defaultNow().notNull(),
});

export const properties = mysqlTable("properties", {
  id: serial("id").primaryKey(),
  address: varchar("address", { length: 255 }).notNull(),
  suburb: varchar("suburb", { length: 128 }).notNull(),
  estateName: varchar("estateName", { length: 128 }).notNull(),
  propertyType: varchar("propertyType", { length: 64 }).notNull(),
  bedrooms: int("bedrooms").notNull(),
  baseValue: int("baseValue").notNull(), // ZAR, AI baseline valuation
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const complaints = mysqlTable("complaints", {
  id: serial("id").primaryKey(),
  userId: bigint("userId", { mode: "number", unsigned: true }).notNull(),
  estateName: varchar("estateName", { length: 128 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  category: mysqlEnum("category", [
    "security",
    "maintenance",
    "noise",
    "cleanliness",
    "other",
  ])
    .default("other")
    .notNull(),
  status: mysqlEnum("status", [
    "logged",
    "under_review",
    "assigned",
    "in_progress",
    "resolved",
    "closed",
  ])
    .default("logged")
    .notNull(),
  providerId: bigint("providerId", { mode: "number", unsigned: true }),
  rating: int("rating"), // 1-5 resident feedback on resolution
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  resolvedAt: timestamp("resolvedAt"),
});

export const announcements = mysqlTable("announcements", {
  id: serial("id").primaryKey(),
  authorId: bigint("authorId", { mode: "number", unsigned: true }),
  estateName: varchar("estateName", { length: 128 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  content: text("content").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const serviceProviders = mysqlTable("service_providers", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 255 }).notNull(),
  specialty: varchar("specialty", { length: 128 }).notNull(),
  contact: varchar("contact", { length: 255 }),
  verified: boolean("verified").default(false).notNull(),
  rating: int("rating").default(0).notNull(), // 0-50 (display /10)
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type Property = typeof properties.$inferSelect;
export type Complaint = typeof complaints.$inferSelect;
export type Announcement = typeof announcements.$inferSelect;
export type ServiceProvider = typeof serviceProviders.$inferSelect;
