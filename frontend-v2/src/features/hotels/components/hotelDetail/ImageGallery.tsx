import { useCallback, useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { Box, Button, Group, Stack } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Images } from 'lucide-react';

import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import {
  buildPlacePhotoProxyUrl,
  useLazySearchPlaceQuery,
} from '@/api/placesApi';
import { useAppSelector } from '@/store';
import { resolveBackendAssetUrlOptional } from '@/utils/apiAssetUrl';

import { AuthenticatedImage } from '../AuthenticatedImage';
import { HOTEL_DETAIL_TOKENS } from './hotelDetailTokens';

/** Figma node 77:10959 — Image Gallery (hero + 2×2 grid, "more photos" pill). */
const RADIUS_PX = 8;
const MAIN_TO_GRID_GAP_PX = 8;
const GAP_COLUMN_PX = 13.71;
const GAP_ROW_PX = 11.545;
const SMALL_W_PX = 213.591;
const SMALL_H_PX = 187.614;
const MAIN_H_PX = 390;
const RIGHT_COL_W_PX = 438.727;

/** Max thumbnails rendered in this gallery; also bounds Places photo refs. */
const MAX_TILES = 5;
/** Width hint for Places photo proxy (smaller for grid tiles, larger for hero). */
const PLACES_TILE_WIDTH_PX = 800;

const imgTileSx: CSSProperties = {
  display: 'block',
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  borderRadius: RADIUS_PX,
};

/**
 * Resolves which source to render for a fallback-chained image tile:
 * primary (backend asset) → Places proxy → static fallback. Each layer
 * is dropped once its `onError` fires; state resets when inputs change.
 */
type ImageFallbackResolution =
  | { mode: 'primary'; src: string; onError: () => void }
  | { mode: 'places'; url: string; onError: () => void }
  | { mode: 'fallback' };

function useImageFallbackChain(
  primaryUrl: string | null | undefined,
  placesProxyUrl: string | null,
): ImageFallbackResolution {
  const [primaryError, setPrimaryError] = useState(false);
  const [placesError, setPlacesError] = useState(false);

  useEffect(() => {
    setPrimaryError(false);
  }, [primaryUrl]);

  useEffect(() => {
    setPlacesError(false);
  }, [placesProxyUrl]);

  const fullPrimary = resolveBackendAssetUrlOptional(primaryUrl);
  if (fullPrimary && !primaryError) {
    return {
      mode: 'primary',
      src: fullPrimary,
      onError: () => setPrimaryError(true),
    };
  }
  if (placesProxyUrl && !placesError) {
    return {
      mode: 'places',
      url: placesProxyUrl,
      onError: () => setPlacesError(true),
    };
  }
  return { mode: 'fallback' };
}

interface FallbackTileBodyProps {
  resolved: ImageFallbackResolution;
  fallbackSrc: string;
  alt: string;
  onPrimaryError: () => void;
}

/** Renders the three-layer fallback chain. Wrapper sizing/Box lives in the parent tile. */
function FallbackTileBody({
  resolved,
  fallbackSrc,
  alt,
  onPrimaryError,
}: FallbackTileBodyProps) {
  if (resolved.mode === 'primary') {
    return (
      <img
        src={resolved.src}
        alt={alt}
        loading="lazy"
        onError={() => {
          resolved.onError();
          onPrimaryError();
        }}
        style={imgTileSx}
      />
    );
  }
  if (resolved.mode === 'places') {
    return (
      <AuthenticatedImage
        url={resolved.url}
        alt={alt}
        fallbackSrc={fallbackSrc}
        sx={imgTileSx}
        onError={resolved.onError}
      />
    );
  }
  return <img src={fallbackSrc} alt={alt} style={imgTileSx} />;
}

interface GalleryTileProps {
  primaryUrl: string | null | undefined;
  placesProxyUrl: string | null;
  fallbackSrc: string;
  alt: string;
  onPrimaryError: () => void;
  lone?: boolean;
}

