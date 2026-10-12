import { useCallback, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, FormEvent } from 'react'
import { RequireEstate } from '../components/RequireEstate'
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  SectionTitle,
  Select,
  Textarea,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useEstateScope } from '../context/EstateContext'
import { ApiError, api } from '../lib/api'
import type { EstatePhoto, EstateProfile, JoinCode } from '../lib/contract'
import {
  ACCEPTED_IMAGE_TYPES,
  MAX_UPLOAD_BYTES,
  UPLOAD_HINT,
  createUnitsBulk,
  currentJoinCode,
  deleteEstatePhoto,
  listEstatePhotos,
  parseUnitLines,
  rotateJoinCode,
  updateEstatePhoto,
  updateEstateProfile,
  uploadEstatePhoto,
} from '../lib/estateAdmin'
import { fullDate } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { IconCheck, IconClose, IconPlus, IconSearch } from '../components/Icons'

function toApiError(cause: unknown, fallback: string): ApiError {
  return cause instanceof ApiError ? cause : new ApiError(0, fallback)
}

/* --------------------------------------------------------------- checklist */

interface ChecklistInput {
  profile: EstateProfile | null
  unitCount: number | null
  photoCount: number | null
  hasJoinCode: boolean | null
}

export function setupChecklist({ profile, unitCount, photoCount, hasJoinCode }: ChecklistInput) {
  return [
    {
      key: 'description',
      label: 'Describe the estate',
      done: Boolean(profile?.description && profile.description.trim().length > 0),
      hint: 'One or two sentences. This is what the public directory shows.',
    },
    {
      key: 'units',
      label: 'Register the units',
      done: (unitCount ?? 0) > 0,
      hint: 'Residents join against a unit number, so units come first.',
    },
    {
      key: 'join-code',
      label: 'Issue a join code',
      done: hasJoinCode === true,
      hint: 'The code is how a resident proves they belong.',
    },
    {
      key: 'photos',
      label: 'Add photographs',
      done: (photoCount ?? 0) > 0,
      hint: 'Up to twelve. Images are re-encoded and stripped of location data.',
    },
    {
      key: 'publish',
      label: 'Publish the estate',
      done: profile?.is_public === true,
      hint: 'Until this is on, the estate is invisible in the public directory.',
    },
  ]
}

function Checklist({ input }: { input: ChecklistInput }) {
  const items = setupChecklist(input)
  const done = items.filter((item) => item.done).length

  return (
    <Card as="section" className="p-5">
      <SectionTitle
        title="Setup checklist"
        hint="Derived from what the API currently holds for this estate"
        action={
          <span className="num text-[12.5px] text-ink-muted">
            {done} of {items.length}
          </span>
        }
      />
      <ol className="space-y-2.5">
        {items.map((item) => (
          <li key={item.key} className="flex gap-3">
            <span
              className={
                item.done
                  ? 'mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-xs bg-accent text-white'
                  : 'mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-xs border border-ink/25 text-ink-muted'
              }
            >
              {item.done ? <IconCheck size={13} /> : <span className="h-1.5 w-1.5 bg-current" />}
            </span>
            <span>
              <span className="block text-[13.5px] font-medium">{item.label}</span>
              <span className="block text-[12.5px] text-ink-muted">{item.hint}</span>
            </span>
          </li>
        ))}
      </ol>
    </Card>
  )
}

/* ------------------------------------------------------------- description */

