import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Every route starts at the top of the page.
 *
 * A client-side navigation keeps the scroll position of the page you left, so
 * following a link from the footer used to land halfway down the next screen.
 * This resets it on each pathname change, and honours an in-page `#hash` by
 * scrolling to that element instead.
 *
 * The reset is deliberately *not* animated: `html { scroll-behavior: smooth }`
 * would otherwise make every route change a half-second glide, so the root's
 * behaviour is pinned to `auto` for the duration of the jump. Scroll position
 * is set through `scrollTop` rather than `window.scrollTo` so the component is
 * silent under jsdom, where `scrollTo` is unimplemented.
 */
export function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    const root = document.documentElement;
    const previous = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';

    if (hash) {
      const target = document.getElementById(hash.slice(1));
      if (target) {
        root.scrollTop = target.getBoundingClientRect().top + window.scrollY;
        if (document.body) document.body.scrollTop = root.scrollTop;
        root.style.scrollBehavior = previous;
        return;
      }
    }

    root.scrollTop = 0;
    if (document.body) document.body.scrollTop = 0;
    root.style.scrollBehavior = previous;
  }, [pathname, hash]);

  return null;
}
