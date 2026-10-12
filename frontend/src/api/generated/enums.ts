/**
 * GENERATED FILE — DO NOT EDIT.
 *
 * Source: docs/openapi.json (the backend is the single source of truth).
 * Regenerate: npm run gen:api   ·   Verify: npm run check:api
 */

export const complaintCategories = ['water', 'electrical', 'security', 'noise', 'infrastructure', 'gardens', 'waste', 'parking', 'administrative', 'other'] as const
export type ComplaintCategory = (typeof complaintCategories)[number]

export const complaintPriorities = ['low', 'normal', 'high', 'urgent'] as const
export type ComplaintPriority = (typeof complaintPriorities)[number]

export const triageCategories = ['water', 'electrical', 'security', 'noise', 'infrastructure', 'gardens', 'waste', 'parking', 'administrative', 'other'] as const
export type TriageCategory = (typeof triageCategories)[number]

export const triagePriorities = ['low', 'normal', 'high', 'urgent'] as const
export type TriagePriority = (typeof triagePriorities)[number]

export const triageTrades = ['plumber', 'electrician', 'security', 'landscaping', 'general_maintenance', 'pest_control', 'roofing', 'other'] as const
export type TriageTrade = (typeof triageTrades)[number]

export const triageDecisions = ['accepted', 'overridden', 'dismissed'] as const
export type TriageDecision = (typeof triageDecisions)[number]
