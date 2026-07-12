/**
 * Shared user avatar.
 *
 * Picks the right imgproxy URL from `photoUrls` based on a size preset and
 * falls back to initials when the user has no uploaded photo or the image
 * fails to load (e.g. S3 key drift after a wipe).
 */

import { Avatar, type AvatarProps, Text } from '@mantine/core';
import { useState } from 'react';
import type { PhotoUrls } from '@/types/auth';

export type VoyaAvatarSize = 'sm' | 'md' | 'lg';

const SIZE_PX: Record<VoyaAvatarSize, number> = {
  sm: 32,
  md: 48,
  lg: 96,
};

const FONT_PX: Record<VoyaAvatarSize, number> = {
  sm: 13,
  md: 18,
  lg: 32,
};

export interface VoyaAvatarProps extends Omit<AvatarProps, 'src' | 'size'> {
  photoUrls?: PhotoUrls | null;
  displayName?: string | null;
  size?: VoyaAvatarSize | number;
  /** Optional explicit fallback src (e.g. legacy `profileImage` URL). */
  fallbackSrc?: string | null;
}

function deriveInitials(displayName: string | null | undefined): string {
  if (!displayName) return '?';
  const parts = displayName.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0]?.[0]?.toUpperCase() ?? '?';
  }
  return (
    (parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')
  ).toUpperCase();
}

export function VoyaAvatar({
  photoUrls,
  displayName,
  size = 'md',
  fallbackSrc,
  ...rest
}: VoyaAvatarProps) {
  const [errored, setErrored] = useState(false);

  const presetKey: VoyaAvatarSize = typeof size === 'string' ? size : 'lg';
  const sizePx = typeof size === 'number' ? size : SIZE_PX[presetKey];
  const fontPx = typeof size === 'number' ? Math.round(size * 0.4) : FONT_PX[presetKey];

  const src = errored
    ? null
    : (photoUrls?.[presetKey] ?? fallbackSrc ?? null);

  return (
    <Avatar
      src={src ?? undefined}
      size={sizePx}
      radius="xl"
      imageProps={{
        // Fall back to initials if the signed URL 404s (e.g. local MinIO wipe).
        onError: () => setErrored(true),
        alt: displayName ? `${displayName} profile photo` : 'profile photo',
      }}
      {...rest}
    >
      <Text style={{ fontSize: fontPx, fontWeight: 800 }}>
        {deriveInitials(displayName)}
      </Text>
    </Avatar>
  );
}

export default VoyaAvatar;
