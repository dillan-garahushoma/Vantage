import { useCallback, useEffect, useRef, useState } from 'react'
import { IconChevronLeft, IconChevronRight, IconClose, IconExpand } from './Icons'
import { Photo } from './Photo'
import { EmptyState, cx } from './ui'
import type { PublicPhoto } from '../lib/contract'
import { photoAlt, publicPhotoUrl } from '../lib/publicDirectory'

/**
 * The photographs an estate published, as a hero mosaic with a viewer.
 *
 * Two things shape this file.
 *
 * The **mosaic** is built from whatever count the estate published — one, two,
 * three, four, or the 1 + 4 arrangement — because a gallery that only looks
 * right at five photographs looks broken at one, and one is the common case.
 * Tiles past the first are desktop-only: a 390px page that stacks five
 * photographs pushes the description, the location and the join steps a long way
 * down, so on a phone the lead photograph carries the section and the same
 * "Show all" button opens the rest.
 *
 * When an estate publishes more than the mosaic can hold, the last tile becomes
 * the **overflow tile**: the concealed photograph under a controlled blur, with
 * the count of everything behind it (`+8 more`), and it opens the viewer. An
 * estate with twenty photographs shows four clearly, then says how many are left
 * rather than trailing off at five as if that were all — and an estate with five
 * gets no blur at all, because nothing is hidden.
 *
 * The **viewer** is a modal dialog, not a bigger image: focus moves into it,
 * `Tab` stays in it, `Escape` closes it, the body cannot scroll behind it, and
 * the tile that opened it gets focus back. Photographs are the one thing on this
 * page that people actually look at, so they are also the one thing that must be
 * usable from a keyboard.
 */

/** Everything focusable inside the dialog, in document order. */
const FOCUSABLE = 'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'

/**
 * Tile geometry per published-photograph count.
 *
 * Every tile keeps a reserved box (an `aspect-ratio`), so the mosaic has its
 * final height before any file loads. The arrangements only apply from `lg` up:
 * below that the gallery is the lead photograph and the button that opens the
 * rest, because four tiles of a 700px band are smaller than one useful
 * photograph.
 */
function arrangement(count: number): { grid: string; tiles: string[] } {
  if (count === 1) {
    return { grid: 'grid grid-cols-1 gap-2', tiles: ['aspect-[3/2] max-h-[560px] w-full'] }
  }
  if (count === 2) {
    return {
      grid: 'grid grid-cols-1 gap-2 lg:grid-cols-2',
      tiles: ['aspect-[3/2]', 'aspect-[3/2] hidden lg:block'],
    }
  }
  if (count === 3) {
    return {
      grid: 'grid grid-cols-1 gap-2 lg:grid-cols-3 lg:grid-rows-2',
      tiles: [
        'aspect-[3/2] lg:aspect-auto lg:col-span-2 lg:row-span-2',
        'aspect-[3/2] hidden lg:block',
        'aspect-[3/2] hidden lg:block',
      ],
    }
  }
  if (count === 4) {
    return {
      grid: 'grid grid-cols-1 gap-2 lg:grid-cols-3 lg:grid-rows-2',
      tiles: [
        'aspect-[3/2] lg:aspect-auto lg:col-span-2',
        'aspect-[4/3] hidden lg:block',
        'aspect-[4/3] hidden lg:block lg:col-span-2',
        'aspect-[4/3] hidden lg:block',
      ],
    }
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
  }
}

/**
 * The mosaic, plus how many photographs it can actually show clearly.
 *
 * `clear` is the number of plain tiles and `overflow` is how many photographs
 * the last tile conceals — zero when the mosaic shows everything, so nothing is
 * ever blurred or counted for nothing. The two always add up to `count`.
 *
 * Exported because the arithmetic is the part that goes wrong: an off-by-one
 * here either hides a photograph nobody can reach, or promises "+2 more" over a
 * gallery that has already shown them all.
 */
