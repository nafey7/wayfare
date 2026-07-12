import type { ReactNode } from 'react';
import { Alert, Group, Loader, Paper, Stack, Text, Title } from '@mantine/core';

interface FareRulesProps {
  fareRules: {
    fare_rules?: Array<{ rule_description?: string }>;
    baggage_information?: unknown[];
    inbound_fare_data?: unknown;
  } | null;
  isLoading?: boolean;
  error?: string | null;
}

/**
 * Fare Rules Component
 * Displays fare rules and cancellation policy after flight selection
 */
export function FareRules({ fareRules, isLoading, error }: FareRulesProps) {
  if (isLoading) {
    return (
      <Group justify="center" align="center" py={32}>
        <Loader />
        <Text c="dimmed">Loading fare rules...</Text>
      </Group>
    );
  }

  if (error) {
    return (
      <Alert color="red" mb="sm">
        {error}
      </Alert>
    );
  }

  if (!fareRules) {
    return (
      <Paper p="md" radius="md">
        <Title order={5} fw={700}>
          📋 Fare Rules & Conditions
        </Title>
        <Text size="sm" c="dimmed" mt="xs">
          No fare rules available for this flight.
        </Text>
      </Paper>
    );
  }

  // Extract cancellation policy from fare_rules array
  let cancellationPolicyContent: ReactNode = null;
  if (fareRules.fare_rules && Array.isArray(fareRules.fare_rules) && fareRules.fare_rules.length > 0) {
    const allRules = fareRules.fare_rules
      .map((rule) => rule.rule_description)
      .filter((desc) => desc && desc.trim())
      .join('\n\n');

    if (allRules) {
      const formattedRules = allRules.split('\n').map((line, index) => (
        <Text key={index} size="sm" mb={4} style={{ lineHeight: 1.6 }}>
          {line || ' '}
        </Text>
      ));

      cancellationPolicyContent = (
        <Stack
          gap={4}
          p="sm"
          mb="md"
          style={{ background: 'var(--mantine-color-gray-0)', borderRadius: 8 }}
        >
          <Text size="md" fw={600} c="dark.8" mb={4}>
            Cancellation Policy
          </Text>
          {formattedRules}
        </Stack>
      );
    }
  }

  return (
    <Paper p="md" radius="md">
      <Title order={5} fw={700}>
        📋 Fare Rules & Conditions
      </Title>
      <Stack gap={4} mt="xs">
        {cancellationPolicyContent || (
          <>
            <Text size="sm" c="dimmed" mb={4}>
              • Fare rules will be displayed here
            </Text>
            <Text size="sm" c="dimmed" mb={4}>
              • Standard booking conditions apply
            </Text>
            <Text size="sm" c="dimmed" mb={4}>
              • Changes and cancellations may incur fees
            </Text>
            <Text size="sm" c="dimmed">
              • Please review all conditions before proceeding
            </Text>
          </>
        )}
      </Stack>
    </Paper>
  );
}
