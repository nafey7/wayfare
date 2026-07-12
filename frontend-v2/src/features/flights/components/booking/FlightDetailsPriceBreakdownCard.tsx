import { Box, Card, Divider, Group, Stack, Text, Title } from '@mantine/core';
import { formatCurrency } from '../../utils/flightUtils';

export interface FlightDetailsPriceBreakdownCardProps {
  baseFare: number;
  totalTax: number;
  /** Pre-platform-fee tickets amount (carrier-charged total). */
  ticketsAmount: number;
  /** Platform fee in major currency units (already computed). */
  platformFee: number;
  /** Platform fee % shown in the row label, e.g. 5 → "Platform Fee (5%)". */
  platformFeePercentage: number;
  /** Final total charged. */
  totalFare: number;
  /** ISO currency code applied to all amounts. */
  currency: string;
}

function PriceRow({ label, value }: { label: string; value: string }) {
  return (
    <Group justify="space-between" mb={4}>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600}>
        {value}
      </Text>
    </Group>
  );
}

/**
 * Price breakdown card on `/flights/details`. Renders base fare + taxes,
 * tickets amount + platform fee, and a gradient total row. All amounts must
 * already be in major currency units (callers compute `totalFare - ticketsAmount`).
 */
export function FlightDetailsPriceBreakdownCard({
  baseFare,
  totalTax,
  ticketsAmount,
  platformFee,
  platformFeePercentage,
  totalFare,
  currency,
}: FlightDetailsPriceBreakdownCardProps) {
  return (
    <Card mb="md" radius="md" withBorder>
      <Box p="md">
        <Title order={4} fw={700}>
          Price Breakdown
        </Title>
        <Divider my="sm" />

        <Stack gap={0} mb="sm">
          <PriceRow label="Base Fare" value={formatCurrency(baseFare, currency)} />
          <PriceRow label="Taxes & Fees" value={formatCurrency(totalTax, currency)} />
        </Stack>

        <Divider my="sm" />

        <Stack gap={0} mt="xs">
          <PriceRow label="🎫 Tickets Amount" value={formatCurrency(ticketsAmount, currency)} />
          <PriceRow
            label={`💼 Platform Fee (${platformFeePercentage}%)`}
            value={formatCurrency(platformFee, currency)}
          />
        </Stack>

        <Divider my="sm" />

        <Group
          justify="space-between"
          align="center"
          pt="sm"
          style={{ borderTop: '2px solid var(--mantine-color-brand-6)' }}
        >
          <Title order={4} fw={700}>
            Total Amount
          </Title>
          <Title
            order={3}
            fw={700}
            style={{
              background: 'linear-gradient(to right, #667eea, #764ba2)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            {formatCurrency(totalFare, currency)}
          </Title>
        </Group>
      </Box>
    </Card>
  );
}
