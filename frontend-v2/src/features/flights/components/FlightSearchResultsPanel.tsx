import { useEffect } from 'react';
import { Box, Text, Transition } from '@mantine/core';
import { formatPrice } from '@/features/chat/utils/formatters';
import { flightMapper } from '@/features/chat/utils/flightUtils';
import { ExpandableFlightCardList } from '@/features/chat/components/flights/ExpandableFlightCardList';
import { trackEvent } from '@/utils/gtm';
import type { MappedFlight } from '@/types/flight';
import type { ExtractedFlightSearchData } from '@/types/api.helpers';

interface FlightSearchResultsPanelProps {
  /** Extracted flight search data (from extractFlightSearchResults or Redux) */
  data: ExtractedFlightSearchData;
  /** GTM source for tracking (e.g. full recommendations page vs chat bubble vs mobile inline panel). */
  source?: 'chat' | 'recommendations' | 'chat-inline';
  /** Show summary text ("We found X flights..."). True in chat, false in recommendations panel. */
  showSummary?: boolean;
  /**
   * @deprecated Issue #1034 — kept for layout-call-site compatibility but no
   * longer changes rendering. Panel now always renders the flat list inline.
   */
  stickyBottomBar?: boolean;
  /**
   * @deprecated Issue #1034 — the "Show All Flights" CTA is gone (panel IS the
   * full list now). Kept in the signature to avoid breaking call sites that
   * still pass it; the value is ignored.
   */
  onSeeFullResultsOverride?: () => void;
  /** When true, skip `flight_search_results_shown` (e.g. parent wrapper fires multicity analytics). */
  suppressFlightSearchResultsShownAnalytics?: boolean;
}

/**
 * Reusable flight search results panel: renders the flat best-value-sorted
 * flight list inline. No category tabs, no "Show All Flights" CTA (#1034).
 */
