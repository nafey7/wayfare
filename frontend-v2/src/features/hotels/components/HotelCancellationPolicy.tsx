import { Box, Card, Divider, Title } from '@mantine/core';
import type { CancellationPolicy as CancellationPolicyType } from '@/types/hotels';

export interface HotelCancellationPolicyProps {
  /** Cancellation policy text (from rate-rules) or object (from room rate) */
  cancellationPolicy: string | CancellationPolicyType | null | undefined;
}

function policyToText(policy: string | CancellationPolicyType): string {
  if (typeof policy === 'string') return policy.trim();
  const parts: string[] = [];
  if (policy.description) parts.push(policy.description);
  if (policy.deadline) parts.push(`Deadline: ${policy.deadline}`);
  if (policy.penaltyAmount != null && policy.penaltyCurrency) {
    parts.push(`Penalty: ${policy.penaltyAmount} ${policy.penaltyCurrency}`);
  }
  if (policy.refundable !== undefined) {
    parts.push(policy.refundable ? 'Refundable' : 'Non-refundable');
  }
  return parts.join(' · ');
}

/**
 * Cancellation policy display with warning-style background (amber/orange).
 */
export function HotelCancellationPolicy({ cancellationPolicy }: HotelCancellationPolicyProps) {
  const text = cancellationPolicy ? policyToText(cancellationPolicy) : '';

  if (!text) return null;

  return (
    <Card
      mb="md"
      p="lg"
      radius="md"
      style={{
        border: '2px solid var(--mantine-color-yellow-6)',
        backgroundColor: 'var(--mantine-color-yellow-0)',
      }}
    >
      <Title order={6} fw={700} c="yellow.8">
        Cancellation policy
      </Title>
      <Divider my="md" />
      <Box
        style={{
          fontSize: '0.875rem',
          lineHeight: 1.6,
          maxHeight: 280,
          overflowY: 'auto',
          whiteSpace: 'pre-wrap',
        }}
      >
        {text}
      </Box>
    </Card>
  );
}
