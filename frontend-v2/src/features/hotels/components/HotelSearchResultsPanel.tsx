import { useEffect, useMemo } from 'react';
import { Box, Text, Transition } from '@mantine/core';
import { formatPrice } from '@/features/chat/utils/formatters';
import { hotelMapper } from '@/features/chat/utils/hotelUtils';
import type { MappedHotel } from '@/features/chat/utils/hotelUtils';
import { ExpandableHotelCardList } from '@/features/chat/components/hotels/ExpandableHotelCardList';
import { useBestHotelsWithValidImages } from '@/features/chat/components/hotels/useBestHotelsWithValidImages';
import type { ExtractedHotelSearchData, HotelSearchParams as ApiHotelSearchParams } from '@/types/api.helpers';
import type { HotelSearchParams as CardHotelSearchParams } from '@/features/chat/components/hotels/HotelDetailsCard';
import { trackEvent } from '@/utils/gtm';
import {
  hotelSearchResultsShownDedupeKey,
  tryMarkHotelSearchResultsShown,
} from '@/features/hotels/utils/hotelSearchResultsAnalyticsDedupe';

function toCardSearchParams(sp: ApiHotelSearchParams): CardHotelSearchParams {
  return {
    destination_city:
      (sp.destination_city ?? sp.destination ?? sp.city_name) as string | undefined,
    country: (sp.country ?? sp.country_name) as string | undefined,
    check_in_date: (sp.check_in_date ?? sp.checkin) as string | undefined,
    check_out_date: (sp.check_out_date ?? sp.checkout) as string | undefined,
    rooms: sp.rooms ?? undefined,
    adults: sp.adults ?? undefined,
    children: sp.children ?? undefined,
  };
}

export interface HotelSearchResultsPanelProps {
  data: ExtractedHotelSearchData;
  source?: 'chat' | 'recommendations' | 'chat-inline';
  showSummary?: boolean;
  /**
   * @deprecated Issue #1034 — panel now always renders the flat list inline.
   * Kept in the signature to avoid breaking call sites; the value is ignored.
   */
  stickyBottomBar?: boolean;
}

/**
 * Reusable hotel search results panel: renders the flat best-value-sorted hotel
 * list inline. No category tabs, no "Show All Hotels" CTA (#1034).
 */
export function HotelSearchResultsPanel({
  data: extracted,
  source = 'recommendations',
  showSummary = false,
  stickyBottomBar: _stickyBottomBar = false,
}: HotelSearchResultsPanelProps) {
  const isRecommendationsLayout = source === 'recommendations' || source === 'chat-inline';

  const { data } = extracted;
  const { summary, search_params: searchParamsRaw } = data;
  const searchParams = toCardSearchParams(searchParamsRaw ?? {});

  // Issue #1034: backend sends a single flat best-value-sorted `hotels`
  // array. No tabs — render the flat list directly. Legacy `categories` is
  // accepted as a fallback for stale cached messages (also when the flat
  // array is present but empty, e.g. cached pre-#1034 payloads).
  const flatHotels = extracted.hotels ?? [];
  const allHotels =
    flatHotels.length > 0 ? flatHotels : (data.categories?.best_value?.hotels ?? []);

  const mappedAllHotels = useMemo(
    () =>
      (allHotels as unknown[])
        .map((h) => hotelMapper(h as Record<string, unknown>))
        .filter(Boolean) as MappedHotel[],
    [allHotels]
  );
  // Keep image filtering so the panel still shows hotels with usable images
  // first; the underlying list is unchanged in count.
  const { hotels: bestHotelsWithImages, isLoading: bestHotelsLoading } =
    useBestHotelsWithValidImages(mappedAllHotels);

  const totalCount = summary.total_found ?? summary.total_hotels ?? 0;
  const nights = summary.nights ?? 1;
  const priceRange = summary.price_range ?? {};
  const priceCurrency = (priceRange as { currency?: string }).currency ?? 'GBP';

  const sessionIdFromExtracted = extracted.session_id;

  useEffect(() => {
    if (sessionIdFromExtracted) {
      try {
        localStorage.setItem('hotelSessionId', sessionIdFromExtracted);
      } catch {
        // Ignore storage errors
      }
    }
  }, [sessionIdFromExtracted]);

  useEffect(() => {
    if (!extracted?.data) return;
    const sp = (extracted.data.search_params ?? {}) as Record<string, unknown>;
    const dedupeKey = hotelSearchResultsShownDedupeKey(
      source,
      sessionIdFromExtracted || undefined,
      sp
    );
    if (!tryMarkHotelSearchResultsShown(dedupeKey)) return;
    trackEvent('hotel_search_results_shown', {
      source,
      search_session_id: sessionIdFromExtracted || undefined,
      destination_city: (sp?.destination_city as string) ?? '',
      country: (sp?.country as string) ?? (sp?.country_name as string) ?? '',
      check_in_date: (sp?.check_in_date as string) ?? '',
      check_out_date: (sp?.check_out_date as string) ?? '',
      rooms: typeof sp?.rooms === 'number' ? sp.rooms : 1,
      adults: typeof sp?.adults === 'number' ? sp.adults : 2,
      children: typeof sp?.children === 'number' ? sp.children : 0,
    });
  }, [extracted?.data, sessionIdFromExtracted, source]);

  if (mappedAllHotels.length === 0) {
    return null;
  }

  const destinationCity = searchParams.destination_city ?? 'your destination';
  const minPrice = (priceRange as { min?: number }).min;
  const summaryText =
    totalCount > 0
      ? `We found ${totalCount} hotel${totalCount !== 1 ? 's' : ''} in ${destinationCity} for ${nights} night${nights !== 1 ? 's' : ''}${minPrice ? `. Prices start from ${formatPrice(minPrice, priceCurrency)}.` : '.'}`
      : `Here are the hotel options in ${destinationCity}.`;

  const isRecommendations = isRecommendationsLayout;

  // Issue #1034: render the flat best-value-sorted list. Prefer the
  // image-validated subset so cards look polished; if that hook is still
  // loading or returns empty, fall back to the raw mapped list.
  const hotelsToRender =
    !bestHotelsLoading && bestHotelsWithImages.length > 0
      ? bestHotelsWithImages
      : mappedAllHotels;

  const mainContent = (
    <>
      {showSummary && (
        <Box mb={4}>
          <Text size="sm" c="dimmed">
            {summaryText}
          </Text>
        </Box>
      )}

      <Box>
        {bestHotelsLoading && hotelsToRender === mappedAllHotels ? (
          <Text size="sm" c="dimmed">
            Loading best options…
          </Text>
        ) : (
          <ExpandableHotelCardList
            hotels={hotelsToRender}
            searchParams={searchParams}
            showAllHotels={isRecommendations}
            valueBadge="Best Value"
          />
        )}
      </Box>
    </>
  );

  // Issue #1034: "Show All Hotels" CTA removed — panel now renders the full
  // hotel list inline, so the CTA was a no-op duplicate. `stickyBottomBar` is
  // kept as a layout prop but no longer renders a bottom bar.
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
