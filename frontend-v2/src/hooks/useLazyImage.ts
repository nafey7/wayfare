import { useCallback, useLayoutEffect, useRef, useState } from 'react';

export interface UseLazyImageOptions {
  /** Extra pixels around the viewport / scrollports before we consider the node “in view”. */
  rootMargin?: string;
  threshold?: number | number[];
  /**
   * When true, skip visibility detection and treat as visible immediately (JWT path).
   */
  disabled?: boolean;
}

function parseRootMarginPx(rootMargin: string): number {
  const first = rootMargin.trim().split(/\s+/)[0] ?? '0';
  const n = parseFloat(first);
  return Number.isFinite(n) ? n : 0;
}

/**
 * True if `el` overlaps the window viewport (with margin) and every vertical scroll
 * ancestor’s visible client rect. Does not rely on IntersectionObserver (avoids browsers
 * where IO never delivers callbacks for nested flex/overflow trees).
 */
export function isPlaceholderInView(el: Element, marginPx: number): boolean {
  const r = el.getBoundingClientRect();
  if (r.width <= 0 && r.height <= 0) return false;

  const pad = marginPx;
  const vh = typeof window !== 'undefined' ? window.innerHeight : 0;
  const vw = typeof window !== 'undefined' ? window.innerWidth : 0;
  if (r.bottom <= -pad || r.top >= vh + pad || r.right <= -pad || r.left >= vw + pad) {
    return false;
  }

  let p: Element | null = el.parentElement;
  while (p && p !== document.documentElement) {
    const st = getComputedStyle(p);
    if (st.overflowY === 'auto' || st.overflowY === 'scroll' || st.overflowY === 'overlay') {
      const cr = p.getBoundingClientRect();
      const top = cr.top - pad;
      const left = cr.left - pad;
      const bottom = cr.bottom + pad;
      const right = cr.right + pad;
      if (r.bottom <= top || r.top >= bottom || r.right <= left || r.left >= right) {
        return false;
      }
    }
    p = p.parentElement;
  }
  return true;
}

function collectVerticalScrollAncestors(el: HTMLElement | null): HTMLElement[] {
  const out: HTMLElement[] = [];
  let p: Element | null = el?.parentElement ?? null;
  while (p && p !== document.documentElement) {
    const st = getComputedStyle(p);
    if (st.overflowY === 'auto' || st.overflowY === 'scroll' || st.overflowY === 'overlay') {
      out.push(p as HTMLElement);
    }
    p = p.parentElement;
  }
  return out;
}

/**
 * Guest Places images: become visible once the placeholder overlaps the viewport (with
 * margin) and all vertical scroll clipping ancestors — driven by scroll/resize/rAF, not IO.
 */
export function useLazyImage(options?: UseLazyImageOptions): {
  ref: (node: HTMLElement | null) => void;
  isVisible: boolean;
} {
  const { rootMargin = '150px', disabled = false } = options ?? {};
  const marginPx = parseRootMarginPx(rootMargin);
  const [isVisible, setIsVisible] = useState(() => disabled);
  const [element, setElement] = useState<HTMLElement | null>(null);
  const doneRef = useRef(false);
  const rafIdRef = useRef(0);

  const ref = useCallback((node: HTMLElement | null) => {
    setElement(node);
  }, []);

  useLayoutEffect(() => {
    doneRef.current = false;
    if (disabled) {
      setIsVisible(true);
      return;
    }
    if (!element) {
      return;
    }

    const check = (): void => {
      if (doneRef.current || !element.isConnected) return;
      const ok = isPlaceholderInView(element, marginPx);
      if (ok) {
        doneRef.current = true;
        if (rafIdRef.current) {
          cancelAnimationFrame(rafIdRef.current);
          rafIdRef.current = 0;
        }
        setIsVisible(true);
      }
    };

    const scrollers = collectVerticalScrollAncestors(element);

    window.addEventListener('resize', check, { passive: true });
    window.addEventListener('scroll', check, { capture: true, passive: true });
    for (const s of scrollers) {
      s.addEventListener('scroll', check, { passive: true });
    }

    let rafFrames = 0;
    const rafLoop = (): void => {
      check();
      rafFrames += 1;
      if (!doneRef.current && element.isConnected && rafFrames < 90) {
        rafIdRef.current = requestAnimationFrame(rafLoop);
      } else {
        rafIdRef.current = 0;
      }
    };
    rafIdRef.current = requestAnimationFrame(rafLoop);

    const safety = window.setInterval(() => {
      check();
      if (doneRef.current) {
        window.clearInterval(safety);
      }
    }, 400);

    check();

    return () => {
      doneRef.current = true;
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = 0;
      window.clearInterval(safety);
      window.removeEventListener('resize', check);
      window.removeEventListener('scroll', check, { capture: true });
      for (const s of scrollers) {
        s.removeEventListener('scroll', check);
      }
    };
  }, [element, disabled, marginPx]);

  return { ref, isVisible };
}
