import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Group,
  Loader,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { Clock, Tag } from 'lucide-react';
import { generateClientVoyaReference } from '@/utils/voyaClientReference';
import { useVoucherRedemption } from '../hooks/useVoucherRedemption';
import { formatCurrencyFromCents } from '@/features/flights/utils/flightUtils';
import { useGetFrontendConfigQuery } from '@/api';
import { showErrorToast } from '@/utils/toast';

function buildReservedForCheckoutCopy(
  reservationExpiresAt: string | undefined,
  reservationTtlMinutes: number | undefined
): string {
  const fallbackNoMinutes =
    "This promo code is reserved for this checkout. If you don't continue to payment, you can apply the same code again after the reservation period ends.";
  const fallbackWithMinutes = (m: number) =>
    `This promo code is reserved for this checkout. If you don't continue to payment, you can apply the same code again after about ${m} minutes.`;
  if (!reservationExpiresAt) {
    return reservationTtlMinutes != null ? fallbackWithMinutes(reservationTtlMinutes) : fallbackNoMinutes;
  }
  const end = new Date(reservationExpiresAt);
  if (Number.isNaN(end.getTime())) {
    return reservationTtlMinutes != null ? fallbackWithMinutes(reservationTtlMinutes) : fallbackNoMinutes;
  }
  const mins = Math.max(1, Math.round((end.getTime() - Date.now()) / 60_000));
  const timeStr = end.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return `This promo is held for this checkout until about ${timeStr} (~${mins} min from now). If you leave without paying, you can apply the same code again after that reservation ends.`;
}

export interface PromoCodeFieldApplied {
  redemptionId: string;
  discountCents: number;
  code: string;
  reservationExpiresAt?: string;
  checkoutVoyaReference: string;
}

export interface PromoCodeFieldProps {
  bookingType: 'flight' | 'hotel';
  /** Pre-discount total in cents (USD). */
  amountCents: number;
  currencyCode: string;
  applied: PromoCodeFieldApplied | null;
  onApplied: (value: PromoCodeFieldApplied) => void;
  onCleared: () => void;
  /** High-contrast panel for the last block before "Continue to payment". */
  emphasized?: boolean;
}

/**
 * Promo / G2A voucher entry for USD checkout only (parent should not render otherwise).
 */
