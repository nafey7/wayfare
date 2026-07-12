import { useState, useCallback, useEffect, useRef } from 'react';
import type { CSSProperties } from 'react';
import { useLazyGetPlaceImageUrlQuery } from '@/api/placesApi';
import { useAppSelector } from '@/store';
import { resolveBackendAssetUrlOptional } from '@/utils/apiAssetUrl';
import { AuthenticatedImage } from './AuthenticatedImage';

export interface HotelImageWithFallbackProps {
  /** Primary image URL (thumbnail, imageUrl, images[0]) - may be null */
  primaryUrl: string | null | undefined;
  hotelName: string;
  city?: string | null;
  address?: string | null;
  fallbackSrc: string;
  alt: string;
  /** CSS overrides; named `sx` for backwards compat with the previous MUI version. */
  sx?: CSSProperties;
}

const baseStyle: CSSProperties = {
  display: 'block',
  width: '100%',
  height: '100%',
  objectFit: 'cover',
};

/**
 * Resolve Google Places image URL for hotel fallback.
 * Uses HotelName, City format for better match quality.
 */
async function resolvePlacesFallback(
  trigger: ReturnType<typeof useLazyGetPlaceImageUrlQuery>[0],
  hotelName: string,
  city?: string | null,
  address?: string | null,
): Promise<string | null> {
  const place = city
    ? `${hotelName}, ${city}`.trim()
    : address
      ? `${hotelName}, ${String(address).split(',')[0]?.trim() || ''}`.trim()
      : hotelName;
  const placeClean = place.replace(/,\s*,/g, ',').replace(/,\s*$/, '').trim();
  if (!placeClean) return null;
  try {
    const result = await trigger({ place: placeClean, maxWidthPx: 400 }).unwrap();
    return result?.imageUrl ?? null;
  } catch {
    return null;
  }
}

/**
 * Hotel image with Google Places fallback.
 * 1. Primary: render primary image when available and loads.
 * 2. On missing or onError: call /api/places/image-url, render via AuthenticatedImage.
 * 3. On API failure: show fallback SVG.
 */
export function HotelImageWithFallback({
  primaryUrl,
  hotelName,
  city,
  address,
  fallbackSrc,
  alt,
  sx = {},
}: HotelImageWithFallbackProps) {
  const token = useAppSelector((s) => s.auth.token);
  const [trigger] = useLazyGetPlaceImageUrlQuery();
  const [primaryError, setPrimaryError] = useState(false);
  const [placesUrl, setPlacesUrl] = useState<string | null>(null);
  const [placesFailed, setPlacesFailed] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    setPrimaryError(false);
    setPlacesUrl(null);
    setPlacesFailed(false);
  }, [primaryUrl]);

  const fullPrimary = resolveBackendAssetUrlOptional(primaryUrl);
  const showPrimary = fullPrimary && !primaryError;

  const tryPlacesFallback = useCallback(() => {
    if (!token || placesFailed || placesUrl) return;
    void resolvePlacesFallback(trigger, hotelName, city, address)
      .then((url) => {
        if (!mountedRef.current) return;
        if (url) setPlacesUrl(url);
        else setPlacesFailed(true);
      })
      .catch(() => {
        if (mountedRef.current) setPlacesFailed(true);
      });
  }, [token, trigger, hotelName, city, address, placesFailed, placesUrl]);

  const handlePlacesImageError = useCallback(() => {
    setPlacesFailed(true);
    setPlacesUrl(null);
  }, []);

  useEffect(() => {
    if (token && !fullPrimary && !placesFailed && !placesUrl) {
      tryPlacesFallback();
    }
  }, [token, fullPrimary, placesFailed, placesUrl, tryPlacesFallback]);

  if (showPrimary) {
    return (
      <img
        src={fullPrimary}
        alt={alt}
        loading="lazy"
        onError={() => {
          setPrimaryError(true);
          tryPlacesFallback();
        }}
        style={{ ...baseStyle, ...sx }}
      />
    );
  }

  if (placesUrl && !placesFailed) {
    return (
      <AuthenticatedImage
        url={placesUrl}
        alt={alt}
        fallbackSrc={fallbackSrc}
        sx={sx}
        onError={handlePlacesImageError}
      />
    );
  }

  return (
    <img
      src={fallbackSrc}
      alt={alt}
      style={{ ...baseStyle, ...sx }}
    />
  );
}
