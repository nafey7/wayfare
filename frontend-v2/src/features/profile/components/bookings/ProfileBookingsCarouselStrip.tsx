import { Box, Group } from '@mantine/core';
import type { ReactNode } from 'react';

/**
 * Horizontal scroll row for profile flight/hotel booking cards — same behavior as PR 631
 * `UpcomingTripsSection` (saved itineraries).
 */
export function ProfileBookingsCarouselStrip({
  'aria-label': ariaLabel,
  children,
}: {
  'aria-label': string;
  children: ReactNode;
}) {
  return (
    <Box
      role="region"
      aria-label={ariaLabel}
      style={{
        overflowX: 'auto',
        overflowY: 'hidden',
        WebkitOverflowScrolling: 'touch',
        paddingBottom: 8,
        paddingLeft: 16,
        paddingRight: 16,
        scrollSnapType: 'x proximity',
      }}
    >
      <Group
        gap="md"
        wrap="nowrap"
        style={{ width: 'max-content', minWidth: '100%', paddingTop: 4, paddingBottom: 4 }}
      >
        {children}
      </Group>
    </Box>
  );
}