export function PromoCodeField({
  bookingType,
  amountCents,
  currencyCode,
  applied,
  onApplied,
  onCleared,
  emphasized = false,
}: PromoCodeFieldProps) {
  const { data: frontendConfig } = useGetFrontendConfigQuery();
  const reservationTtlMinutes = frontendConfig?.voucherReservationTtlMinutes;
  const { applyVoucher, releaseVoucher, busy } = useVoucherRedemption();
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleApply = async () => {
    const code = input.trim();
    if (!code) {
      setError('Enter a promo code.');
      return;
    }
    setError(null);
    const checkoutVoyaReference =
      applied?.checkoutVoyaReference ?? generateClientVoyaReference();
    const result = await applyVoucher({
      code,
      voyaBookingReference: checkoutVoyaReference,
      amountCents,
      bookingType,
      applyErrorOptions: { reservationTtlMinutes: reservationTtlMinutes },
    });
    if (!result.ok) {
      showErrorToast(result.error);
      return;
    }
    onApplied({
      redemptionId: result.applied.redemptionId,
      discountCents: result.applied.discountCents,
      code: result.applied.code,
      reservationExpiresAt: result.applied.reservationExpiresAt,
      checkoutVoyaReference,
    });
    setInput('');
  };

  const handleRemove = async () => {
    if (!applied) return;
    setError(null);
    await releaseVoucher(applied.redemptionId, 'user_removed');
    onCleared();
    setInput('');
  };

  const upper = currencyCode.toUpperCase();
  const postCents = Math.max(0, amountCents - (applied?.discountCents ?? 0));
  const emphasizedPanelStyle: React.CSSProperties = {
    marginBottom: 0,
    padding: 20,
    borderRadius: 8,
    backgroundColor: 'var(--mantine-color-brand-9)',
    color: 'var(--mantine-color-white)',
    border: '1px solid var(--mantine-color-brand-6)',
    boxShadow: 'var(--mantine-shadow-md)',
  };
  const outerStyle: React.CSSProperties = emphasized ? emphasizedPanelStyle : { marginBottom: 16 };

  if (applied) {
    return (
      <Box style={outerStyle}>
        {emphasized && (
          <Group gap="xs" align="center" mb="sm">
            <Tag size={22} style={{ opacity: 0.9 }} />
            <Text fw={700} size="md" c="inherit">
              Promo code applied
            </Text>
          </Group>
        )}
        {emphasized && (
          <Group
            gap="sm"
            align="flex-start"
            wrap="nowrap"
            mb="sm"
            style={{
              padding: 14,
              paddingLeft: 12,
              borderRadius: 12,
              border: '1px solid rgba(255,255,255,0.14)',
              borderLeft: '3px solid rgba(255,255,255,0.5)',
              background:
                'linear-gradient(110deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.04) 100%)',
            }}
          >
            <Box
              aria-hidden
              style={{
                flexShrink: 0,
                width: 40,
                height: 40,
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'rgba(255,255,255,0.12)',
                color: 'rgba(255,255,255,0.92)',
                border: '1px solid rgba(255,255,255,0.1)',
              }}
            >
              <Clock size={22} />
            </Box>
            <Box style={{ minWidth: 0, flex: 1 }}>
              <Text fw={600} size="sm" c="white" mb={4} style={{ letterSpacing: 0.1 }}>
                Code reserved for this booking
              </Text>
              <Text
                size="sm"
                style={{
                  color: 'rgba(255,255,255,0.78)',
                  lineHeight: 1.55,
                  maxWidth: '52ch',
                }}
              >
                {buildReservedForCheckoutCopy(applied.reservationExpiresAt, reservationTtlMinutes)}
              </Text>
            </Box>
          </Group>
        )}
        <Alert
          color="green"
          variant={emphasized ? 'outline' : 'light'}
          style={{
            backgroundColor: emphasized ? 'rgba(255,255,255,0.12)' : undefined,
            color: emphasized ? 'white' : undefined,
            borderColor: emphasized ? 'rgba(255,255,255,0.35)' : undefined,
          }}
        >
          <Stack gap="xs">
            <Group justify="space-between" gap="xs" wrap="wrap">
              <Text size="sm" style={emphasized ? { color: 'white' } : undefined}>
                <strong>{applied.code}</strong> — {formatCurrencyFromCents(applied.discountCents, upper)} off
              </Text>
              <Button
                size="xs"
                tt="none"
                onClick={handleRemove}
                disabled={busy}
                variant={emphasized ? 'outline' : 'subtle'}
                style={
                  emphasized
                    ? { color: 'white', borderColor: 'rgba(255,255,255,0.5)' }
                    : undefined
                }
              >
                {busy ? <Loader size={16} /> : 'Remove'}
              </Button>
            </Group>
            <Group gap="md" align="baseline" wrap="wrap" pt={4}>
              <Text
                size="sm"
                c={emphasized ? undefined : 'dimmed'}
                style={{
                  textDecoration: 'line-through',
                  ...(emphasized ? { color: 'rgba(255,255,255,0.65)' } : null),
                }}
              >
                Was {formatCurrencyFromCents(amountCents, upper)}
              </Text>
              <Text
                size="lg"
                fw={800}
                style={{
                  color: emphasized ? 'white' : 'var(--mantine-color-green-9)',
                }}
              >
                Now {formatCurrencyFromCents(postCents, upper)}
              </Text>
            </Group>
          </Stack>
        </Alert>
      </Box>
    );
  }

  return (
    <Box style={outerStyle}>
      {emphasized && (
        <Group gap="xs" align="center" mb="sm">
          <Tag size={22} style={{ opacity: 0.9 }} />
          <Text fw={700} size="md" c="inherit">
            Have a promo code?
          </Text>
        </Group>
      )}
      {!emphasized && (
        <Text fw={600} size="sm" mb="xs">
          Promo code
        </Text>
      )}
      <Text
        size="xs"
        c={emphasized ? undefined : 'dimmed'}
        mb="xs"
        style={emphasized ? { opacity: 0.85, color: 'inherit' } : undefined}
      >
        USD vouchers only.{' '}
        {reservationTtlMinutes != null ? (
          <>
            Each apply holds the code for about {reservationTtlMinutes} minutes — complete payment before it
            expires.
          </>
        ) : (
          <>Each apply holds the code for a limited time — complete payment before it expires.</>
        )}
      </Text>
      <Group gap="xs" wrap="wrap" align="flex-start">
        <TextInput
          size="sm"
          label="Code"
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          disabled={busy}
          style={{ minWidth: 200, flex: 1 }}
          styles={
            emphasized
              ? {
                  input: {
                    backgroundColor: 'var(--mantine-color-body)',
                    color: 'var(--mantine-color-dark-8)',
                  },
                  label: { color: 'var(--mantine-color-dimmed)' },
                }
              : undefined
          }
          onKeyDown={(e) => {
            if (e.key === 'Enter') void handleApply();
          }}
        />
        <Button
          variant={emphasized ? 'filled' : 'outline'}
          color={emphasized ? undefined : 'grape'}
          tt="none"
          fw={600}
          onClick={() => void handleApply()}
          disabled={busy}
          style={
            emphasized
              ? {
                  backgroundColor: 'var(--mantine-color-white)',
                  color: 'var(--mantine-color-brand-9)',
                  fontWeight: 700,
                  boxShadow: 'var(--mantine-shadow-sm)',
                }
              : undefined
          }
        >
          {busy ? <Loader size={20} color={emphasized ? 'var(--mantine-color-brand-9)' : undefined} /> : 'Apply'}
        </Button>
      </Group>
      {error && (
        <Alert
          color="red"
          mt="sm"
          withCloseButton
          onClose={() => setError(null)}
          style={{
            backgroundColor: emphasized ? 'var(--mantine-color-red-9)' : undefined,
            color: emphasized ? 'white' : undefined,
          }}
        >
          {error}
        </Alert>
      )}
    </Box>
  );
}
