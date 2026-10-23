import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Reset the document scroll before paint whenever the active route changes.
 * URL hashes are intentional in-page navigation and take precedence over reset.
 * This is mounted once above the router's route tree so public and authenticated
 * routes receive the same behaviour.
 */
export function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useLayoutEffect(() => {
    const root = document.documentElement;
    const scroller = document.scrollingElement ?? root;
    const previousBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';

    try {
      if (hash) {
        const target = document.getElementById(decodeURIComponent(hash.slice(1)));
        if (target) {
          const top = target.getBoundingClientRect().top + window.scrollY;
          scroller.scrollTop = top;
          root.scrollTop = top;
          if (document.body) document.body.scrollTop = top;
          return;
        }
      }

      scroller.scrollTop = 0;
      root.scrollTop = 0;
      if (document.body) document.body.scrollTop = 0;
    } finally {
      root.style.scrollBehavior = previousBehavior;
    }
  }, [pathname, hash]);

  return null;
}
