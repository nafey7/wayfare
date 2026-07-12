import { Box, Button, Stack, Text, Title } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Calendar, MapPin, Users } from 'lucide-react';

import tokyoImage from '@/assets/images/landing-page/example-itineraries/Tokyo.png';
import phuketImage from '@/assets/images/landing-page/example-itineraries/Phuket.png';

import { LANDING_SECTION_SCROLL_MARGIN_TOP, LANDING_TOKENS } from '../landingTokens';

const TOKENS = {
  baseColor: LANDING_TOKENS.baseColor,
  baseColor10: LANDING_TOKENS.baseColor10,
  baseColor20: LANDING_TOKENS.baseColor20,
  baseLighter: LANDING_TOKENS.baseLighter,
  textColor: LANDING_TOKENS.textColor,
} as const;

export interface ItineraryCardItem {
  /** Card hero image URL */
  imageUrl?: string;
  /** Full first message for "Plan a trip like this" (chat / public-chat `?prompt=`). Falls back to title + location if omitted. */
  examplePrompt?: string;
  /** Tag overlay on image (e.g. "Cherry blossom season") */
  tagText: string;
  /** Trip title (e.g. "7 Days in Tokyo") */
  tripTitle: string;
  /** Location label (e.g. "Japan") */
  location: string;
  /** Duration (e.g. "7 days") */
  duration: string;
  /** Price range (e.g. "$2,500 - $4,000") */
  priceRange: string;
  /** Traveler type (e.g. "Solo or couple") */
  travelerType: string;
  /** List of inclusions */
  inclusions: string[];
  /** Button label */
  buttonText?: string;
}

export interface ExampleItinerariesDomIds {
  section?: string;
  chip?: string;
  heading?: string;
  subtitle?: string;
  itineraryCard?: (index: number) => string;
  ctaPlanOwn?: string;
  planDescription?: string;
  cardPlanCta?: (index: number) => string;
}

export interface ExampleItinerariesSectionProps {
  domIds?: ExampleItinerariesDomIds;
  /** Chip label above heading */
  chipLabel?: string;
  /** Main heading */
  title?: string;
  /** Subheadline below heading */
  subtitle?: string;
  /** Itinerary cards */
  itineraries?: ItineraryCardItem[];
  /** Primary CTA button text */
  planMyOwnTripText?: string;
  /** Secondary text below CTA */
  planDescription?: string;
  /** "Plan my own trip" button click handler */
  onPlanMyOwnTripClick?: () => void;
  /** Card "Plan a trip like this" button click handler (receives itinerary item for prompt pre-fill) */
  onCardPlanClick?: (item: ItineraryCardItem) => void;
}

/** Landing example cards — chat pre-fill copy. Each prompt uses "Plan a" and a fixed origin city (backend itinerary routing). */
export const EXAMPLE_ITINERARY_CARD_PROMPTS = {
  tokyo:
    'Plan a 7 days trip from Paris to Tokyo for 2 adults starting Saturday in 3 weeks',
  phuket:
    'Plan a 5 days trip from Amsterdam to Phuket for 1 remote worker, staying in a co-living in Phuket, starting Monday in 4 weeks.',
  europe:
    'Plan a 4 days family trip from New York across Paris, Barcelona, and Rome for 4 people, staying in family-friendly hotels, starting Saturday in 5 weeks.',
} as const;

const DEFAULT_CHIP_LABEL = 'example itineraries';
const DEFAULT_TITLE = 'See what Voya can plan for you';
const DEFAULT_SUBTITLE =
  'Real examples of AI-generated trip plans — click any to start planning yours';
const DEFAULT_PLAN_BUTTON = 'Plan my own trip';
const DEFAULT_PLAN_DESCRIPTION =
  'Or describe any destination and get a custom itinerary in minutes';
const DEFAULT_CARD_BUTTON = 'Plan a trip like this';

