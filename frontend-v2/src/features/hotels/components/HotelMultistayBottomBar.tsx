import { Box, Button, Group, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import type { HotelMultistayLegState, HotelMultistaySegment } from '@/types/hotels';
import { zIndex } from '@/theme';

interface HotelMultistayBottomBarProps {
  segments: HotelMultistaySegment[];
  legs: HotelMultistayLegState[];
  onProceedToReview: () => void;
}

const INFO_BORDER = 'rgba(34, 139, 230, 0.35)';
const PRIMARY_COLOR = 'var(--mantine-primary-color-filled)';

export function HotelMultistayBottomBar({
  segments,
  legs,
  onProceedToReview,
}: HotelMultistayBottomBarProps) {
  const isMobile = useMediaQuery('(max-width: 47.99em)');
  const total = segments.length;
  const selectedCount = segments.filter((_, i) => {
    const leg = legs[i];
    return leg?.selectedHotel && leg.selectedRoom && leg.rateRulesResponse;
  }).length;
  const allSelected = selectedCount === total;

  return (
    <Box
      component="aside"
      aria-label="Multi-stay hotel selection summary"
      style={{
        position: 'sticky',
        bottom: 0,
        zIndex: zIndex.stickyFooter,
        width: '100%',
        maxWidth: '100%',
        boxSizing: 'border-box',
        overflowX: 'hidden',
        flexShrink: 0,
        marginTop: 'auto',
        alignSelf: 'stretch',
        backgroundColor: 'var(--mantine-color-body)',
        borderTop: `1px solid ${INFO_BORDER}`,
        borderBottom: `1px solid ${INFO_BORDER}`,
        boxShadow: 'var(--mantine-shadow-lg)',
        padding: '12px 16px',
        paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))',
      }}
    >
      <Box
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          alignItems: isMobile ? 'stretch' : 'center',
          flexWrap: 'wrap',
          gap: 'var(--mantine-spacing-md)',
          width: '100%',
          minWidth: 0,
          overflow: 'hidden',
        }}
      >
        <Group align="center" gap="sm" wrap="nowrap" style={{ flexShrink: 0 }}>
          <div
            aria-live="polite"
            style={{
              width: 40,
              height: 40,
              borderRadius: '50%',
              backgroundColor: PRIMARY_COLOR,
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.875rem',
              flexShrink: 0,
            }}
          >
            {selectedCount}/{total}
          </div>
          <Box style={{ minWidth: 0 }}>
            <Text size="sm" fw={700}>
              {selectedCount} of {total} stays selected
            </Text>
            <Text size="xs" c="dimmed" display="block">
              {allSelected
                ? 'All stays selected — you can review and book.'
                : 'You can continue with any selection; unselected stays stay unbooked.'}
            </Text>
          </Box>
        </Group>

        {!isMobile && <Box style={{ flex: 1, minWidth: 0 }} />}

        <Button
          size="md"
          disabled={selectedCount === 0}
          onClick={onProceedToReview}
          radius={999}
          fw={600}
          px="md"
          fullWidth={isMobile}
          style={isMobile ? undefined : { flexShrink: 0 }}
        >
          Review and book
        </Button>
      </Box>
    </Box>
  );
}
