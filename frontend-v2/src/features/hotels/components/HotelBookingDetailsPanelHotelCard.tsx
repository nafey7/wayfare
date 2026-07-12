import { useState } from 'react';
import {
  ActionIcon,
  Anchor,
  Badge,
  Box,
  Divider,
  Group,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { Calendar, ChevronLeft, ChevronRight, Info } from 'lucide-react';

import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import { HotelImageWithFallback } from './HotelImageWithFallback';
import {
  HOTEL_BOOKING_DETAILS_FF,
  hotelBookingDetailsPalette as palette,
} from './hotelBookingDetailsPanel.theme';

export interface HotelBookingDetailsPanelHotelCardProps {
  destinationTitle: string;
  stayDateLine: string;
  hotelImageUrls: string[];
  hotelCity?: string | null;
  hotelName: string;
  addressLine: string;
  showOnMapHref?: string | null;
  hotelDescription?: string | null;
  nightsAdultsLine: string;
  roomTypeName: string;
  roomAmenityChip?: string | null;
  reservationCode: string;
}

const navButtonStyle: React.CSSProperties = {
  backgroundColor: 'rgba(0,0,0,0.5)',
  color: 'white',
  width: 32,
  height: 32,
};

export function HotelBookingDetailsPanelHotelCard({
  destinationTitle,
  stayDateLine,
  hotelImageUrls,
  hotelCity,
  hotelName,
  addressLine,
  showOnMapHref,
  hotelDescription,
  nightsAdultsLine,
  roomTypeName,
  roomAmenityChip,
  reservationCode,
}: HotelBookingDetailsPanelHotelCardProps) {
  const images = hotelImageUrls.filter(Boolean);
  const [imgIndex, setImgIndex] = useState(0);
  const safeIndex = images.length ? Math.min(imgIndex, images.length - 1) : 0;
  const currentImg = images[safeIndex];

  const cycle = (delta: number) => {
    if (images.length < 2) return;
    setImgIndex((i: number) => (i + delta + images.length) % images.length);
  };

  const trimmedAddress = addressLine.trim();
  const showAddressLine = Boolean(trimmedAddress) && trimmedAddress !== '—';

  return (
    <Box
      p="md"
      style={{
        border: `1px solid ${palette.neutralBorder}`,
        borderRadius: 16,
        width: '100%',
        minWidth: 0,
      }}
    >
      <Stack gap="md" align="stretch">
        <Text
          component="span"
          style={{
            margin: 0,
            display: 'block',
            width: '100%',
            fontFamily: HOTEL_BOOKING_DETAILS_FF,
            fontSize: '1.375rem',
            fontWeight: 700,
            lineHeight: '28px',
            color: 'black',
          }}
        >
          Hotel Details
        </Text>

        <Stack gap="md">
          <Text
            component="span"
            style={{
              margin: 0,
              display: 'block',
              fontFamily: HOTEL_BOOKING_DETAILS_FF,
              fontSize: '1.125rem',
              fontWeight: 700,
              lineHeight: '25px',
              letterSpacing: '0.15px',
              color: 'black',
            }}
          >
            {destinationTitle}
          </Text>
          <Group gap="xs" align="flex-start" wrap="nowrap" style={{ minWidth: 0 }}>
            <Calendar size={18} color={palette.text} style={{ flexShrink: 0, marginTop: 2 }} />
            <Text
              component="span"
              style={{
                margin: 0,
                display: 'block',
                minWidth: 0,
                fontFamily: HOTEL_BOOKING_DETAILS_FF,
                fontSize: '1.125rem',
                fontWeight: 400,
                lineHeight: '26px',
                letterSpacing: '0.1px',
                color: palette.text,
              }}
            >
              {stayDateLine}
            </Text>
          </Group>
        </Stack>

        <Group
          align="stretch"
          gap="md"
          wrap="wrap"
          p={8}
          style={{
            backgroundColor: 'white',
            border: `1px solid ${palette.neutralBorder}`,
            borderRadius: 12,
            minHeight: 263,
            width: '100%',
            minWidth: 0,
          }}
        >
          <Box
            style={{
              position: 'relative',
              width: 247,
              minHeight: 247,
              borderRadius: 8,
              overflow: 'hidden',
              flexShrink: 0,
            }}
          >
            <HotelImageWithFallback
              key={`${safeIndex}-${currentImg ?? 'none'}`}
              primaryUrl={currentImg ?? null}
              hotelName={hotelName}
              city={hotelCity?.trim() ? hotelCity : undefined}
              address={showAddressLine ? trimmedAddress : undefined}
              fallbackSrc={hotelFallback}
              alt=""
              sx={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                borderRadius: 8,
              }}
            />
            {images.length > 1 ? (
              <Group
                align="center"
                justify="space-between"
                style={{
                  position: 'absolute',
                  left: 6,
                  right: 7,
                  top: '50%',
                  transform: 'translateY(-50%)',
                }}
              >
                <ActionIcon
                  size="lg"
                  onClick={() => cycle(-1)}
                  variant="filled"
                  style={navButtonStyle}
                  aria-label="Previous image"
                >
                  <ChevronLeft size={20} />
                </ActionIcon>
                <ActionIcon
                  size="lg"
                  onClick={() => cycle(1)}
                  variant="filled"
                  style={navButtonStyle}
                  aria-label="Next image"
                >
                  <ChevronRight size={20} />
                </ActionIcon>
              </Group>
            ) : null}
          </Box>

          <Group
            align="stretch"
            gap={0}
            wrap="wrap"
            py="md"
            pr="md"
            style={{ flex: 1, minWidth: 0 }}
          >
            <Stack gap="md" style={{ flex: 1, minWidth: 0 }}>
              <Text
                component="span"
                style={{
                  margin: 0,
                  display: 'block',
                  fontFamily: HOTEL_BOOKING_DETAILS_FF,
                  fontSize: '1.375rem',
                  fontWeight: 700,
                  lineHeight: '28px',
                  color: 'black',
                  wordBreak: 'break-word',
                }}
              >
                {hotelName}
              </Text>

              {showAddressLine || roomAmenityChip || showOnMapHref ? (
                <Stack
                  gap="xs"
                  justify={showOnMapHref ? 'space-between' : 'flex-start'}
                  align="stretch"
                  style={{
                    flex: showOnMapHref ? 1 : 0,
                    minHeight: showOnMapHref ? 100 : 0,
                    width: '100%',
                  }}
                >
                  <Stack gap="xs" style={{ width: '100%' }}>
                    {showAddressLine ? (
                      <Text
                        component="span"
                        style={{
                          margin: 0,
                          display: 'block',
                          minWidth: 0,
                          fontFamily: HOTEL_BOOKING_DETAILS_FF,
                          fontSize: '0.875rem',
                          fontWeight: 400,
                          lineHeight: '18px',
                          letterSpacing: '0.1px',
                          color: 'black',
                          wordBreak: 'break-word',
                        }}
                      >
                        {trimmedAddress}
                      </Text>
                    ) : null}
                    {roomAmenityChip ? (
                      <Badge
                        size="lg"
                        radius="sm"
                        styles={{
                          root: {
                            height: 32,
                            fontFamily: HOTEL_BOOKING_DETAILS_FF,
                            fontWeight: 600,
                            alignSelf: 'flex-start',
                            textTransform: 'none',
                          },
                        }}
                      >
                        {roomAmenityChip}
                      </Badge>
                    ) : null}
                  </Stack>
                  {showOnMapHref ? (
                    <Anchor
                      href={showOnMapHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        alignSelf: 'flex-start',
                        fontFamily: HOTEL_BOOKING_DETAILS_FF,
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        lineHeight: '20px',
                        letterSpacing: '0.1px',
                        color: 'black',
                        textDecoration: 'underline',
                        flexShrink: 0,
                      }}
                    >
                      show on map
                    </Anchor>
                  ) : null}
                </Stack>
              ) : null}

              {hotelDescription ? (
                <Text
                  component="span"
                  style={{
                    margin: 0,
                    display: 'block',
                    fontFamily: HOTEL_BOOKING_DETAILS_FF,
                    fontSize: '0.875rem',
                    fontWeight: 400,
                    lineHeight: '18px',
                    letterSpacing: '0.1px',
                    color: 'black',
                  }}
                >
                  {hotelDescription}
                </Text>
              ) : null}
            </Stack>

            <Divider
              orientation="vertical"
              mx="md"
              visibleFrom="md"
              style={{ borderColor: palette.neutralBorder }}
            />

            <Box
              py="xs"
              style={{
                width: 196,
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                justifyContent: 'center',
                alignSelf: 'stretch',
              }}
            >
              <Stack gap={4} align="flex-end" style={{ width: '100%', textAlign: 'right' }}>
                <Text
                  component="span"
                  style={{
                    margin: 0,
                    display: 'block',
                    width: '100%',
                    textAlign: 'right',
                    fontFamily: HOTEL_BOOKING_DETAILS_FF,
                    fontSize: '1rem',
                    fontWeight: 600,
                    lineHeight: '20px',
                    color: palette.text,
                    wordBreak: 'break-word',
                  }}
                >
                  {nightsAdultsLine}
                </Text>
                <Group gap={4} align="center" justify="flex-end" style={{ width: '100%' }}>
                  <Text
                    component="span"
                    style={{
                      margin: 0,
                      display: 'block',
                      fontFamily: HOTEL_BOOKING_DETAILS_FF,
                      fontSize: '1.5rem',
                      fontWeight: 700,
                      lineHeight: '32px',
                      color: palette.text,
                      textAlign: 'right',
                      wordBreak: 'break-word',
                    }}
                  >
                    {roomTypeName}
                  </Text>
                  <Tooltip label="Includes room rate and fees">
                    <span style={{ display: 'inline-flex' }}>
                      <Info size={14} color={palette.text} style={{ flexShrink: 0 }} />
                    </span>
                  </Tooltip>
                </Group>
              </Stack>
            </Box>
          </Group>
        </Group>

        <Box
          py={26}
          px={26}
          style={{
            borderRadius: 14,
            border: '2px dashed rgba(107,114,183,0.3)',
            background: 'linear-gradient(90deg, rgba(107,114,183,0.05) 0%, rgba(107,114,183,0.1) 100%)',
            minHeight: 113,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Group
            align="center"
            justify="center"
            gap={24}
            wrap="wrap"
            style={{ textAlign: 'center' }}
          >
            <Text
              component="span"
              style={{
                margin: 0,
                display: 'block',
                fontFamily: HOTEL_BOOKING_DETAILS_FF,
                fontSize: '1.125rem',
                fontWeight: 700,
                lineHeight: '25px',
                letterSpacing: '0.15px',
                color: palette.gray500,
              }}
            >
              Reservation Code
            </Text>
            <Text
              component="span"
              style={{
                margin: 0,
                display: 'block',
                fontFamily: HOTEL_BOOKING_DETAILS_FF,
                fontSize: '1.75rem',
                fontWeight: 700,
                lineHeight: '36px',
                color: palette.base,
                wordBreak: 'break-all',
              }}
            >
              {reservationCode}
            </Text>
          </Group>
        </Box>
      </Stack>
    </Box>
  );
}
