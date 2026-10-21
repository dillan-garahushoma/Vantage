import { useState } from 'react';
import { Megaphone } from 'lucide-react';
import { IconPlus } from '../components/Icons';
import { RequireEstate } from '../components/RequireEstate';
import { Button, Drawer, EmptyState, ErrorState, Field, Input, LoadingState, Textarea, } from '../components/ui';
import { Badge } from '../components/ui/badge';
import { Button as BrandButton } from '../components/ui/button';
import { SectionHeading } from '../components/valora/SectionHeading';
import { Surface } from '../components/valora/Surface';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api, ApiError } from '../lib/api';
import { fullDate, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';
function PublishDrawer({ onClose, onDone }) {
    const { estateId } = useEstateScope();
    const [title, setTitle] = useState('');
    const [message, setMessage] = useState('');
    const [expiresAt, setExpiresAt] = useState('');
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    async function submit() {
        setBusy(true);
        setError(null);
        try {
            await api.post('/api/v1/announcements', {
                title: title.trim(),
                message: message.trim(),
                expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
            }, { estate_id: estateId });
            onDone();
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not publish the announcement.'));
        }
        finally {
            setBusy(false);
        }
    }
    const invalid = title.trim().length < 1 || message.trim().length < 1;
    return (<Drawer open onClose={onClose} title="Publish an announcement" subtitle="Visible to every member of this estate" footer={<div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit} disabled={busy || invalid}>
            {busy ? 'Publishing…' : 'Publish'}
          </Button>
        </div>}>
      <div className="space-y-4">
        {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
        <p className="border-l-2 border-l-accent bg-accent-wash px-3.5 py-3 text-[12.5px] text-ink-soft">
          Governance activity is itself a health signal. Announcements replace the WhatsApp groups
          and paper notices residents currently rely on.
        </p>
        <Field label="Title">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={255} placeholder="Scheduled water interruption — Tuesday 09:00 to 13:00"/>
        </Field>
        <Field label="Message">
          <Textarea value={message} onChange={(event) => setMessage(event.target.value)} maxLength={10000} placeholder="The municipality will be replacing a valve on Ridge Close…"/>
        </Field>
        <Field label="Expires (optional)" hint="After this date the notice stops showing to residents.">
          <Input type="date" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)}/>
        </Field>
      </div>
    </Drawer>);
}
function AnnouncementsBody() {
    const { estateId } = useEstateScope();
    const { user } = useAuth();
    const isAdmin = user?.role === 'hoa_admin';
    const [publishing, setPublishing] = useState(false);
    const [includeExpired, setIncludeExpired] = useState(false);
    const [busyId, setBusyId] = useState(null);
    const [actionError, setActionError] = useState(null);
    const announcements = useAsync(() => api.get('/api/v1/announcements', {
        estate_id: estateId,
        size: 50,
        include_expired: isAdmin && includeExpired ? true : undefined,
    }), [estateId, includeExpired, isAdmin]);
    async function remove(id) {
        setBusyId(id);
        setActionError(null);
        try {
            await api.remove(`/api/v1/announcements/${id}`, { estate_id: estateId });
            announcements.reload();
        }
        catch (cause) {
            setActionError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not delete it.'));
        }
        finally {
            setBusyId(null);
        }
    }
    const items = announcements.data?.items ?? [];
    return (<div className="space-y-5">
      <SectionHeading eyebrow="Estate" title="Announcements" description="One place for the notices that currently scatter across WhatsApp groups, emails and letterboxes." action={<div className="flex flex-wrap items-center gap-3">
            {isAdmin ? (<label className="flex items-center gap-2 text-[0.8rem] text-ink-soft">
                <input type="checkbox" checked={includeExpired} onChange={(event) => setIncludeExpired(event.target.checked)} className="h-4 w-4 accent-[#7C3AED]"/>
                Include expired
              </label>) : null}
            {isAdmin ? (<BrandButton variant="ink" onClick={() => setPublishing(true)} className="rounded-full px-5">
                <IconPlus size={16}/>
                Publish
              </BrandButton>) : null}
          </div>}/>

      {actionError ? <ErrorState message={actionError.message} requestId={actionError.requestId}/> : null}

      {announcements.loading ? (<LoadingState label="Loading announcements"/>) : announcements.error ? (<ErrorState message={announcements.error.message} requestId={announcements.error.requestId}/>) : items.length === 0 ? (<EmptyState title="No announcements published" body={isAdmin
                ? 'Publish the first notice — an outage, an AGM, a security upgrade. Residents will see it immediately.'
                : 'Your HOA has not published anything yet. Notices will appear here as soon as they do.'} action={isAdmin ? (<BrandButton variant="default" onClick={() => setPublishing(true)}>
                Publish an announcement
              </BrandButton>) : undefined}/>) : (<ul className="space-y-4">
          {items.map((item) => {
                const expired = item.expires_at ? new Date(item.expires_at) < new Date() : false;
                return (<li key={item.id}>
                <Surface hover className="relative overflow-hidden">
                  <span className="absolute inset-y-0 left-0 w-1 bg-brand-soft"/>
                  <div className="flex flex-wrap items-start justify-between gap-3 pl-2">
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-canvas text-brand">
                        <Megaphone className="h-4 w-4"/>
                      </span>
                      <div className="min-w-0">
                        <h2 className="font-heading text-[1rem] leading-snug font-bold text-ink">
                          {item.title}
                        </h2>
                        <p className="num mt-0.5 text-[0.72rem] text-ink-muted">
                          Published {fullDate(item.created_at)} · by user #{item.created_by}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={expired ? 'attention' : 'positive'}>
                        {expired ? 'Expired' : 'Active'}
                      </Badge>
                      {isAdmin ? (<Button variant="ghost" disabled={busyId === item.id} onClick={() => remove(item.id)}>
                          {busyId === item.id ? 'Removing…' : 'Delete'}
                        </Button>) : null}
                    </div>
                  </div>
                  <p className="mt-3 pl-2 text-[0.86rem] leading-relaxed whitespace-pre-line text-ink-soft">
                    {item.message}
                  </p>
                  {item.expires_at ? (<p className="num mt-3 border-t border-line pt-2.5 pl-2 text-[0.72rem] text-ink-muted">
                      Expires {shortDate(item.expires_at)}
                    </p>) : null}
                </Surface>
              </li>);
            })}
        </ul>)}

      {publishing ? (<PublishDrawer onClose={() => setPublishing(false)} onDone={() => {
                setPublishing(false);
                announcements.reload();
            }}/>) : null}
    </div>);
}
export function Announcements() {
    return (<RequireEstate>
      <AnnouncementsBody />
    </RequireEstate>);
}