function GalleryTile({
  primaryUrl,
  placesProxyUrl,
  fallbackSrc,
  alt,
  onPrimaryError,
  lone,
}: GalleryTileProps) {
  const isMd = useMediaQuery('(min-width: 768px)') ?? false;
  const resolved = useImageFallbackChain(primaryUrl, placesProxyUrl);

  return (
    <Box
      style={{
        position: 'relative',
        width: lone ? '100%' : isMd ? SMALL_W_PX : '50%',
        flex: lone ? 1 : isMd ? 'none' : 1,
        minWidth: 0,
        height: isMd ? SMALL_H_PX : 'auto',
        aspectRatio: isMd ? undefined : `${SMALL_W_PX} / ${SMALL_H_PX}`,
        borderRadius: RADIUS_PX,
        overflow: 'hidden',
        backgroundColor: 'var(--mantine-color-gray-1)',
      }}
    >
      <FallbackTileBody
        resolved={resolved}
        fallbackSrc={fallbackSrc}
        alt={alt}
        onPrimaryError={onPrimaryError}
      />
    </Box>
  );
}

interface HeroTileProps {
  primaryUrl: string | null | undefined;
  placesProxyUrl: string | null;
  fallbackSrc: string;
  alt: string;
  onPrimaryError: () => void;
}

function HeroTile({
  primaryUrl,
  placesProxyUrl,
  fallbackSrc,
  alt,
  onPrimaryError,
}: HeroTileProps) {
  const resolved = useImageFallbackChain(primaryUrl, placesProxyUrl);

  return (
    <Box
      style={{
        position: 'relative',
        width: 'auto',
        maxWidth: '100%',
        flex: '1 1 0%',
        minWidth: 0,
        height: MAIN_H_PX,
        borderRadius: RADIUS_PX,
        overflow: 'hidden',
        backgroundColor: 'var(--mantine-color-gray-1)',
      }}
    >
      <FallbackTileBody
        resolved={resolved}
        fallbackSrc={fallbackSrc}
        alt={alt}
        onPrimaryError={onPrimaryError}
      />
    </Box>
  );
}

export interface ImageGalleryProps {
  /** Optional DOM id for scroll targets (e.g. `HOTEL_DETAIL_NAV_SECTION_IDS.photos`). */
  id?: string;
  /** Unique resolved URLs (hotel + rooms). At most five are shown; omit empty slots. */
  images?: readonly string[];
  /** Same Google Places fallback as hotel search list (`HotelCard` / `HotelImageWithFallback`). */
  hotelName: string;
  city?: string | null;
  address?: string | null;
  /** Label on the dark pill (Figma: `10+ `). */
  morePhotosLabel?: string;
  onMorePhotosClick?: () => void;
}

