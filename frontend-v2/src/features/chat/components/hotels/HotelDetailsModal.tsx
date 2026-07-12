import {
  ActionIcon,
  Box,
  Button,
  Divider,
  Group,
  Modal,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { X, MapPin, Star, Building2, Wifi, Car, Coffee, Dumbbell } from 'lucide-react';
import { formatPrice } from '@/features/chat/utils/formatters';
import { resolveHotelImageUrl } from '@/features/chat/utils/hotelUtils';
import { HotelImageWithFallback } from '@/features/hotels/components/HotelImageWithFallback';
import type { MappedHotel } from '@/features/chat/utils/hotelUtils';
import { zIndex } from '@/theme';

const HOTEL_PLACEHOLDER_SVG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='250' height='180'%3E%3Crect width='250' height='180' fill='rgba(255,255,255,0.2)'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dominant-baseline='middle' fill='rgba(255,255,255,0.8)' font-family='Arial' font-size='36'%3E🏨%3C/text%3E%3C/svg%3E";

const facilityIcons: Record<string, React.ElementType> = {
  wifi: Wifi,
  'free wifi': Wifi,
  parking: Car,
  'free parking': Car,
  restaurant: Coffee,
  breakfast: Coffee,
  gym: Dumbbell,
  fitness: Dumbbell,
};

function getFacilityIcon(facility: string): React.ElementType {
  const lower = facility.toLowerCase();
  for (const [key, Icon] of Object.entries(facilityIcons)) {
    if (lower.includes(key)) return Icon;
  }
  return Building2;
}

interface HotelDetailsModalProps {
  open: boolean;
  onClose: () => void;
  hotel: MappedHotel;
}

export function HotelDetailsModal({ open, onClose, hotel }: HotelDetailsModalProps) {
  const isMobile = useMediaQuery('(max-width: 37.49em)');

  const renderStars = (rating: number) => {
    const stars = [];
    const starCount = Math.floor(rating || 0);
    for (let i = 0; i < starCount; i++) {
      stars.push(<Star key={i} size={16} fill="#FFB800" color="#FFB800" />);
    }
    return stars;
  };

  const rawUrl = hotel.thumbnail_url ?? '';
  const thumbnailUrl = resolveHotelImageUrl(rawUrl);

  return (
    <Modal
      opened={open}
      onClose={onClose}
      fullScreen={isMobile}
      size={!isMobile ? 500 : '100%'}
      withCloseButton={false}
      padding={0}
      zIndex={zIndex.detailModal}
    >
      <Box
        style={{
          background: 'linear-gradient(to right, #667eea, #764ba2)',
          color: 'white',
          padding: 24,
          position: 'relative',
          width: '100%',
        }}
      >
        <ActionIcon
          onClick={onClose}
          variant="transparent"
          style={{ position: 'absolute', top: 12, right: 8, color: 'white' }}
          aria-label="Close"
        >
          <X size={20} />
        </ActionIcon>

        <Group align="flex-start" gap={16}>
          <Box
            style={{
              position: 'relative',
              width: !isMobile ? 200 : 120,
              height: !isMobile ? 150 : 90,
              minWidth: 120,
              minHeight: 90,
              borderRadius: 8,
              overflow: 'hidden',
              flexShrink: 0,
              border: '2px solid rgba(255,255,255,0.3)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
            }}
          >
            <HotelImageWithFallback
              primaryUrl={thumbnailUrl}
              hotelName={hotel.hotel_name}
              city={hotel.city}
              address={hotel.address}
              fallbackSrc={HOTEL_PLACEHOLDER_SVG}
              alt={hotel.hotel_name}
              sx={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          </Box>

          <Box style={{ flex: 1, minWidth: 0 }}>
            <Title
              order={6}
              fw={600}
              c="white"
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}
            >
              {hotel.hotel_name}
            </Title>
            <Group gap={4} align="center" mt={4}>
              {renderStars(hotel.hotel_rating)}
              {hotel.hotel_rating ? (
                <Text size="sm" style={{ color: 'rgba(255,255,255,0.8)', marginLeft: 4 }}>
                  {hotel.hotel_rating} Star Hotel
                </Text>
              ) : null}
            </Group>
          </Box>
        </Group>
      </Box>

      <Box style={{ padding: 24 }}>
        <Box mb={24}>
          <Text size="xs" c="dimmed" fw={600} style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
            Location
          </Text>
          <Group mt={8} align="flex-start" gap={8} wrap="nowrap">
            <Box style={{ flexShrink: 0, marginTop: 2 }}>
              <MapPin size={18} style={{ color: '#9ca3af' }} />
            </Box>
            <Box>
              {hotel.address ? <Text size="sm">{hotel.address}</Text> : null}
              <Text size="sm" c="dimmed">
                {[hotel.city, hotel.country].filter(Boolean).join(', ')}
              </Text>
              {hotel.distance_value != null ? (
                <Text size="xs" c="dimmed">
                  {String(hotel.distance_value)} {hotel.distance_unit || 'km'} from city center
                </Text>
              ) : null}
            </Box>
          </Group>
        </Box>

        <Divider my={16} />

        <Box mb={24}>
          <Text size="xs" c="dimmed" fw={600} style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
            Ratings
          </Text>
          <Group mt={8} gap={16} wrap="wrap">
            {hotel.trip_advisor_rating != null ? (
              <Group
                gap={8}
                p={12}
                style={{
                  backgroundColor: '#f0fdf4',
                  borderRadius: 8,
                  border: '1px solid #bbf7d0',
                }}
              >
                <Box
                  style={{
                    backgroundColor: '#00AA6C',
                    color: 'white',
                    paddingInline: 8,
                    paddingBlock: 4,
                    borderRadius: 4,
                    fontWeight: 700,
                    fontSize: '1rem',
                  }}
                >
                  {hotel.trip_advisor_rating}
                </Box>
                <Box>
                  <Text size="sm" fw={600}>
                    TripAdvisor
                  </Text>
                  {hotel.trip_advisor_reviews != null ? (
                    <Text size="xs" c="dimmed">
                      {hotel.trip_advisor_reviews} reviews
                    </Text>
                  ) : null}
                </Box>
              </Group>
            ) : null}

            {hotel.hotel_rating ? (
              <Group
                gap={8}
                p={12}
                style={{
                  backgroundColor: '#fefce8',
                  borderRadius: 8,
                  border: '1px solid #fef08a',
                }}
              >
                <Star size={24} fill="#FFB800" color="#FFB800" />
                <Box>
                  <Text size="sm" fw={600}>
                    {hotel.hotel_rating} Star
                  </Text>
                  <Text size="xs" c="dimmed">
                    Hotel Rating
                  </Text>
                </Box>
              </Group>
            ) : null}
          </Group>
        </Box>

        {hotel.facilities && hotel.facilities.length > 0 ? (
          <>
            <Divider my={16} />
            <Box mb={24}>
              <Text size="xs" c="dimmed" fw={600} style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                Facilities
              </Text>
              <Group mt={8} gap={8} wrap="wrap">
                {hotel.facilities.slice(0, 8).map((facility, index) => {
                  const Icon = getFacilityIcon(facility);
                  return (
                    <Box
                      key={index}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        height: 24,
                        paddingInline: 8,
                        borderRadius: 9999,
                        fontSize: '0.75rem',
                        backgroundColor: '#f3f4f6',
                      }}
                    >
                      <Icon size={14} style={{ color: '#6b7280' }} />
                      <Text size="xs">{facility}</Text>
                    </Box>
                  );
                })}
                {hotel.facilities.length > 8 ? (
                  <Box
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      height: 24,
                      paddingInline: 8,
                      borderRadius: 9999,
                      fontSize: '0.75rem',
                      backgroundColor: '#e5e7eb',
                    }}
                  >
                    +{hotel.facilities.length - 8} more
                  </Box>
                ) : null}
              </Group>
            </Box>
          </>
        ) : null}

        <Divider my={16} />

        <Box>
          <Text size="xs" c="dimmed" fw={600} style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
            Price Details
          </Text>
          <Stack mt={12} gap={12}>
            {hotel.per_night_price != null && hotel.per_night_price > 0 ? (
              <Group justify="space-between" align="center">
                <Text size="sm" c="dimmed">
                  Price per night
                </Text>
                <Text size="sm" fw={600}>
                  {formatPrice(hotel.per_night_price, hotel.currency, true)}
                </Text>
              </Group>
            ) : null}

            {hotel.fare_type ? (
              <Group justify="space-between" align="center">
                <Text size="sm" c="dimmed">
                  Rate type
                </Text>
                <Box
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    height: 24,
                    paddingInline: 8,
                    borderRadius: 9999,
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    backgroundColor: hotel.fare_type.toLowerCase().includes('refund') ? '#dcfce7' : '#fef3c7',
                    color: hotel.fare_type.toLowerCase().includes('refund') ? '#166534' : '#92400e',
                  }}
                >
                  {hotel.fare_type}
                </Box>
              </Group>
            ) : null}

            {hotel.original_total_fare != null && hotel.original_total_fare > 0 ? (
              <>
                <Group justify="space-between" align="center">
                  <Text size="sm" c="dimmed">
                    🏨 Hotel Amount
                  </Text>
                  <Text size="sm" fw={600}>
                    {formatPrice(hotel.original_total_fare, hotel.currency, true)}
                  </Text>
                </Group>
                <Group justify="space-between" align="center">
                  <Text size="sm" c="dimmed">
                    💼 Platform Fee ({hotel.platform_fee_percentage ?? 10.5}%)
                  </Text>
                  <Text size="sm" fw={600}>
                    {formatPrice(
                      Number(
                        ((hotel.total_price ?? 0) - (hotel.original_total_fare ?? 0)).toFixed(2)
                      ),
                      hotel.currency,
                      true
                    )}
                  </Text>
                </Group>
                <Divider my={8} />
                <Group justify="space-between" align="center">
                  <Text fw={500}>Total Price</Text>
                  <Title order={5} fw={700} c="indigo">
                    {formatPrice(hotel.total_price, hotel.currency, true)}
                  </Title>
                </Group>
              </>
            ) : (
              <>
                <Divider my={8} />
                <Group justify="space-between" align="center">
                  <Text fw={500}>Total Price</Text>
                  <Title order={5} fw={700} c="indigo">
                    {formatPrice(hotel.total_price, hotel.currency, true)}
                  </Title>
                </Group>
              </>
            )}
          </Stack>
        </Box>
      </Box>

      <Box style={{ padding: 24, paddingTop: 0 }}>
        <Button fullWidth variant="outline" onClick={onClose} radius={8}>
          Close
        </Button>
      </Box>
    </Modal>
  );
}
