import { Activity, Building2, HardHat, LayoutDashboard, Megaphone, ShieldAlert, Sparkles, UserCheck, Users, Wrench, } from 'lucide-react';
export const navGroups = [
    {
        label: 'Estate',
        items: [
            {
                to: '/app',
                label: 'Overview',
                icon: LayoutDashboard,
                hint: 'Estate health at a glance',
            },
            {
                to: '/app/health',
                label: 'Estate health',
                icon: Activity,
                hint: 'The stored Living Score and its five pillars',
            },
            {
                to: '/app/properties',
                label: 'Residential units',
                icon: Building2,
                roles: ['resident', 'hoa_admin'],
                hint: 'Registered homes and the estate property roll',
            },
            {
                to: '/app/announcements',
                label: 'Announcements',
                icon: Megaphone,
                hint: 'Notices published by the estate',
            },
        ],
    },
    {
        label: 'Operations',
        items: [
            {
                to: '/app/complaints',
                label: 'Maintenance & complaints',
                icon: Wrench,
                roles: ['resident', 'hoa_admin'],
                hint: 'Log an issue and follow it to resolution',
            },
            {
                to: '/app/work-orders',
                label: 'Work orders',
                icon: HardHat,
                roles: ['hoa_admin', 'service_provider'],
                hint: 'Assigned work, its cost and its SLA',
            },
            {
                to: '/provider/work',
                label: 'My work',
                icon: HardHat,
                roles: ['service_provider'],
                hint: 'Jobs assigned to your provider profile',
            },
            {
                to: '/app/incidents',
                label: 'Incidents & security',
                icon: ShieldAlert,
                roles: ['resident', 'hoa_admin'],
                hint: 'Security and safety incidents on record',
            },
        ],
    },
    {
        label: 'Intelligence',
        items: [
            {
                to: '/intelligence',
                label: 'VALORA Intelligence',
                icon: Sparkles,
                accent: true,
                hint: 'This week’s findings, with their evidence',
            },
        ],
    },
    {
        label: 'Network & admin',
        items: [
            {
                to: '/app/providers',
                label: 'Providers',
                icon: Users,
                roles: ['hoa_admin'],
                hint: 'The estate’s service-provider directory',
            },
            {
                to: '/admin/settings',
                label: 'Estate profile & settings',
                icon: Settings,
                roles: ['hoa_admin'],
                hint: 'Rules, methodology and notifications',
            },
            {
                to: '/admin/setup',
                label: 'Estate setup',
                icon: Building2,
                roles: ['hoa_admin'],
                hint: 'Description, units, photographs, publishing',
            },
            {
                to: '/admin/members',
                label: 'Members',
                icon: Users,
                roles: ['hoa_admin'],
                hint: 'Who may act inside this estate',
            },
            {
                to: '/admin/residency',
                label: 'Approvals',
                icon: UserCheck,
                roles: ['hoa_admin'],
                hint: 'Resident registration requests awaiting a decision',
            },
        ],
    },
];
export const allNavItems = navGroups.flatMap((group) => group.items);
/** The destinations the bottom bar carries on a phone. */
export const mobilePrimaryPaths = ['/app', '/app/complaints', '/intelligence', '/app/announcements'];
export function navItemsForRole(role) {
    if (!role)
        return [];
    return allNavItems.filter((item) => !item.roles || item.roles.includes(role));
}
export function navGroupsForRole(role) {
    return navGroups
        .map((group) => ({
        label: group.label,
        items: group.items.filter((item) => !item.roles || (role ? item.roles.includes(role) : false)),
    }))
        .filter((group) => group.items.length > 0);
}