export function mosaic(count: number): {
  grid: string
  tiles: string[]
  clear: number
  overflow: number
} {
  const geometry = arrangement(count)
  const slots = geometry.tiles.length
  const overflow = count > slots ? count - (slots - 1) : 0
  return {
    ...geometry,
    clear: overflow > 0 ? slots - 1 : Math.min(count, slots),
    overflow,
  }
}

function PhotoViewer({
  estateName,
  photos,
  index,
  onStep,
  onClose,
}: {
  estateName: string
  photos: PublicPhoto[]
  index: number
  onStep: (delta: number) => void
  onClose: () => void
}) {
  const panel = useRef<HTMLDivElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)

  // Focus enters the dialog; `PhotoGallery` puts it back on the tile afterwards.
  useEffect(() => {
    closeButton.current?.focus()
  }, [])

  // The page behind a full-screen viewer must not scroll under it.
  useEffect(() => {
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key === 'ArrowRight') {
        onStep(1)
        return
      }
      if (event.key === 'ArrowLeft') {
        onStep(-1)
        return
      }
      if (event.key !== 'Tab' || !panel.current) return
      const focusable = Array.from(panel.current.querySelectorAll<HTMLElement>(FOCUSABLE))
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement
      if (event.shiftKey && (active === first || !panel.current.contains(active))) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, onStep])

  const photo = photos[index]
  if (!photo) return null
  const many = photos.length > 1
  const stepClass =
    'absolute top-1/2 z-10 -translate-y-1/2 rounded-xs border border-paper/25 bg-ink/60 p-2 text-paper/85 hover:border-paper/60 hover:text-paper'

  return (
    <div
      ref={panel}
      role="dialog"
      aria-modal="true"
      aria-label={`Photographs of ${estateName}`}
      className="fixed inset-0 z-50 flex flex-col bg-ink"
    >
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <p aria-live="polite" className="num text-[12.5px] text-paper/80">
          {index + 1} of {photos.length}
        </p>
        <button
          ref={closeButton}
          type="button"
          onClick={onClose}
          aria-label="Close the photo viewer"
          className="rounded-xs border border-paper/25 p-2 text-paper/85 hover:border-paper/60 hover:text-paper"
        >
          <IconClose size={18} />
        </button>
      </div>

      <div className="relative flex min-h-0 flex-1 items-center justify-center px-3 sm:px-16">
        {many ? (
          <button
            type="button"
            onClick={() => onStep(-1)}
            aria-label="Previous photograph"
            className={cx(stepClass, 'left-3')}
          >
            <IconChevronLeft size={20} />
          </button>
        ) : null}

        <Photo
          src={publicPhotoUrl(photo.public_id, 'full')}
          alt={photoAlt(estateName, photo.caption)}
          width={1920}
          height={1280}
          loading="eager"
          fallbackLabel="Photograph unavailable"
          className="max-h-full max-w-full object-contain"
        />

        {many ? (
          <button
            type="button"
            onClick={() => onStep(1)}
            aria-label="Next photograph"
            className={cx(stepClass, 'right-3')}
          >
            <IconChevronRight size={20} />
          </button>
        ) : null}
      </div>

      <div className="px-4 py-3">
        {photo.caption ? <p className="text-[13px] text-paper/85">{photo.caption}</p> : null}
        <p className="num mt-1 text-[11px] text-paper/55">
          {estateName} · published by its administrator
        </p>
      </div>
    </div>
  )
}

