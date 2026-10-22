import { useEffect, useState } from 'react';
import { RequireEstate } from '../components/RequireEstate';
import { Button, Card, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui';
import { useEstateScope } from '../context/EstateContext';
import { ApiError } from '../lib/api';
import { getNotificationPreferences, listNotifications, markNotificationRead, updateNotificationPreferences } from '../lib/accountSupport';
import { displayLabel, fullDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';

function NotificationsBody() {
    const { estateId, estate } = useEstateScope();
    const notifications = useAsync(() => estateId === null
        ? Promise.resolve(null)
        : listNotifications(estateId, { size: 50 }), [estateId]);
    const preferences = useAsync(() => getNotificationPreferences(), []);
    const [maintenanceNotifications, setMaintenanceNotifications] = useState(true);
    const [preferenceError, setPreferenceError] = useState(null);
    const [savingPreference, setSavingPreference] = useState(false);
    const [readingId, setReadingId] = useState(null);
    const [readError, setReadError] = useState(null);

    useEffect(() => {
        if (preferences.data) {
            setMaintenanceNotifications(preferences.data.maintenance_notifications);
        }
    }, [preferences.data]);

    async function changePreference(next) {
        setMaintenanceNotifications(next);
        setSavingPreference(true);
        setPreferenceError(null);
        try {
            const saved = await updateNotificationPreferences({ maintenance_notifications: next });
            setMaintenanceNotifications(saved.maintenance_notifications);
        }
        catch (cause) {
            setMaintenanceNotifications(!next);
            setPreferenceError(cause instanceof ApiError
                ? cause
                : new ApiError(0, 'Could not save your notification preference.'));
        }
        finally {
            setSavingPreference(false);
        }
    }
    async function markRead(notification) {
        if (estateId === null || notification.read_at || readingId !== null)
            return;
        setReadingId(notification.id);
        setReadError(null);
        try {
            await markNotificationRead(estateId, notification.id);
            notifications.reload();
        }
        catch (cause) {
            setReadError(cause instanceof ApiError
                ? cause
                : new ApiError(0, 'Could not mark that notification as read.'));
        }
        finally {
            setReadingId(null);
        }
    }
    const items = notifications.data?.items ?? [];
    return (<div className="space-y-6">
      <header>
        <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">Estate activity</p>
        <h1 className="mt-2 text-[26px] leading-tight font-semibold">Notifications</h1>
        <p className="mt-1 max-w-2xl text-[13.5px] text-ink-muted">
          Operational notices delivered to your account for {estate?.estate_name ?? 'the selected estate'}.
        </p>
      </header>

      <Card className="p-4">
        <SectionTitle title="Maintenance notifications" hint="Choose whether operational maintenance notices are delivered to this account."/>
        {preferences.loading ? <LoadingState label="Loading notification preference"/> : preferences.error ? <ErrorState message={preferences.error.message} requestId={preferences.error.requestId} action={<Button onClick={preferences.reload}>Try again</Button>}/> : (<label className="flex items-start justify-between gap-5">
          <span>
            <span className="block text-[14px] font-medium">Maintenance updates</span>
            <span className="mt-1 block text-[13px] text-ink-muted">Assignments, progress, completion and complaint review updates.</span>
          </span>
          <input type="checkbox" aria-label="Maintenance notifications" checked={maintenanceNotifications} disabled={savingPreference} onChange={(event) => changePreference(event.target.checked)} className="mt-1 h-4 w-4 accent-accent"/>
        </label>)}
        {preferenceError ? <div className="mt-3"><ErrorState message={preferenceError.message} requestId={preferenceError.requestId}/></div> : null}
      </Card>

      <section>
        <SectionTitle title="Recent activity" hint="Unread notices remain here until you mark them read." action={<Button onClick={notifications.reload}>Refresh</Button>}/>
        {readError ? <div className="mb-3"><ErrorState message={readError.message} requestId={readError.requestId}/></div> : null}
        {notifications.loading ? <LoadingState label="Loading notifications"/> : notifications.error ? <ErrorState message={notifications.error.message} requestId={notifications.error.requestId} action={<Button onClick={notifications.reload}>Try again</Button>}/> : items.length === 0 ? <EmptyState title="No operational notifications yet" body="New maintenance activity for this estate will appear here when it is addressed to your account."/> : (<ul className="space-y-2">
          {items.map((notification) => (<li key={notification.id} className="hairline flex flex-wrap items-start justify-between gap-4 rounded-xs bg-surface p-4">
              <div>
                <p className="text-[14px] font-medium">{displayLabel(notification.kind)}</p>
                <p className="mt-1 text-[12.5px] text-ink-muted">
                  Reference #{notification.resource_id} · {fullDate(notification.created_at)}
                </p>
              </div>
              {notification.read_at ? <span className="text-[12px] text-ink-muted">Read</span> : (<Button variant="secondary" disabled={readingId === notification.id} onClick={() => markRead(notification)} aria-label={`Mark ${displayLabel(notification.kind)} as read`}>
                  {readingId === notification.id ? 'Saving…' : 'Mark read'}
                </Button>)}
            </li>))}
        </ul>)}
      </section>
    </div>);
}
export function Notifications() {
    return (<RequireEstate>
      <NotificationsBody />
    </RequireEstate>);
}
