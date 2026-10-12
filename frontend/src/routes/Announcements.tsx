import { useState } from 'react'
import { IconMegaphone, IconPlus } from '../components/Icons'
import { RequireEstate } from '../components/RequireEstate'
import {
  Button,
  Card,
  Chip,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Textarea,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useEstateScope } from '../context/EstateContext'
import { api, ApiError } from '../lib/api'
import { fullDate, shortDate } from '../lib/format'
import type { Announcement, Page } from '../lib/types'
import { useAsync } from '../lib/useAsync'

function PublishDrawer({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { estateId } = useEstateScope()
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [error, setError] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      await api.post<Announcement>(
        '/api/v1/announcements',
        {
          title: title.trim(),
          message: message.trim(),
          expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        },
        { estate_id: estateId },
      )
      onDone()
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not publish the announcement.'),
      )
    } finally {
      setBusy(false)
    }
  }

  const invalid = title.trim().length < 1 || message.trim().length < 1

  return (
    <Drawer
      open
      onClose={onClose}
      title="Publish an announcement"
      subtitle="Visible to every member of this estate"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit} disabled={busy || invalid}>
            {busy ? 'Publishing…' : 'Publish'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}
        <p className="border-l-2 border-l-accent bg-accent-wash px-3.5 py-3 text-[12.5px] text-ink-soft">
          Governance activity is itself a health signal. Announcements replace the WhatsApp groups
          and paper notices residents currently rely on.
        </p>
        <Field label="Title">
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={255}
            placeholder="Scheduled water interruption — Tuesday 09:00 to 13:00"
          />
        </Field>
        <Field label="Message">
          <Textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={10000}
            placeholder="The municipality will be replacing a valve on Ridge Close…"
          />
        </Field>
        <Field label="Expires (optional)" hint="After this date the notice stops showing to residents.">
          <Input type="date" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} />
        </Field>
      </div>
    </Drawer>
  )
}

function AnnouncementsBody() {
  const { estateId } = useEstateScope()
  const { user } = useAuth()
  const isAdmin = user?.role === 'hoa_admin'

  const [publishing, setPublishing] = useState(false)
  const [includeExpired, setIncludeExpired] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [actionError, setActionError] = useState<ApiError | null>(null)

  const announcements = useAsync(
    () =>
      api.get<Page<Announcement>>('/api/v1/announcements', {
        estate_id: estateId,
        size: 50,
        include_expired: isAdmin && includeExpired ? true : undefined,
      }),
    [estateId, includeExpired, isAdmin],
  )

  async function remove(id: number) {
    setBusyId(id)
    setActionError(null)
    try {
      await api.remove<void>(`/api/v1/announcements/${id}`, { estate_id: estateId })
      announcements.reload()
    } catch (cause) {
      setActionError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not delete it.'))
    } finally {
      setBusyId(null)
    }
  }

  const items = announcements.data?.items ?? []

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Governance activity
          </p>
          <h1 className="mt-2 text-[26px] leading-tight font-semibold">Announcements</h1>
          <p className="mt-1 text-[13.5px] text-ink-muted">
            One place for the notices that currently scatter across WhatsApp groups, emails and
            letterboxes.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isAdmin ? (
            <label className="flex items-center gap-2 text-[12.5px] text-ink-soft">
              <input
                type="checkbox"
                checked={includeExpired}
                onChange={(event) => setIncludeExpired(event.target.checked)}
                className="h-4 w-4 accent-[#1F6F5C]"
              />
              Include expired
            </label>
          ) : null}
          {isAdmin ? (
            <Button variant="primary" onClick={() => setPublishing(true)}>
              <IconPlus size={16} />
              Publish
            </Button>
          ) : null}
        </div>
      </header>

      {actionError ? <ErrorState message={actionError.message} requestId={actionError.requestId} /> : null}

      {announcements.loading ? (
        <LoadingState label="Loading announcements" />
      ) : announcements.error ? (
        <ErrorState message={announcements.error.message} requestId={announcements.error.requestId} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No announcements published"
          body={
            isAdmin
              ? 'Publish the first notice — an outage, an AGM, a security upgrade. Residents will see it immediately.'
              : 'Your HOA has not published anything yet. Notices will appear here as soon as they do.'
          }
          action={
            isAdmin ? (
              <Button variant="primary" onClick={() => setPublishing(true)}>
                Publish an announcement
              </Button>
            ) : undefined
          }
        />
      ) : (
        <ul className="space-y-4">
          {items.map((item) => {
            const expired = item.expires_at ? new Date(item.expires_at) < new Date() : false
            return (
              <li key={item.id}>
                <Card className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="mt-0.5 shrink-0 text-accent-ink">
                        <IconMegaphone size={18} />
                      </span>
                      <div className="min-w-0">
                        <h2 className="text-[15.5px] font-semibold">{item.title}</h2>
                        <p className="num mt-0.5 text-[11.5px] text-ink-muted">
                          Published {fullDate(item.created_at)} · by user #{item.created_by}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {expired ? <Chip tone="warn" glyph="◷">Expired</Chip> : <Chip tone="progress">Active</Chip>}
                      {isAdmin ? (
                        <Button
                          variant="ghost"
                          disabled={busyId === item.id}
                          onClick={() => remove(item.id)}
                        >
                          {busyId === item.id ? 'Removing…' : 'Delete'}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                  <p className="mt-3 text-[13.5px] leading-relaxed whitespace-pre-line text-ink-soft">
                    {item.message}
                  </p>
                  {item.expires_at ? (
                    <p className="num mt-3 border-t border-ink/10 pt-2.5 text-[11.5px] text-ink-muted">
                      Expires {shortDate(item.expires_at)}
                    </p>
                  ) : null}
                </Card>
              </li>
            )
          })}
        </ul>
      )}

      {publishing ? (
        <PublishDrawer
          onClose={() => setPublishing(false)}
          onDone={() => {
            setPublishing(false)
            announcements.reload()
          }}
        />
      ) : null}
    </div>
  )
}

export function Announcements() {
  return (
    <RequireEstate>
      <AnnouncementsBody />
    </RequireEstate>
  )
}
