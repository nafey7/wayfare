/**
 * Skeleton render for in-flight itinerary streaming (#1117 piece 4d).
 *
 * Shown when the streaming chat endpoint has emitted the first
 * ``itinerary_partial`` event but the final ``complete`` response
 * hasn't landed yet. Pulls the partial snapshot from Redux via
 * :func:`useStreamingItineraryItems` and renders one card per day —
 * the day title appears as soon as the LLM emits it, then "Loading
 * activities…" placeholders fill the body until the day's
 * ``expandedContent.activities`` populate.
 *
 * Drop-in companion to :class:`ItineraryDetailsComponent`. The page
 * decides which to render based on
 * ``streamingItinerary.active`` (see ``useStreamingItineraryItems``).
 */

import { Box, Skeleton, Stack, Text, Title } from '@mantine/core';

import { useStreamingItineraryItems } from '../hooks/useStreamingItineraryItems';

interface StreamingItinerarySkeletonProps {
  /** Day count the user originally asked for (e.g. "5-day trip"). When
   * we have it, render that many placeholder slots so the layout
   * doesn't jump around as days arrive. Defaults to the partial's
   * current day count. */
  expectedDayCount?: number;
}

export function StreamingItinerarySkeleton({
  expectedDayCount,
}: StreamingItinerarySkeletonProps) {
  const { items, active } = useStreamingItineraryItems();

  if (!active) return null;

  // No partial yet — generic "thinking" placeholder block.
  if (!items || items.length === 0) {
    return (
      <Box data-testid="streaming-itinerary-skeleton" p="lg">
        <Stack gap="md">
          <Text size="sm" c="dimmed" fs="italic">
            Generating your itinerary…
          </Text>
          {Array.from({ length: expectedDayCount ?? 3 }).map((_, idx) => (
            <Skeleton key={idx} height={80} radius="md" />
          ))}
        </Stack>
      </Box>
    );
  }

  // Pad with empty skeleton rows up to ``expectedDayCount`` so the
  // user can see how many days the trip will be even before all
  // titles have streamed.
  const dayCount = Math.max(items.length, expectedDayCount ?? 0);

  return (
    <Box data-testid="streaming-itinerary-skeleton" p="lg">
      <Stack gap="md">
        {Array.from({ length: dayCount }).map((_, idx) => {
          const item = items[idx];
          if (!item) {
            return <Skeleton key={`pending-${idx}`} height={80} radius="md" />;
          }
          const hasActivities =
            !!item.expandedContent &&
            Array.isArray(item.expandedContent.activities) &&
            item.expandedContent.activities.length > 0;
          return (
            <Box
              key={item.day}
              data-testid={`streaming-day-${item.day}`}
              p="md"
              style={{
                background: 'white',
                borderRadius: 12,
                border: '1px solid var(--mantine-color-gray-3)',
              }}
            >
              <Stack gap="xs">
                <Title order={5} fw={700}>
                  Day {item.day} · {item.title}
                </Title>
                {hasActivities ? (
                  <Text size="sm" c="dimmed">
                    {item.expandedContent?.activities?.length ?? 0} activities
                  </Text>
                ) : (
                  <Stack gap={6}>
                    <Skeleton height={12} radius="sm" width="80%" />
                    <Skeleton height={12} radius="sm" width="60%" />
                    <Skeleton height={12} radius="sm" width="70%" />
                  </Stack>
                )}
              </Stack>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}
