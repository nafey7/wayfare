import { useState, useEffect, useRef } from 'react';

/**
 * Returns true when the user is scrolling down past 60px so the BottomNav
 * can slide out of view during content reading.
 */
export function useScrollDirectionHidden(): boolean {
  const [hidden, setHidden] = useState(false);
  const lastY = useRef(0);

  useEffect(() => {
    const el = document.getElementById('main-scroll-root') ?? window;
    const getY = () => el === window ? window.scrollY : (el as HTMLElement).scrollTop;

    // Seed from actual position so the first handler delta is correct
    lastY.current = getY();

    let ticking = false;
    const handler = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = getY();
        if (y > lastY.current && y > 60) {
          setHidden(true);
        } else if (y < lastY.current) {
          setHidden(false);
        }
        lastY.current = y;
        ticking = false;
      });
    };

    el.addEventListener('scroll', handler, { passive: true });
    return () => el.removeEventListener('scroll', handler);
  }, []);

  return hidden;
}
