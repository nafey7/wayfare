import { useState } from 'react';
import { Box } from '@mantine/core';

import { useStartNewChat } from '@/features/chat/hooks/useStartNewChat';
import { useGuestNewConversationGuard } from '@/features/chat/hooks/useGuestNewConversationGuard';
import { ConfirmNewConversationDialog } from '@/features/chat/components/ConfirmNewConversationDialog';

import { useGetLandingPageQuery } from '@/api/strapiApi';
import { useDetectLocationQuery } from '@/api/locationApi';
import type { InspirationRailsData } from '@/api/strapi/mapInspirationRails';
import { HomeHero } from './components/HomeHero';
import { HomeSignInCard } from './components/HomeSignInCard';
import { TripsRail } from './components/TripsRail';
import { EditorialCard } from './components/EditorialCard';
import { ClosingChatSection } from './components/ClosingChatSection';
import type { InspirationTripData } from './components/InspirationTripCard';
import {
  FROM_LONDON_TRIPS,
  WEEKEND_TRIPS,
  INTEREST_TRIPS,
  INTEREST_CHIPS,
  type InspirationTrip,
} from './data/inspirationTrips';
import { buildInspirationTripPrompt, appendOriginToPrompt, POPULAR_ORIGIN_CITIES } from './utils/inspirationTripChat';
import type { LandingPageIds } from './landingPageIds';
import kyotoEditorialImage from '@/assets/images/landing-page/inspiration-trips/kyoto-editorial.jpg';

export interface LandingPageSectionsProps {
  onSearchSubmit: (value: string) => void;
  onCtaClick?: () => void;
  /** Stable `landing-*` DOM ids — only pass on `/` (not `/home`). */
  ids?: LandingPageIds;
  /**
   * Override Strapi data from a slug-specific fetch. Any defined value (including
   * an empty object `{}`) suppresses the default query — only `undefined` falls
   * back to it.
   */
  strapiData?: InspirationRailsData;
  /** @deprecated unused in new design; kept for backward compat with page wrappers */
  cms?: unknown;
  /** @deprecated unused in new design; kept for backward compat with page wrappers */
  onCardPlanClick?: (item: unknown) => void;
}

/**
 * Shared landing layout sections — same tree for `/` and `/home`.
 *
 * Replicates the RossMyvoya V2 home design using Mantine components:
 * SignInCard → Hero → Weekend rail → From-city rail → Editorial card → Interest rail
 */