const DEFAULT_ITINERARIES: ItineraryCardItem[] = [
  {
    imageUrl: tokyoImage,
    examplePrompt: EXAMPLE_ITINERARY_CARD_PROMPTS.tokyo,
    tagText: 'Cherry blossom season',
    tripTitle: '7 Days in Tokyo',
    location: 'Japan',
    duration: '7 days',
    priceRange: '$2,500 - $4,000',
    travelerType: 'Solo or couple',
    inclusions: ['Flights from Europe', '4-star hotel in Shibuya', 'JR Pass', 'Food tours'],
    buttonText: DEFAULT_CARD_BUTTON,
  },
  {
    imageUrl: phuketImage,
    examplePrompt: EXAMPLE_ITINERARY_CARD_PROMPTS.phuket,
    tagText: 'Work & explore',
    tripTitle: 'Digital Nomad Month',
    location: 'Phuket, Thailand',
    duration: '30 days',
    priceRange: '$1,800 - $3,000',
    travelerType: 'Remote workers',
    inclusions: ['Flights', 'Co-living space', 'Coworking access', 'Weekend adventures'],
    buttonText: DEFAULT_CARD_BUTTON,
  },
  // Temporarily hidden: Family Europe (Paris → Barcelona → Rome)
  // {
  //   imageUrl: europeImage,
  //   examplePrompt: EXAMPLE_ITINERARY_CARD_PROMPTS.europe,
  //   tagText: 'Summer holidays',
  //   tripTitle: 'Family Europe Adventure',
  //   location: 'Paris → Barcelona → Rome',
  //   duration: '14 days',
  //   priceRange: '$8,000 - $12,000',
  //   travelerType: 'Family of 4',
  //   inclusions: [
  //     'Multi-city flights',
  //     'Family-friendly hotels',
  //     'Skip-the-line tickets',
  //     'Kid-friendly activities',
  //   ],
  //   buttonText: DEFAULT_CARD_BUTTON,
  // },
];

interface ItineraryCardProps extends ItineraryCardItem {
  /** Full itinerary item (for passing to onPlanClick) */
  itineraryItem?: ItineraryCardItem;
  /** Card button click handler (receives full item for prompt pre-fill) */
  onPlanClick?: (item: ItineraryCardItem) => void;
  /** Stable id for card CTA (public landing only). */
  planButtonId?: string;
  /** Stable id for the whole card block (public landing only). */
  cardSectionId?: string;
  /** Resolved sm-up flag for responsive minWidth (single hook lives in the section). */
  isSmUp: boolean | undefined;
}

