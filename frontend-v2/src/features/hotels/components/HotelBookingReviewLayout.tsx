/**
 * Review booking + guest details — layout aligned with Paula UI (Figma).
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  ActionIcon,
  Box,
  Button,
  Container,
  Divider,
  Group,
  Loader,
  Stack,
  Text,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Calendar, ChevronRight } from 'lucide-react';
import { ImageLightboxModal } from './ImageLightboxModal';
import { HOTEL_REVIEW_BOOKING_TOKENS } from '../utils/hotelReviewBookingTokens';
import { HOTEL_DETAIL_TOKENS } from './hotelDetail';

const {
  base: BASE,
  textMain: TEXT_MAIN,
  textMuted: TEXT_MUTED,
  borderLight: BORDER_LIGHT,
  highlightBg: HIGHLIGHT_BG,
  highlightBorder: HIGHLIGHT_BORDER,
} = HOTEL_REVIEW_BOOKING_TOKENS;

export interface HotelBookingReviewLayoutProps {
  subtitle: string;
  dateLine: string;
  hotelName: string;
  hotelImageUrl?: string | null;
  /** Resolved URLs for hero + lightbox (deduped). When length > 1, chevrons cycle the hero image. */
  hotelLightboxImages?: string[] | null;
  hotelAddressLine: string;
  onShowOnMap?: () => void;
  /** Paula Figma room card (same component as select-room step). */
  selectedRoomCard: ReactNode;
  hotelAmountLabel: string;
  hotelAmountDisplay: string;
  platformFeeLabel: string;
  platformFeeDisplay: string;
  totalAmountDisplay: string;
  totalSubtext: string;
  guestSectionTitle?: string;
  guestSectionSubtitle?: string;
  guestForms: ReactNode;
  contactSection: ReactNode;
  selectedSummaryTitle: string;
  selectedGuestBullets: string[];
  footerPrimaryLabel: string;
  onContinue: () => void;
  continueLoading?: boolean;
  /** Secondary control (e.g. browser-history back). Omit to hide. */
  footerBackLabel?: string;
  onFooterBack?: () => void;
  currencySymbol?: string;
  /** Renders above the footer divider (e.g. promo code) and above Continue. */
  preFooterContent?: ReactNode;
}

const navButtonStyle: React.CSSProperties = {
  backgroundColor: HOTEL_DETAIL_TOKENS.overlayDark,
  color: HOTEL_DETAIL_TOKENS.textLight,
  width: 32,
  height: 32,
};

