export const Session = {
  cookieName: "kimi_sid",
  maxAgeMs: 365 * 24 * 60 * 60 * 1000,
} as const;

export const ErrorMessages = {
  unauthenticated: "Authentication required",
  insufficientRole: "Insufficient permissions",
} as const;

export const Paths = {
  login: "/login",
  oauthCallback: "/api/oauth/callback",
} as const;

export const COMPLAINT_STATUSES = [
  "logged",
  "under_review",
  "assigned",
  "in_progress",
  "resolved",
  "closed",
] as const;
export type ComplaintStatus = (typeof COMPLAINT_STATUSES)[number];

export const COMPLAINT_STATUS_LABELS: Record<ComplaintStatus, string> = {
  logged: "Logged",
  under_review: "Under Review",
  assigned: "Assigned",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

export const COMPLAINT_CATEGORIES = [
  "security",
  "maintenance",
  "noise",
  "cleanliness",
  "other",
] as const;
export type ComplaintCategory = (typeof COMPLAINT_CATEGORIES)[number];

export const USER_ROLES = ["resident", "investor", "hoa_admin"] as const;
export type UserRole = (typeof USER_ROLES)[number];

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  resident: "Resident",
  investor: "Investor",
  hoa_admin: "HOA Admin",
};

export const SCORE_COMPONENTS = [
  { key: "resolutionTime", label: "Resolution Time", weight: 0.25 },
  { key: "complaintFrequency", label: "Complaint Frequency", weight: 0.2 },
  { key: "security", label: "Security", weight: 0.2 },
  { key: "satisfaction", label: "Satisfaction", weight: 0.2 },
  { key: "maintenance", label: "Maintenance", weight: 0.15 },
] as const;
export type ScoreComponentKey = (typeof SCORE_COMPONENTS)[number]["key"];
