import { useState, useEffect } from 'react';

/**
 * Sticky-header collapse hook with hysteresis.
 * Collapses once scrollTop exceeds collapseAt, and only expands again
 * when scrollTop drops below expandAt. The dead-zone between the two
 * thresholds prevents rapid toggling when the user lingers near the boundary.
 */
export function useScrollCollapsed(collapseAt: number, expandAt: number): boolean {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const el = document.getElementById('main-scroll-root') ?? window;
    const getY = () =>
      el === window ? window.scrollY : (el as HTMLElement).scrollTop;

    let rafId: number | null = null;

    const handler = () => {
      if (rafId !== null) return;
      rafId = requestAnimationFrame(() => {
        rafId = null;
        const y = getY();
        setCollapsed((prev) => {
          if (!prev && y > collapseAt) return true;
          if (prev && y < expandAt) return false;
          return prev;
        });
      });
    };

    el.addEventListener('scroll', handler, { passive: true });
    handler();
    return () => {
      el.removeEventListener('scroll', handler);
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, [collapseAt, expandAt]);

  return collapsed;
}
