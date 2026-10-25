import { Building2 } from 'lucide-react';
import { listEstatePhotos } from '../lib/estateAdmin';
import { publicPhotoUrl } from '../lib/publicDirectory';
import { useAsync } from '../lib/useAsync';
import { Photo } from './Photo';

function SelectedEstateImage({ estate, className = '', compact = false }) {
  const photos = useAsync(() => listEstatePhotos(estate.estate_id), [estate.estate_id]);
  const cover = Array.isArray(photos.data) ? photos.data[0] : null;
  const label = photos.loading ? 'Loading estate photo' : photos.error ? 'Estate photo unavailable' : 'Estate photo not added yet';
  if (!cover?.public_id) {
    return (
      <div className={`flex flex-col items-center justify-center gap-2 bg-brand-wash text-brand-ink ${className}`} role={photos.loading ? 'status' : 'img'} aria-label={label}>
        <Building2 className={compact ? 'h-5 w-5' : 'h-8 w-8 opacity-45'} aria-hidden="true" />
        {!compact ? <span className="px-4 text-center text-xs">{label}</span> : <span className="sr-only">{label}</span>}
      </div>
    );
  }
  return <Photo key={cover.public_id} src={publicPhotoUrl(cover.public_id)} alt={`${cover.caption || 'Estate photograph'} — ${estate.estate_name}`} className={`object-cover ${className}`} fallbackLabel="Estate photo unavailable" />;
}

/** Only authorised, uploaded photos represent an estate. A new estate resets image state. */
export function EstateImage({ estate, ...props }) {
  if (!estate?.estate_id) return <div className={`bg-brand-wash ${props.className ?? ''}`} />;
  return <SelectedEstateImage key={estate.estate_id} estate={estate} {...props} />;
}
