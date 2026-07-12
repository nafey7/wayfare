import { useEffect, useRef, useState } from 'react';

import { useAppSelector } from '@/store/hooks';
import { selectAuthToken } from '@/store/slices/authSlice';

// Build-time constant — same pattern as useSendChatMessage.ts
const API_BASE: string = (import.meta.env.VITE_API_URL as string | undefined) || '/api';

interface UsePlacesImageOptions {
  place: string;
  disabled?: boolean;
  rootMargin?: number;
}

interface UsePlacesImageResult {
  ref: React.RefObject<HTMLElement | null>;
  objectUrl: string | null;
}

/**
 * Lazy-loads a Google Places image (#1143).
 *
 * Separates visibility detection from fetching so a late-arriving JWT
 * token (Redux hydration after first render) doesn't permanently block
 * the fetch. Two independent effects:
 *   1. Visibility effect: sets `visible` via IntersectionObserver.
 *   2. Fetch effect: fires as soon as BOTH `visible` AND `token` are set.
 *      Uses an AbortController so place changes or unmount cancel in-flight
 *      requests and prevent stale setObjectUrl calls.
 */
export function usePlacesImage({
  place,
  disabled = false,
  rootMargin = 150,
}: UsePlacesImageOptions): UsePlacesImageResult {
  const ref = useRef<HTMLElement | null>(null);
  const token = useAppSelector(selectAuthToken);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  // Effect 1: visibility detection — fires once and stays
  useEffect(() => {
    if (disabled || !place.trim()) return;

    const el = ref.current;
    if (!el) return;

    if (typeof IntersectionObserver !== 'undefined') {
      const observer = new IntersectionObserver(
        (entries) => {
          if (entries[0]?.isIntersecting) {
            setVisible(true);
            observer.disconnect();
          }
        },
        { rootMargin: `${rootMargin}px` },
      );
      observer.observe(el);
      return () => observer.disconnect();
    } else {
      setVisible(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disabled, place, rootMargin]);

  // Effect 2: fetch — AbortController ensures unmount / place change cancels
  // any in-flight request before it can call setObjectUrl on a stale render.
  useEffect(() => {
    if (!visible || !token || !place.trim() || objectUrl || disabled) return;

    const controller = new AbortController();

    async function doFetch(): Promise<void> {
      try {
        const urlRes = await fetch(
          `${API_BASE}/places/image-url?place=${encodeURIComponent(place.trim())}&max_width_px=400`,
          { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal },
        );
        if (!urlRes.ok) return;

        const json = (await urlRes.json()) as { imageUrl?: string };
        const proxyUrl = json.imageUrl;
        if (!proxyUrl) return;

        const imgRes = await fetch(proxyUrl, {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'default',
          signal: controller.signal,
        });
        if (!imgRes.ok) return;

        const blob = await imgRes.blob();
        setObjectUrl(URL.createObjectURL(blob));
      } catch {
        // silently skip — includes AbortError on cleanup
      }
    }

    void doFetch();
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, token, place, disabled]);

  // Revoke blob URL on unmount to release memory
  useEffect(() => {
    const url = objectUrl;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [objectUrl]);

  return { ref, objectUrl };
}