export function LandingPageSections({ onSearchSubmit, onCtaClick, ids, strapiData }: LandingPageSectionsProps) {
  const [activeInterest, setActiveInterest] = useState('adventure');
  const startNewChat = useStartNewChat();
  const { requestNewConversation, dialogProps } = useGuestNewConversationGuard();

  const { data: defaultRails } = useGetLandingPageQuery(undefined, { skip: !!strapiData });
  const strapiRails = strapiData ?? defaultRails;

  // Skip the IP lookup under vitest (MODE === 'test') so unmocked test renderers
  // and Storybook play-function runs don't hit ipapi.co. Production / dev still detect.
  const { data: detectedLocation } = useDetectLocationQuery(undefined, {
    skip: import.meta.env.MODE === 'test',
  });
  const detectedCity = detectedLocation?.city;

  const handleTripClick = (data: InspirationTripData) => {
    const trip = data as InspirationTrip;
    requestNewConversation(() => {
      startNewChat();
      if (trip.chatPrompt) {
        // Strapi-sourced prompt: pass detected origin explicitly so appendOriginToPrompt
        // uses it instead of the random session-cached fallback.
        onSearchSubmit(appendOriginToPrompt(trip.chatPrompt, trip.destinationCity, detectedCity));
      } else if (trip.destinationCity) {
        // Hardcoded trip: override originCity so buildInspirationTripPrompt frames the
        // prompt as "from {user's city} to {destination}" instead of the curated origin.
        const tripWithOrigin = detectedCity ? { ...trip, originCity: detectedCity } : trip;
        onSearchSubmit(buildInspirationTripPrompt(tripWithOrigin));
      }
    });
  };

  // Use Strapi data when available, fall back to hardcoded
  const weekendTrips = strapiRails?.weekendRail?.trips ?? WEEKEND_TRIPS;
  const weekendTitle = strapiRails?.weekendRail?.title ?? 'Trips for this weekend';
  const weekendSubtitle = strapiRails?.weekendRail?.subtitle ?? 'Quick escapes — leave Friday, back Sunday';

  const fromCityTrips = strapiRails?.fromCityRail?.trips ?? FROM_LONDON_TRIPS;
  const fromCityTitle =
    strapiRails?.fromCityRail?.title
    ?? (detectedCity ? `From ${detectedCity}` : 'Inspiration trips');
  const fromCitySubtitle =
    strapiRails?.fromCityRail?.subtitle
    ?? (detectedCity
      ? `Trips starting from ${detectedCity} · detected automatically`
      : 'Curated trips from popular hubs');

  const activeInterestTrips: InspirationTripData[] =
    strapiRails?.interestRails?.[activeInterest]
    ?? INTEREST_TRIPS[activeInterest]
    ?? INTEREST_TRIPS['adventure']
    ?? [];

  // Voya picks editorial card — CMS or hardcoded fallback
  const voyaPicks = strapiRails?.voyaPicksCard;
  const voyaPicksTitle = voyaPicks?.title ?? 'A 7-day journey through Kyoto';
  const voyaPicksBody = voyaPicks?.body ?? 'Temples at dawn. Tea ceremony in Gion. Nishiki Market lunches. A sunset boat on the Hozugawa. We built the whole week — flights from London, ryokan stays, and a curated day plan — in 53 seconds.';
  const voyaPicksMeta = voyaPicks?.meta ?? ['⚡ Built in 53s', '$3,290 total · 7 nights', '★ 4.9 Voya guests'];
  const voyaPicksChatPrompt = voyaPicks?.chatPrompt ?? 'Plan a 7-day trip to Kyoto, visiting temples at dawn, a tea ceremony in Gion, exploring Nishiki Market, and a boat ride on the Hozugawa river';
  const voyaPicksImageUrl = voyaPicks?.imageUrl ?? kyotoEditorialImage;
  const voyaPicksCtaLabel = voyaPicks?.ctaLabel ?? 'See the trip';
  const voyaPicksEyebrow = voyaPicks?.eyebrow;

  const handleVoyaPicksClick = () => {
    requestNewConversation(() => {
      startNewChat();
      const destination = POPULAR_ORIGIN_CITIES.find(
        (c) => voyaPicksTitle.toLowerCase().includes(c.toLowerCase())
      );
      onSearchSubmit(appendOriginToPrompt(voyaPicksChatPrompt, destination, detectedCity));
    });
  };

  return (
    <Box style={{ paddingTop: 12 }}>
      <HomeSignInCard id={ids?.signInCard.root} />

      <HomeHero
        onSearchSubmit={onSearchSubmit}
        domIds={ids ? {
          section: ids.hero.section,
          callout: ids.hero.calloutChip,
          heading: ids.hero.heading,
          subheadline: ids.hero.subheadline,
          ctaPrimary: ids.hero.ctaPrimary,
          flightMiniCard: ids.hero.flightMiniCard,
          hotelMiniCard: ids.hero.hotelMiniCard,
          chatInput: ids.hero.search.input,
          chatSendButton: ids.hero.search.sendButton,
        } : undefined}
        onCtaClick={onCtaClick}
        {...(strapiRails?.heroContent ?? {})}
      />

      <TripsRail
        title={weekendTitle}
        subtitle={weekendSubtitle}
        trips={weekendTrips}
        background="white"
        onTripClick={handleTripClick}
        domIds={ids ? {
          section: ids.weekendRail.section,
          heading: ids.weekendRail.heading,
          tripCard: ids.weekendRail.tripCard,
        } : undefined}
      />

      <TripsRail
        title={fromCityTitle}
        subtitle={fromCitySubtitle}
        trips={fromCityTrips}
        background="mist"
        onTripClick={handleTripClick}
        domIds={ids ? {
          section: ids.fromCityRail.section,
          heading: ids.fromCityRail.heading,
          tripCard: ids.fromCityRail.tripCard,
        } : undefined}
      />

      <EditorialCard
        title={voyaPicksTitle}
        body={voyaPicksBody}
        meta={voyaPicksMeta}
        ctaLabel={voyaPicksCtaLabel}
        imageUrl={voyaPicksImageUrl}
        {...(voyaPicksEyebrow ? { eyebrow: voyaPicksEyebrow } : {})}
        onClick={handleVoyaPicksClick}
        domIds={ids ? {
          section: ids.voyaPicks.section,
          heading: ids.voyaPicks.heading,
          cta: ids.voyaPicks.cta,
        } : undefined}
      />

      <TripsRail
        title="By your interests"
        subtitle="Pick what you love — we'll show trips for that vibe"
        trips={activeInterestTrips}
        background="mist"
        chips={INTEREST_CHIPS}
        activeChip={activeInterest}
        onChipSelect={setActiveInterest}
        onTripClick={handleTripClick}
        domIds={ids ? {
          section: ids.interestRail.section,
          heading: ids.interestRail.heading,
          chip: ids.interestRail.chip,
          tripCard: ids.interestRail.tripCard,
        } : undefined}
      />

      <ClosingChatSection
        onSearchSubmit={onSearchSubmit}
        domIds={ids ? {
          section: ids.closingChat.section,
          heading: ids.closingChat.heading,
          chatInput: ids.closingChat.input,
          chatSendButton: ids.closingChat.sendButton,
        } : undefined}
      />
      <ConfirmNewConversationDialog {...dialogProps} />
    </Box>
  );
}
