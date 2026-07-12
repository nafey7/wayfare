import { Box, Button, Group, Stack, Text } from '@mantine/core';
import { ArrowRight, CheckCircle } from 'lucide-react';

import type { HotelNextStepItem } from '@/features/hotels/utils/hotelBookingDetailsUtils';
import { HOTEL_BOOKING_DETAILS_FF, hotelBookingDetailsPalette as palette } from './hotelBookingDetailsPanel.theme';

export interface HotelBookingDetailsPanelNextStepsSectionProps {
  nextStepsItems: HotelNextStepItem[];
  hotelWebsiteUrl?: string | null;
  onGoToHotelWebsite?: () => void;
}

export function HotelBookingDetailsPanelNextStepsSection({
  nextStepsItems,
  hotelWebsiteUrl,
  onGoToHotelWebsite,
}: HotelBookingDetailsPanelNextStepsSectionProps) {
  return (
    <Stack gap="md" style={{ width: '100%', minWidth: 0 }}>
      <Text
        component="span"
        style={{
          margin: 0,
          display: 'block',
          fontFamily: HOTEL_BOOKING_DETAILS_FF,
          fontSize: '1.375rem',
          fontWeight: 700,
          lineHeight: '28px',
          color: palette.text,
        }}
      >
        Next Steps
      </Text>
      <Box
        p="md"
        style={{
          backgroundColor: palette.nextStepsBg,
          border: `1px solid ${palette.cardBorder}`,
          borderRadius: 14,
          minWidth: 0,
        }}
      >
        <Stack gap="md">
          <Stack gap={12}>
            {nextStepsItems.map((item) => (
              <Group key={item.id} align="flex-start" gap={11} wrap="nowrap" style={{ minWidth: 0 }}>
                <CheckCircle
                  size={24}
                  color={palette.base}
                  style={{ flexShrink: 0, marginTop: 2 }}
                />
                <Text
                  component="span"
                  style={{
                    margin: 0,
                    display: 'block',
                    fontFamily: HOTEL_BOOKING_DETAILS_FF,
                    fontSize: '1rem',
                    fontWeight: 400,
                    lineHeight: '21px',
                    letterSpacing: '0.1px',
                    color: item.tone === 'muted' ? palette.gray700 : palette.text,
                    minWidth: 0,
                    wordBreak: 'break-word',
                  }}
                >
                  {item.text}
                </Text>
              </Group>
            ))}
          </Stack>
          {hotelWebsiteUrl || onGoToHotelWebsite ? (
            <Button
              component={hotelWebsiteUrl ? 'a' : 'button'}
              href={hotelWebsiteUrl ?? undefined}
              target={hotelWebsiteUrl ? '_blank' : undefined}
              rel={hotelWebsiteUrl ? 'noopener noreferrer' : undefined}
              onClick={hotelWebsiteUrl ? undefined : () => onGoToHotelWebsite?.()}
              size="sm"
              radius={9999}
              tt="none"
              rightSection={<ArrowRight size={18} color="white" />}
              styles={{
                root: {
                  alignSelf: 'flex-start',
                  backgroundColor: palette.base,
                  paddingLeft: 24,
                  paddingRight: 16,
                  paddingTop: 10,
                  paddingBottom: 10,
                  fontFamily: HOTEL_BOOKING_DETAILS_FF,
                  fontSize: 14,
                  fontWeight: 600,
                  letterSpacing: '0.1px',
                  color: 'white',
                },
              }}
            >
              Go to hotel website
            </Button>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  );
}
