import { Box, Button, Divider, Group, Stack, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Bed } from 'lucide-react';
import { useEffect, useState } from 'react';

import type { RoomRate } from '@/types/hotels';
import roomFallback from '@/assets/images/hotels/room-fallback.svg';
import { formatHotelPrice, resolveHotelImageUrl } from '../../utils';
import { ImageLightboxModal } from '../ImageLightboxModal';

import { resolveRoomStayPricing, type RoomStayPricing } from './roomStayPricing';
import { HOTEL_DETAIL_TOKENS } from './hotelDetailTokens';

const ORIGINAL_VS_TOTAL_EPS = 0.05;

/**
 * Min viewport width at which the room card switches to its side-by-side layout
 * (image beside content). The card lives in the right content panel beside the
 * chat panel, so the effective card width is much smaller than the viewport —
 * below this breakpoint the side-by-side layout gets cramped and we stack.
 * Note: this is intentionally higher than Mantine's `md` token (768px).
 */
const ROOM_CARD_WIDE_LAYOUT_MIN_WIDTH = 1100;

/** Review booking: shorter image than select-room; padding 8+8 matches card `p: '8px'`. */
const REVIEW_IMAGE_MD = 200;
const REVIEW_CARD_MIN_HEIGHT_MD = 8 + REVIEW_IMAGE_MD + 8;

const chipBaseStyle: React.CSSProperties = {
  height: 32,
  borderRadius: 8,
  border: `1px solid ${HOTEL_DETAIL_TOKENS.black20}`,
  backgroundColor: 'transparent',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 12px',
};

const chipLabelStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  lineHeight: '20px',
  letterSpacing: '0.1px',
  color: HOTEL_DETAIL_TOKENS.textHighlight,
  margin: 0,
  display: 'block',
};

function getRoomTitle(room: RoomRate): string {
  return room.roomType ?? room.roomName ?? 'Room';
}

function getMealLabel(room: RoomRate): string {
  const raw = room.mealPlan ?? room.boardBasis;
  if (raw == null || raw === '') return '';
  return String(raw).trim();
}

function getBedLabel(room: RoomRate): string {
  const mo = room.maxOccupancy;
  if (!mo) return 'Standard room';
  const a = mo.adults ?? 0;
  const c = mo.children ?? 0;
  if (a === 0 && c === 0) return 'Standard room';
  if (c === 0) return `${a} guest${a !== 1 ? 's' : ''} max`;
  return `${a} adults, ${c} children max`;
}

function InfoChip({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span style={chipBaseStyle}>
      <span style={{ color: HOTEL_DETAIL_TOKENS.textHighlight, display: 'inline-flex' }}>{icon}</span>
      <span style={chipLabelStyle}>{label}</span>
    </span>
  );
}

function RoomImageBlock({
  imageUrl,
  imageAlt,
  onOpenGallery,
  hasGallery,
  onImageError,
  matchHotelSummaryImage,
  isWideLayout,
}: {
  imageUrl: string;
  imageAlt: string;
  onOpenGallery: () => void;
  hasGallery: boolean;
  onImageError: () => void;
  /** Review booking: fixed image column height (see `REVIEW_IMAGE_MD`). */
  matchHotelSummaryImage?: boolean;
  /** Viewport ≥ `ROOM_CARD_WIDE_LAYOUT_MIN_WIDTH`: image sits beside the content column instead of stacking above it. */
  isWideLayout: boolean;
}) {
  const mdWidth = matchHotelSummaryImage ? REVIEW_IMAGE_MD : 396.5;
  const mdImg = matchHotelSummaryImage ? REVIEW_IMAGE_MD : 247;
  return (
    <Box
      style={{
        position: 'relative',
        width: isWideLayout ? mdWidth : '100%',
        flexShrink: isWideLayout ? 0 : undefined,
        minHeight: isWideLayout ? mdImg : 200,
        height: isWideLayout && matchHotelSummaryImage ? REVIEW_IMAGE_MD : isWideLayout ? '100%' : 'auto',
        borderRadius: 8,
        overflow: 'hidden',
        alignSelf: 'stretch',
      }}
    >
      <img
        src={imageUrl}
        alt={imageAlt}
        onError={onImageError}
        onClick={hasGallery ? onOpenGallery : undefined}
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
          minHeight: mdImg,
          objectFit: 'cover',
          borderRadius: 8,
          cursor: hasGallery ? 'pointer' : 'default',
        }}
      />
    </Box>
  );
}