function ItineraryCard({
  imageUrl,
  tagText,
  tripTitle,
  location,
  duration,
  priceRange,
  travelerType,
  inclusions,
  buttonText = DEFAULT_CARD_BUTTON,
  itineraryItem,
  onPlanClick,
  planButtonId,
  cardSectionId,
  isSmUp,
}: ItineraryCardProps) {
  const visibleInclusions = inclusions.slice(0, 4);
  const hasMore = inclusions.length > 4;

  return (
    <Box
      id={cardSectionId}
      style={{
        flex: 1,
        minWidth: isSmUp ? 320 : '100%',
        maxWidth: 373,
        backgroundColor: 'white',
        border: `1px solid ${TOKENS.baseLighter}`,
        borderRadius: 16,
        overflow: 'hidden',
      }}
    >
      <Stack gap={0}>
        <Box
          style={{
            height: 192,
            position: 'relative',
            overflow: 'hidden',
            backgroundColor: '#e0e0e0',
          }}
        >
          {imageUrl && (
            <img
              src={imageUrl}
              alt={tagText ? `${tagText} - ${tripTitle}, ${location}` : `${tripTitle}, ${location}`}
              loading="lazy"
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          )}
          <Box
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0.7) 100%)',
            }}
          />
          <Stack
            gap={4}
            style={{
              position: 'absolute',
              left: 24,
              right: 24,
              bottom: 24,
            }}
          >
            <Box
              style={{
                alignSelf: 'flex-start',
                height: 22,
                paddingInline: 10,
                display: 'inline-flex',
                alignItems: 'center',
                borderRadius: 9999,
                backgroundColor: TOKENS.baseLighter,
                border: `1px solid ${TOKENS.baseLighter}`,
                fontWeight: 600,
                fontSize: 12,
                color: TOKENS.textColor,
              }}
            >
              {tagText}
            </Box>
            <Text
              style={{
                fontSize: 24,
                fontWeight: 700,
                lineHeight: 32 / 24,
                color: 'white',
                fontFamily: '"Proxima Nova", sans-serif',
              }}
            >
              {tripTitle}
            </Text>
            <Box style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <MapPin size={16} color={TOKENS.baseLighter} />
              <Text
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  lineHeight: 20 / 16,
                  color: TOKENS.baseLighter,
                  fontFamily: '"Proxima Nova", sans-serif',
                }}
              >
                {location}
              </Text>
            </Box>
          </Stack>
        </Box>

        <Stack gap={16} style={{ padding: 24 }}>
          <Box style={{ display: 'flex', flexDirection: 'row', gap: 24 }}>
            <Box style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Calendar size={16} color={TOKENS.textColor} />
              <Text
                style={{
                  fontSize: 14,
                  lineHeight: 18 / 14,
                  letterSpacing: 0.1,
                  color: TOKENS.textColor,
                  fontFamily: '"Proxima Nova", sans-serif',
                }}
              >
                {duration}
              </Text>
            </Box>
            <Text
              style={{
                fontSize: 14,
                lineHeight: 18 / 14,
                letterSpacing: 0.1,
                color: TOKENS.textColor,
                fontFamily: '"Proxima Nova", sans-serif',
              }}
            >
              {priceRange}
            </Text>
          </Box>

          <Box style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Users size={16} color={TOKENS.textColor} />
            <Text
              style={{
                fontSize: 14,
                lineHeight: 18 / 14,
                letterSpacing: 0.1,
                color: TOKENS.textColor,
                fontFamily: '"Proxima Nova", sans-serif',
              }}
            >
              {travelerType}
            </Text>
          </Box>

          <Box style={{ borderTop: `1px solid ${TOKENS.baseLighter}`, paddingTop: 16, marginTop: 4 }}>
            <Text
              style={{
                fontSize: 14,
                fontWeight: 500,
                lineHeight: 20 / 14,
                color: TOKENS.textColor,
                fontFamily: '"Inter", sans-serif',
                marginBottom: 12,
              }}
            >
              What&apos;s included:
            </Text>
            <Stack gap={8}>
              {visibleInclusions.map((item, i) => (
                <Box
                  key={`${item}-${i}`}
                  style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 12 }}
                >
                  <Box
                    style={{
                      width: 4,
                      height: 4,
                      borderRadius: '50%',
                      backgroundColor: TOKENS.baseColor,
                    }}
                  />
                  <Text
                    style={{
                      fontSize: 14,
                      lineHeight: 20 / 14,
                      color: TOKENS.textColor,
                      fontFamily: '"Inter", sans-serif',
                    }}
                  >
                    {item}
                  </Text>
                </Box>
              ))}
              {hasMore && (
                <Text
                  style={{
                    fontSize: 14,
                    lineHeight: 20 / 14,
                    color: TOKENS.baseColor,
                    fontFamily: '"Inter", sans-serif',
                  }}
                >
                  +{inclusions.length - 4} more
                </Text>
              )}
            </Stack>
          </Box>

          <Button
            id={planButtonId}
            onClick={() => itineraryItem && onPlanClick?.(itineraryItem)}
            radius={100}
            styles={{
              root: {
                alignSelf: 'center',
                marginTop: 4,
                paddingInline: 24,
                paddingBlock: 10,
                backgroundColor: TOKENS.baseColor,
                color: 'white',
                fontSize: 14,
                fontWeight: 600,
                letterSpacing: 0.1,
                fontFamily: '"Proxima Nova", sans-serif',
                boxShadow: 'none',
                '&:hover': { backgroundColor: '#5a6089', boxShadow: 'none' },
              },
            }}
          >
            {buttonText}
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}

/**
 * "See what Voya can plan for you" section (Figma Frame 403:9265)
 * Layout: Chip | Heading | Subheadline | 3 itinerary cards | Carousel nav | Action toolbar
 */
