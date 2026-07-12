import { useState, useEffect, useRef } from 'react';
import type { CSSProperties } from 'react';
import { useAppSelector } from '@/store';
import { resolveBackendAssetUrl } from '@/utils/apiAssetUrl';

export interface AuthenticatedImageProps {
  /** Protected URL (e.g. /api/places/photos/.../media) - requires JWT to fetch */
  url: string;
  alt: string;
  /** Fallback shown while loading or on error; avoids returning null */
  fallbackSrc?: string;
  /** Render with custom CSS; merges with default img styles. Named `sx` for backwards compat with the previous MUI version — accepts any plain CSSProperties object. */
  sx?: CSSProperties;
  onError?: () => void;
  onLoad?: () => void;
}

const baseImgStyle: CSSProperties = {
  display: 'block',
  maxWidth: '100%',
  maxHeight: '100%',
  width: '100%',
  height: '100%',
  objectFit: 'cover',
};

/**
 * Fetches a protected image URL with Authorization header and renders via blob URL.
 * Use for Places photo media and other endpoints that require JWT.
 * Revokes blob URL on unmount to avoid leaks.
 */
export function AuthenticatedImage({
  url,
  alt,
  fallbackSrc,
  sx = {},
  onError,
  onLoad,
}: AuthenticatedImageProps) {
  const token = useAppSelector((s) => s.auth.token);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const blobRef = useRef<string | null>(null);
  const onErrorRef = useRef(onError);
  const onLoadRef = useRef(onLoad);
  onErrorRef.current = onError;
  onLoadRef.current = onLoad;

  useEffect(() => {
    setBlobUrl(null);
    setFailed(false);

    if (!url || !token) {
      setFailed(true);
      onErrorRef.current?.();
      return;
    }

    const fetchUrl = resolveBackendAssetUrl(url);
    let cancelled = false;
    fetch(fetchUrl, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        const objUrl = URL.createObjectURL(blob);
        blobRef.current = objUrl;
        setBlobUrl(objUrl);
        onLoadRef.current?.();
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
          onErrorRef.current?.();
        }
      });
    return () => {
      cancelled = true;
      const toRevoke = blobRef.current;
      blobRef.current = null;
      if (toRevoke) URL.revokeObjectURL(toRevoke);
    };
  }, [url, token]);

  const imgStyle: CSSProperties = { ...baseImgStyle, ...sx };
  if (failed || !blobUrl) {
    return fallbackSrc ? (
      <img src={fallbackSrc} alt={alt} style={imgStyle} />
    ) : (
      <div style={{ ...imgStyle, backgroundColor: 'var(--mantine-color-gray-2)' }} aria-hidden />
    );
  }

  return (
    <img
      src={blobUrl}
      alt={alt}
      loading="lazy"
      onError={() => {
        setFailed(true);
        onErrorRef.current?.();
      }}
      style={imgStyle}
    />
  );
}
