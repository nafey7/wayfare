import { useState, useEffect } from 'react';
import { resolveHotelImageUrl } from '@/features/chat/utils/hotelUtils';
import type { MappedHotel } from '@/features/chat/utils/hotelUtils';

const MAX_BEST_DISPLAY = 3;
/**
 * Per-image probe timeout. Some hotel thumbnail URLs neither load nor fire an
 * error event (e.g. CORS-blocked hosts, fixture URLs pointing at unreachable
 * domains). Without a cap, ``Promise.all`` below would never settle and the
 * "Loading best options…" placeholder would hang forever.
 */
const IMAGE_PROBE_TIMEOUT_MS = 2500;

function checkImageAccessible(url: string): Promise<boolean> {
  if (!url) return Promise.resolve(false);
  return new Promise((resolve) => {
    const img = new Image();
    let timer: ReturnType<typeof setTimeout> | null = null;
    const done = (ok: boolean) => {
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
      img.onload = null;
      img.onerror = null;
      img.src = '';
      resolve(ok);
    };
    img.onload = () => done(true);
    img.onerror = () => done(false);
    timer = setTimeout(() => done(false), IMAGE_PROBE_TIMEOUT_MS);
    img.src = url;
  });
}

/**
 * From the Best value hotel list (up to 20 from backend), returns at most 3 hotels
 * that have accessible thumbnail images, in original order. Used only for the Best tab.
 */
export function useBestHotelsWithValidImages(
  mappedBestHotels: MappedHotel[] | null | undefined
): { hotels: MappedHotel[]; isLoading: boolean } {
  const [hotels, setHotels] = useState<MappedHotel[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!mappedBestHotels?.length) {
      setHotels([]);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    const n = mappedBestHotels.length;
    const results: { hotel: MappedHotel; ok: boolean }[] = [];

    const tryComplete = () => {
      const withValidImages: MappedHotel[] = [];
      for (let i = 0; i < n && withValidImages.length < MAX_BEST_DISPLAY; i++) {
        const r = results[i];
        if (r === undefined) return;
        if (r.ok) withValidImages.push(r.hotel);
      }
      if (withValidImages.length >= MAX_BEST_DISPLAY) {
        if (!cancelled) {
          setHotels(withValidImages.slice(0, MAX_BEST_DISPLAY));
          setIsLoading(false);
        }
      }
    };

    const promises = mappedBestHotels.map((hotel, index) => {
      const url = resolveHotelImageUrl(hotel.thumbnail_url);
      return checkImageAccessible(url ?? '').then((ok) => {
        if (cancelled) return;
        results[index] = { hotel, ok };
        tryComplete();
      });
    });

    void Promise.all(promises).then(() => {
      if (cancelled) return;
      const withValidImages = results
        .filter((r): r is { hotel: MappedHotel; ok: boolean } => r != null && r.ok)
        .slice(0, MAX_BEST_DISPLAY)
        .map((r) => r.hotel);
      if (!cancelled) {
        setHotels(withValidImages);
        setIsLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [mappedBestHotels]);

  return { hotels, isLoading };
}
