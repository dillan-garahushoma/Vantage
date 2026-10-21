import { Activity, Boxes, Building2, HardHat, HeartHandshake, LayoutDashboard, Megaphone, Settings, ShieldAlert, Sparkles, UserCheck, Users, Wallet, Wrench, } from 'lucide-react';
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
                to: '/app/assets',
                label: 'Assets & infrastructure',
                icon: Boxes,
                hint: 'Plant equipment, spatial map & operational assets',
            },
            {
                to: '/app/properties',
                label: 'Residential units',
                icon: Building2,
                roles: ['resident', 'hoa_admin', 'investor', 'estate_agent'],
                hint: 'Registered homes and the estate property roll',
            },
            {
                to: '/app/property-workflows',
                label: 'Property & investment',
                icon: Building2,
                roles: ['resident', 'hoa_admin', 'investor', 'estate_agent'],
                hint: 'Units, listings, sale requests and investment capabilities',
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
                to: '/provider/portal',
                label: 'Provider portal',
                icon: HardHat,
                roles: ['service_provider', 'hoa_admin'],
                hint: 'Check-in, photo evidence and contractor jobs',
            },
            {
                to: '/app/incidents',
                label: 'Incidents & security',
                icon: ShieldAlert,
                roles: ['resident', 'hoa_admin', 'investor', 'estate_agent'],
                hint: 'Security and safety incidents on record',
            },
        ],
    },
    {
        label: 'Governance',
        items: [
            {
                to: '/app/financial',
                label: 'Financial & service',
                icon: Wallet,
                roles: ['hoa_admin', 'investor'],
                hint: 'Budget variance, levy collection and capital reserves',
            },
            {
                to: '/app/community',
                label: 'Resident experience',
                icon: HeartHandshake,
                roles: ['resident', 'hoa_admin'],
                hint: 'Satisfaction pulse, service themes and sentiment',
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