export function PhotoGallery({ estateName, photos }: { estateName: string; photos: PublicPhoto[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null)
  const returnFocus = useRef<HTMLElement | null>(null)

  const close = useCallback(() => {
    setOpenIndex(null)
    returnFocus.current?.focus()
    returnFocus.current = null
  }, [])

  const step = useCallback(
    (delta: number) =>
      setOpenIndex((current) =>
        current === null ? current : (current + delta + photos.length) % photos.length,
      ),
    [photos.length],
  )

  if (photos.length === 0) {
    return (
      <EmptyState
        title="No photographs published yet"
        body="This estate has published its profile but has not added any photographs."
      />
    )
  }

  const { grid, tiles, clear, overflow } = mosaic(photos.length)
  // `clear` plain tiles, then — only if photographs are left over — one tile
  // that carries the count of them.
  const shown = photos.slice(0, clear)

  return (
    <div className="relative">
      <div className={grid}>
        {shown.map((photo, index) => (
          <button
            key={photo.public_id}
            type="button"
            onClick={(event) => {
              returnFocus.current = event.currentTarget
              setOpenIndex(index)
            }}
            aria-label={`Open photograph ${index + 1} of ${photos.length}: ${photoAlt(estateName, photo.caption)}`}
            className={cx(
              'group relative block overflow-hidden border border-ink/15 bg-ink/5',
              tiles[index],
            )}
          >
            <Photo
              // The lead tile is the widest thing on the page, so it gets the
              // stored full image; the small tiles are inside the thumbnail's
              // 480px long side and never need it.
              src={publicPhotoUrl(photo.public_id, index === 0 ? 'full' : 'thumb')}
              alt={photoAlt(estateName, photo.caption)}
              width={index === 0 ? 1920 : 480}
              height={index === 0 ? 1280 : 320}
              loading={index === 0 ? 'eager' : 'lazy'}
              fallbackLabel="Photograph unavailable"
              className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-[1.02]"
            />
          </button>
        ))}

        {overflow > 0 ? (
          <button
            type="button"
            onClick={(event) => {
              returnFocus.current = event.currentTarget
              // The tile *is* the concealed photographs, so it opens on the
              // first of them rather than sending the visitor back to the start.
              setOpenIndex(clear)
            }}
            aria-label={`Show all ${photos.length} photographs, including ${overflow} not shown here`}
            className={cx(
              'group relative block overflow-hidden border border-ink/15 bg-ink/5',
              tiles[tiles.length - 1],
            )}
          >
            <Photo
              // A thumbnail never needs the stored full image, and a blurred
              // one least of all: every tile here is inside the 480px long side.
              src={publicPhotoUrl(photos[clear].public_id, 'thumb')}
              alt=""
              width={480}
              height={320}
              fallbackLabel="Photographs"
              className="h-full w-full scale-105 object-cover blur-[3px] transition-transform duration-200 group-hover:scale-[1.08]"
            />
            {/* The scrim is what makes the count readable over a photograph
                nobody chose for its contrast. */}
            <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-ink/50 px-2 text-center text-paper">
              <span className="num text-[19px] leading-none font-semibold">+{overflow} more</span>
              <span className="text-[11.5px] text-paper/85">Open the full gallery</span>
            </span>
          </button>
        ) : null}
      </div>

      {photos.length > 1 ? (
        <button
          type="button"
          onClick={(event) => {
            returnFocus.current = event.currentTarget
            setOpenIndex(0)
          }}
          className={cx(
            // Frosted rather than opaque: this control lands on top of a
            // photograph the estate chose, and a translucent panel keeps the
            // picture visible while holding the text legible.
            'absolute right-3 bottom-3 z-10 inline-flex items-center gap-2 rounded-xs border border-ink/25 bg-surface/80 px-3 py-2 text-[12.5px] font-medium backdrop-blur-md hover:bg-surface',
            // At `lg` and up the overflow tile already says this, and once is
            // enough; below `lg` that tile is hidden and this is the only way in.
            overflow > 0 && 'lg:hidden',
          )}
        >
          <IconExpand size={15} />
          Show all {photos.length} photos
        </button>
      ) : null}

      {openIndex === null ? null : (
        <PhotoViewer
          estateName={estateName}
          photos={photos}
          index={openIndex}
          onStep={step}
          onClose={close}
        />
      )}
    </div>
  )
}
