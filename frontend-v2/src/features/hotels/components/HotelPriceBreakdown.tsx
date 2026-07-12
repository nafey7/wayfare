import { Card, Divider, Group, Text, Title } from '@mantine/core';
import { formatHotelPrice } from '../utils/hotelUtils';

export interface HotelPriceBreakdownProps {
  /** Hotel amount (original price before platform fee) in major units */
  hotelAmount: number;
  /** Platform fee percentage (e.g. 10.5) */
  platformFeePercentage: number;
  /** Total amount to pay in major units (before promo, if any) */
  totalAmount: number;
  /** Currency code (e.g. USD, EUR) */
  currency: string;
  /** When set, shows a discount row and reduces the final total (USD voucher). */
  voucherDiscountCents?: number | null;
  /** Promo code label for the discount row */
  voucherCode?: string | null;
}

/**
 * Price breakdown: hotel amount, platform service fee, total.
 * Styled with success/green accent to match flight review.
 */
export function HotelPriceBreakdown({
  hotelAmount,
  platformFeePercentage,
  totalAmount,
  currency,
  voucherDiscountCents,
  voucherCode,
}: HotelPriceBreakdownProps) {
  const platformFee = totalAmount - hotelAmount;
  const disc = Math.max(0, voucherDiscountCents ?? 0);
  const payTotal = disc > 0 ? Math.max(0, totalAmount - disc / 100) : totalAmount;
  const codeLabel = voucherCode?.trim() ? ` (${voucherCode.trim()})` : '';

  return (
    <Card
      mb="md"
      p="lg"
      radius="md"
      style={{
        border: '2px solid var(--mantine-color-green-3)',
        backgroundColor: 'var(--mantine-color-green-0)',
      }}
    >
      <Title order={6} fw={700} c="green.8">
        Price summary
      </Title>
      <Divider my="md" />
      <Group justify="space-between" mb={4}>
        <Text size="sm" c="dimmed">
          Hotel amount
        </Text>
        <Text size="sm" fw={600}>
          {formatHotelPrice(hotelAmount, currency)}
        </Text>
      </Group>
      <Group justify="space-between" mb="sm">
        <Text size="sm" c="dimmed">
          Platform service fee ({platformFeePercentage}%)
        </Text>
        <Text size="sm" fw={600}>
          {formatHotelPrice(platformFee, currency)}
        </Text>
      </Group>
      {disc > 0 && (
        <Group justify="space-between" align="center" mb={4}>
          <Text size="sm" c="dimmed">
            Promo discount{codeLabel}
          </Text>
          <Text size="sm" fw={600} c="navy.7">
            −{formatHotelPrice(disc / 100, currency)}
          </Text>
        </Group>
      )}
      <Group
        justify="space-between"
        align="center"
        pt="md"
        mt="md"
        style={{ borderTop: '2px solid var(--mantine-color-green-8)' }}
      >
        <Text size="sm" fw={600} c="green.8">
          {disc > 0 ? 'Total to pay' : 'Total amount'}
        </Text>
        <Title order={4} fw={700} c="green.8">
          {formatHotelPrice(payTotal, currency)}
        </Title>
      </Group>
    </Card>
  );
}
