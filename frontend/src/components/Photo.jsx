import { useState } from 'react';
import { cx } from './ui';
/**
 * One photograph, in a box the caller has already reserved.
 *
 * The stored files are whatever an administrator uploaded, so the caller always
 * decides the box (`aspect-[3/2]`, a mosaic tile, a full-screen viewer) and the
 * crop (`object-cover` in a grid, `object-contain` in the viewer). What this
 * component adds is the failure path: when a file is gone — a deleted upload, or
 * a `public_id` the API no longer serves — the *same* box stays on screen, filled
 * by `PhotoFallback`, instead of the browser's broken-image glyph. Nothing moves.
 */
export function PhotoFallback({ label, className }) {
    return (<div role="img" aria-label={label} className={cx('survey-grid flex items-center justify-center bg-ink/5 px-3 text-center text-[12px] text-ink-muted', className)}>
      {label}
    </div>);
}
export function Photo({ src, alt, width, height, className, fallbackLabel, loading = 'lazy', }) {
    const [failed, setFailed] = useState(false);
    if (!src || failed) {
        return <PhotoFallback label={fallbackLabel ?? alt} className={className}/>;
    }
    return (<img src={src} alt={alt} width={width} height={height} loading={loading} decoding="async" onError={() => setFailed(true)} className={className}/>);
}
