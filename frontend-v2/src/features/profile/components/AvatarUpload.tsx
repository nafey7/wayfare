/**
 * Profile photo upload / replace / delete control.
 *
 * Renders the current avatar large and lets the user pick a new file or
 * remove the existing one. Validation mirrors the backend: 5 MiB, JPEG/PNG/WebP.
 */

import { Box, Button, Group, Modal, Stack, Text } from '@mantine/core';
import { useCallback, useRef, useState } from 'react';
import {
  useUploadProfilePhotoMutation,
  useDeleteProfilePhotoMutation,
} from '@/api/usersApi';
import { useAppDispatch } from '@/store';
import { setUserPhoto } from '@/store/slices/authSlice';
import { VoyaAvatar } from '@/components/VoyaAvatar';
import type { PhotoUrls } from '@/types/auth';

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPTED_MIME = ['image/jpeg', 'image/png', 'image/webp'];

export interface AvatarUploadProps {
  photoUrls: PhotoUrls | null | undefined;
  displayName: string | null | undefined;
  fallbackSrc?: string | null;
}

export function AvatarUpload({
  photoUrls,
  displayName,
  fallbackSrc,
}: AvatarUploadProps) {
  const dispatch = useAppDispatch();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [uploadPhoto, { isLoading: uploading }] = useUploadProfilePhotoMutation();
  const [deletePhoto, { isLoading: deleting }] = useDeleteProfilePhotoMutation();

  const handlePick = useCallback(() => {
    setError(null);
    inputRef.current?.click();
  }, []);

  const handleFile = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      // Always clear the input so the same file can be re-selected after error.
      e.target.value = '';
      if (!file) return;

      if (!ACCEPTED_MIME.includes(file.type)) {
        setError('Photo must be a JPEG, PNG, or WebP image.');
        return;
      }
      if (file.size > MAX_BYTES) {
        setError('Photo must be 5 MB or smaller.');
        return;
      }

      try {
        const result = await uploadPhoto(file).unwrap();
        dispatch(
          setUserPhoto({
            photoKey: result.photoKey,
            photoUrls: result.photoUrls,
          })
        );
      } catch (err) {
        const detail =
          err && typeof err === 'object' && 'data' in err
            ? String(
                (err as { data?: { detail?: string } }).data?.detail ??
                  'Upload failed'
              )
            : 'Upload failed';
        setError(detail);
      }
    },
    [uploadPhoto, dispatch]
  );

  const handleDeleteClick = useCallback(() => {
    setError(null);
    setConfirmOpen(true);
  }, []);

  const confirmDelete = useCallback(async () => {
    setConfirmOpen(false);
    try {
      await deletePhoto().unwrap();
      dispatch(setUserPhoto({ photoKey: null, photoUrls: null }));
    } catch (err) {
      const detail =
        err && typeof err === 'object' && 'data' in err
          ? String(
              (err as { data?: { detail?: string } }).data?.detail ??
                'Failed to remove photo'
            )
          : 'Failed to remove photo';
      setError(detail);
    }
  }, [deletePhoto, dispatch]);

  const hasPhoto = Boolean(photoUrls?.lg);
  const busy = uploading || deleting;

  return (
    <Stack gap="sm">
      <Group gap="lg" align="center" wrap="nowrap">
        <Box style={{ position: 'relative' }}>
          <VoyaAvatar
            photoUrls={photoUrls}
            displayName={displayName}
            fallbackSrc={fallbackSrc}
            size={96}
          />
        </Box>
        <Stack gap={6}>
          <Group gap="sm">
            <Button
              variant="light"
              size="sm"
              radius="xl"
              onClick={handlePick}
              loading={uploading}
              disabled={busy}
              aria-label={hasPhoto ? 'Change profile photo' : 'Upload profile photo'}
            >
              {hasPhoto ? 'Change photo' : 'Upload photo'}
            </Button>
            {hasPhoto && (
              <Button
                variant="subtle"
                color="red"
                size="sm"
                radius="xl"
                onClick={handleDeleteClick}
                loading={deleting}
                disabled={busy}
                aria-label="Remove profile photo"
              >
                Remove
              </Button>
            )}
          </Group>
          <Text size="xs" c="dimmed">
            JPEG, PNG, or WebP. Max 5 MB.
          </Text>
          {error && (
            <Text size="xs" c="red" role="alert">
              {error}
            </Text>
          )}
        </Stack>
      </Group>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_MIME.join(',')}
        onChange={handleFile}
        style={{ display: 'none' }}
        data-testid="avatar-upload-input"
      />
      <Modal
        opened={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Remove profile photo?"
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Your profile photo will be removed and replaced with your initials.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button
              variant="default"
              size="sm"
              radius="xl"
              onClick={() => setConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              color="red"
              size="sm"
              radius="xl"
              onClick={confirmDelete}
              loading={deleting}
            >
              Remove
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

export default AvatarUpload;
