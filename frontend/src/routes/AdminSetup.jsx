import { useCallback, useEffect, useRef, useState } from 'react';
import { RequireEstate } from '../components/RequireEstate';
import { Button, Card, Chip, EmptyState, ErrorState, Field, Input, LoadingState, SectionTitle, Select, Textarea, } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { ApiError, api } from '../lib/api';
import { ACCEPTED_IMAGE_LABEL, ACCEPTED_IMAGE_TYPES, MAX_ESTATE_PHOTOS, MAX_UPLOAD_BYTES, UPLOAD_HINT, createUnitsBulk, currentJoinCode, deleteEstatePhoto, listEstatePhotos, parseUnitLines, rotateJoinCode, updateEstatePhoto, updateEstateProfile, uploadEstatePhoto, } from '../lib/estateAdmin';
import { fullDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { IconClose, IconPlus } from '../components/Icons';
function toApiError(cause, fallback) {
    return cause instanceof ApiError ? cause : new ApiError(0, fallback);
}
export function setupChecklist({ profile, unitCount, photoCount, hasJoinCode }) {
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
    ];
}
/* ------------------------------------------------------------- description */
function DescriptionEditor({ profile, onSaved, }) {
    const [value, setValue] = useState(profile.description ?? '');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [saved, setSaved] = useState(false);
    async function save(event) {
        event.preventDefault();
        setBusy(true);
        setError(null);
        setSaved(false);
        try {
            await updateEstateProfile(profile.estate_id, { description: value.trim() || null });
            setSaved(true);
            onSaved();
        }
        catch (cause) {
            setError(toApiError(cause, 'Could not save the description.'));
        }
        finally {
            setBusy(false);
        }
    }
    return (<Card as="section" className="p-5">
      <SectionTitle title="Estate description" hint="Shown on the public profile"/>
      <form onSubmit={save} className="space-y-3">
        {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
        <Field label="Description" hint="Plain text. The estate name is fixed — it is not editable here.">
          <Textarea name="description" value={value} maxLength={5000} onChange={(event) => setValue(event.target.value)} placeholder="A 24-unit complex in Centurion with a shared pool and a single monitored gate."/>
        </Field>
        <div className="flex items-center gap-3">
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save description'}
          </Button>
          {saved ? <span className="text-[12.5px] text-accent-ink">Saved.</span> : null}
        </div>
      </form>
    </Card>);
}
/* ---------------------------------------------------------------- publish */
function PublishToggles({ profile, onSaved }) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    async function toggle(changes) {
        setBusy(true);
        setError(null);
        try {
            await updateEstateProfile(profile.estate_id, changes);
            onSaved();
        }
        catch (cause) {
            setError(toApiError(cause, 'Could not change that setting.'));
        }
        finally {
            setBusy(false);
        }
    }
    return (<Card as="section" className="p-5">
      <SectionTitle title="Publishing" hint="Two separate decisions. A photograph and a health score are not the same thing."/>
      {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
      <div className="space-y-4">
        <label className="flex items-start gap-3">
          <input type="checkbox" name="is_public" checked={profile.is_public} disabled={busy} onChange={(event) => toggle({ is_public: event.target.checked })} className="mt-1 h-4 w-4 accent-[#1F6F5C]"/>
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
          <input type="checkbox" name="show_living_score" checked={profile.show_living_score} disabled={busy || !profile.is_public} onChange={(event) => toggle({ show_living_score: event.target.checked })} className="mt-1 h-4 w-4 accent-[#1F6F5C]"/>
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
    </Card>);
}
/* ------------------------------------------------------------------- units */
function UnitsBulkAdd({ estateId, onCreated }) {
    const [text, setText] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [created, setCreated] = useState(null);
    async function submit(event) {
        event.preventDefault();
        const { lines, rejected } = parseUnitLines(text);
        if (lines.length === 0) {
            setError(new ApiError(422, 'Nothing to add yet. Each line needs at least a unit number.'));
            return;
        }
        if (rejected.length > 0) {
            setError(new ApiError(422, `Line ${rejected.join(', ')} could not be read. Use “unit_no, street address, size, bedrooms, bathrooms” with numbers where numbers belong.`));
            return;
        }
        setBusy(true);
        setError(null);
        setCreated(null);
        try {
            const result = await createUnitsBulk(estateId, lines);
            setCreated(result.length);
            setText('');
            onCreated();
        }
        catch (cause) {
            setError(toApiError(cause, 'Could not add those units.'));
        }
        finally {
            setBusy(false);
        }
    }
    return (<Card as="section" className="p-5">
      <SectionTitle title="Register units" hint="One per line: unit_no, street address, size, bedrooms, bathrooms"/>
      <form onSubmit={submit} className="space-y-3">
        {error ? (<ErrorState title={error.status === 409 ? 'Those unit numbers are already in use' : 'Could not add those units'} message={error.message} requestId={error.requestId}/>) : null}
        {created !== null ? (<p className="text-[13px] text-accent-ink">
            Added {created} {created === 1 ? 'unit' : 'units'}.
          </p>) : null}

        <Field label="Units" hint="All or nothing: if one line is a duplicate, the whole batch is refused.">
          <Textarea name="units" value={text} onChange={(event) => setText(event.target.value)} spellCheck={false} className="num min-h-32 text-[13px]" placeholder={'A-101, 12 Ridge Close, 96, 3, 2\nA-102, 14 Ridge Close, 88, 2, 2'}/>
        </Field>
        <Button type="submit" variant="primary" disabled={busy}>
          <IconPlus size={16}/>
          {busy ? 'Adding…' : 'Add units'}
        </Button>
      </form>
    </Card>);
}
let nextQueuedId = 0;
/**
 * Everything the picker refuses before a byte is spent. The API still decides;
 * this only keeps an obviously unacceptable file from costing a resident
 * bandwidth — and it says *which* file and *why*, per row.
 */
function problemWith(file) {
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
        return `Not ${ACCEPTED_IMAGE_LABEL}. This file is ${file.type || 'of an unknown type'}.`;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
        return `Larger than ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB.`;
    }
    return null;
}
/** The same photograph chosen twice, whatever the picker called it. */
const isSameFile = (a, b) => a.name === b.name && a.size === b.size && a.lastModified === b.lastModified;
export function PhotoUploader({ estateId, existingCount, onChanged, }) {
    const inputRef = useRef(null);
    const [dragging, setDragging] = useState(false);
    const [queue, setQueue] = useState([]);
    const [notice, setNotice] = useState(null);
    const [uploading, setUploading] = useState(false);
    // The previews are this component's own memory. A row that leaves with one
    // still attached is a photograph the browser holds until the tab closes.
    const queueRef = useRef([]);
    queueRef.current = queue;
    useEffect(() => () => {
        for (const item of queueRef.current)
            URL.revokeObjectURL(item.previewUrl);
    }, []);
    const pending = queue.filter((item) => item.problem === null && item.status !== 'uploading');
    function addFiles(picked) {
        setNotice(null);
        // `existingCount` is what the estate already has stored; the queue is what
        // has not been sent yet. Both count against the estate's 12, so a batch is
        // never queued only for the server to refuse its last photograph.
        const slotsLeft = Math.max(0, MAX_ESTATE_PHOTOS - existingCount - queue.length);
        const additions = [];
        let duplicates = 0;
        let noRoom = 0;
        for (const file of picked) {
            if ([...queue, ...additions].some((item) => isSameFile(item.file, file))) {
                duplicates += 1;
                continue;
            }
            if (additions.length >= slotsLeft) {
                noRoom += 1;
                continue;
            }
            nextQueuedId += 1;
            additions.push({
                id: `photo-${nextQueuedId}`,
                file,
                previewUrl: URL.createObjectURL(file),
                caption: '',
                status: 'ready',
                progress: 0,
                error: null,
                problem: problemWith(file),
            });
        }
        if (additions.length > 0)
            setQueue((current) => [...current, ...additions]);
        const notes = [];
        if (noRoom > 0) {
            notes.push(slotsLeft === 0
                ? `Nothing added: an estate holds ${MAX_ESTATE_PHOTOS} photographs, and this one is at its limit. Delete one first.`
                : `Only ${slotsLeft} of those ${picked.length} added — an estate holds ${MAX_ESTATE_PHOTOS} photographs.`);
        }
        if (duplicates > 0) {
            notes.push(`${duplicates} ${duplicates === 1 ? 'file was' : 'files were'} already in the list.`);
        }
        if (notes.length > 0)
            setNotice(notes.join(' '));
    }
    function remove(id) {
        setQueue((current) => {
            const item = current.find((row) => row.id === id);
            if (item)
                URL.revokeObjectURL(item.previewUrl);
            return current.filter((row) => row.id !== id);
        });
    }
    function clearQueue() {
        setNotice(null);
        setQueue((current) => {
            for (const item of current)
                URL.revokeObjectURL(item.previewUrl);
            return [];
        });
    }
    /**
     * Sequential, one request per photograph — which is what the API takes. It also
     * keeps the estate's photo count honest between requests: the server checks the
     * ceiling per upload, so firing twelve at once would make its answer depend on
     * the order they happened to land in.
     */
    async function upload() {
        const batch = queue.filter((item) => item.problem === null && item.status !== 'uploading');
        if (batch.length === 0)
            return;
        setUploading(true);
        setNotice(null);
        let uploaded = 0;
        let failed = 0;
        for (const item of batch) {
            setQueue((current) => current.map((row) => row.id === item.id ? { ...row, status: 'uploading', progress: 0, error: null } : row));
            try {
                await uploadEstatePhoto(estateId, item.file, {
                    caption: item.caption.trim() || undefined,
                    onProgress: (percent) => setQueue((current) => current.map((row) => (row.id === item.id ? { ...row, progress: percent } : row))),
                });
                uploaded += 1;
                // Stored. It belongs to the list below now, not to the queue.
                setQueue((current) => {
                    URL.revokeObjectURL(item.previewUrl);
                    return current.filter((row) => row.id !== item.id);
                });
            }
            catch (cause) {
                failed += 1;
                const failure = toApiError(cause, 'That photo was rejected.');
                setQueue((current) => current.map((row) => row.id === item.id
                    ? { ...row, status: 'failed', error: failure.message, requestId: failure.requestId }
                    : row));
            }
        }
        setUploading(false);
        if (uploaded > 0)
            onChanged();
        const notes = [];
        if (uploaded > 0)
            notes.push(`${uploaded} ${uploaded === 1 ? 'photograph' : 'photographs'} uploaded.`);
        if (failed > 0) {
            notes.push(`${failed} could not be sent — the reason is on ${failed === 1 ? 'that row' : 'those rows'}. The rest are unaffected.`);
        }
        if (notes.length > 0)
            setNotice(notes.join(' '));
    }
    function onDrop(event) {
        event.preventDefault();
        setDragging(false);
        const files = Array.from(event.dataTransfer?.files ?? []);
        if (files.length > 0)
            addFiles(files);
    }
    function onPick(event) {
        const files = Array.from(event.target.files ?? []);
        // Clearing the value is what lets the same photograph be chosen again after
        // it was removed from the queue.
        event.target.value = '';
        if (files.length > 0)
            addFiles(files);
    }
    return (<div className="space-y-3">
      {notice ? (<p className="hairline rounded-xs bg-ochre-wash px-3 py-2 text-[12.5px] text-ochre-ink">
          {notice}
        </p>) : null}

      <div onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
        }} onDragLeave={() => setDragging(false)} onDrop={onDrop} className={dragging
            ? 'hairline rounded-xs border-accent bg-accent-wash px-4 py-6 text-center'
            : 'hairline rounded-xs bg-paper px-4 py-6 text-center'}>
        <p className="text-[13.5px] font-medium">Drop photographs here, or choose several at once</p>
        <p className="mt-1 text-[12.5px] text-ink-muted">{UPLOAD_HINT}</p>
        <div className="mt-3">
          <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
            Choose photographs
          </Button>
        </div>
        <input ref={inputRef} type="file" name="file" 
    // Many at a time, and the same control can be used again to add more
    // without losing what is already queued.
    multiple accept={ACCEPTED_IMAGE_TYPES.join(',')} className="sr-only" aria-label="Choose photographs to upload" onChange={onPick}/>
      </div>

      {queue.length > 0 ? (<div className="space-y-2">
          <p className="num text-[12px] text-ink-muted">
            {queue.length} {queue.length === 1 ? 'photograph' : 'photographs'} queued
            {' · '}
            {MAX_ESTATE_PHOTOS - existingCount} of {MAX_ESTATE_PHOTOS} places left in the estate
          </p>
          <ul className="space-y-2">
            {queue.map((item) => (<li key={item.id} className="hairline rounded-xs bg-surface p-2.5">
                <div className="flex items-start gap-3">
                  <img src={item.previewUrl} alt="" width={56} height={42} className="h-[42px] w-14 shrink-0 border border-ink/15 object-cover"/>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12.5px] font-medium">{item.file.name}</p>
                    <p className="num text-[11.5px] text-ink-muted">
                      {Math.max(1, Math.round(item.file.size / 1024))} KB
                      {item.problem ? '' : ' · ready'}
                    </p>
                    {item.problem ? (<p className="mt-1 text-[12px] text-signal-ink">
                        Cannot be sent: {item.problem}
                      </p>) : (<label className="mt-1.5 block">
                        <span className="sr-only">Caption for {item.file.name}</span>
                        <Input value={item.caption} maxLength={140} disabled={item.status === 'uploading'} placeholder="Caption (optional)" onChange={(event) => setQueue((current) => current.map((row) => row.id === item.id ? { ...row, caption: event.target.value } : row))}/>
                      </label>)}
                    {item.error ? (<p className="mt-1 text-[12px] text-signal-ink">
                        {item.error}
                        {item.requestId ? <span className="num"> · ref {item.requestId}</span> : null}
                      </p>) : null}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    {item.status === 'uploading' ? (<span className="num text-[11.5px] text-ink-muted">{item.progress}%</span>) : null}
                    <Button type="button" variant="ghost" disabled={uploading} aria-label={`Remove ${item.file.name} from the queue`} onClick={() => remove(item.id)}>
                      Remove
                    </Button>
                  </div>
                </div>
                {item.status === 'uploading' ? (<div className="mt-2 h-1.5 w-full bg-ink/10" role="progressbar" aria-label={`Uploading ${item.file.name}`} aria-valuenow={item.progress} aria-valuemin={0} aria-valuemax={100}>
                    <div className="h-full bg-accent" style={{ width: `${item.progress}%` }}/>
                  </div>) : null}
              </li>))}
          </ul>

          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="primary" disabled={uploading || pending.length === 0} onClick={upload}>
              {uploading
                ? 'Uploading…'
                : `Upload ${pending.length} ${pending.length === 1 ? 'photograph' : 'photographs'}`}
            </Button>
            <Button type="button" variant="ghost" disabled={uploading} onClick={() => clearQueue()}>
              Clear
            </Button>
          </div>
        </div>) : null}
    </div>);
}
function PhotoList({ estateId, photos, onChanged }) {
    const [busy, setBusy] = useState(null);
    const [confirming, setConfirming] = useState(null);
    const [error, setError] = useState(null);
    async function move(index, direction) {
        const target = index + direction;
        if (target < 0 || target >= photos.length)
            return;
        setBusy(photos[index].photo_id);
        setError(null);
        try {
            // Swap the two positions: positions are display order, not identity.
            await updateEstatePhoto(estateId, photos[index].photo_id, {
                position: photos[target].position,
            });
            await updateEstatePhoto(estateId, photos[target].photo_id, {
                position: photos[index].position,
            });
            onChanged();
        }
        catch (cause) {
            setError(toApiError(cause, 'Could not reorder the photographs.'));
        }
        finally {
            setBusy(null);
        }
    }
    async function remove(photoId) {
        setBusy(photoId);
        setError(null);
        try {
            await deleteEstatePhoto(estateId, photoId);
            setConfirming(null);
            onChanged();
        }
        catch (cause) {
            setError(toApiError(cause, 'Could not delete that photograph.'));
        }
        finally {
            setBusy(null);
        }
    }
    if (photos.length === 0) {
        return <EmptyState title="No photographs yet" body="The first one becomes the estate’s cover photo."/>;
    }
    return (<div className="space-y-3">
      {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {photos.map((photo, index) => (<li key={photo.photo_id} className="hairline rounded-xs bg-surface p-3">
            <div className="flex items-center justify-between">
              <span className="num text-[11.5px] text-ink-muted">#{index + 1}</span>
              {index === 0 ? <Chip tone="progress">Cover</Chip> : null}
            </div>
            <p className="mt-1.5 text-[12.5px] text-ink-soft">{photo.caption ?? 'No caption'}</p>
            <p className="num mt-1 text-[11px] text-ink-muted">
              {photo.width}×{photo.height} · {Math.round(photo.bytes / 1024)} KB
            </p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              <Button type="button" variant="ghost" aria-label={`Move photo ${index + 1} up`} disabled={index === 0 || busy !== null} onClick={() => move(index, -1)}>
                ↑
              </Button>
              <Button type="button" variant="ghost" aria-label={`Move photo ${index + 1} down`} disabled={index === photos.length - 1 || busy !== null} onClick={() => move(index, 1)}>
                ↓
              </Button>
              {confirming === photo.photo_id ? (<>
                  <Button type="button" variant="danger" disabled={busy === photo.photo_id} onClick={() => remove(photo.photo_id)}>
                    {busy === photo.photo_id ? 'Deleting…' : 'Confirm delete'}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setConfirming(null)}>
                    <IconClose size={14}/>
                    Cancel
                  </Button>
                </>) : (<Button type="button" variant="secondary" onClick={() => setConfirming(photo.photo_id)}>
                  Delete
                </Button>)}
            </div>
          </li>))}
      </ul>
    </div>);
}
/* ---------------------------------------------------------------- join code */
function JoinCodeCard({ estateId, code, onChanged, }) {
    const [expires, setExpires] = useState('30');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [copied, setCopied] = useState(false);
    async function rotate() {
        setBusy(true);
        setError(null);
        try {
            await rotateJoinCode(estateId, Number(expires));
            setCopied(false);
            onChanged();
        }
        catch (cause) {
            setError(toApiError(cause, 'Could not issue a new code.'));
        }
        finally {
            setBusy(false);
        }
    }
    async function copy() {
        if (!code)
            return;
        try {
            await navigator.clipboard.writeText(code.code);
            setCopied(true);
        }
        catch {
            setCopied(false);
        }
    }
    return (<Card as="section" className="p-5">
      <SectionTitle title="Join code" hint="One live code per estate. Rotating revokes the old one."/>
      {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}

      {code ? (<div className="flex flex-wrap items-end gap-3">
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
              <Select name="expires_in_days" value={expires} onChange={(event) => setExpires(event.target.value)}>
                <option value="7">7 days</option>
                <option value="30">30 days</option>
                <option value="90">90 days</option>
              </Select>
            </label>
            <Button type="button" variant="primary" onClick={rotate} disabled={busy}>
              {busy ? 'Rotating…' : 'Rotate code'}
            </Button>
          </div>
        </div>) : (<div className="space-y-3">
          <p className="text-[13px] text-ink-soft">
            This estate has no live code. Issue one so residents can join.
          </p>
          <label className="inline-block">
            <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
              Code lasts
            </span>
            <Select name="expires_in_days" value={expires} onChange={(event) => setExpires(event.target.value)}>
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
        </div>)}
    </Card>);
}
/* ------------------------------------------------------------------- screen */
function AdminSetupBody() {
    const { estateId } = useEstateScope();
    const { user } = useAuth();
    const scope = estateId ?? 0;
    const isAdmin = user?.role === 'hoa_admin';
    const profile = useAsync(() => (scope ? api.get('/api/v1/estates/profile', { estate_id: scope }) : Promise.resolve(null)), [scope]);
    const units = useAsync(() => (scope ? api.get('/api/v1/properties', { estate_id: scope, size: 1 }) : Promise.resolve(null)), [scope]);
    const photos = useAsync(() => (scope ? listEstatePhotos(scope) : Promise.resolve([])), [scope]);
    const code = useAsync(() => (scope ? currentJoinCode(scope) : Promise.resolve(null)), [scope]);
    const [publishing, setPublishing] = useState(false);
    const [activeStep, setActiveStep] = useState(1);
    const [publishError, setPublishError] = useState(null);
    const reloadAll = useCallback(() => {
        profile.reload();
        units.reload();
        photos.reload();
        code.reload();
    }, [profile, units, photos, code]);
    if (!isAdmin) {
        return (<ErrorState title="Setting up an estate is an HOA administrator task" message="You are a member of this estate, but not its administrator. Ask your estate office to change the estate profile."/>);
    }
    // Only the *first* load takes over the screen. A refresh after a save keeps
    // everything mounted, so the checklist updates in place and the confirmation
    // the person just earned does not vanish under a loading state.
    const firstLoad = profile.data === null && (profile.loading || units.loading || photos.loading);
    if (firstLoad) {
        return <LoadingState label="Loading your estate setup"/>;
    }
    if (profile.error) {
        return (<ErrorState title="Could not load the estate profile" message={profile.error.message} requestId={profile.error.requestId} action={<Button variant="secondary" onClick={reloadAll}>
            Try again
          </Button>}/>);
    }
    const detail = profile.data;
    if (!detail)
        return null;

    async function publishEstate() {
      if (!detail || publishing) return;
      setPublishing(true);
      setPublishError(null);
      try {
        await updateEstateProfile(detail.estate_id, { is_public: true });
        profile.reload();
      } catch (cause) {
        setPublishError(toApiError(cause, 'Could not publish the estate.'));
      } finally {
        setPublishing(false);
      }
    }

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

        {(() => {
          const checklist = setupChecklist({ profile: detail, unitCount: units.data?.total ?? 0, photoCount: photos.data?.length ?? 0, hasJoinCode: code.error ? (code.error.status === 404 ? false : null) : Boolean(code.data) });
          const completed = checklist.filter((item) => item.done).length;
          const steps = [{ number: 1, title: "Estate profile", done: checklist[0].done }, { number: 2, title: "Units", done: checklist[1].done }, { number: 3, title: "Resident access", done: checklist[2].done }, { number: 4, title: "Photography", done: checklist[3].done }, { number: 5, title: "Go live", done: checklist[4].done }];
          const stepContent = activeStep === 1 ? (
            <div className="space-y-5"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-ink">Step 1 · Estate profile</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Introduce your community.</h2><p className="mt-1 text-sm text-ink-muted">A clear description helps residents understand the place and helps your public profile feel complete.</p></div><DescriptionEditor profile={detail} onSaved={profile.reload} /></div>
          ) : activeStep === 2 ? (
            <div className="space-y-5"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-ink">Step 2 · Homes and units</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Map the homes in your estate.</h2><p className="mt-1 text-sm text-ink-muted">Residents use their unit number when requesting access. Add units in a batch to save time.</p></div><UnitsBulkAdd estateId={scope} onCreated={reloadAll} /></div>
          ) : activeStep === 3 ? (
            <div className="space-y-5"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-ink">Step 3 · Resident access</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Give residents a secure way to join.</h2><p className="mt-1 text-sm text-ink-muted">Share the current code only with people who belong to this estate. Rotating it revokes the previous code.</p></div>{code.error && code.error.status !== 404 ? <ErrorState title="Could not read the join code" message={code.error.message} requestId={code.error.requestId} action={<Button variant="secondary" onClick={code.reload}>Try again</Button>} /> : <JoinCodeCard estateId={scope} code={code.data ?? null} onChanged={code.reload} />}</div>
          ) : activeStep === 4 ? (
            <div className="space-y-5"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-ink">Step 4 · Photography</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Make the first impression count.</h2><p className="mt-1 text-sm text-ink-muted">Add up to 12 photographs. Images are re-encoded and location metadata is removed.</p></div><Card as="section" className="p-5"><SectionTitle title="Estate photographs" hint={photos.error ? "Could not load photographs" : (photos.data?.length ?? 0) + " of 12 uploaded"} />{photos.error ? <ErrorState message={photos.error.message} requestId={photos.error.requestId} action={<Button variant="secondary" onClick={photos.reload}>Try again</Button>} /> : <div className="space-y-5"><PhotoList estateId={scope} photos={photos.data ?? []} onChanged={photos.reload} /><PhotoUploader estateId={scope} existingCount={photos.data?.length ?? 0} onChanged={reloadAll} /></div>}</Card></div>
          ) : (
            <div className="space-y-5"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-ink">Step 5 · Go live</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">You’re in control of what’s public.</h2><p className="mt-1 text-sm text-ink-muted">Review visibility settings, then publish when the essentials are ready.</p></div><PublishToggles profile={detail} onSaved={profile.reload} /><div className="rounded-xl border border-line bg-paper/60 p-4"><p className="text-sm font-medium text-ink">{detail.is_public ? "Your estate is published." : "Your estate is currently private."}</p><p className="mt-1 text-xs leading-relaxed text-ink-muted">Public profiles show the estate name, location, description, unit count and photographs — never resident details, units, complaints or incidents.</p>{!detail.is_public ? <Button type="button" variant="primary" className="mt-4" disabled={publishing || !checklist.slice(0, 4).every((item) => item.done)} onClick={publishEstate}>{publishing ? "Publishing…" : "Publish estate"}</Button> : null}{!checklist.slice(0, 4).every((item) => item.done) && !detail.is_public ? <p className="mt-2 text-xs text-ink-muted">Complete the first four steps before publishing.</p> : null}</div>{publishError ? <ErrorState message={publishError.message} requestId={publishError.requestId} /> : null}</div>
          );
          return <section className="overflow-hidden rounded-2xl border border-white/70 bg-surface shadow-[0_24px_70px_-24px_rgba(35,30,70,0.24)] ring-1 ring-black/[0.025]">
            <div className="border-b border-line/80 px-5 py-5 sm:px-7"><div className="flex items-end justify-between gap-4"><div><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-muted">Estate setup</p><p className="mt-1 text-sm text-ink">{completed} of 5 milestones complete</p></div><span className="num text-sm font-semibold text-accent-ink">{Math.round((completed / 5) * 100)}%</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink/10"><div className="h-full rounded-full bg-accent transition-all duration-500" style={{ width: ((completed / 5) * 100) + "%" }} /></div><ol className="mt-5 grid grid-cols-5 gap-2" aria-label="Estate onboarding progress">{steps.map((item) => <li key={item.number}><button type="button" onClick={() => setActiveStep(item.number)} aria-current={activeStep === item.number ? "step" : undefined} className="group flex w-full flex-col items-start gap-2 text-left"><span className={"flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-colors " + (activeStep === item.number ? "border-accent bg-accent text-white shadow-md" : item.done ? "border-mint/40 bg-mint-wash text-mint-ink" : "border-line bg-paper text-ink-muted")}>{item.done ? "✓" : item.number}</span><span className={"hidden text-[11px] leading-tight sm:block " + (activeStep === item.number ? "font-semibold text-ink" : "text-ink-muted")}>{item.title}</span></button></li>)}</ol></div>
            <div className="p-5 sm:p-7">{stepContent}<div className="mt-7 flex items-center justify-between gap-3 border-t border-line pt-5"><Button type="button" variant="secondary" disabled={activeStep === 1} onClick={() => setActiveStep((step) => Math.max(1, step - 1))}>Back</Button><div className="flex items-center gap-3"><span className="hidden text-xs text-ink-muted sm:inline">Step {activeStep} of 5</span>{activeStep < 5 ? <Button type="button" variant="primary" onClick={() => setActiveStep((step) => Math.min(5, step + 1))}>Next step <span aria-hidden="true">→</span></Button> : <Button type="button" variant="secondary" onClick={() => window.location.assign("/app")}>Go to dashboard</Button>}</div></div></div>
          </section>;
        })()}
      </div>
    );
}
export function AdminSetup() {
    return (<RequireEstate>
      <AdminSetupBody />
    </RequireEstate>);
}
