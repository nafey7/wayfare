import { useEffect } from 'react';
import { Box, Button, Group, Loader, Pagination, Stack, Text, Title } from '@mantine/core';
import { HotelCard } from './HotelCard';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import type { FilterableHotel } from '../utils/hotelFilters';

export interface HotelResultsProps {
  hotels: FilterableHotel[];
  /** Original hotel objects for display (same order as hotels) */
  hotelObjects: (Hotel | HotelItinerary)[];
  nights: number;
  onHotelSelect: (hotel: Hotel | HotelItinerary) => void;
  selectingTokenId?: string | null;
  /** Curated highlights from API */
  curatedHotels?: {
    bestValue?: Hotel | HotelItinerary;
    cheapest?: Hotel | HotelItinerary;
    highestRated?: Hotel | HotelItinerary;
  };
  nextToken?: string | null;
  onLoadMore?: () => void;
  isLoadingMore?: boolean;
  /** Pagination: only hotels for the current page are rendered (reduces image requests). */
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  /** Called with the card's DOM element when mounted/unmounted — used by parent to scroll-to on map pin click. */
  onCardRef?: (key: string, el: HTMLElement | null) => void;
  /** Key of the card that should appear highlighted (from a map pin click). */
  highlightedKey?: string | null;
}

export function HotelResults({
  hotels: _hotels,
  hotelObjects,
  nights,
  onHotelSelect,
  selectingTokenId,
  curatedHotels,
  nextToken,
  onLoadMore,
  isLoadingMore = false,
  page = 1,
  pageSize = 24,
  onPageChange,
  onCardRef,
  highlightedKey,
}: HotelResultsProps) {
  const hasCurated =
    curatedHotels &&
    (curatedHotels.bestValue || curatedHotels.cheapest || curatedHotels.highestRated);

  const curatedIds = new Set<string>();
  if (curatedHotels?.bestValue) curatedIds.add(curatedHotels.bestValue.tokenId ?? curatedHotels.bestValue.id);
  if (curatedHotels?.cheapest) curatedIds.add(curatedHotels.cheapest.tokenId ?? curatedHotels.cheapest.id);
  if (curatedHotels?.highestRated) curatedIds.add(curatedHotels.highestRated.tokenId ?? curatedHotels.highestRated.id);
  const listHotels = hotelObjects.filter((h) => !curatedIds.has(h.tokenId ?? h.id));
  const totalCount = listHotels.length;
  const pageCount = Math.max(1, Math.ceil(totalCount / pageSize));
  const effectivePage = Math.max(1, Math.min(page, pageCount));
  const pageStart = (effectivePage - 1) * pageSize;
  const listHotelsPage = listHotels.slice(pageStart, pageStart + pageSize);

  // Keep parent page in sync when we clamp (e.g. after sort reduces total pages)
  useEffect(() => {
    if (pageCount > 0 && page !== effectivePage && onPageChange) {
      onPageChange(effectivePage);
    }
  }, [page, effectivePage, pageCount, onPageChange]);

  return (
    <Box>
      {/* Curated highlights */}
      {hasCurated && (
        <Box mb="md">
          <Title order={6} fw={600} mb="xs">
            Top picks
          </Title>
          <Stack gap="sm">
            {curatedHotels!.bestValue && (
              <Box ref={(el: HTMLDivElement | null) => onCardRef?.(curatedHotels.bestValue!.tokenId ?? curatedHotels.bestValue!.id, el)}>
                <HotelCard
                  hotel={curatedHotels.bestValue}
                  nights={nights}
                  onSelect={() => onHotelSelect(curatedHotels.bestValue!)}
                  isSelecting={selectingTokenId === curatedHotels.bestValue.tokenId}
                  isSelected={highlightedKey === (curatedHotels.bestValue.tokenId ?? curatedHotels.bestValue.id)}
                  valueBadge="Best Value"
                />
              </Box>
            )}
            {curatedHotels!.cheapest && (
              <Box ref={(el: HTMLDivElement | null) => onCardRef?.(curatedHotels.cheapest!.tokenId ?? curatedHotels.cheapest!.id, el)}>
                <HotelCard
                  hotel={curatedHotels.cheapest}
                  nights={nights}
                  onSelect={() => onHotelSelect(curatedHotels.cheapest!)}
                  isSelecting={selectingTokenId === curatedHotels.cheapest.tokenId}
                  isSelected={highlightedKey === (curatedHotels.cheapest.tokenId ?? curatedHotels.cheapest.id)}
                  valueBadge="Cheapest"
                />
              </Box>
            )}
            {curatedHotels!.highestRated && (
              <Box ref={(el: HTMLDivElement | null) => onCardRef?.(curatedHotels.highestRated!.tokenId ?? curatedHotels.highestRated!.id, el)}>
                <HotelCard
                  hotel={curatedHotels.highestRated}
                  nights={nights}
                  onSelect={() => onHotelSelect(curatedHotels.highestRated!)}
                  isSelecting={selectingTokenId === curatedHotels.highestRated.tokenId}
                  isSelected={highlightedKey === (curatedHotels.highestRated.tokenId ?? curatedHotels.highestRated.id)}
                  valueBadge="Highest Rated"
                />
              </Box>
            )}
          </Stack>
        </Box>
      )}

      {/* All results list (excluding curated to avoid duplicates) */}
      <Box className="hotels-list-container" style={{ overflowAnchor: 'none' }}>
        {listHotels.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            No hotels match your filters. Try adjusting your criteria.
          </Text>
        ) : (
          <>
            <Stack gap="xs">
              {listHotelsPage.map((hotel) => {
                const key = hotel.tokenId ?? hotel.id;
                return (
                  <Box key={key} ref={(el: HTMLDivElement | null) => onCardRef?.(key, el)}>
                    <HotelCard
                      hotel={hotel}
                      nights={nights}
                      onSelect={() => onHotelSelect(hotel)}
                      isSelecting={selectingTokenId === hotel.tokenId}
                      isSelected={highlightedKey === key}
                    />
                  </Box>
                );
              })}
            </Stack>
            {pageCount > 1 && onPageChange && (
              <Group justify="center" py="md">
                <Pagination
                  total={pageCount}
                  value={effectivePage}
                  onChange={(p) => onPageChange(p)}
                  withEdges
                />
              </Group>
            )}
            {nextToken && onLoadMore && (
              <Group justify="center" py="md">
                <Button
                  variant="outline"
                  onClick={onLoadMore}
                  disabled={isLoadingMore}
                  leftSection={isLoadingMore ? <Loader size="xs" /> : null}
                >
                  {isLoadingMore ? 'Loading…' : 'Load More Hotels'}
                </Button>
              </Group>
            )}
          </>
        )}
      </Box>
    </Box>
  );
}
