/**
 * Where a signed-in person belongs, decided from server-resolved memberships.
 *
 * The rules come straight from the onboarding design, and they are deliberately a
 * pure function so they can be tested without a router, a DOM or a network:
 *
 * * an estate administrator lands on the setup checklist for their estate;
 * * a resident with no estate yet goes to the join screen (a code plus a unit);
 * * a service provider with no estate waits on the "an HOA adds you by email"
 *   screen, because no amount of self-service can add them;
 * * anybody with an estate they can act in gets the dashboard.
 *
 * `role` alone is never enough: the estate outcome is decided by membership, which
 * only the server can resolve.
 */
import type { CurrentUser, EstateAccess } from './types'

export type HomeRoute = '/app' | '/admin/setup' | '/join' | '/provider/waiting'

export function homeRouteFor(user: CurrentUser | null, estates: EstateAccess[]): HomeRoute {
  if (!user) return '/join'

  if (estates.length === 0) {
    if (user.role === 'service_provider') return '/provider/waiting'
    return '/join'
  }

  if (estates.some((estate) => estate.is_estate_admin)) return '/admin/setup'
  return '/app'
}
