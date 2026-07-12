import { Box, Card, Divider, Text, UnstyledButton } from '@mantine/core';
import { Plane } from 'lucide-react';
import { Link as RouterLink } from 'react-router-dom';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { flightBookingDetail } from '@/features/routing/constants';
import type { ProfileFlightBookingRowModel } from './mapFlightBookingEvent';
import type { BookingListAction } from './listFormatters';
import { NAVY, LINE, MUTED, MIST } from '../../profileTokens';

export interface ProfileFlightBookingCardProps {
  row: ProfileFlightBookingRowModel;
  /** Kept for API compatibility — new design is always full-width. */
  layout?: 'grid' | 'carousel';
}

export function ProfileFlightBookingCard({ row }: ProfileFlightBookingCardProps) {
  const originCode = row.originIata ?? row.departureIata ?? '—';
  const destinationCode = row.destinationIata ?? '—';

  const infoLine = [row.dateLabel, row.airlineLabel].filter(Boolean).join(' · ');

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

      {/* Route: large IATA codes + dashed line + plane icon */}
      <Box style={{ padding: '20px 24px 12px' }}>
        <Box
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Text style={{ fontSize: 28, fontWeight: 900, color: NAVY, lineHeight: 1 }}>
            {originCode}
          </Text>

          <Box
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              margin: '0 16px',
              gap: 6,
            }}
          >
            <Box style={{ flex: 1, borderTop: `1.5px dashed ${LINE}` }} />
            <Plane size={20} color={MUTED} />
            <Box style={{ flex: 1, borderTop: `1.5px dashed ${LINE}` }} />
          </Box>

          <Text style={{ fontSize: 28, fontWeight: 900, color: NAVY, lineHeight: 1 }}>
            {destinationCode}
          </Text>
        </Box>
      </Box>

      {/* Info row: date · airline (left) | amount (right) */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          padding: '0 24px 16px',
          gap: 16,
        }}
      >
        {infoLine && (
          <Text style={{ fontSize: 13, color: NAVY, fontWeight: 500, flex: 1, minWidth: 0 }}>
            {infoLine}
          </Text>
        )}
        {row.amountLabel && (
          <Text style={{ fontSize: 22, fontWeight: 800, color: NAVY, flexShrink: 0 }}>
            {row.amountLabel}
          </Text>
        )}
      </Box>

      <Divider color={LINE} />

      {/* Footer: Get receipt */}
      <Box style={{ padding: '10px 16px', display: 'flex', justifyContent: 'flex-end' }}>
        {row.canNavigate && row.reference ? (
          <UnstyledButton
            component={RouterLink}
            to={flightBookingDetail(row.reference)}
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
      <Text style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>
        {label}
      </Text>
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
