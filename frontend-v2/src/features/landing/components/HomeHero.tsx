import { Box, Stack, Text, Button } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { PlaneTakeoff, MapPin } from 'lucide-react';

import voyaImage from '@/assets/images/voya.jpeg';

import { NAVY, NAVY_SOFT, LAVENDER, MIST_HERO as MIST } from '../landingColors';
import { HeroChatBox } from './HeroChatBox';

export interface HomeHeroDomIds {
  section?: string;
  callout?: string;
  heading?: string;
  subheadline?: string;
  ctaPrimary?: string;
  flightMiniCard?: string;
  hotelMiniCard?: string;
  chatInput?: string;
  chatSendButton?: string;
}

export interface HomeHeroProps {
  headline?: string;
  calloutText?: string;
  calloutTextMobile?: string;
  subheadline?: string;
  avatarImageUrl?: string;
  flightOrigin?: string;
  flightDestination?: string;
  flightDetails?: string;
  hotelName?: string;
  hotelDetails?: string;
  ctaLabel?: string;
  onCtaClick?: () => void;
  /** Stable marketing ids (only wired on `/`). */
  domIds?: HomeHeroDomIds;
  /** Submits the prompt to chat; if omitted, the hero chatbox is hidden. */
  onSearchSubmit?: (value: string) => void;
}

/**
 * Home hero — branded copy block on the left, mascot + floating mini-cards on the right.
 * Stacks centered on mobile.
 */