export function ExampleItinerariesSection({
  domIds,
  chipLabel = DEFAULT_CHIP_LABEL,
  title = DEFAULT_TITLE,
  subtitle = DEFAULT_SUBTITLE,
  itineraries = DEFAULT_ITINERARIES,
  planMyOwnTripText = DEFAULT_PLAN_BUTTON,
  planDescription = DEFAULT_PLAN_DESCRIPTION,
  onPlanMyOwnTripClick,
  onCardPlanClick,
}: ExampleItinerariesSectionProps) {
  // Resolve responsive values at runtime; Mantine's static `style` prop can't
  // accept the `{ xs, md }` shape MUI's sx supported.
  const isSmUp = useMediaQuery('(min-width: 37.5em)');
  const isMdUp = useMediaQuery('(min-width: 48em)');
  const scrollMarginTop = domIds?.section
    ? isMdUp
      ? LANDING_SECTION_SCROLL_MARGIN_TOP.md
      : LANDING_SECTION_SCROLL_MARGIN_TOP.xs
    : undefined;
  const headlineSize = isMdUp ? 57 : 36;
  const subtitleSize = isMdUp ? 24 : 18;

  return (
    <Box
      component="section"
      id={domIds?.section}
      aria-labelledby={domIds?.heading}
      style={{
        width: '100%',
        paddingBlock: isMdUp ? 100 : 48,
        paddingInline: isMdUp ? 60 : 24,
        backgroundColor: TOKENS.baseColor10,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        scrollMarginTop,
      }}
    >
      <Stack align="center" gap={24} style={{ maxWidth: 1116, width: '100%' }}>
        <Stack align="center" gap={34} style={{ width: '100%', maxWidth: 1116 }}>
          <Box
            id={domIds?.chip}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              paddingInline: 34,
              paddingBlock: 11,
              borderRadius: 9999,
              backgroundColor: TOKENS.baseColor,
              border: `1.429px solid ${TOKENS.baseColor20}`,
              color: 'white',
              fontSize: 16,
              fontWeight: 600,
              lineHeight: 20 / 16,
              letterSpacing: 1,
              textTransform: 'uppercase',
              fontFamily: '"Proxima Nova", sans-serif',
            }}
          >
            {chipLabel}
          </Box>
          <Title
            id={domIds?.heading}
            order={2}
            style={{
              fontSize: headlineSize,
              fontWeight: 700,
              lineHeight: 64 / 57,
              color: 'black',
              textAlign: 'center',
              width: '100%',
              fontFamily: '"Proxima Nova", sans-serif',
            }}
          >
            {title}
          </Title>
          <Text
            id={domIds?.subtitle}
            style={{
              fontSize: subtitleSize,
              fontWeight: 700,
              lineHeight: 32 / 24,
              color: 'black',
              textAlign: 'center',
              width: '100%',
              fontFamily: '"Proxima Nova", sans-serif',
            }}
          >
            {subtitle}
          </Text>
        </Stack>

        <Box style={{ width: '100%', maxWidth: 1152 }}>
          <Box
            style={{
              display: 'flex',
              flexDirection: isMdUp ? 'row' : 'column',
              gap: 24,
              justifyContent: 'center',
              alignItems: 'stretch',
              overflowX: 'auto',
              scrollbarWidth: 'none',
            }}
          >
            {itineraries.map((item, index) => (
              <ItineraryCard
                key={`${item.tripTitle}-${index}`}
                {...item}
                itineraryItem={item}
                onPlanClick={onCardPlanClick}
                planButtonId={domIds?.cardPlanCta?.(index)}
                cardSectionId={domIds?.itineraryCard?.(index)}
                isSmUp={isSmUp}
              />
            ))}
          </Box>
        </Box>

        <Stack align="center" gap={8} style={{ paddingBlock: 16, width: '100%', maxWidth: 400 }}>
          <Button
            id={domIds?.ctaPlanOwn}
            onClick={onPlanMyOwnTripClick}
            radius={100}
            styles={{
              root: {
                paddingInline: 24,
                paddingBlock: 10,
                backgroundColor: TOKENS.baseColor,
                color: 'white',
                fontSize: 14,
                fontWeight: 600,
                letterSpacing: 0.1,
                fontFamily: '"Proxima Nova", sans-serif',
                boxShadow: 'none',
                '&:hover': { backgroundColor: '#5a6089', boxShadow: 'none' },
              },
            }}
          >
            {planMyOwnTripText}
          </Button>
          <Text
            id={domIds?.planDescription}
            style={{
              paddingInline: 12,
              paddingBlock: 10,
              color: TOKENS.textColor,
              fontSize: 14,
              fontWeight: 600,
              letterSpacing: 0.1,
              fontFamily: '"Proxima Nova", sans-serif',
            }}
          >
            {planDescription}
          </Text>
        </Stack>
      </Stack>
    </Box>
  );
}
