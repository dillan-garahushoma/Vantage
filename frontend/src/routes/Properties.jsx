import { useState } from 'react';
import { IconHome, IconPlus } from '../components/Icons';
import { RequireEstate } from '../components/RequireEstate';
import { Button, Card, Chip, Drawer, EmptyState, ErrorState, Field, Input, LoadingState, Select, TableShell, Td, Th, Textarea, cx, } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api, ApiError } from '../lib/api';
import { metres } from '../lib/format';
import { publicPhotoUrl } from '../lib/publicDirectory';
import { useAsync } from '../lib/useAsync';
function CreatePropertyDrawer({ onClose, onDone }) {
    const { estateId } = useEstateScope();
    const [form, setForm] = useState({
        unit_no: '',
        complex_name: '',
        street_address: '',
        suburb: '',
        size_m2: '',
        bedrooms: '',
        bathrooms: '',
    });
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    function update(key, value) {
        setForm((previous) => ({ ...previous, [key]: value }));
    }
    async function submit() {
        setBusy(true);
        setError(null);
        try {
            await api.post('/api/v1/properties', {
                estate_id: estateId,
                unit_no: form.unit_no.trim(),
                complex_name: form.complex_name.trim(),
                street_address: form.street_address.trim(),
                suburb: form.suburb.trim() || null,
                size_m2: form.size_m2 === '' ? null : Number(form.size_m2),
                bedrooms: form.bedrooms === '' ? null : Number(form.bedrooms),
                bathrooms: form.bathrooms === '' ? null : Number(form.bathrooms),
            });
            onDone();
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not create the unit.'));
        }
        finally {
            setBusy(false);
        }
    }
    const invalid = form.unit_no.trim() === '' ||
        form.complex_name.trim() === '' ||
        form.street_address.trim() === '';
    return (<Drawer open onClose={onClose} title="Add a unit" subtitle="Registered against the estate you are scoped to" footer={<div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit} disabled={busy || invalid}>
            {busy ? 'Creating…' : 'Create unit'}
          </Button>
        </div>}>
      <div className="space-y-4">
        {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Unit number">
            <Input value={form.unit_no} onChange={(e) => update('unit_no', e.target.value)} maxLength={10} placeholder="HR-07"/>
          </Field>
          <Field label="Complex / estate name">
            <Input value={form.complex_name} onChange={(e) => update('complex_name', e.target.value)} placeholder="Highveld Ridge"/>
          </Field>
        </div>
        <Field label="Street address">
          <Input value={form.street_address} onChange={(e) => update('street_address', e.target.value)} placeholder="7 Ridge Close"/>
        </Field>
        <Field label="Suburb (optional)">
          <Input value={form.suburb} onChange={(e) => update('suburb', e.target.value)} placeholder="Centurion"/>
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Size m²">
            <Input inputMode="decimal" value={form.size_m2} onChange={(e) => update('size_m2', e.target.value)} placeholder="128.00"/>
          </Field>
          <Field label="Bedrooms">
            <Input inputMode="numeric" value={form.bedrooms} onChange={(e) => update('bedrooms', e.target.value)} placeholder="3"/>
          </Field>
          <Field label="Bathrooms">
            <Input inputMode="numeric" value={form.bathrooms} onChange={(e) => update('bathrooms', e.target.value)} placeholder="2"/>
          </Field>
        </div>
      </div>
    </Drawer>);
}
function EditPropertyDrawer({ property, onClose, onDone }) {
    const { estateId } = useEstateScope();
    const [form, setForm] = useState({
        street_address: property.street_address ?? '',
        size_m2: property.size_m2 ?? '',
        bedrooms: property.bedrooms ?? '',
        bathrooms: property.bathrooms ?? '',
        listing_title: property.listing_title ?? '',
        listing_description: property.listing_description ?? '',
        amenities: (property.amenities ?? []).join(', '),
        availability_status: property.availability_status ?? 'not_available',
        is_public_listing: Boolean(property.is_public_listing),
    });
    const [busy, setBusy] = useState(false);
    const [photoBusy, setPhotoBusy] = useState(false);
    const [error, setError] = useState(null);
    const [photoError, setPhotoError] = useState(null);
    const photos = useAsync(() => api.get(`/api/v1/properties/${property.id}/photos`, { estate_id: estateId }), [property.id, estateId]);
    function update(key, value) { setForm((previous) => ({ ...previous, [key]: value })); }
    async function submit() {
        setBusy(true);
        setError(null);
        try {
            await api.patch(`/api/v1/properties/${property.id}`, {
                street_address: form.street_address.trim(),
                size_m2: form.size_m2 === '' ? null : String(form.size_m2),
                bedrooms: form.bedrooms === '' ? null : Number(form.bedrooms),
                bathrooms: form.bathrooms === '' ? null : Number(form.bathrooms),
                listing_title: form.listing_title.trim() || null,
                listing_description: form.listing_description.trim() || null,
                amenities: form.amenities.split(',').map((item) => item.trim()).filter(Boolean),
                availability_status: form.availability_status,
                is_public_listing: form.is_public_listing,
            }, { estate_id: estateId });
            onDone();
        }
        catch (cause) { setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not update this unit.')); }
        finally { setBusy(false); }
    }
    async function uploadPhoto(event) {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        setPhotoBusy(true);
        setPhotoError(null);
        try {
            const body = new FormData();
            body.append('file', file);
            await api.upload(`/api/v1/properties/${property.id}/photos`, body, { estate_id: estateId });
            photos.reload();
        } catch (cause) {
            setPhotoError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not upload this unit photo.'));
        } finally {
            setPhotoBusy(false);
        }
    }
    async function deletePhoto(photoId) {
        setPhotoError(null);
        try {
            await api.remove(`/api/v1/properties/${property.id}/photos/${photoId}`, { estate_id: estateId });
            photos.reload();
        } catch (cause) {
            setPhotoError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not delete this unit photo.'));
        }
    }
    return <Drawer open onClose={onClose} title={`Edit ${property.unit_no}`} subtitle="Manage unit details, listing photos and availability" footer={<div className="flex justify-end gap-2"><Button variant="ghost" onClick={onClose} disabled={busy || photoBusy}>Cancel</Button><Button variant="primary" onClick={submit} disabled={busy || photoBusy || !form.street_address.trim()}>{busy ? 'Saving…' : 'Save unit changes'}</Button></div>}>
      <div className="space-y-5">
        {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-ink">Unit details</h3>
          <Field label="Internal street address"><Input value={form.street_address} maxLength={255} onChange={(event) => update('street_address', event.target.value)}/></Field>
          <div className="grid gap-4 sm:grid-cols-3"><Field label="Size m²"><Input inputMode="decimal" value={form.size_m2} onChange={(event) => update('size_m2', event.target.value)}/></Field><Field label="Bedrooms"><Input inputMode="numeric" value={form.bedrooms} onChange={(event) => update('bedrooms', event.target.value)}/></Field><Field label="Bathrooms"><Input inputMode="numeric" value={form.bathrooms} onChange={(event) => update('bathrooms', event.target.value)}/></Field></div>
        </section>
        <section className="space-y-3 border-t border-ink/10 pt-5">
          <div><h3 className="text-sm font-semibold text-ink">Public unit listing</h3><p className="mt-1 text-xs leading-relaxed text-ink-muted">These details appear beneath the complex profile. Internal unit number and street address are never shown publicly.</p></div>
          <Field label="Listing title"><Input value={form.listing_title} maxLength={160} onChange={(event) => update('listing_title', event.target.value)} placeholder="Two-bedroom garden residence"/></Field>
          <Field label="Description"><Textarea value={form.listing_description} maxLength={4000} onChange={(event) => update('listing_description', event.target.value)} placeholder="Describe the layout, natural light and what makes this unit distinctive."/></Field>
          <Field label="Amenities (comma-separated)"><Input value={form.amenities} onChange={(event) => update('amenities', event.target.value)} placeholder="Secure parking, Patio, Fibre-ready"/></Field>
          <Field label="Availability"><Select value={form.availability_status} onChange={(event) => update('availability_status', event.target.value)}><option value="available">Available</option><option value="occupied">Occupied</option><option value="not_available">Not available</option></Select></Field>
          <label className="flex items-start gap-3 rounded-lg border border-ink/15 bg-paper p-3.5"><input type="checkbox" checked={form.is_public_listing} onChange={(event) => update('is_public_listing', event.target.checked)} className="mt-1 h-4 w-4 accent-accent"/><span><span className="block text-sm font-medium text-ink">Publish this unit</span><span className="mt-0.5 block text-xs leading-relaxed text-ink-muted">Requires a title, description, amenities, room measurements and at least one photo. Only available units appear on the public complex page.</span></span></label>
        </section>
        <section className="space-y-3 border-t border-ink/10 pt-5">
          <div className="flex items-center justify-between gap-3"><div><h3 className="text-sm font-semibold text-ink">Unit photographs</h3><p className="mt-1 text-xs text-ink-muted">{(photos.data ?? []).length} of 8 photographs</p></div><label className="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-ink/15 px-3 text-xs font-medium hover:bg-ink/5">{photoBusy ? 'Uploading…' : 'Add photo'}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadPhoto} disabled={photoBusy || (photos.data?.length ?? 0) >= 8} className="sr-only"/></label></div>
          {photoError ? <ErrorState message={photoError.message} requestId={photoError.requestId}/> : null}
          {photos.error ? <ErrorState message={photos.error.message} requestId={photos.error.requestId} action={<Button variant="secondary" onClick={photos.reload}>Try again</Button>}/> : null}
          {photos.loading ? <LoadingState label="Loading unit photographs"/> : (photos.data ?? []).length ? <div className="grid grid-cols-2 gap-3">{photos.data.map((photo) => <div key={photo.photo_id} className="overflow-hidden rounded-lg border border-ink/10"><img src={publicPhotoUrl(photo.public_id, 'thumb')} alt={photo.caption || form.listing_title || property.unit_no} className="aspect-[4/3] w-full object-cover"/><div className="flex items-center justify-between gap-2 p-2"><span className="truncate text-[11px] text-ink-muted">{photo.caption || 'Unit photograph'}</span><button type="button" onClick={() => deletePhoto(photo.photo_id)} className="text-[11px] font-medium text-signal hover:underline">Remove</button></div></div>)}</div> : <p className="rounded-lg border border-dashed border-ink/20 px-4 py-5 text-center text-xs text-ink-muted">Add clear photographs of this specific unit, not just the complex.</p>}
        </section>
      </div>
    </Drawer>;
}
function PropertyDrawer({ property, mine, isAdmin, onClose, onEdit, }) {
    return (<Drawer open onClose={onClose} title={property.unit_no} subtitle={`${property.complex_name} · unit #${property.id}`}>
      <div className="space-y-6">
        <div className="flex flex-wrap gap-2">
          {mine ? <Chip tone="progress" glyph="◆">Your unit</Chip> : null}
          {property.estate_id ? <Chip>Estate #{property.estate_id}</Chip> : <Chip tone="warn">No estate</Chip>}
        </div>

        <dl className="space-y-3">
          {[
            ['Street address', property.street_address],
            ['Suburb', property.suburb ?? '—'],
            ['Size', metres(property.size_m2)],
            ['Bedrooms', property.bedrooms === null ? '—' : String(property.bedrooms)],
            ['Bathrooms', property.bathrooms === null ? '—' : String(property.bathrooms)],
        ].map(([label, value]) => (<div key={label} className="flex items-baseline justify-between gap-4 border-b border-ink/10 pb-2">
              <dt className="text-[12.5px] text-ink-muted">{label}</dt>
              <dd className="num text-[13px] font-medium">{value}</dd>
            </div>))}
        </dl>

        <div className="border-l-2 border-l-ochre bg-ochre-wash px-3.5 py-3">
          <p className="text-[12.5px] text-ink-soft">
            This unit is the operational anchor for resident access, maintenance issues and the
            evidence that follows their resolution. VALORA does not use it as a market listing.
          </p>
        </div>
        {isAdmin ? <Button variant="secondary" onClick={onEdit}>Edit unit</Button> : null}
      </div>
    </Drawer>);
}
function PropertiesBody() {
    const { estateId, estate } = useEstateScope();
    const { user } = useAuth();
    const isAdmin = user?.role === 'hoa_admin';
    const myUnits = new Set(estate?.property_ids ?? []);
    const [bedrooms, setBedrooms] = useState('');
    const [minSize, setMinSize] = useState('');
    const [selected, setSelected] = useState(null);
    const [creating, setCreating] = useState(false);
    const [editing, setEditing] = useState(null);
    const properties = useAsync(() => api.get('/api/v1/properties', {
        estate_id: estateId,
        size: 100,
        bedrooms: bedrooms === '' ? undefined : Number(bedrooms),
        min_size_m2: minSize === '' ? undefined : Number(minSize),
    }), [estateId, bedrooms, minSize]);
    const items = properties.data?.items ?? [];
    const showOnlyMine = user?.role === 'resident' && myUnits.size > 0;
    const visible = showOnlyMine ? items.filter((item) => myUnits.has(item.id)) : items;
    return (<div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Estate register
          </p>
          <h1 className="mt-2 text-[26px] leading-tight font-semibold">Properties</h1>
          <p className="mt-1 text-[13.5px] text-ink-muted">
            Every registered unit in this estate. Operational history attaches to these records.
          </p>
        </div>
        {isAdmin ? (<Button variant="primary" onClick={() => setCreating(true)}>
            <IconPlus size={16}/>
            Add a unit
          </Button>) : null}
      </header>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <label className="min-w-[10rem] flex-1">
          <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Bedrooms
          </span>
          <Select value={bedrooms} onChange={(event) => setBedrooms(event.target.value)}>
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map((count) => (<option key={count} value={count}>
                {count}
              </option>))}
          </Select>
        </label>
        <label className="min-w-[10rem] flex-1">
          <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Minimum size (m²)
          </span>
          <Input inputMode="numeric" value={minSize} onChange={(event) => setMinSize(event.target.value)} placeholder="100"/>
        </label>
        <p className="num text-[12.5px] text-ink-muted">
          {properties.data?.total ?? 0} units on record
        </p>
      </Card>

      {properties.loading ? (<LoadingState label="Loading properties"/>) : properties.error ? (<ErrorState message={properties.error.message} requestId={properties.error.requestId}/>) : visible.length === 0 ? (<EmptyState title={showOnlyMine ? 'No unit linked to your account' : 'No units match these filters'} body={showOnlyMine
                ? 'Your membership does not reference a property yet. Ask your HOA to link your unit.'
                : 'Clear the filters, or add the estate’s units to the register.'} action={isAdmin ? (<Button variant="primary" onClick={() => setCreating(true)}>
                Add a unit
              </Button>) : undefined}/>) : (<TableShell>
          <thead>
            <tr>
              <Th className="w-24">Unit</Th>
              <Th>Address</Th>
              <Th className="w-32">Suburb</Th>
              <Th className="w-24 text-right">Size</Th>
              <Th className="w-20 text-right">Beds</Th>
              <Th className="w-20 text-right">Baths</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((property) => (<tr key={property.id} onClick={() => setSelected(property)} className={cx('cursor-pointer transition-colors hover:bg-accent-wash/40', selected?.id === property.id && 'bg-accent-wash/60')}>
                <Td className="num font-medium">
                  <span className="flex items-center gap-2">
                    {property.unit_no}
                    {myUnits.has(property.id) ? <span className="h-1.5 w-1.5 bg-accent" title="Your unit"/> : null}
                  </span>
                </Td>
                <Td>
                  {property.street_address}
                  <span className="block text-[11.5px] text-ink-muted">{property.complex_name}</span>
                </Td>
                <Td className="text-ink-soft">{property.suburb ?? '—'}</Td>
                <Td className="num text-right">{metres(property.size_m2)}</Td>
                <Td className="num text-right">{property.bedrooms ?? '—'}</Td>
                <Td className="num text-right">{property.bathrooms ?? '—'}</Td>
              </tr>))}
          </tbody>
        </TableShell>)}

      {selected ? (<PropertyDrawer property={selected} mine={myUnits.has(selected.id)} isAdmin={isAdmin} onClose={() => setSelected(null)} onEdit={() => setEditing(selected)}/>) : null}

      {editing ? <EditPropertyDrawer property={editing} onClose={() => setEditing(null)} onDone={() => { setEditing(null); setSelected(null); properties.reload(); }}/> : null}

      {creating ? (<CreatePropertyDrawer onClose={() => setCreating(false)} onDone={() => {
                setCreating(false);
                properties.reload();
            }}/>) : null}

      <p className="flex items-center gap-2 text-[12px] text-ink-muted">
        <IconHome size={15}/>
        Listing and sale routes are disabled in this build — VALORA is not a marketplace.
      </p>
    </div>);
}
export function Properties() {
    return (<RequireEstate>
      <PropertiesBody />
    </RequireEstate>);
}
