import { Box, Card, Divider, Text, UnstyledButton } from '@mantine/core';
import { BedDouble } from 'lucide-react';
import { Link as RouterLink } from 'react-router-dom';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { hotelBookingDetail } from '@/features/routing/constants';
import type { ProfileHotelBookingRowModel } from './mapHotelBookingEvent';
import type { BookingListAction } from './listFormatters';
import { NAVY, LINE, MUTED, MIST } from '../../profileTokens';

export interface ProfileHotelBookingCardProps {
  row: ProfileHotelBookingRowModel;
  /** Kept for API compatibility — new design is always full-width. */
  layout?: 'grid' | 'carousel';
}

export function ProfileHotelBookingCard({ row }: ProfileHotelBookingCardProps) {
  const nightsText =
    row.hotelNights != null && row.hotelNights > 0
      ? `${row.hotelNights} night${row.hotelNights === 1 ? '' : 's'}`
      : null;

  return (
    <Card
      withBorder
      padding={0}
      radius="md"
      style={{ borderColor: LINE, overflow: 'hidden', width: '100%' }}
    >
      {/* Header: status indicator + reference */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: MIST,
          borderBottom: `1px solid ${LINE}`,
        }}
      >
        <StatusIndicator action={row.action} label={row.statusLabel} />
        {row.reference && (
          <Text style={{ fontSize: 13, color: MUTED, fontWeight: 500 }}>
            Ref:{' '}
            <span style={{ fontWeight: 700, color: NAVY }}>{row.reference}</span>
          </Text>
        )}
      </Box>

      {/* Body: icon + info (left) | price (right) */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 14,
          padding: '18px 20px 14px',
        }}
      >
        {/* Hotel icon */}
        <Box
          style={{
            width: 48,
            height: 48,
            borderRadius: 10,
            background: 'rgba(107, 114, 183, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <BedDouble size={22} color={LANDING_TOKENS.baseColor} />
        </Box>

        {/* Hotel details */}
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Text
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: NAVY,
              lineHeight: '24px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {row.hotelNameRaw ?? 'Hotel booking'}
          </Text>
          {row.locationLine && (
            <Text
              style={{
                fontSize: 14,
                color: MUTED,
                marginTop: 2,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {row.locationLine}
            </Text>
          )}
          {row.dateLabel && (
            <Text style={{ fontSize: 14, color: NAVY, marginTop: 6 }}>{row.dateLabel}</Text>
          )}
        </Box>

        {/* Price */}
        {row.amountLabel && (
          <Box style={{ textAlign: 'right', flexShrink: 0 }}>
            <Text style={{ fontSize: 22, fontWeight: 800, color: NAVY, lineHeight: '28px' }}>
              {row.amountLabel}
            </Text>
            {nightsText && (
              <Text style={{ fontSize: 13, color: MUTED, marginTop: 2 }}>{nightsText}</Text>
            )}
          </Box>
        )}
      </Box>

      <Divider color={LINE} />

      {/* Footer: Get receipt */}
      <Box style={{ padding: '10px 16px', display: 'flex', justifyContent: 'flex-end' }}>
        {row.canNavigate && row.reference ? (
          <UnstyledButton
            component={RouterLink}
            to={hotelBookingDetail(row.reference)}
            style={receiptButtonStyle}
          >
            Get receipt
          </UnstyledButton>
        ) : (
          <UnstyledButton
            disabled
            style={{ ...receiptButtonStyle, opacity: 0.5, cursor: 'default' }}
          >
            Get receipt
          </UnstyledButton>
        )}
      </Box>
    </Card>
  );
}

function StatusIndicator({ action, label }: { action: BookingListAction; label: string }) {
  let dotColor: string;
  if (action === 'CANCELLED') dotColor = LANDING_TOKENS.crossRed;
  else if (action === 'PENDING') dotColor = '#F59E0B';
  else dotColor = LANDING_TOKENS.confirmColor;

  return (
    <Box style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <Box
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: dotColor,
          flexShrink: 0,
        }}
      />
      <Text style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>{label}</Text>
    </Box>
  );
}

const receiptButtonStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 700,
  color: NAVY,
  cursor: 'pointer',
  textDecoration: 'none',
  background: 'transparent',
};