function DescriptionEditor({
  profile,
  onSaved,
}: {
  profile: EstateProfile
  onSaved: () => void
}) {
  const [value, setValue] = useState(profile.description ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [saved, setSaved] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setSaved(false)
    try {
      await updateEstateProfile(profile.estate_id, { description: value.trim() || null })
      setSaved(true)
      onSaved()
    } catch (cause) {
      setError(toApiError(cause, 'Could not save the description.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card as="section" className="p-5">
      <SectionTitle title="Estate description" hint="Shown on the public profile" />
      <form onSubmit={save} className="space-y-3">
        {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}
        <Field
          label="Description"
          hint="Plain text. The estate name is fixed — it is not editable here."
        >
          <Textarea
            name="description"
            value={value}
            maxLength={5000}
            onChange={(event) => setValue(event.target.value)}
            placeholder="A 24-unit complex in Centurion with a shared pool and a single monitored gate."
          />
        </Field>
        <div className="flex items-center gap-3">
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save description'}
          </Button>
          {saved ? <span className="text-[12.5px] text-accent-ink">Saved.</span> : null}
        </div>
      </form>
    </Card>
  )
}

/* ---------------------------------------------------------------- publish */

function PublishToggles({ profile, onSaved }: { profile: EstateProfile; onSaved: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function toggle(changes: { is_public?: boolean; show_living_score?: boolean }) {
    setBusy(true)
    setError(null)
    try {
      await updateEstateProfile(profile.estate_id, changes)
      onSaved()
    } catch (cause) {
      setError(toApiError(cause, 'Could not change that setting.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card as="section" className="p-5">
      <SectionTitle
        title="Publishing"
        hint="Two separate decisions. A photograph and a health score are not the same thing."
      />
      {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}
      <div className="space-y-4">
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            name="is_public"
            checked={profile.is_public}
            disabled={busy}
            onChange={(event) => toggle({ is_public: event.target.checked })}
            className="mt-1 h-4 w-4 accent-[#1F6F5C]"
          />
          <span>
            <span className="block text-[13.5px] font-medium">
              List this estate in the public directory
            </span>
            <span className="block text-[12.5px] text-ink-muted">
              Shows the name, location, description, unit count and photographs. Never the units,
              residents, complaints or incidents.
            </span>
          </span>
        </label>

        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            name="show_living_score"
            checked={profile.show_living_score}
            disabled={busy || !profile.is_public}
            onChange={(event) => toggle({ show_living_score: event.target.checked })}
            className="mt-1 h-4 w-4 accent-[#1F6F5C]"
          />
          <span>
            <span className="block text-[13.5px] font-medium">
              Show the Living Score on the public profile
            </span>
            <span className="block text-[12.5px] text-ink-muted">
              {profile.is_public
                ? 'Only the latest stored score is published, with its engine version and date.'
                : 'Available once the estate is listed.'}
            </span>
          </span>
        </label>
      </div>
    </Card>
  )
}

/* ------------------------------------------------------------------- units */

function UnitsBulkAdd({ estateId, onCreated }: { estateId: number; onCreated: () => void }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [created, setCreated] = useState<number | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const { lines, rejected } = parseUnitLines(text)
    if (lines.length === 0) {
      setError(
        new ApiError(422, 'Nothing to add yet. Each line needs at least a unit number.'),
      )
      return
    }
    if (rejected.length > 0) {
      setError(
        new ApiError(
          422,
          `Line ${rejected.join(', ')} could not be read. Use “unit_no, street address, size, bedrooms, bathrooms” with numbers where numbers belong.`,
        ),
      )
      return
    }

    setBusy(true)
    setError(null)
    setCreated(null)
    try {
      const result = await createUnitsBulk(estateId, lines)
      setCreated(result.length)
      setText('')
      onCreated()
    } catch (cause) {
      setError(toApiError(cause, 'Could not add those units.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card as="section" className="p-5">
      <SectionTitle
        title="Register units"
        hint="One per line: unit_no, street address, size, bedrooms, bathrooms"
      />
      <form onSubmit={submit} className="space-y-3">
        {error ? (
          <ErrorState
            title={error.status === 409 ? 'Those unit numbers are already in use' : 'Could not add those units'}
            message={error.message}
            requestId={error.requestId}
          />
        ) : null}
        {created !== null ? (
          <p className="text-[13px] text-accent-ink">
            Added {created} {created === 1 ? 'unit' : 'units'}.
          </p>
        ) : null}

        <Field
          label="Units"
          hint="All or nothing: if one line is a duplicate, the whole batch is refused."
        >
          <Textarea
            name="units"
            value={text}
            onChange={(event) => setText(event.target.value)}
            spellCheck={false}
            className="num min-h-32 text-[13px]"
            placeholder={'A-101, 12 Ridge Close, 96, 3, 2\nA-102, 14 Ridge Close, 88, 2, 2'}
          />
        </Field>
        <Button type="submit" variant="primary" disabled={busy}>
          <IconPlus size={16} />
          {busy ? 'Adding…' : 'Add units'}
        </Button>
      </form>
    </Card>
  )
}

/* ------------------------------------------------------------------ photos */

function PhotoUploader({ estateId, onChanged }: { estateId: number; onChanged: () => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [dragging, setDragging] = useState(false)
  const [caption, setCaption] = useState('')
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [hint, setHint] = useState<string | null>(null)

  const send = useCallback(
    async (file: File) => {
      setError(null)
      setHint(null)

      // Client-side hints only. The API decodes and decides; these just avoid
      // spending a resident's bandwidth on something that cannot be accepted.
      if (!ACCEPTED_IMAGE_TYPES.includes(file.type as (typeof ACCEPTED_IMAGE_TYPES)[number])) {
        setHint(`${UPLOAD_HINT}. This file is ${file.type || 'an unknown type'}.`)
        return
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        setHint(`${UPLOAD_HINT}. This file is larger than 5 MB.`)
        return
      }

      setProgress(0)
      try {
        await uploadEstatePhoto(estateId, file, {
          caption: caption.trim() || undefined,
          onProgress: setProgress,
        })
        setCaption('')
        onChanged()
      } catch (cause) {
        setError(toApiError(cause, 'That photo was rejected.'))
      } finally {
        setProgress(null)
        if (inputRef.current) inputRef.current.value = ''
      }
    },
    [caption, estateId, onChanged],
  )

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    const file = event.dataTransfer.files?.[0]
    if (file) void send(file)
  }

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) void send(file)
  }

  return (
    <div className="space-y-3">
      {error ? <ErrorState title="The server rejected that photo" message={error.message} requestId={error.requestId} /> : null}
      {hint ? (
        <p className="hairline rounded-xs bg-ochre-wash px-3 py-2 text-[12.5px] text-ochre-ink">
          {hint}
        </p>
      ) : null}

      <Field label="Caption (optional)" hint="How you would caption it. Max 140 characters.">
        <Input
          name="caption"
          value={caption}
          maxLength={140}
          onChange={(event) => setCaption(event.target.value)}
          placeholder="The pool at dusk"
        />
      </Field>

      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={
          dragging
            ? 'hairline rounded-xs border-accent bg-accent-wash px-4 py-6 text-center'
            : 'hairline rounded-xs bg-paper px-4 py-6 text-center'
        }
      >
        <p className="text-[13.5px] font-medium">Drop a photograph here</p>
        <p className="mt-1 text-[12.5px] text-ink-muted">{UPLOAD_HINT}</p>
        <div className="mt-3">
          <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
            Choose a file
          </Button>
        </div>
        <input
          ref={inputRef}
          type="file"
          name="file"
          accept={ACCEPTED_IMAGE_TYPES.join(',')}
          className="sr-only"
          aria-label="Choose a photograph to upload"
          onChange={onPick}
        />
      </div>

      {progress !== null ? (
        <div>
          <div className="flex items-baseline justify-between text-[12px] text-ink-muted">
            <span>Uploading</span>
            <span className="num">{progress}%</span>
          </div>
          <div
            className="mt-1 h-1.5 w-full bg-ink/10"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="h-full bg-accent" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : null}
    </div>
  )
}

function PhotoList({ estateId, photos, onChanged }: { estateId: number; photos: EstatePhoto[]; onChanged: () => void }) {
  const [busy, setBusy] = useState<number | null>(null)
  const [confirming, setConfirming] = useState<number | null>(null)
  const [error, setError] = useState<ApiError | null>(null)

  async function move(index: number, direction: -1 | 1) {
    const target = index + direction
    if (target < 0 || target >= photos.length) return
    setBusy(photos[index].photo_id)
    setError(null)
    try {
      // Swap the two positions: positions are display order, not identity.
      await updateEstatePhoto(estateId, photos[index].photo_id, {
        position: photos[target].position,
      })
      await updateEstatePhoto(estateId, photos[target].photo_id, {
        position: photos[index].position,
      })
      onChanged()
    } catch (cause) {
      setError(toApiError(cause, 'Could not reorder the photographs.'))
    } finally {
      setBusy(null)
    }
  }

  async function remove(photoId: number) {
    setBusy(photoId)
    setError(null)
    try {
      await deleteEstatePhoto(estateId, photoId)
      setConfirming(null)
      onChanged()
    } catch (cause) {
      setError(toApiError(cause, 'Could not delete that photograph.'))
    } finally {
      setBusy(null)
    }
  }

  if (photos.length === 0) {
    return <EmptyState title="No photographs yet" body="The first one becomes the estate’s cover photo." />
  }

  return (
    <div className="space-y-3">
      {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {photos.map((photo, index) => (
          <li key={photo.photo_id} className="hairline rounded-xs bg-surface p-3">
            <div className="flex items-center justify-between">
              <span className="num text-[11.5px] text-ink-muted">#{index + 1}</span>
              {index === 0 ? <Chip tone="progress">Cover</Chip> : null}
            </div>
            <p className="mt-1.5 text-[12.5px] text-ink-soft">{photo.caption ?? 'No caption'}</p>
            <p className="num mt-1 text-[11px] text-ink-muted">
              {photo.width}×{photo.height} · {Math.round(photo.bytes / 1024)} KB
            </p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              <Button
                type="button"
                variant="ghost"
                aria-label={`Move photo ${index + 1} up`}
                disabled={index === 0 || busy !== null}
                onClick={() => move(index, -1)}
              >
                ↑
              </Button>
              <Button
                type="button"
                variant="ghost"
                aria-label={`Move photo ${index + 1} down`}
                disabled={index === photos.length - 1 || busy !== null}
                onClick={() => move(index, 1)}
              >
                ↓
              </Button>
              {confirming === photo.photo_id ? (
                <>
                  <Button type="button" variant="danger" disabled={busy === photo.photo_id} onClick={() => remove(photo.photo_id)}>
                    {busy === photo.photo_id ? 'Deleting…' : 'Confirm delete'}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setConfirming(null)}>
                    <IconClose size={14} />
                    Cancel
                  </Button>
                </>
              ) : (
                <Button type="button" variant="secondary" onClick={() => setConfirming(photo.photo_id)}>
                  Delete
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ---------------------------------------------------------------- join code */

function JoinCodeCard({
  estateId,
  code,
  onChanged,
}: {
  estateId: number
  code: JoinCode | null
  onChanged: () => void
}) {
  const [expires, setExpires] = useState('30')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [copied, setCopied] = useState(false)

  async function rotate() {
    setBusy(true)
    setError(null)
    try {
      await rotateJoinCode(estateId, Number(expires))
      setCopied(false)
      onChanged()
    } catch (cause) {
      setError(toApiError(cause, 'Could not issue a new code.'))
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    if (!code) return
    try {
      await navigator.clipboard.writeText(code.code)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  return (
    <Card as="section" className="p-5">
      <SectionTitle title="Join code" hint="One live code per estate. Rotating revokes the old one." />
      {error ? <ErrorState message={error.message} requestId={error.requestId} /> : null}

      {code ? (
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
              Current code
            </p>
            <p className="num mt-1 text-[26px] leading-none font-semibold tracking-[0.18em]">
              {code.code}
            </p>
            <p className="num mt-1.5 text-[12px] text-ink-muted">
              {code.expires_at ? `Expires ${fullDate(code.expires_at)}` : 'No expiry set'}
            </p>
          </div>
          <div className="ml-auto flex flex-wrap items-end gap-2">
            <Button type="button" variant="secondary" onClick={copy}>
              {copied ? 'Copied' : 'Copy code'}
            </Button>
            <label>
              <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                New code lasts
              </span>
              <Select
                name="expires_in_days"
                value={expires}
                onChange={(event) => setExpires(event.target.value)}
              >
                <option value="7">7 days</option>
                <option value="30">30 days</option>
                <option value="90">90 days</option>
              </Select>
            </label>
            <Button type="button" variant="primary" onClick={rotate} disabled={busy}>
              {busy ? 'Rotating…' : 'Rotate code'}
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-[13px] text-ink-soft">
            This estate has no live code. Issue one so residents can join.
          </p>
          <label className="inline-block">
            <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
              Code lasts
            </span>
            <Select
              name="expires_in_days"
              value={expires}
              onChange={(event) => setExpires(event.target.value)}
            >
              <option value="7">7 days</option>
              <option value="30">30 days</option>
              <option value="90">90 days</option>
            </Select>
          </label>
          <div>
            <Button type="button" variant="primary" onClick={rotate} disabled={busy}>
              {busy ? 'Issuing…' : 'Issue a code'}
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

/* ------------------------------------------------------------------- screen */

function AdminSetupBody() {
  const { estateId } = useEstateScope()
  const { user } = useAuth()
  const scope = estateId ?? 0
  const isAdmin = user?.role === 'hoa_admin'

  const profile = useAsync(
    () => (scope ? api.get<EstateProfile>('/api/v1/estates/profile', { estate_id: scope }) : Promise.resolve(null)),
    [scope],
  )
  const units = useAsync(
    () => (scope ? api.get<{ total: number }>('/api/v1/properties', { estate_id: scope, size: 1 }) : Promise.resolve(null)),
    [scope],
  )
  const photos = useAsync(
    () => (scope ? listEstatePhotos(scope) : Promise.resolve([] as EstatePhoto[])),
    [scope],
  )
  const code = useAsync(
    () => (scope ? currentJoinCode(scope) : Promise.resolve(null)),
    [scope],
  )

  const reloadAll = useCallback(() => {
    profile.reload()
    units.reload()
    photos.reload()
    code.reload()
  }, [profile, units, photos, code])

  if (!isAdmin) {
    return (
      <ErrorState
        title="Setting up an estate is an HOA administrator task"
        message="You are a member of this estate, but not its administrator. Ask your estate office to change the estate profile."
      />
    )
  }

  // Only the *first* load takes over the screen. A refresh after a save keeps
  // everything mounted, so the checklist updates in place and the confirmation
  // the person just earned does not vanish under a loading state.
  const firstLoad = profile.data === null && (profile.loading || units.loading || photos.loading)
  if (firstLoad) {
    return <LoadingState label="Loading your estate setup" />
  }

  if (profile.error) {
    return (
      <ErrorState
        title="Could not load the estate profile"
        message={profile.error.message}
        requestId={profile.error.requestId}
        action={
          <Button variant="secondary" onClick={reloadAll}>
            Try again
          </Button>
        }
      />
    )
  }

  const detail = profile.data
  if (!detail) return null

  return (
    <div className="space-y-5">
      <header>
        <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
          Estate administration
        </p>
        <h1 className="mt-2 text-[26px] leading-tight font-semibold">Set up {detail.name}</h1>
        <p className="mt-1 max-w-2xl text-[13.5px] text-ink-muted">
          Five steps and the complex is usable end to end: described, unitised, with a join code,
          photographs, and published if you want it found.
        </p>
      </header>

      <Checklist
        input={{
          profile: detail,
          unitCount: units.data?.total ?? (units.error ? null : 0),
          photoCount: photos.error ? null : (photos.data?.length ?? 0),
          hasJoinCode: code.error ? (code.error.status === 404 ? false : null) : code.data ? true : null,
        }}
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <DescriptionEditor profile={detail} onSaved={profile.reload} />
        <PublishToggles profile={detail} onSaved={profile.reload} />
      </div>

      <UnitsBulkAdd estateId={scope} onCreated={reloadAll} />

      <Card as="section" className="p-5">
        <SectionTitle
          title="Photographs"
          hint={
            photos.error
              ? 'Could not load the photographs'
              : `${photos.data?.length ?? 0} of 12 uploaded`
          }
        />
        {photos.error ? (
          <ErrorState
            message={photos.error.message}
            requestId={photos.error.requestId}
            action={
              <Button variant="secondary" onClick={photos.reload}>
                Try again
              </Button>
            }
          />
        ) : null}
        {!photos.error ? (
          <div className="space-y-5">
            <PhotoList estateId={scope} photos={photos.data ?? []} onChanged={photos.reload} />
            <PhotoUploader estateId={scope} onChanged={reloadAll} />
          </div>
        ) : null}
      </Card>

      {code.error && code.error.status !== 404 ? (
        <ErrorState
          title="Could not read the join code"
          message={code.error.message}
          requestId={code.error.requestId}
          action={
            <Button variant="secondary" onClick={code.reload}>
              Try again
            </Button>
          }
        />
      ) : (
        <JoinCodeCard estateId={scope} code={code.data ?? null} onChanged={code.reload} />
      )}

      <Card as="section" className="p-5">
        <SectionTitle title="Next" hint="Once the checklist is complete" />
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              window.location.assign('/app/members')
            }}
          >
            <IconSearch size={16} />
            Manage members
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              window.location.assign('/app')
            }}
          >
            Go to the dashboard
          </Button>
        </div>
      </Card>
    </div>
  )
}

export function AdminSetup() {
  return (
    <RequireEstate>
      <AdminSetupBody />
    </RequireEstate>
  )
}
