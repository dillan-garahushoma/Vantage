/** Response shapes, mirroring the FastAPI schemas in backend/app. */

export type UserRole =
  | 'casual_visitor'
  | 'resident'
  | 'investor'
  | 'estate_agent'
  | 'hoa_admin'
  | 'service_provider'

export interface CurrentUser {
  id: number
  email: string
  full_name: string
  role: UserRole
  unit_no: string | null
  email_verified: boolean
  hoa_approved: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: CurrentUser
}

export interface EstateAccess {
  estate_id: number
  estate_name: string
  suburb: string
  city: string
  province: string
  membership_roles: string[]
  property_ids: number[]
  is_estate_admin: boolean
  is_estate_provider: boolean
}

export interface EstateAccessList {
  estates: EstateAccess[]
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export type ComplaintStatus =
  | 'submitted'
  | 'reviewed'
  | 'assigned'
  | 'in_progress'
  | 'resolved'
  | 'rated'
  | 'closed'

export interface Complaint {
  id: number
  user_id: number | null
  estate_id: number | null
  unit_id: number
  category: string
  description: string
  priority: string
  is_anonymous: boolean | null
  status: ComplaintStatus | null
  assigned_to: string | null
  reviewed_at: string | null
  assigned_at: string | null
  started_at: string | null
  resolved_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ComplaintEvent {
  id: number
  actor_user_id: number | null
  event_type: string
  from_status: string | null
  to_status: string | null
  note: string | null
  occurred_at: string
}

export interface ComplaintStats {
  total: number
  by_status: Record<string, number>
  by_category: Record<string, number>
  resolution_rate_pct: string
  avg_resolution_hours: string | null
}

export type WorkOrderStatus = 'assigned' | 'in_progress' | 'completed' | 'cancelled'

export interface WorkOrder {
  id: number
  complaint_id: number
  provider_id: number
  assigned_at: string | null
  resolved_at: string | null
  job_cost: string | null
  resident_rating: number | null
  completion_notes: string | null
  status: WorkOrderStatus | null
  estimated_completion_date: string | null
  actual_completion_date: string | null
  created_at: string | null
  updated_at: string | null
}

export interface Announcement {
  id: number
  estate_id: number | null
  title: string
  message: string
  created_by: number
  expires_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface Property {
  id: number
  estate_id: number | null
  unit_no: string
  complex_name: string
  street_address: string
  suburb: string | null
  size_m2: string | null
  bedrooms: number | null
  bathrooms: number | null
}

/**
 * A security incident: the Living Score's security input.
 *
 * `category`, `severity` and `status` are the backend's controlled vocabulary,
 * kept as strings here because the contract publishes them as `Literal` unions
 * rather than an enum the runtime can read. They are always rendered through
 * `displayLabel`/`StatusChip`, never compared against a hand-typed list.
 */
export interface Incident {
  id: number
  estate_id: number
  category: string
  severity: string
  status: string
  occurred_at: string
  resolved_at: string | null
  /** Null for everyone who is not an estate administrator. */
  property_id: number | null
  resolution_notes: string | null
  created_by: number | null
  created_at: string | null
  updated_at: string | null
}

export interface ServiceProvider {
  id: number
  full_name: string
  trade: string
  phone: string
  email: string
  avg_rating: string | null
  total_reviews: number | null
  verified: boolean
  emergency_available: boolean
}
