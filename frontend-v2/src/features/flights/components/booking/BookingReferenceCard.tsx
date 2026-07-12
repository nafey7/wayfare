import { Badge, Box, Card, Divider, Group, Stack, Text, Title } from '@mantine/core';
import type { MulticityLegBookingResult } from '@/store/slices/flightBookingSlice';

export interface BookingReferenceCardProps {
  /** Primary VOYA booking reference. Falls back to multicityGroupReference for multicity flows. */
  voyaBookingReference: string;
  /** Carrier / GDS reference (rendered as secondary line when present). */
  externalBookingReference?: string;
  /** Multicity per-leg results — when length > 1, renders per-leg references instead of a single ref. */
  multicityLegs?: MulticityLegBookingResult[] | null;
  /** Multicity group reference (shown above the per-leg list). */
  multicityGroupReference?: string | null;
  /** Payment status from the Revolut transaction (e.g. 'succeeded'). Renders a chip when present. */
  paymentStatus?: string;
}

/**
 * Booking reference card used on the flight confirmation surface.
 * Renders either a single booking reference or a multicity group + per-leg breakdown,
 * with an optional external (carrier/GDS) reference and payment status chip.
 */
export function BookingReferenceCard({
  voyaBookingReference,
  externalBookingReference,
  multicityLegs,
  multicityGroupReference,
  paymentStatus,
}: BookingReferenceCardProps) {
  const isMulticity = !!multicityLegs && multicityLegs.length > 1;

  return (
    <Card mb="md" radius="md" withBorder style={{ borderColor: 'var(--mantine-color-green-6)', borderWidth: 2 }}>
      <Box p="md">
        <Title order={5} fw={700}>
          Booking Reference
        </Title>
        <Divider my="sm" />
        {isMulticity ? (
          <Stack gap="sm">
            {multicityGroupReference && (
              <Box>
                <Text size="sm" c="dimmed">
                  Multi-city group
                </Text>
                <Text size="md" fw={600}>
                  {multicityGroupReference}
                </Text>
              </Box>
            )}
            {multicityLegs!.map((leg) => (
              <Box
                key={`${leg.legIndex}-${leg.voyaBookingReference}`}
                p="xs"
                style={{
                  backgroundColor: 'var(--mantine-color-gray-0)',
                  borderRadius: 4,
                  borderLeft: '3px solid var(--mantine-color-green-6)',
                }}
              >
                <Text size="xs" c="dimmed">
                  Leg {leg.legIndex + 1}
                </Text>
                <Title order={5} fw={700} c="green.7">
                  {leg.voyaBookingReference}
                </Title>
              </Box>
            ))}
          </Stack>
        ) : (
          <Group gap="sm" align="center" wrap="wrap">
            <Title order={4} fw={700} c="green.7">
              {voyaBookingReference}
            </Title>
            {externalBookingReference && (
              <>
                <Text size="sm" c="dimmed">
                  External Reference:
                </Text>
                <Text size="md" fw={600}>
                  {externalBookingReference}
                </Text>
              </>
            )}
          </Group>
        )}
        {paymentStatus && (
          <Box mt="sm">
            <Badge
              color={paymentStatus === 'succeeded' ? 'green' : 'gray'}
              variant="filled"
              fw={600}
            >
              Payment Status: {paymentStatus.toUpperCase()}
            </Badge>
          </Box>
        )}
      </Box>
    </Card>
  );
}