export function ImageGallery({
  id,
  images = [],
  hotelName,
  city,
  address,
  morePhotosLabel = 'Photos',
  onMorePhotosClick,
}: ImageGalleryProps) {
  const token = useAppSelector((s) => s.auth.token);
  const [triggerSearchPlace] = useLazySearchPlaceQuery();
  const [placesPhotos, setPlacesPhotos] = useState<string[] | null>(null);
  const [placesStatus, setPlacesStatus] = useState<
    'idle' | 'loading' | 'failed'
  >('idle');

  const requestPlacesPhotos = useCallback(() => {
    if (!token) return;
    if (placesPhotos || placesStatus !== 'idle') return;

    const place = city
      ? `${hotelName}, ${city}`.trim()
      : address
        ? `${hotelName}, ${String(address).split(',')[0]?.trim() || ''}`.trim()
        : hotelName;
    const placeClean = place.replace(/,\s*,/g, ',').replace(/,\s*$/, '').trim();
    if (!placeClean) {
      setPlacesStatus('failed');
      return;
    }

    setPlacesStatus('loading');
    void triggerSearchPlace({ textQuery: placeClean, pageSize: 1 })
      .unwrap()
      .then((res) => {
        const refs = res.places?.[0]?.photos ?? [];
        if (refs.length === 0) {
          setPlacesStatus('failed');
          return;
        }
        const urls = refs
          .slice(0, MAX_TILES)
          .map((p) => buildPlacePhotoProxyUrl(p.name, PLACES_TILE_WIDTH_PX));
        setPlacesPhotos(urls);
        setPlacesStatus('idle');
      })
      .catch(() => setPlacesStatus('failed'));
  }, [token, hotelName, city, address, placesPhotos, placesStatus, triggerSearchPlace]);

  // Reset places state when hotel identity changes.
  useEffect(() => {
    setPlacesPhotos(null);
    setPlacesStatus('idle');
  }, [hotelName, city, address]);

  // Match HotelImageWithFallback: only fetch Places eagerly when there are no
  // primary images at all. Otherwise defer to the per-tile `onError` handler so
  // we avoid a Places call per hotel view when primaries load fine.
  useEffect(() => {
    if (images.length === 0) {
      requestPlacesPhotos();
    }
  }, [images.length, requestPlacesPhotos]);

  const hasReal = images.length > 0;
  const mainUrl = hasReal ? images[0]! : null;
  const restPrimary = hasReal ? images.slice(1, MAX_TILES) : [];

  // Always render 4 side tiles so the layout is stable while Places photos load;
  // each slot independently renders a placeholder until its image resolves.
  const sideSlotCount = MAX_TILES - 1;
  const showSideGrid = true;

  // Each side slot gets (a) the primary at index+1 if available, else null; and
  // (b) the Places photo at index+1 (hero consumes index 0).
  const sideSlots = Array.from({ length: sideSlotCount }, (_, i) => ({
    primaryUrl: restPrimary[i] ?? null,
    placesProxyUrl: placesPhotos?.[i + 1] ?? null,
  }));
  const row1Slots = sideSlots.slice(0, 2);
  const row2Slots = sideSlots.slice(2, 4);

  const heroPlaces = placesPhotos?.[0] ?? null;

  return (
    <Stack
      id={id}
      component="section"
      aria-label="Property photos"
      align="stretch"
      style={{ width: '100%' }}
    >
      <Group
        align="center"
        justify="flex-start"
        gap={MAIN_TO_GRID_GAP_PX}
        wrap="wrap"
        style={{ width: '100%' }}
      >
        <HeroTile
          primaryUrl={mainUrl}
          placesProxyUrl={heroPlaces}
          fallbackSrc={hotelFallback}
          alt={`${hotelName} — property photo`}
          onPrimaryError={requestPlacesPhotos}
        />

        {showSideGrid ? (
          <Stack
            gap={GAP_COLUMN_PX}
            style={{
              position: 'relative',
              width: RIGHT_COL_W_PX,
              maxWidth: '100%',
              flexShrink: 0,
              minHeight: 0,
            }}
          >
            {row1Slots.length > 0 ? (
              <Group gap={GAP_ROW_PX} wrap="nowrap" style={{ width: '100%' }}>
                {row1Slots.map((slot, i) => (
                  <GalleryTile
                    key={`r1-${i}`}
                    primaryUrl={slot.primaryUrl}
                    placesProxyUrl={slot.placesProxyUrl}
                    fallbackSrc={hotelFallback}
                    alt={`${hotelName} — photo ${i + 2}`}
                    onPrimaryError={requestPlacesPhotos}
                    lone={row1Slots.length === 1}
                  />
                ))}
              </Group>
            ) : null}

            {row2Slots.length > 0 ? (
              <Group gap={GAP_ROW_PX} wrap="nowrap" style={{ width: '100%' }}>
                {row2Slots.map((slot, i) => (
                  <GalleryTile
                    key={`r2-${i}`}
                    primaryUrl={slot.primaryUrl}
                    placesProxyUrl={slot.placesProxyUrl}
                    fallbackSrc={hotelFallback}
                    alt={`${hotelName} — photo ${row1Slots.length + i + 2}`}
                    onPrimaryError={requestPlacesPhotos}
                    lone={row2Slots.length === 1}
                  />
                ))}
              </Group>
            ) : null}

            {onMorePhotosClick ? (
              <Button
                size="xs"
                aria-label="View more photos"
                onClick={onMorePhotosClick}
                leftSection={<Images size={17} color="white" />}
                tt="none"
                styles={{
                  root: {
                    position: 'absolute',
                    right: GAP_ROW_PX,
                    bottom: GAP_ROW_PX,
                    height: 32,
                    padding: '6px 12px',
                    borderRadius: 8,
                    backgroundColor: HOTEL_DETAIL_TOKENS.overlayDark,
                    backdropFilter: 'blur(1.5px)',
                    color: 'white',
                    fontSize: 16,
                    fontWeight: 400,
                  },
                }}
              >
                {morePhotosLabel}
              </Button>
            ) : null}
          </Stack>
        ) : null}
      </Group>
    </Stack>
  );
}
