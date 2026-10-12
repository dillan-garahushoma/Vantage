/**
 * The generated contract, with readable names.
 *
 * Nothing here is hand-written: every type is read out of
 * `src/api/generated/schema.d.ts`, which `npm run gen:api` produces from
 * `docs/openapi.json`. That is the whole point — a field renamed in the backend
 * breaks this file at typecheck time instead of silently dropping out of a screen.
 * `npm run check:api` fails the build when the generated files are stale.
 */
import type { components } from '../api/generated/schema'

type Schemas = components['schemas']

/* ------------------------------------------------------------------ public */

export type PublicEstateListItem = Schemas['PublicEstateListItem']
export type PublicEstateDetail = Schemas['PublicEstateDetailResponse']
export type PublicPhoto = Schemas['PublicPhotoResponse']
export type PublicLivingScoreSummary = Schemas['PublicLivingScoreSummary']
export type PublicEstatePage = Schemas['Page_PublicEstateListItem_']

/* ------------------------------------------------------------ estate admin */

export type EstateProfile = Schemas['EstateProfileResponse']
export type EstatePhoto = Schemas['EstatePhotoResponse']
export type EstateMember = Schemas['MembershipResponse']
export type EstateMemberPage = Schemas['Page_MembershipResponse_']
export type JoinCode = Schemas['JoinCodeResponse']
export type JoinResult = Schemas['MembershipJoinResponse']
export type ServiceProvider = Schemas['ServiceProviderResponse']
export type ServiceProviderPage = Schemas['Page_ServiceProviderResponse_']

/* ----------------------------------------------------- living score (stored) */

export type LivingScoreSnapshot = Schemas['LivingScoreSnapshotResponse']
export type LivingScoreComponent = Schemas['LivingScoreComponentResponse']

/* ----------------------------------------------------------- work / orders */

export type WorkOrder = Schemas['WorkOrderResponse']
export type WorkOrderPage = Schemas['Page_WorkOrderResponse_']

/* -------------------------------------------------------------- onboarding */

export type RegisterRequest = Schemas['RegisterRequest']
export type EstateSignup = Schemas['EstateSignup']
export type ProviderSignup = Schemas['ProviderSignup']
export type AuthResponse = Schemas['AuthResponse']
