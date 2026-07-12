import {
  Box,
  Button,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import {
  useUpdateMeMutation,
} from '@/api/usersApi';
import { useAppDispatch } from '@/store';
import { setUser } from '@/store/slices/authSlice';
import type { ProfileUser } from '@/types/profile';
import { AvatarUpload } from './AvatarUpload';

export interface AccountSectionProps {
  user: ProfileUser | null | undefined;
}

export function AccountSection({ user }: AccountSectionProps) {
  const dispatch = useAppDispatch();
  const [updateMe, { isLoading: isUpdating }] = useUpdateMeMutation();
  const [firstName, setFirstName] = useState(user?.firstName ?? '');
  const [lastName, setLastName] = useState(user?.lastName ?? '');
  const [mobile, setMobile] = useState(user?.mobile ?? '');
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setFirstName(user?.firstName ?? '');
    setLastName(user?.lastName ?? '');
    setMobile(user?.mobile ?? '');
  }, [user?.firstName, user?.lastName, user?.mobile]);

  const handleSave = useCallback(async () => {
    setSaveError(null);
    try {
      const updatedUser = await updateMe({
        firstName: firstName.trim() || undefined,
        lastName: lastName.trim() || undefined,
        mobile: mobile.trim() || undefined,
      }).unwrap();
      dispatch(setUser(updatedUser));
    } catch (e) {
      setSaveError(
        e && typeof e === 'object' && 'data' in e
          ? String((e as { data?: { detail?: string } }).data?.detail ?? 'Failed to save')
          : 'Failed to save'
      );
    }
  }, [firstName, lastName, mobile, updateMe, dispatch]);

  return (
    <>
      <Stack gap="lg">
        <Stack gap={0}>
          <Text
            style={{
              flex: 1,
              fontSize: 28,
              fontWeight: 700,
              lineHeight: 1.29,
              color: LANDING_TOKENS.textColor,
              margin: 0,
              display: 'block',
              fontFamily: LANDING_TOKENS.fontFamily.display,
              padding: '10px 16px',
            }}
          >
            Account
          </Text>
          <Box
            style={{
              border: `1px solid ${LANDING_TOKENS.baseLighter}`,
              borderRadius: 25,
              padding: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
                <AvatarUpload
                  photoUrls={user?.photoUrls ?? null}
                  displayName={
                    [user?.firstName, user?.lastName].filter(Boolean).join(' ') ||
                    user?.email ||
                    null
                  }
                  fallbackSrc={user?.profileImage ?? null}
                />
                <Text
                  style={{
                    fontSize: 16,
                    fontWeight: 600,
                    color: LANDING_TOKENS.textColor,
                    fontFamily: LANDING_TOKENS.fontFamily.display,
                    paddingBottom: 4,
                  }}
                >
                  Personal information
                </Text>
                <Stack gap="md" style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                  <TextInput
                    label="First name"
                    value={firstName}
                    onChange={(e) => setFirstName(e.currentTarget.value)}
                    size="sm"
                    style={{ flex: 1, minWidth: 180 }}
                    radius="md"
                  />
                  <TextInput
                    label="Last name"
                    value={lastName}
                    onChange={(e) => setLastName(e.currentTarget.value)}
                    size="sm"
                    style={{ flex: 1, minWidth: 180 }}
                    radius="md"
                  />
                </Stack>
                <TextInput
                  label="Phone"
                  value={mobile}
                  onChange={(e) => setMobile(e.currentTarget.value)}
                  size="sm"
                  placeholder="+1 234 567 8900"
                  radius="md"
                  style={{ maxWidth: 320 }}
                />
                {user?.email && (
                  <Text
                    style={{
                      fontSize: 14,
                      color: LANDING_TOKENS.textHighlight,
                      fontFamily: LANDING_TOKENS.fontFamily.display,
                    }}
                  >
                    Email: {user.email} (cannot be changed)
                  </Text>
                )}
                {saveError && (
                  <Text c="red" size="sm">
                    {saveError}
                  </Text>
                )}
                <Button
                  onClick={handleSave}
                  disabled={isUpdating}
                  tt="none"
                  fw={600}
                  style={{
                    alignSelf: 'flex-start',
                    backgroundColor: LANDING_TOKENS.baseColor,
                    color: 'white',
                  }}
                >
                  {isUpdating ? 'Saving...' : 'Save changes'}
                </Button>

          </Box>
        </Stack>

      </Stack>
    </>
  );
}
