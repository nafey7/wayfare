import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Box,
  Button,
  Group,
  Modal,
  PasswordInput,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { Lock, Tag, CalendarDays, ChevronRight } from 'lucide-react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { useChangePasswordMutation } from '@/api/usersApi';
import { ROUTES } from '@/features/routing';
import { NAVY, MUTED, LINE, MIST } from '../profileTokens';

const ADMIN_NAV_ITEMS = [
  { icon: <Tag size={16} color={MUTED} />, label: 'Discounts', sub: 'Manage voucher batches', route: ROUTES.ADMIN_DISCOUNTS },
  { icon: <CalendarDays size={16} color={MUTED} />, label: 'Booking Management', sub: 'View and manage all bookings', route: ROUTES.ADMIN_BOOKINGS },
];

export function SecuritySection({ isAdmin = false }: { isAdmin?: boolean }) {
  const [open, setOpen] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [changePassword, { isLoading }] = useChangePasswordMutation();

  const handleClose = () => {
    setOpen(false);
    setError(null);
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  const handleSubmit = async () => {
    setError(null);
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    try {
      await changePassword({ oldPassword, newPassword }).unwrap();
      handleClose();
    } catch (e) {
      setError(
        e && typeof e === 'object' && 'data' in e
          ? String(
              (e as { data?: { detail?: string } }).data?.detail ??
                'Failed to change password',
            )
          : 'Failed to change password',
      );
    }
  };

  return (
    <>
      <Text
        style={{
          fontSize: 28,
          fontWeight: 700,
          color: LANDING_TOKENS.textColor,
          fontFamily: LANDING_TOKENS.fontFamily.display,
          marginBottom: 8,
        }}
      >
        Login &amp; Security
      </Text>
      <Text
        style={{ fontSize: 13, color: MUTED, marginBottom: 24, lineHeight: 1.6 }}
      >
        Manage your account security and login preferences.
      </Text>

      <Box
        style={{
          background: 'white',
          borderRadius: 14,
          border: `1px solid ${LINE}`,
          overflow: 'hidden',
        }}
      >
        <Box
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
          }}
        >
          <Box style={{ flex: 1, minWidth: 0 }}>
            <Text style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>
              Password
            </Text>
            <Text style={{ fontSize: 12, color: MUTED, marginTop: 4 }}>
              Keep your account secure with a strong, unique password.
            </Text>
          </Box>
          <UnstyledButton
            onClick={() => setOpen(true)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              border: `1px solid ${LINE}`,
              borderRadius: 999,
              padding: '6px 14px',
              fontSize: 13,
              fontWeight: 600,
              color: NAVY,
              cursor: 'pointer',
              flexShrink: 0,
              marginLeft: 16,
              background: 'transparent',
            }}
          >
            <Lock size={14} />
            Change password
          </UnstyledButton>
        </Box>
      </Box>

      {isAdmin && (
        <Box
          style={{
            background: 'white',
            borderRadius: 14,
            border: `1px solid ${LINE}`,
            overflow: 'hidden',
            marginTop: 24,
          }}
        >
          <Box style={{ padding: '16px 20px 12px' }}>
            <Text style={{ fontSize: 14, fontWeight: 700, color: NAVY }}>Administration</Text>
            <Text style={{ fontSize: 12, color: MUTED, marginTop: 4 }}>Admin tools and management.</Text>
          </Box>

          {ADMIN_NAV_ITEMS.map((item, i) => (
            <Box key={item.route}>
              {i > 0 && <Box style={{ height: 1, background: LINE, margin: '0 20px' }} />}
              <UnstyledButton
                component={Link}
                to={item.route}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '14px 20px',
                  width: '100%',
                  transition: 'background 120ms',
                }}
                styles={{ root: { '&:hover': { background: MIST } } }}
              >
                <Box
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: MIST,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  {item.icon}
                </Box>
                <Box style={{ flex: 1, minWidth: 0 }}>
                  <Text style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>{item.label}</Text>
                  <Text style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>{item.sub}</Text>
                </Box>
                <ChevronRight size={16} color={MUTED} style={{ flexShrink: 0 }} />
              </UnstyledButton>
            </Box>
          ))}
        </Box>
      )}

      <Modal
        opened={open}
        onClose={handleClose}
        title={
          <Text fw={700} size="lg">
            Change password
          </Text>
        }
        size="md"
        radius="md"
        centered
      >
        <Stack gap="md" pt={4}>
          <PasswordInput
            label="Current password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.currentTarget.value)}
            size="sm"
            autoComplete="current-password"
            radius="md"
          />
          <PasswordInput
            label="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.currentTarget.value)}
            size="sm"
            autoComplete="new-password"
            radius="md"
          />
          <PasswordInput
            label="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.currentTarget.value)}
            size="sm"
            autoComplete="new-password"
            radius="md"
          />
          {error && (
            <Text c="red" size="sm">
              {error}
            </Text>
          )}
          <Group justify="flex-end" gap="xs">
            <Button
              variant="subtle"
              tt="none"
              onClick={() => {
                setOpen(false);
                setError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isLoading}
              tt="none"
              fw={600}
              style={{ backgroundColor: NAVY, color: 'white' }}
            >
              {isLoading ? 'Changing...' : 'Change password'}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
