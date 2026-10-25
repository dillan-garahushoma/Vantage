import { useCallback, useEffect, useRef, useState } from 'react';
import { IconChevronLeft, IconChevronRight, IconClose, IconExpand, IconGrid } from './Icons';
import { Photo } from './Photo';
import { EmptyState, cx } from './ui';
import { photoAlt, publicPhotoUrl } from '../lib/publicDirectory';
/**
 * The photographs an estate published, as a hero mosaic with a viewer.
 */
const FOCUSABLE = 'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

function arrangement(count) {
    if (count === 1) {
        return { grid: 'grid grid-cols-1 gap-2', tiles: ['aspect-[3/2] max-h-[560px] w-full'] };
    }
    if (count === 2) {
        return {
            grid: 'grid grid-cols-1 gap-2 lg:grid-cols-2',
            tiles: ['aspect-[3/2]', 'aspect-[3/2] hidden lg:block'],
        };
    }
    if (count === 3) {
        return {
            grid: 'grid grid-cols-1 gap-2 lg:grid-cols-2',
            tiles: [
                'aspect-[3/2] lg:aspect-auto lg:row-span-2',
                'aspect-[3/2] hidden lg:block',
                'aspect-[3/2] hidden lg:block',
            ],
        };
    }
    if (count === 4) {
        return {
            grid: 'grid w-full grid-cols-2 gap-2 lg:grid-cols-4 lg:grid-rows-2',
            tiles: [
                'aspect-[4/3] lg:aspect-auto lg:col-span-2 lg:row-span-2',
                'aspect-[4/3]',
                'aspect-[4/3]',
                'aspect-[4/3]',
            ],
        };
    }
    return {
        grid: 'grid grid-cols-1 gap-2 lg:grid-cols-4 lg:grid-rows-2',
        tiles: [
            'aspect-[3/2] lg:aspect-auto lg:col-span-2 lg:row-span-2',
            'aspect-[4/3] hidden lg:block',
            'aspect-[4/3] hidden lg:block',
            'aspect-[4/3] hidden lg:block',
            'aspect-[4/3] hidden lg:block',
        ],
    };
}

export function mosaic(count) {
    const geometry = arrangement(count);
    const slots = geometry.tiles.length;
    const overflow = count > slots ? count - (slots - 1) : 0;
    return {
        ...geometry,
        clear: overflow > 0 ? slots - 1 : Math.min(count, slots),
        overflow,
    };
}

function PhotoViewer({ estateName, photos, index, onStep, onClose, }) {
    const panel = useRef(null);
    const closeButton = useRef(null);
    useEffect(() => {
        closeButton.current?.focus();
        const previous = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = previous;
        };
    }, []);
    useEffect(() => {
        function onKey(event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                onClose();
                return;
            }
            if (event.key === 'ArrowRight') {
                onStep(1);
                return;
            }
            if (event.key === 'ArrowLeft') {
                onStep(-1);
                return;
            }
            if (event.key !== 'Tab' || !panel.current)
                return;
            const focusable = Array.from(panel.current.querySelectorAll(FOCUSABLE));
            if (focusable.length === 0)
                return;
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            const active = document.activeElement;
            if (event.shiftKey && (active === first || !panel.current.contains(active))) {
                event.preventDefault();
                last.focus();
            }
            else if (!event.shiftKey && active === last) {
                event.preventDefault();
                first.focus();
            }
        }
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose, onStep]);
    const photo = photos[index];
    if (!photo)
        return null;
    const many = photos.length > 1;
    const stepClass = 'absolute top-1/2 z-10 -translate-y-1/2 rounded-xs border border-paper/25 bg-ink/60 p-2 text-paper/85 hover:border-paper/60 hover:text-paper';
    return (<div ref={panel} role="dialog" aria-modal="true" aria-label={`Photographs of ${estateName}`} className="fixed inset-0 z-50 flex flex-col bg-ink">
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <p aria-live="polite" className="num text-[12.5px] text-paper/80">
          {index + 1} of {photos.length}
        </p>
        <button ref={closeButton} type="button" onClick={onClose} aria-label="Close the photo viewer" className="rounded-xs border border-paper/25 p-2 text-paper/85 hover:border-paper/60 hover:text-paper">
          <IconClose size={18}/>
        </button>
      </div>

      <div className="relative flex min-h-0 flex-1 items-center justify-center px-3 sm:px-16">
        {many ? (<button type="button" onClick={() => onStep(-1)} aria-label="Previous photograph" className={cx(stepClass, 'left-3')}>
            <IconChevronLeft size={20}/>
          </button>) : null}

        <Photo src={publicPhotoUrl(photo.public_id, 'full')} alt={photoAlt(estateName, photo.caption)} width={1920} height={1280} loading="eager" fallbackLabel="Photograph unavailable" className="max-h-full max-w-full object-contain"/>

        {many ? (<button type="button" onClick={() => onStep(1)} aria-label="Next photograph" className={cx(stepClass, 'right-3')}>
            <IconChevronRight size={20}/>
          </button>) : null}
      </div>

      <div className="px-4 py-3">
        {photo.caption ? <p className="text-[13px] text-paper/85">{photo.caption}</p> : null}
        <p className="num mt-1 text-[11px] text-paper/55">
          {estateName} · published by its administrator
        </p>
      </div>
    </div>);
}

