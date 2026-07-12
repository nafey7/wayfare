import type { ReactNode } from 'react';
import { Box, Card, Divider, Group, Stack, Text, Title } from '@mantine/core';

export interface BookingDetailsRefCardProps {
  /** VOYA booking reference (primary). */
  voyaBookingReference: string;
  /** Carrier / GDS reference (rendered as a key/value row when present). */
  externalBookingReference?: string;
  /** Backend booking status string (rendered as a row when present). */
  bookingStatus?: string;
  /** Backend ticket status string (rendered as a row when present). */
  ticketStatus?: string;
  /** Optional action slot rendered below the rows (e.g. "Pay now" Link button). */
  actions?: ReactNode;
}

const ROW_LABEL_WIDTH = 140;

function Row({ label, value }: { label: string; value: string }) {
  return (
    <Group gap="xs" wrap="wrap" align="baseline">
      <Text size="sm" c="dimmed" miw={ROW_LABEL_WIDTH}>
        {label}
      </Text>
      <Text size="md" fw={600}>
        {value}
      </Text>
    </Group>
  );
}

/**
 * Booking reference card on the user-facing booking-details page (`/flights/bookings/:ref`).
 * Renders key/value rows for VOYA reference + optional carrier / booking / ticket statuses,
 * plus an optional action slot (used for the "Pay now" CTA when payment is still pending).
 *
 * Differs from `BookingReferenceCard` (confirmation flow): different border (primary, not success),
 * row-style layout, and no payment-status chip — that signal is carried by the action slot.
 */
export function BookingDetailsRefCard({
  voyaBookingReference,
  externalBookingReference,
  bookingStatus,
  ticketStatus,
  actions,
}: BookingDetailsRefCardProps) {
  return (
    <Card mb="md" radius="md" withBorder style={{ borderColor: 'var(--mantine-color-brand-2)', borderWidth: 2 }}>
      <Box p="md">
        <Title order={5} fw={700}>
          Booking Reference
        </Title>
        <Divider my="sm" />
        <Stack gap="xs">
          <Row label="VOYA booking reference" value={voyaBookingReference} />
          {externalBookingReference && (
            <Row label="External reference" value={externalBookingReference} />
          )}
          {bookingStatus && <Row label="Booking status" value={bookingStatus} />}
          {ticketStatus && <Row label="Ticket status" value={ticketStatus} />}
        </Stack>
        {actions && <Box mt="sm">{actions}</Box>}
      </Box>
    </Card>
  );
}
