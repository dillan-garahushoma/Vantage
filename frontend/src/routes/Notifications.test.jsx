import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Notifications } from './Notifications';

const mocks = vi.hoisted(() => ({
    notifications: vi.fn(),
    markRead: vi.fn(),
    preferences: vi.fn(),
    updatePreferences: vi.fn(),
}));

vi.mock('../lib/accountSupport', () => ({
    listNotifications: mocks.notifications,
    markNotificationRead: mocks.markRead,
    getNotificationPreferences: mocks.preferences,
    updateNotificationPreferences: mocks.updatePreferences,
}));
vi.mock('../context/EstateContext', () => ({
    useEstateScope: () => ({ estateId: 4, estate: { estate_id: 4, estate_name: 'Ridge Close' } }),
    useEstate: () => ({ loading: false, error: null, awaitingProvisioning: false, reload: vi.fn() }),
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 1, role: 'resident' } }),
}));

function notification(overrides = {}) {
    return {
        id: 17,
        estate_id: 4,
        kind: 'work_order_completed',
        resource_id: 42,
        created_at: '2026-10-22T10:30:00Z',
        read_at: null,
        ...overrides,
    };
}

beforeEach(() => {
    mocks.notifications.mockReset();
    mocks.markRead.mockReset();
    mocks.preferences.mockReset();
    mocks.updatePreferences.mockReset();
    mocks.notifications.mockResolvedValue({ items: [notification()], total: 1, page: 1, size: 50, pages: 1 });
    mocks.preferences.mockResolvedValue({ maintenance_notifications: true });
});

describe('Notifications', () => {
    it('shows only the active estate’s operational notices and can mark one read', async () => {
        mocks.markRead.mockResolvedValue(notification({ read_at: '2026-10-22T11:00:00Z' }));
        const user = userEvent.setup();
        render(<Notifications />);
        expect(await screen.findByText('Work order completed')).toBeVisible();
        await user.click(screen.getByRole('button', { name: /mark work order completed as read/i }));
        expect(mocks.markRead).toHaveBeenCalledWith(4, 17);
    });

    it('persists the signed-in user’s maintenance notification preference', async () => {
        mocks.updatePreferences.mockResolvedValue({ maintenance_notifications: false });
        const user = userEvent.setup();
        render(<Notifications />);
        const toggle = await screen.findByRole('checkbox', { name: 'Maintenance notifications' });
        expect(toggle).toBeChecked();
        await user.click(toggle);
        expect(mocks.updatePreferences).toHaveBeenCalledWith({ maintenance_notifications: false });
    });
});