export function PhotoGallery({ estateName, photos }) {
    const [openIndex, setOpenIndex] = useState(null);
    const returnFocus = useRef(null);
    const close = useCallback(() => {
        setOpenIndex(null);
        returnFocus.current?.focus();
        returnFocus.current = null;
    }, []);
    const step = useCallback((delta) => setOpenIndex((current) => current === null ? current : (current + delta + photos.length) % photos.length), [photos.length]);
    if (photos.length === 0) {
        return (<EmptyState title="No photographs published yet" body="This estate has published its profile but has not added any photographs."/>);
    }
    const { grid, tiles, clear, overflow } = mosaic(photos.length);
    const shown = photos.slice(0, clear);
    return (<div className="relative w-full overflow-hidden rounded-2xl lg:h-[320px] xl:h-[380px]">
      <div className={grid}>
        {shown.map((photo, index) => (<button key={photo.public_id} type="button" onClick={(event) => {
                returnFocus.current = event.currentTarget;
                setOpenIndex(index);
            }} aria-label={`Open photograph ${index + 1} of ${photos.length}: ${photoAlt(estateName, photo.caption)}`} className={cx('group relative block overflow-hidden border border-ink/15 bg-ink/5', tiles[index])}>
            <Photo
        src={publicPhotoUrl(photo.public_id, index === 0 ? 'full' : 'thumb')} alt={photoAlt(estateName, photo.caption)} width={index === 0 ? 1920 : 480} height={index === 0 ? 1280 : 320} loading={index === 0 ? 'eager' : 'lazy'} fallbackLabel="Photograph unavailable" className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-[1.02]"/>
          </button>))}

        {overflow > 0 ? (<button type="button" onClick={(event) => {
                returnFocus.current = event.currentTarget;
                setOpenIndex(clear);
            }} aria-label={`Show all ${photos.length} photographs, including ${overflow} not shown here`} className={cx('group relative block overflow-hidden border border-ink/15 bg-ink/5', tiles[tiles.length - 1])}>
            <Photo
        src={publicPhotoUrl(photos[clear].public_id, 'thumb')} alt="" width={480} height={320} fallbackLabel="Photographs" className="h-full w-full scale-105 object-cover blur-[3px] transition-transform duration-200 group-hover:scale-[1.08]"/>
            <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-ink/50 px-2 text-center text-paper">
              <span className="num text-[19px] leading-none font-semibold">+{overflow} more</span>
              <span className="text-[11.5px] text-paper/85">Open the full gallery</span>
            </span>
          </button>) : null}
      </div>

      {photos.length > 1 ? (<button type="button" onClick={(event) => {
                returnFocus.current = event.currentTarget;
                setOpenIndex(0);
            }} className={cx(
            'absolute right-3.5 bottom-3.5 z-10 inline-flex items-center gap-2 rounded-xl border border-ink/20 bg-surface/90 px-3.5 py-2 text-[13px] font-medium text-ink shadow-sm backdrop-blur-md transition-all hover:bg-surface hover:shadow-md hover:border-ink/40 active:scale-95',
          )}>
          <IconGrid size={15}/>
          Show all {photos.length} photos
        </button>) : null}

      {openIndex === null ? null : (<PhotoViewer estateName={estateName} photos={photos} index={openIndex} onStep={step} onClose={close}/>)}
    </div>);
}
