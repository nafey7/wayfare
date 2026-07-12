import { Accordion, Box, Button, Card, Divider, Group, Stack, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { ArrowRight, CalendarDays, Search as SearchIcon, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { ROUTES } from '@/features/routing/constants';
import { ListItemRow } from '../shared';

import TokyoImage from '@/assets/images/landing-page/example-itineraries/Tokyo.png';
import PhuketImage from '@/assets/images/landing-page/example-itineraries/Phuket.png';
import EuropeImage from '@/assets/images/landing-page/example-itineraries/Europe.png';

export interface SavedSearchCard {
  id: string;
  searchId?: string;
  title: string;
  location: string;
  imageUrl: string;
  dateRange: string;
  criteria: string;
  passengers: string;
}

const DEFAULT_SEARCHES: SavedSearchCard[] = [
  {
    id: '1',
    title: 'Jamaica',
    location: 'Jamaica',
    imageUrl: TokyoImage,
    dateRange: 'Apr 12 – 18, 2026',
    criteria: 'Economy · Direct',
    passengers: '6 passengers',
  },
  {
    id: '2',
    title: 'Alaska',
    location: 'United States',
    imageUrl: EuropeImage,
    dateRange: 'Nov 11 – 16, 2026',
    criteria: 'Economy · 1 stop',
    passengers: '4 passengers',
  },
  {
    id: '3',
    title: 'Cartagena',
    location: 'Colombia',
    imageUrl: PhuketImage,
    dateRange: 'Dec 26 – Jan 7, 2027',
    criteria: 'Business · Direct',
    passengers: '2 passengers',
  },
];

export interface SavedSearchesSectionProps {
  searches?: SavedSearchCard[];
}

/**
 * Saved searches section — collapsible header + saved search cards.
 * Same design as ActiveChatsSection.
 */
export function SavedSearchesSection({ searches = DEFAULT_SEARCHES }: SavedSearchesSectionProps) {
  const navigate = useNavigate();
  const isMdUp = useMediaQuery('(min-width: 900px)') ?? false;
  const count = searches.length;

  return (
    <Accordion
      defaultValue="saved-searches"
      variant="default"
      chevronPosition="right"
      styles={{
        item: { border: 'none' },
        control: { padding: '10px 16px', minHeight: 48 },
        content: { padding: 0, paddingBottom: 24 },
        chevron: { color: LANDING_TOKENS.textColor },
      }}
    >
      <Accordion.Item value="saved-searches">
        <Accordion.Control>
          <Text
            style={{
              flex: 1,
              fontFamily: LANDING_TOKENS.fontFamily.display,
              fontWeight: 700,
              fontSize: 28,
              lineHeight: '36px',
              color: LANDING_TOKENS.textColor,
              margin: 0,
              display: 'block',
            }}
          >
            Saved Searches ({count})
          </Text>
        </Accordion.Control>
        <Accordion.Panel>
          <Stack
            gap="lg"
            px="md"
            style={{
              flexDirection: isMdUp ? 'row' : 'column',
              flexWrap: 'wrap',
            }}
          >
            {searches.map((search) => (
              <SavedSearchCardView
                key={search.id}
                search={search}
                onSearch={() => handleSearch(search)}
              />
            ))}
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );

  function handleSearch(search: SavedSearchCard) {
    const path = search.searchId
      ? `${ROUTES.FLIGHTS}?searchId=${encodeURIComponent(search.searchId)}`
      : ROUTES.FLIGHTS;
    navigate(path);
  }
}

function SavedSearchCardView({
  search,
  onSearch,
}: {
  search: SavedSearchCard;
  onSearch: () => void;
}) {
  return (
    <Card
      withBorder
      padding={0}
      radius="md"
      style={{
        flex: 1,
        minWidth: 280,
        maxWidth: 460,
        width: '100%',
        borderColor: LANDING_TOKENS.baseLighter,
        overflow: 'hidden',
      }}
    >
      <Box style={{ height: 240, position: 'relative', overflow: 'hidden' }}>
        <Box
          component="img"
          src={search.imageUrl}
          alt={search.title}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
        <Stack
          gap={8}
          style={{
            position: 'absolute',
            left: 11,
            bottom: 11,
          }}
        >
          <Text
            style={{
              fontFamily: LANDING_TOKENS.fontFamily.display,
              fontWeight: 700,
              fontSize: 22,
              lineHeight: '28px',
              color: LANDING_TOKENS.textLight,
            }}
          >
            {search.title}
          </Text>
          <Text
            style={{
              fontFamily: LANDING_TOKENS.fontFamily.display,
              fontWeight: 600,
              fontSize: 14,
              lineHeight: '20px',
              letterSpacing: 0.1,
              color: LANDING_TOKENS.textLight,
            }}
          >
            {search.location}
          </Text>
        </Stack>
      </Box>

      <Box style={{ padding: '11px 30px 11px 16px' }}>
        <Stack gap={11}>
          <Stack gap={0}>
            <ListItemRow icon={<CalendarDays size={24} />} text={search.dateRange} />
            <ListItemRow icon={<SearchIcon size={24} />} text={search.criteria} />
            <ListItemRow icon={<Users size={24} />} text={search.passengers} />
          </Stack>
          <Divider color={LANDING_TOKENS.borderDivider} />
          <Group justify="center" style={{ width: '100%' }}>
            <Button
              size="sm"
              onClick={onSearch}
              rightSection={<ArrowRight size={18} />}
              radius={100}
              tt="none"
              fw={600}
              style={{
                backgroundColor: LANDING_TOKENS.baseColor,
                color: LANDING_TOKENS.textLight,
                fontFamily: LANDING_TOKENS.fontFamily.display,
                fontSize: 14,
                lineHeight: '20px',
                letterSpacing: 0.1,
              }}
            >
              Resume
            </Button>
          </Group>
        </Stack>
      </Box>
    </Card>
  );
}
