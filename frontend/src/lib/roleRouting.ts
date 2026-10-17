/**
 * Where a signed-in person belongs, decided from server-resolved memberships.
 *
 * The rules come straight from the onboarding design, and they are deliberately a
 * pure function so they can be tested without a router, a DOM or a network:
 *
 * * an estate administrator lands on the setup checklist for their estate;
 * * a resident with no estate yet goes to the request-access screen, where they
 *   ask to join a unit and an administrator approves it (a join code remains an
 *   alternative the estate office can hand out);
 * * a service provider with no estate waits on the "an HOA adds you by email"
 *   screen, because no amount of self-service can add them;
 * * anybody with an estate they can act in gets the dashboard.
 *
 * `role` alone is never enough: the estate outcome is decided by membership, which
 * only the server can resolve.
 */
import type { CurrentUser, EstateAccess } from './types'

export type HomeRoute = '/app' | '/admin/setup' | '/join' | '/request-access' | '/provider/waiting'

export function homeRouteFor(user: CurrentUser | null, estates: EstateAccess[]): HomeRoute {
  if (!user) return '/join'

  if (estates.length === 0) {
    if (user.role === 'service_provider') return '/provider/waiting'
    // Approval is the default resident path; a join code stays available from the
    // estate office and is reachable from that screen.
    return user.role === 'resident' ? '/request-access' : '/join'
  }

  if (estates.some((estate) => estate.is_estate_admin)) return '/admin/setup'
  return '/app'
}