export function HomeHero({
  headline = 'Your next trip, planned in minutes.',
  calloutText = 'Your personal travel AI, available 24/7',
  calloutTextMobile = 'Your personal travel AI',
  subheadline = 'Describe your ideal trip — Voya plans every detail. Flights, hotels, itinerary, your way. Fast and personal, on call 24/7.',
  avatarImageUrl,
  flightOrigin = 'DUB',
  flightDestination = 'LON',
  flightDetails = '6:55 AM • Direct',
  hotelName = 'The Ritz London',
  hotelDetails = 'Checked in • 2 Guests',
  // Canonical default lives in cms/src/api/landing-page/content-types/landing-page/schema.json heroCtaLabel.default
  ctaLabel = 'Plan My Trip',
  onCtaClick,
  domIds,
  onSearchSubmit,
}: HomeHeroProps) {
  const isMdUp = useMediaQuery('(min-width: 48em)');
  const showCallout = calloutText.length > 0 || calloutTextMobile.length > 0;
  const activeCallout = isMdUp ? calloutText : calloutTextMobile;

  return (
    <Box
      id={domIds?.section}
      component="section"
      style={{
        backgroundColor: 'white',
        paddingBlock: isMdUp ? 72 : 32,
        paddingInline: isMdUp ? 32 : 16,
      }}
    >
      <Box
        style={{
          maxWidth: 1200,
          marginInline: 'auto',
          display: 'flex',
          flexDirection: isMdUp ? 'row' : 'column',
          alignItems: 'center',
          gap: isMdUp ? 48 : 40,
          justifyContent: isMdUp ? 'space-between' : 'flex-start',
        }}
      >
        {/* Left: copy block */}
        <Stack
          gap={isMdUp ? 28 : 24}
          style={{
            flex: 1,
            maxWidth: 600,
            width: '100%',
            alignItems: isMdUp ? 'flex-start' : 'center',
            textAlign: isMdUp ? 'left' : 'center',
          }}
        >
          {showCallout && (
            <Box
              id={domIds?.callout}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: isMdUp ? 10 : 7,
                paddingInline: isMdUp ? 16 : 12,
                paddingBlock: isMdUp ? 8 : 5,
                borderRadius: 100,
                backgroundColor: MIST,
                border: `1px solid ${LAVENDER}`,
                maxWidth: '100%',
              }}
            >
              <Text
                component="span"
                style={{
                  fontSize: isMdUp ? 12 : 11,
                  fontWeight: 700,
                  lineHeight: 1.2,
                  letterSpacing: isMdUp ? '0.08em' : '0.06em',
                  color: NAVY,
                  textTransform: 'uppercase',
                  whiteSpace: 'nowrap',
                }}
              >
                {activeCallout}
              </Text>
            </Box>
          )}

          <Text
            id={domIds?.heading}
            component="h1"
            style={{
              fontSize: isMdUp ? 52 : 28,
              fontWeight: 900,
              color: NAVY,
              letterSpacing: '-.025em',
              lineHeight: 1.08,
              margin: 0,
            }}
          >
            {headline}
          </Text>

          <Text
            id={domIds?.subheadline}
            style={{
              fontSize: isMdUp ? 17 : 14,
              fontWeight: 400,
              lineHeight: 1.55,
              color: NAVY_SOFT,
              maxWidth: 540,
            }}
          >
            {subheadline}
          </Text>

          {onCtaClick && ctaLabel !== '' && (
            <Button
              id={domIds?.ctaPrimary}
              onClick={onCtaClick}
              size={isMdUp ? 'lg' : 'md'}
              radius="xl"
              variant="filled"
              style={{
                backgroundColor: NAVY,
                color: 'white',
                fontWeight: 700,
                letterSpacing: '0.01em',
                paddingInline: isMdUp ? 32 : 24,
                alignSelf: isMdUp ? 'flex-start' : 'center',
              }}
            >
              {ctaLabel}
            </Button>
          )}

          {onSearchSubmit && (
            <Box
              style={{
                width: '100%',
                maxWidth: 560,
                marginTop: isMdUp ? 4 : 2,
              }}
            >
              <HeroChatBox
                onSubmit={onSearchSubmit}
                variant="hero"
                {...(domIds?.chatInput || domIds?.chatSendButton
                  ? {
                      domIds: {
                        ...(domIds.chatInput ? { input: domIds.chatInput } : {}),
                        ...(domIds.chatSendButton ? { sendButton: domIds.chatSendButton } : {}),
                      },
                    }
                  : {})}
              />
            </Box>
          )}
        </Stack>

        {/* Right: mascot + floating mini cards */}
        <Box
          style={{
            position: 'relative',
            width: '100%',
            maxWidth: 380,
            flex: isMdUp ? '0 0 auto' : undefined,
            paddingInline: isMdUp ? 0 : 20,
          }}
        >
          <Box
            style={{
              position: 'relative',
              width: '100%',
              aspectRatio: '380 / 340',
              borderRadius: 28,
              overflow: 'hidden',
              backgroundColor: 'rgba(23,27,99,0.06)',
            }}
          >
            <img
              src={avatarImageUrl ?? voyaImage}
              alt="AI Travel Assistant"
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                borderRadius: 28,
              }}
            />
          </Box>

          {/* Flight mini card — bottom-left */}
          <Stack
            id={domIds?.flightMiniCard}
            gap={4}
            style={{
              position: 'absolute',
              left: isMdUp ? -28 : 4,
              bottom: 40,
              width: 168,
              paddingInline: 14,
              paddingBlock: 14,
              borderRadius: 13,
              backgroundColor: 'rgba(10, 10, 31, 0.22)',
              backdropFilter: 'blur(8px)',
              border: '0.84px solid rgba(255, 255, 255, 0.10)',
              boxShadow: '0px 4px 10px rgba(23,27,99,0.06)',
            }}
          >
            <Box style={{ display: 'flex', flexDirection: 'row', gap: 6, alignItems: 'center' }}>
              <PlaneTakeoff size={12.6} color="rgba(255, 255, 255, 0.45)" />
              <Text style={{
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: '1.1px',
                color: 'rgba(255, 255, 255, 0.45)',
                textTransform: 'uppercase',
              }}>
                Flight
              </Text>
            </Box>
            <Box style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Text style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.7)' }}>
                {flightOrigin}
              </Text>
              <Box style={{ flex: 1, height: 1, backgroundColor: 'rgba(255, 255, 255, 0.18)', minWidth: 30 }} />
              <Text style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.7)' }}>
                {flightDestination}
              </Text>
            </Box>
            <Text style={{ fontSize: 12, fontWeight: 400, color: 'rgba(255, 255, 255, 0.45)', letterSpacing: '0.2px' }}>
              {flightDetails}
            </Text>
          </Stack>

          {/* Hotel mini card — top-right */}
          <Box
            id={domIds?.hotelMiniCard}
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              gap: 10,
              position: 'absolute',
              right: isMdUp ? -10 : 4,
              top: 14,
              paddingInline: 20,
              paddingBlock: 12,
              borderRadius: 12,
              backgroundColor: 'rgba(10, 10, 31, 0.22)',
              backdropFilter: 'blur(8px)',
              border: '0.84px solid rgba(255, 255, 255, 0.10)',
              boxShadow: '0px 4px 10px rgba(23,27,99,0.06)',
            }}
          >
            <Box style={{
              width: 33.5,
              height: 33.5,
              borderRadius: 8,
              backgroundColor: 'rgba(23,27,99,0.04)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <MapPin size={19} color="rgba(255, 255, 255, 0.7)" />
            </Box>
            <Stack gap={0}>
              <Text style={{ fontSize: 14, fontWeight: 400, lineHeight: '18px', color: 'rgba(255,255,255,0.7)' }}>
                {hotelName}
              </Text>
              <Text style={{ fontSize: 11, fontWeight: 600, lineHeight: '14px', color: 'rgba(255, 255, 255, 0.45)', letterSpacing: '0.2px' }}>
                {hotelDetails}
              </Text>
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