export function FlightSearchResultsPanel({
  data: extracted,
  source = 'recommendations',
  showSummary = false,
  stickyBottomBar: _stickyBottomBar = false,
  onSeeFullResultsOverride: _onSeeFullResultsOverride,
  suppressFlightSearchResultsShownAnalytics = false,
}: FlightSearchResultsPanelProps) {
  const useRecommendationsCardStyle = source === 'recommendations' || source === 'chat-inline';

  const sessionIdFromExtra = extracted.session_id ?? '';

  useEffect(() => {
    if (sessionIdFromExtra) {
      localStorage.setItem('sessionId', sessionIdFromExtra);
    }
  }, [sessionIdFromExtra]);

  useEffect(() => {
    if (suppressFlightSearchResultsShownAnalytics || !extracted?.data) return;
    const sp = extracted.data.search_params as unknown as Record<string, unknown>;
    const sm = extracted.data.summary as unknown as Record<string, unknown>;
    const passengers =
      (sp?.passengers as {
        adults?: number;
        children?: number;
        infants?: number;
      }) ?? {};
    const priceRange =
      (sm?.price_range as { min?: number; max?: number; currency?: string }) ??
      {};
    trackEvent('flight_search_results_shown', {
      source,
      search_session_id: sessionIdFromExtra || undefined,
      origin: (sp?.origin as string) ?? '',
      origin_city: (sp?.origin_city as string) ?? '',
      destination: (sp?.destination as string) ?? '',
      destination_city: (sp?.destination_city as string) ?? '',
      departure_date: (sp?.departure_date as string) ?? '',
      return_date: (sp?.return_date as string | null) ?? null,
      journey_type: (sp?.journey_type as string) ?? 'OneWay',
      adults: typeof passengers.adults === 'number' ? passengers.adults : 1,
      children: typeof passengers.children === 'number' ? passengers.children : 0,
      infants: typeof passengers.infants === 'number' ? passengers.infants : 0,
      cabin_class: (sp?.cabin_class as string) ?? 'Economy',
      total_results: typeof sm?.total_flights === 'number' ? sm.total_flights : 0,
      direct_count: typeof sm?.direct_count === 'number' ? sm.direct_count : 0,
      price_min: typeof priceRange.min === 'number' ? priceRange.min : 0,
      price_max: typeof priceRange.max === 'number' ? priceRange.max : 0,
      currency: (priceRange.currency as string) ?? 'USD',
    });
  }, [extracted?.data, sessionIdFromExtra, source, suppressFlightSearchResultsShownAnalytics]);

  // Issue #1034: handleSeeFullResults removed — panel renders the full list
  // inline, no separate "Show All Flights" navigation needed.

  const { data } = extracted;
  const { summary } = data;
  // Issue #1034: backend now sends a single flat best-value-sorted `flights`
  // array. We render that directly — no Cheapest/Best/Fastest tabs. Users
  // sort/filter via the full-results page. Legacy `categories.best_value.flights`
  // is accepted as a fallback for stale cached messages (and for tests that
  // still build fixtures in the pre-#1034 shape).
  const flatFlights = extracted.flights ?? [];
  const legacyBestFlights = data.categories?.best_value?.flights ?? [];
  const allFlights = flatFlights.length > 0 ? flatFlights : legacyBestFlights;
  if (allFlights.length === 0) {
    return null;
  }

  const totalCount = summary.total_flights ?? allFlights.length;
  const directCount = summary.direct_count ?? 0;
  const priceRange = summary.price_range ?? { min: 0, max: 0 };

  const airlines = [...new Set(allFlights.map((f) => f.airline))].filter(Boolean);
  const airline1 = airlines[0];
  const airline2 = airlines[1];
  const airline3 = airlines[2];

  const finalDestinationCode = data.search_params?.destination ?? '';
  const journeyType = data.search_params?.journey_type ?? 'OneWay';

  const mappedFlights: MappedFlight[] = allFlights.map((f) =>
    flightMapper(
      f as unknown as Record<string, unknown>,
      finalDestinationCode,
      journeyType
    )
  );
  // Used for the summary line ("Prices start from X on Airline Y...")
  const leadFlight = mappedFlights[0];

  const mainContent = (
    <>
      {showSummary && (
        <Box mb={4}>
          <Text size="sm" c="dimmed">
            {`We found ${totalCount} flights to your destination on ${
              leadFlight?.outbound?.departure_date || 'the selected date'
            },${
              directCount > 0
                ? ` including ${directCount} direct flight${directCount > 1 ? 's' : ''}.`
                : ''
            } Prices start from ${formatPrice(priceRange.min, 'USD')} on ${airline1 || 'various airlines'}${
              airline2 && airline3
                ? `, ${airline2}, and ${airline3}`
                : airline2
                  ? ` and ${airline2}`
                  : ''
            }.`}
          </Text>
        </Box>
      )}

      <Box style={{ width: '100%', minWidth: 0 }}>
        <ExpandableFlightCardList
          flights={mappedFlights}
          searchParams={
            data.search_params as Parameters<
              typeof ExpandableFlightCardList
            >[0]['searchParams']
          }
          showAllFlights={useRecommendationsCardStyle}
          categoryLabel="Best Value"
        />
      </Box>
    </>
  );

  // Issue #1034: the panel now renders the full flat flight list inline, so
  // the "Show All Flights" CTA is redundant. ``stickyBottomBar`` is kept as a
  // layout prop but no longer renders a bottom bar.
  if (_stickyBottomBar) {
    return (
      <Transition mounted transition="fade" duration={300}>
        {(styles) => (
          <Box
            style={{
              ...styles,
              flex: 1,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              overflowY: 'auto',
            }}
          >
            {mainContent}
          </Box>
        )}
      </Transition>
    );
  }

  return (
    <Transition mounted transition="fade" duration={300}>
      {(styles) => (
        <Box
          style={{
            ...styles,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          {mainContent}
        </Box>
      )}
    </Transition>
  );
}
