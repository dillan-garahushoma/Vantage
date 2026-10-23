/**
 * Where a signed-in person belongs.
 *
 * These rules are what stop the app dropping somebody on a dashboard they cannot
 * read: the destination is derived from server-resolved membership, never from
 * the global role alone.
 */
import { describe, expect, it } from 'vitest';
import { homeRouteFor } from './roleRouting';
function user(role) {
    return {
        id: 1,
        email: 'person@example.co.za',
        full_name: 'Test Person',
        role,
        unit_no: null,
        email_verified: false,
        hoa_approved: false,
    };
}
function estate(overrides = {}) {
    return {
        estate_id: 1,
        estate_name: 'Ridge Close',
        suburb: 'Centurion',
        city: 'Tshwane',
        province: 'Gauteng',
        membership_roles: ['resident'],
        property_ids: [10],
        is_estate_admin: false,
        is_estate_provider: false,
        ...overrides,
    };
}
describe('homeRouteFor', () => {
    it('sends a signed-out visitor to the join screen', () => {
        expect(homeRouteFor(null, [])).toBe('/join');
    });
    it('sends an estate administrator to their setup checklist', () => {
        expect(homeRouteFor(user('hoa_admin'), [estate({ is_estate_admin: true })])).toBe('/admin/setup');
    });
    it('sends a member of an estate to the dashboard', () => {
        expect(homeRouteFor(user('resident'), [estate()])).toBe('/app');
        expect(homeRouteFor(user('investor'), [estate({ membership_roles: ['investor'] })])).toBe('/app');
    });
    it('sends a resident with no estate to request access for approval', () => {
        expect(homeRouteFor(user('resident'), [])).toBe('/request-access');
    });
    it('sends a non-resident with no estate to the join-code screen', () => {
        expect(homeRouteFor(user('investor'), [])).toBe('/join');
    });
    it('sends a provider with no estate to the waiting screen', () => {
        expect(homeRouteFor(user('service_provider'), [])).toBe('/provider/waiting');
    });
    it('sends a provider with an estate to their assigned work, not a resident dashboard', () => {
        expect(homeRouteFor(user('service_provider'), [estate({ is_estate_provider: true })])).toBe('/provider/work');
    });
    it('prefers the administrator view when the person is an admin of one estate among several', () => {
        const estates = [
            estate({ estate_id: 2 }),
            estate({ estate_id: 3, is_estate_admin: true, membership_roles: ['hoa_admin'] }),
        ];
        expect(homeRouteFor(user('hoa_admin'), estates)).toBe('/admin/setup');
    });
    it('never returns the onboarding screen itself, so the redirect cannot loop', () => {
        const cases = [
            [null, []],
            [user('resident'), []],
            [user('investor'), []],
            [user('service_provider'), []],
            [user('hoa_admin'), [estate({ is_estate_admin: true })]],
            [user('resident'), [estate()]],
        ];
        for (const [who, estates] of cases) {
            expect(homeRouteFor(who, estates)).not.toBe('/welcome');
        }
    });
});