export function HotelBookingReviewLayout({
  subtitle,
  dateLine,
  hotelName,
  hotelImageUrl,
  hotelLightboxImages,
  hotelAddressLine,
  onShowOnMap,
  selectedRoomCard,
  hotelAmountLabel,
  hotelAmountDisplay,
  platformFeeLabel,
  platformFeeDisplay,
  totalAmountDisplay,
  totalSubtext,
  guestSectionTitle = 'Guest Details',
  guestSectionSubtitle = 'Enter details for each guest as they appear on travel documents.',
  guestForms,
  contactSection,
  selectedSummaryTitle,
  selectedGuestBullets,
  footerPrimaryLabel,
  onContinue,
  continueLoading,
  footerBackLabel = 'Back',
  onFooterBack,
  preFooterContent,
}: HotelBookingReviewLayoutProps) {
  const isMd = useMediaQuery('(min-width: 768px)') ?? false;

  const resolvedGallery = useMemo(() => {
    if (hotelLightboxImages?.length) return hotelLightboxImages;
    if (hotelImageUrl) return [hotelImageUrl];
    return [];
  }, [hotelLightboxImages, hotelImageUrl]);

  const [heroIndex, setHeroIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  useEffect(() => {
    setHeroIndex(0);
  }, [resolvedGallery]);

  const heroSrc = resolvedGallery[heroIndex] ?? resolvedGallery[0];
  const hasCarousel = resolvedGallery.length > 1;

  const goPrev = () => {
    setHeroIndex((i) => (i <= 0 ? resolvedGallery.length - 1 : i - 1));
  };

  const goNext = () => {
    setHeroIndex((i) => (i >= resolvedGallery.length - 1 ? 0 : i + 1));
  };

  return (
    <Box
      style={{
        backgroundColor: 'var(--mantine-color-body)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        minHeight: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Same horizontal constraint as /hotels/rooms/:tokenId */}
      <Container
        size="lg"
        py="xl"
        style={{ flex: 1, minHeight: 0, overflow: 'auto' }}
      >
        <Stack gap={32} style={{ width: '100%', paddingBottom: 16 }}>
          {/* Header */}
          <Stack gap={32} py="sm" style={{ width: '100%' }}>
            <Stack gap="md">
              <Text
                component="span"
                style={{
                  margin: 0,
                  display: 'block',
                  fontSize: 24,
                  fontWeight: 700,
                  lineHeight: '32px',
                  color: TEXT_MAIN,
                }}
              >
                Review Booking
              </Text>
              <Text
                component="span"
                style={{
                  margin: 0,
                  display: 'block',
                  fontSize: 18,
                  fontWeight: 600,
                  lineHeight: '23px',
                  color: TEXT_MAIN,
                }}
              >
                {subtitle}
              </Text>
            </Stack>

            {/* Trip / hotel summary */}
            <Stack gap="md">
              <Group align="center" gap="xs" wrap="wrap">
                <Calendar size={18} color={TEXT_MAIN} />
                <Text
                  component="span"
                  style={{
                    margin: 0,
                    display: 'block',
                    fontSize: 18,
                    fontWeight: 400,
                    lineHeight: '26px',
                    letterSpacing: '0.1px',
                    color: TEXT_MAIN,
                  }}
                >
                  {dateLine}
                </Text>
              </Group>

              {/* Hotel card */}
              <Group
                align="stretch"
                gap="md"
                wrap="wrap"
                p={4}
                style={{
                  border: `1px solid ${BORDER_LIGHT}`,
                  borderRadius: 12,
                }}
              >
                <Box
                  style={{
                    position: 'relative',
                    width: isMd ? 247 : '100%',
                    height: isMd ? 247 : 200,
                    flexShrink: isMd ? 0 : undefined,
                    borderRadius: 8,
                    overflow: 'hidden',
                  }}
                >
                  {heroSrc ? (
                    <Box
                      role={hasCarousel ? 'button' : undefined}
                      tabIndex={hasCarousel ? 0 : undefined}
                      onClick={() => hasCarousel && setLightboxOpen(true)}
                      onKeyDown={(e) => {
                        if (hasCarousel && (e.key === 'Enter' || e.key === ' ')) {
                          e.preventDefault();
                          setLightboxOpen(true);
                        }
                      }}
                      style={{
                        width: '100%',
                        height: '100%',
                        cursor: hasCarousel ? 'pointer' : 'default',
                      }}
                    >
                      <img
                        src={heroSrc}
                        alt={hotelName}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    </Box>
                  ) : (
                    <Box style={{ width: '100%', height: '100%', backgroundColor: 'var(--mantine-color-gray-2)' }} />
                  )}
                  {hasCarousel ? (
                    <Group
                      align="center"
                      justify="space-between"
                      style={{
                        position: 'absolute',
                        left: 6,
                        right: 7,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        pointerEvents: 'none',
                      }}
                    >
                      <ActionIcon
                        size="lg"
                        aria-label="Previous hotel image"
                        onClick={(e) => {
                          e.stopPropagation();
                          goPrev();
                        }}
                        variant="filled"
                        style={{ ...navButtonStyle, transform: 'rotate(180deg)', pointerEvents: 'auto' }}
                      >
                        <ChevronRight size={20} />
                      </ActionIcon>
                      <ActionIcon
                        size="lg"
                        aria-label="Next hotel image"
                        onClick={(e) => {
                          e.stopPropagation();
                          goNext();
                        }}
                        variant="filled"
                        style={{ ...navButtonStyle, pointerEvents: 'auto' }}
                      >
                        <ChevronRight size={20} />
                      </ActionIcon>
                    </Group>
                  ) : null}
                </Box>
                <Stack gap="md" py="md" px="md" style={{ flex: 1, minWidth: 0 }}>
                  <Text
                    component="span"
                    style={{
                      margin: 0,
                      fontSize: 22,
                      fontWeight: 700,
                      lineHeight: '28px',
                      color: TEXT_MAIN,
                    }}
                  >
                    {hotelName}
                  </Text>
                  <Group align="flex-start" justify="space-between" gap="xs">
                    <Text
                      component="span"
                      style={{
                        margin: 0,
                        flex: 1,
                        fontSize: 14,
                        fontWeight: 400,
                        lineHeight: '18px',
                        letterSpacing: '0.1px',
                        color: TEXT_MAIN,
                      }}
                    >
                      {hotelAddressLine}
                    </Text>
                    {onShowOnMap && (
                      <Button
                        variant="subtle"
                        onClick={onShowOnMap}
                        styles={{
                          root: {
                            padding: 0,
                            color: TEXT_MAIN,
                            fontSize: 14,
                            fontWeight: 600,
                            letterSpacing: '0.1px',
                            textDecoration: 'underline',
                            textTransform: 'none',
                          },
                        }}
                      >
                        show on map
                      </Button>
                    )}
                  </Group>
                </Stack>
              </Group>
            </Stack>

            {/* Selected room — same Paula room card as select-room step */}
            <Stack gap={28}>
              <Text
                component="span"
                style={{
                  margin: 0,
                  display: 'block',
                  fontSize: 28,
                  fontWeight: 700,
                  lineHeight: '36px',
                  color: TEXT_MAIN,
                }}
              >
                Selected room
              </Text>
              {selectedRoomCard}
            </Stack>
          </Stack>

          {/* Price summary */}
          <Box
            p="md"
            style={{
              border: `1px solid ${HIGHLIGHT_BORDER}`,
              backgroundColor: HIGHLIGHT_BG,
              borderRadius: 16,
              width: '100%',
            }}
          >
            <Stack gap="md">
              <Text
                component="span"
                style={{
                  margin: 0,
                  fontSize: 28,
                  fontWeight: 700,
                  lineHeight: '36px',
                  color: TEXT_MAIN,
                }}
              >
                Price Summary
              </Text>
              <Divider style={{ borderColor: HOTEL_DETAIL_TOKENS.dividerSubtle }} />
              <Group justify="space-between" align="center">
                <Text component="span" style={{ margin: 0, fontSize: 16, fontWeight: 600, lineHeight: '20px', color: TEXT_MUTED }}>
                  {hotelAmountLabel}
                </Text>
                <Text component="span" style={{ margin: 0, fontSize: 18, fontWeight: 700, lineHeight: '25px', letterSpacing: '0.15px', color: TEXT_MUTED }}>
                  {hotelAmountDisplay}
                </Text>
              </Group>
              <Group justify="space-between" align="center">
                <Text component="span" style={{ margin: 0, fontSize: 16, fontWeight: 600, lineHeight: '20px', color: TEXT_MUTED }}>
                  {platformFeeLabel}
                </Text>
                <Text component="span" style={{ margin: 0, fontSize: 18, fontWeight: 700, lineHeight: '25px', letterSpacing: '0.15px', color: TEXT_MUTED }}>
                  {platformFeeDisplay}
                </Text>
              </Group>
              <Divider style={{ borderColor: HOTEL_DETAIL_TOKENS.dividerSubtle }} />
              <Group justify="space-between" align="flex-start" gap="md">
                <Stack gap={4}>
                  <Text component="span" style={{ margin: 0, fontSize: 32, fontWeight: 700, lineHeight: '40px', color: TEXT_MAIN }}>
                    Total Amount
                  </Text>
                  <Text component="span" style={{ margin: 0, fontSize: 16, fontWeight: 600, lineHeight: '20px', color: TEXT_MAIN }}>
                    {totalSubtext}
                  </Text>
                </Stack>
                <Text component="span" style={{ margin: 0, fontSize: 32, fontWeight: 700, lineHeight: '40px', color: BASE }}>
                  {totalAmountDisplay}
                </Text>
              </Group>
            </Stack>
          </Box>

          {/* Guest details (forms) */}
          <Stack gap="sm" style={{ width: '100%' }}>
            <Text component="span" style={{ margin: 0, fontSize: 32, fontWeight: 700, lineHeight: '40px', color: TEXT_MAIN }}>
              {guestSectionTitle}
            </Text>
            <Text component="span" style={{ margin: 0, fontSize: 16, fontWeight: 600, lineHeight: '20px', color: TEXT_MAIN }}>
              {guestSectionSubtitle}
            </Text>
          </Stack>

          {guestForms}

          {/* Contact (after guest details) */}
          {contactSection}

          <Box
            px="lg"
            py="md"
            style={{
              backgroundColor: 'rgba(107, 114, 183, 0.1)',
              border: `1px solid ${BASE}`,
              borderRadius: 12,
              width: '100%',
            }}
          >
            <Text
              component="span"
              mb="xs"
              style={{ margin: 0, display: 'block', fontSize: 16, fontWeight: 700, lineHeight: '24px', color: TEXT_MAIN }}
            >
              {selectedSummaryTitle}
            </Text>
            <Stack gap={4}>
              {selectedGuestBullets.map((line, i) => (
                <Text
                  key={i}
                  component="span"
                  style={{ margin: 0, fontSize: 14, fontWeight: 600, lineHeight: '21px', color: TEXT_MUTED }}
                >
                  • {line}
                </Text>
              ))}
            </Stack>
          </Box>
        </Stack>
      </Container>

      {/* Footer — align with lg column */}
      <Container size="lg" style={{ flexShrink: 0, backgroundColor: 'var(--mantine-color-body)' }}>
        {preFooterContent ? (
          <Box pt="md" pb="xs" style={{ width: '100%' }}>
            {preFooterContent}
          </Box>
        ) : null}
        <Group
          justify="space-between"
          align="center"
          gap="xs"
          py="md"
          style={{ borderTop: `1px solid ${BORDER_LIGHT}` }}
        >
          {onFooterBack ? (
            <Button
              variant="subtle"
              onClick={onFooterBack}
              disabled={continueLoading}
              tt="none"
              styles={{
                root: {
                  fontSize: 14,
                  fontWeight: 600,
                  color: TEXT_MAIN,
                },
              }}
            >
              {footerBackLabel}
            </Button>
          ) : (
            <Box />
          )}
          <Button
            onClick={onContinue}
            disabled={continueLoading}
            radius={9999}
            tt="none"
            leftSection={continueLoading ? <Loader size={16} color="white" /> : undefined}
            styles={{
              root: {
                paddingLeft: 24,
                paddingRight: 24,
                paddingTop: 10,
                paddingBottom: 10,
                fontSize: 14,
                fontWeight: 600,
              },
            }}
          >
            {footerPrimaryLabel}
          </Button>
        </Group>
      </Container>

      <ImageLightboxModal
        open={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        images={resolvedGallery}
        alt={hotelName}
      />
    </Box>
  );
}
