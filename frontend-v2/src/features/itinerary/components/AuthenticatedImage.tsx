import { Box, Text } from '@mantine/core';
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { runAuthRefresh } from '@/api/baseApi';
import { PLACES_SESSION_FORBIDDEN_EVENT } from '@/features/chat/constants/placesSessionEvents';
import { getPublicChatSessionId } from '@/features/chat/utils/publicChatSession';
import { toPublicPlacesPhotoUrl } from '@/features/itinerary/utils/placesPhotoUrl';
import { useLazyImage } from '@/hooks/useLazyImage';
import { store, useAppSelector } from '@/store';
import { selectAuthToken } from '@/store/slices/authSlice';
import { clearUserSession } from '@/store/thunks/clearUserSession';
import { selectPlacesSessionToken } from '@/store/slices/uiSlice';

interface AuthenticatedImageProps {
  src?: string;
  alt: string;
  /** Inline CSS for the rendered <img>; named `sx` for backwards compat with the previous MUI version. */
  sx?: CSSProperties;
  fallback?: ReactNode;
  /** Used when the guest session image returns 403 (expired token / IP mismatch). */
  unavailableLabel?: string;
}

const FORBIDDEN_BG = 'linear-gradient(135deg, rgba(190, 195, 246, 0.25) 0%, rgba(220, 224, 255, 0.35) 100%)';

/**
 * Fetches a protected image with the current JWT, or (for guests) with Places session headers.
 *
 * **Guest (public Places proxy):** loads only after the placeholder is in view (`useLazyImage`),
 * limiting fetches for security.
 * **JWT:** lazy loading is disabled so behavior matches classic immediate fetch (no IO races).
 */
export function AuthenticatedImage({
  src,
  alt,
  sx,
  fallback = null,
  unavailableLabel,
}: AuthenticatedImageProps) {
  const token = useAppSelector(selectAuthToken);
  const placesSessionToken = useAppSelector(selectPlacesSessionToken);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [sessionForbidden, setSessionForbidden] = useState(false);

  const publicChatSessionId = getPublicChatSessionId();
  const useJwt = Boolean(token);
  const isPlacesProxyUrl =
    Boolean(src) &&
    (src!.includes('/api/places/photos/') || src!.includes('/api/public/places/photos/'));
  const useSession =
    !useJwt && Boolean(placesSessionToken && publicChatSessionId && isPlacesProxyUrl);

  const { ref: lazyRef, isVisible: guestVisible } = useLazyImage({
    disabled: !useSession,
    rootMargin: '150px',
  });
  /** JWT: always true (lazy disabled). Guest session: true only after intersection. */
  const guestFetchReady = !useSession || guestVisible;

  useEffect(() => {
    setSessionForbidden(false);
  }, [src, token, placesSessionToken, publicChatSessionId]);

  useEffect(() => {
    if (!src) {
      return;
    }

    if (!useJwt && !useSession) {
      setObjectUrl(null);
      return;
    }

    if (!guestFetchReady) {
      return;
    }

    const imageSrc = useJwt ? src : toPublicPlacesPhotoUrl(src);
    const controller = new AbortController();
    let nextObjectUrl: string | null = null;
    let disposed = false;

    setObjectUrl(null);

    async function loadImage(): Promise<void> {
      try {
        const headers: Record<string, string> = {};
        if (useJwt && token) {
          headers.Authorization = `Bearer ${token}`;
        } else if (useSession && placesSessionToken && publicChatSessionId) {
          headers['X-Places-Session-Token'] = placesSessionToken;
          headers['X-Public-Chat-Session'] = publicChatSessionId;
        }

        const response = await fetch(imageSrc, {
          headers,
          signal: controller.signal,
          cache: 'default',
        });

        if (useJwt && response.status === 401) {
          const refreshed = await runAuthRefresh(store.dispatch, store.getState);
          if (refreshed) {
            return;
          }
          if (!controller.signal.aborted) {
            store.dispatch(clearUserSession());
            window.dispatchEvent(new CustomEvent('auth:expired'));
            setObjectUrl(null);
          }
          return;
        }

        if (!useJwt && (response.status === 403 || response.status === 401)) {
          if (!controller.signal.aborted) {
            setSessionForbidden(true);
            setObjectUrl(null);
            window.dispatchEvent(new CustomEvent(PLACES_SESSION_FORBIDDEN_EVENT));
          }
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to load image: ${response.status}`);
        }

        const blob = await response.blob();
        nextObjectUrl = URL.createObjectURL(blob);

        if (disposed) {
          URL.revokeObjectURL(nextObjectUrl);
          return;
        }

        setObjectUrl(nextObjectUrl);
      } catch {
        if (!controller.signal.aborted) {
          setObjectUrl(null);
        }
      }
    }

    void loadImage();

    return () => {
      disposed = true;
      controller.abort();

      if (nextObjectUrl) {
        URL.revokeObjectURL(nextObjectUrl);
      }
    };
  }, [src, useJwt, useSession, guestFetchReady, token, placesSessionToken, publicChatSessionId]);

  if (!src) {
    return <>{fallback}</>;
  }

  if (!useJwt && !useSession) {
    return <>{fallback}</>;
  }

  const showForbiddenMessage = sessionForbidden && unavailableLabel;

  return (
    <Box
      ref={lazyRef}
      style={{
        width: '100%',
        height: '100%',
        minHeight: 48,
        ...(showForbiddenMessage
          ? {
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0 8px',
              background: FORBIDDEN_BG,
            }
          : null),
      }}
    >
      {showForbiddenMessage ? (
        <Text size="xs" c="dimmed" ta="center" fw={600}>
          {unavailableLabel}
        </Text>
      ) : sessionForbidden ? (
        <>{fallback}</>
      ) : !objectUrl ? (
        <>{fallback}</>
      ) : (
        <img src={objectUrl} alt={alt} style={sx} />
      )}
    </Box>
  );
}
