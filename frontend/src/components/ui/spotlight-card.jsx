import { useRef } from 'react';
import { cx } from '../ui';

/**
 * SpotlightCard — a card whose rim lights up around the cursor.
 *
 * The point is local: the card listens on itself, not on `document`, so a page of
 * six complexes tracks one pointer instead of six global listeners, and the glow
 * is a masked ring rather than a background repaint, so nothing reflows.
 *
 * Touch and pen are ignored on purpose. `pointermove` fires on a tap, and without
 * the check the last-tapped card would stay lit until the next tap elsewhere.
 */
export function SpotlightCard({ as: Tag = 'div', className, children, ...rest }) {
  const ref = useRef(null);

  function track(event) {
    if (event.pointerType && event.pointerType !== 'mouse') return;
    const node = ref.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    node.style.setProperty('--spot-x', `${event.clientX - rect.left}px`);
    node.style.setProperty('--spot-y', `${event.clientY - rect.top}px`);
    node.dataset.glowing = 'true';
  }

  function dim() {
    if (ref.current) ref.current.dataset.glowing = 'false';
  }

  return (
    <Tag
      ref={ref}
      onPointerMove={track}
      onPointerLeave={dim}
      onPointerCancel={dim}
      className={cx('spotlight-card', className)}
      {...rest}
    >
      <span className="spotlight-glow" aria-hidden="true" />
      {children}
    </Tag>
  );
}
