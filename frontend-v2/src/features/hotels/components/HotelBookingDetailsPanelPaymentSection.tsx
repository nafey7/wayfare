import { Badge, Box, Group, Stack, Text } from '@mantine/core';
import { CreditCard } from 'lucide-react';

import { HOTEL_BOOKING_DETAILS_FF, hotelBookingDetailsPalette as palette } from './hotelBookingDetailsPanel.theme';

export interface HotelBookingDetailsPanelPaymentSectionProps {
  paymentMethodLabel: string;
  paymentTimestamp: string;
  paymentAmountFormatted: string;
  paymentApproved?: boolean;
}

export function HotelBookingDetailsPanelPaymentSection({
  paymentMethodLabel,
  paymentTimestamp,
  paymentAmountFormatted,
  paymentApproved = false,
}: HotelBookingDetailsPanelPaymentSectionProps) {
  const trimmedPaymentTime = paymentTimestamp.trim();
  const showPaymentTimestamp = Boolean(trimmedPaymentTime) && trimmedPaymentTime !== '—';

  return (
    <Stack gap="md" style={{ width: '100%' }}>
      <Text
        component="span"
        style={{
          margin: 0,
          display: 'block',
          fontFamily: HOTEL_BOOKING_DETAILS_FF,
          fontSize: '1.375rem',
          fontWeight: 700,
          lineHeight: '28px',
          color: palette.text,
        }}
      >
        Payment Confirmation
      </Text>
      <Box
        py="sm"
        px="md"
        style={{
          backgroundColor: 'white',
          border: `1px solid ${palette.cardBorder}`,
          borderRadius: 14,
          minHeight: 100,
          display: 'flex',
          alignItems: 'center',
          minWidth: 0,
        }}
      >
        <Group align="center" justify="space-between" wrap="wrap" gap="md" style={{ width: '100%' }}>
          <Group align="center" gap={12} wrap="nowrap" style={{ minWidth: 0, flex: '1 1 auto' }}>
            <Box
              style={{
                backgroundColor: 'rgba(107,114,183,0.1)',
                borderRadius: 10,
                width: 48,
                height: 48,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <CreditCard size={24} color={palette.base} />
            </Box>
            <Stack
              gap={showPaymentTimestamp ? 2 : 0}
              style={{ minWidth: 0, flex: 1, justifyContent: 'center' }}
            >
              <Text
                component="span"
                style={{
                  margin: 0,
                  display: 'block',
                  fontFamily: HOTEL_BOOKING_DETAILS_FF,
                  fontSize: '1rem',
                  fontWeight: 600,
                  lineHeight: '24px',
                  color: palette.text,
                  wordBreak: 'break-word',
                }}
              >
                {paymentMethodLabel}
              </Text>
              {showPaymentTimestamp ? (
                <Text
                  component="span"
                  style={{
                    margin: 0,
                    display: 'block',
                    fontFamily: HOTEL_BOOKING_DETAILS_FF,
                    fontSize: '0.875rem',
                    fontWeight: 400,
                    lineHeight: '21px',
                    color: palette.gray500,
                  }}
                >
                  {trimmedPaymentTime}
                </Text>
              ) : null}
            </Stack>
          </Group>
          <Group align="center" gap={24} justify="flex-end" style={{ flexShrink: 0 }}>
            {paymentApproved ? (
              <Badge
                radius="sm"
                styles={{
                  root: {
                    backgroundColor: palette.chipApprovedBg,
                    color: palette.chipApprovedFg,
                    fontFamily: HOTEL_BOOKING_DETAILS_FF,
                    fontWeight: 600,
                    fontSize: 14,
                    lineHeight: '20px',
                    letterSpacing: '0.1px',
                    height: 32,
                    paddingLeft: 12,
                    paddingRight: 12,
                    textTransform: 'none',
                  },
                }}
              >
                Approved
              </Badge>
            ) : null}
            <Text
              component="span"
              style={{
                margin: 0,
                display: 'block',
                fontFamily: HOTEL_BOOKING_DETAILS_FF,
                fontSize: '1.5rem',
                fontWeight: 700,
                lineHeight: '36px',
                color: palette.text,
              }}
            >
              {paymentAmountFormatted}
            </Text>
          </Group>
        </Group>
      </Box>
    </Stack>
  );
}