export interface HotelDetailRoomCardProps {
  room: RoomRate;
  stayNights: number;
  /** Select-room step: reserve CTA. Review step: omit or set false. */
  showReserveButton?: boolean;
  onReserve?: () => void;
  isSelecting?: boolean;
  /**
   * Review booking: compact image (`REVIEW_IMAGE_MD`), tighter vertical padding, price column
   * vertically centered when `showReserveButton` is false.
   */
  matchHotelSummaryImage?: boolean;
}

/**
 * Figma-style room row: image, title, chips, per-night + stay total, optional reserve CTA.
 * Select-room flow matches `645-task-implement-paula-ui-figma-for-hotel-select-room-step`.
 */
export function HotelDetailRoomCard({
  room,
  stayNights,
  showReserveButton = true,
  onReserve,
  isSelecting = false,
  matchHotelSummaryImage = false,
}: HotelDetailRoomCardProps) {
  const isWideLayout = useMediaQuery(`(min-width: ${ROOM_CARD_WIDE_LAYOUT_MIN_WIDTH}px)`) ?? false;
  const pricing: RoomStayPricing = resolveRoomStayPricing(room, stayNights);
  const currency = pricing.currency;
  const title = getRoomTitle(room);
  const meal = getMealLabel(room);
  const bedLabel = getBedLabel(room);

  const imageUrl = resolveHotelImageUrl(room.images?.[0]) ?? undefined;
  const [imageError, setImageError] = useState(false);
  const [imageModalOpen, setImageModalOpen] = useState(false);
  useEffect(() => setImageError(false), [imageUrl]);
  const imageSrc = imageUrl && !imageError ? imageUrl : roomFallback;

  const roomImages = (room.images ?? [])
    .map((u) => resolveHotelImageUrl(u))
    .filter((u): u is string => u != null);
  const lightboxImages = roomImages;

  const originalTotal = room.originalTotalPrice;
  const showStrikethrough =
    originalTotal != null && originalTotal > pricing.total + ORIGINAL_VS_TOTAL_EPS;

  const nightsLabel =
    pricing.nights === 1 ? '× 1 night' : `× ${pricing.nights} nights`;
  const multiNight = pricing.nights > 1;

  const ra = room.roomsAvailable;
  const showScarcity = ra != null && ra > 0 && ra <= 3;

  return (
    <>
      <Group
        align={matchHotelSummaryImage ? 'stretch' : 'center'}
        gap={16}
        wrap="wrap"
        p={8}
        style={{
          backgroundColor: 'var(--mantine-color-body)',
          border: `1px solid ${HOTEL_DETAIL_TOKENS.neutralHighlight}`,
          borderRadius: 12,
          minHeight: isWideLayout ? (matchHotelSummaryImage ? REVIEW_CARD_MIN_HEIGHT_MD : 263) : 0,
          width: '100%',
          overflow: 'hidden',
        }}
      >
        <RoomImageBlock
          imageUrl={imageSrc}
          imageAlt={title}
          hasGallery={lightboxImages.length > 0}
          onOpenGallery={() => setImageModalOpen(true)}
          onImageError={() => setImageError(true)}
          matchHotelSummaryImage={matchHotelSummaryImage}
          isWideLayout={isWideLayout}
        />

        <Group
          align="stretch"
          gap={16}
          wrap="wrap"
          py={matchHotelSummaryImage ? 8 : 16}
          px={isWideLayout ? undefined : 8}
          pr={isWideLayout ? 16 : undefined}
          style={{ flex: 1, minWidth: 0 }}
        >
          <Stack
            gap={12}
            align="flex-start"
            style={{ flex: isWideLayout ? '2 1 0' : '1 1 100%', minWidth: 0 }}
          >
            <Stack pr={isWideLayout ? 16 : 0} style={{ width: '100%' }}>
              <Group align="center" gap="xs" wrap="wrap">
                <Text
                  component="span"
                  fw={700}
                  style={{
                    fontSize: 22,
                    lineHeight: '28px',
                    color: HOTEL_DETAIL_TOKENS.textPrimary,
                    wordBreak: 'break-word',
                  }}
                >
                  {title}
                </Text>
                {showScarcity ? (
                  <Text
                    component="span"
                    style={{
                      fontSize: 12,
                      fontWeight: 400,
                      lineHeight: '16px',
                      letterSpacing: '0.2px',
                      color: HOTEL_DETAIL_TOKENS.scarcityAlert,
                    }}
                  >
                    {ra} room{ra !== 1 ? 's' : ''} left
                  </Text>
                ) : null}
              </Group>
            </Stack>

            <Group gap={4} wrap="wrap" style={{ width: '100%' }}>
              <InfoChip icon={<Bed size={18} />} label={bedLabel} />
              {meal ? (
                <span
                  style={{
                    ...chipBaseStyle,
                    height: 'auto',
                    minHeight: 32,
                    paddingTop: 4,
                    paddingBottom: 4,
                  }}
                >
                  <span style={{ ...chipLabelStyle, whiteSpace: 'normal' }}>{meal}</span>
                </span>
              ) : null}
            </Group>
          </Stack>

          <Divider
            orientation="vertical"
            style={{ borderColor: HOTEL_DETAIL_TOKENS.dividerSubtle }}
            visibleFrom="md"
          />

          <Stack
            gap="xs"
            align={isWideLayout ? 'flex-end' : 'flex-start'}
            justify={
              showReserveButton
                ? 'space-between'
                : matchHotelSummaryImage
                  ? 'center'
                  : 'flex-start'
            }
            style={{
              flex: isWideLayout ? '1 1 0' : '1 1 100%',
              minWidth: 0,
              alignSelf: matchHotelSummaryImage ? 'stretch' : undefined,
            }}
          >
            <Stack gap={8} align={isWideLayout ? 'flex-end' : 'flex-start'} style={{ width: '100%' }}>
              {multiNight ? (
                <>
                  <Group gap={8} justify={isWideLayout ? 'flex-end' : 'flex-start'} align="baseline" wrap="wrap" style={{ width: '100%' }}>
                    <Text
                      component="span"
                      fw={600}
                      style={{ fontSize: 16, lineHeight: '20px', color: HOTEL_DETAIL_TOKENS.textColor }}
                    >
                      {formatHotelPrice(pricing.perNight, currency)}
                    </Text>
                    <Text
                      component="span"
                      fw={500}
                      style={{ fontSize: 14, color: HOTEL_DETAIL_TOKENS.navInactive }}
                    >
                      / night
                    </Text>
                  </Group>
                  <Text
                    component="span"
                    fw={600}
                    ta={isWideLayout ? 'right' : 'left'}
                    style={{
                      width: '100%',
                      fontSize: 16,
                      lineHeight: '20px',
                      color: HOTEL_DETAIL_TOKENS.textColor,
                    }}
                  >
                    {nightsLabel}
                  </Text>
                </>
              ) : null}
              <Group gap={4} justify={isWideLayout ? 'flex-end' : 'flex-start'} wrap="wrap" style={{ width: '100%' }}>
                {showStrikethrough ? (
                  <Text
                    component="span"
                    style={{
                      fontSize: 12,
                      lineHeight: '16px',
                      color: HOTEL_DETAIL_TOKENS.navInactive,
                      textDecoration: 'line-through',
                      marginRight: 4,
                    }}
                  >
                    {formatHotelPrice(originalTotal as number, currency)}
                  </Text>
                ) : null}
                <Text
                  component="span"
                  fw={600}
                  style={{ fontSize: 16, lineHeight: '20px', color: HOTEL_DETAIL_TOKENS.textColor }}
                >
                  Total:
                </Text>
                <Text
                  component="span"
                  fw={600}
                  style={{ fontSize: 16, lineHeight: '20px', color: HOTEL_DETAIL_TOKENS.textColor }}
                >
                  {formatHotelPrice(pricing.total, currency)}
                </Text>
              </Group>
              {!multiNight ? (
                <Text size="xs" c="dimmed" ta={isWideLayout ? 'right' : 'left'} style={{ width: '100%' }}>
                  Total for 1 night
                </Text>
              ) : null}
            </Stack>

            {showReserveButton ? (
              <Box style={{ width: '100%', maxWidth: 280, alignSelf: 'center' }}>
                <Button
                  fullWidth
                  disabled={isSelecting}
                  onClick={onReserve}
                  radius={9999}
                  tt="none"
                  styles={{
                    root: {
                      padding: '10px 24px',
                      fontSize: 14,
                      fontWeight: 600,
                      letterSpacing: '0.1px',
                    },
                  }}
                >
                  {isSelecting ? 'Please wait…' : 'Reserve'}
                </Button>
              </Box>
            ) : null}
          </Stack>
        </Group>
      </Group>

      <ImageLightboxModal
        open={imageModalOpen}
        onClose={() => setImageModalOpen(false)}
        images={lightboxImages}
        alt={title}
        fallbackSrc={roomFallback}
      />
    </>
  );
}
