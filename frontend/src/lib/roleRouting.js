export function homeRouteFor(user, estates) {
    if (!user)
        return '/join';
    if (estates.length === 0) {
        if (user.role === 'service_provider')
            return '/provider/waiting';
        // Approval is the default resident path; a join code stays available from the
        // estate office and is reachable from that screen.
        return user.role === 'resident' ? '/request-access' : '/join';
    }
    if (estates.some((estate) => estate.is_estate_admin))
        return '/admin/setup';
    return '/app';
}
