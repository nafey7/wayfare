import { useEffect, useRef } from 'react';
import { Box, Stack } from '@mantine/core';
import { Outlet, useLocation } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  setLastFlightPath,
  setLastHotelPath,
  setLastItineraryPath,
  setLastItineraryState,
  selectLastFlightPath,
  selectLastHotelPath,
  selectLastItineraryPath,
} from '@/store/slices/uiSlice';
import { selectChatId } from '@/store/slices/chatSlice';
import { parseItineraryNavigationState } from '@/features/itinerary/utils/navigationState';
import { getContentDomain } from '@/features/routing';
import { LAYOUT } from './layoutConstants';

/**
 * Persistent right-hand content panel for LayoutWithChat.
 * Tabs (Itinerary | Flights | Hotel) always visible; Chat tab chip is mobile-only (md+ hides it; chat stays in the left column).
 * Renders child routes (home, itinerary, flights, hotels) via Outlet below.
 */
export function ContentPanel() {
  const location = useLocation();
  const dispatch = useAppDispatch();
  const lastFlightPath = useAppSelector(selectLastFlightPath);
  const lastHotelPath = useAppSelector(selectLastHotelPath);
  const lastItineraryPath = useAppSelector(selectLastItineraryPath);
  const chatId = useAppSelector(selectChatId);

  // Guard against re-running the effect when lastItineraryPath changes due to a
  // conversation switch (per-chat keying) while we're not actually navigating.
  // Without this guard, switching chats while on /flights/search would re-run
  // the effect and overwrite lastFlightPath — stripping ?q=PAR→LON URL params.
  const prevLocationKeyRef = useRef('');

  // Sync last flight/hotel/itinerary path for tab chip resume (navigate back to last step).
  // fullPath is stored as-is (auth- or `/public/chat/...`); see resolveContentPanelTabTarget.
  // Only dispatch when path actually changes to avoid redundant Redux + localStorage writes.
  useEffect(() => {
    const { pathname, search } = location;
    const fullPath = pathname + search;

    // Only fire on actual navigation — not on selector-value changes caused by
    // switching active chatId (which changes lastItineraryPath without a real nav).
    if (fullPath === prevLocationKeyRef.current) return;
    prevLocationKeyRef.current = fullPath;

    const domain = getContentDomain(pathname);
    const resolvedChatId = chatId ?? '__anon__';
    if (domain === 'flights' && fullPath !== lastFlightPath) {
      dispatch(setLastFlightPath(fullPath));
    } else if (domain === 'hotels' && fullPath !== lastHotelPath) {
      dispatch(setLastHotelPath(fullPath));
    } else if (domain === 'itinerary') {
      if (fullPath !== lastItineraryPath) {
        dispatch(setLastItineraryPath({ chatId: resolvedChatId, path: fullPath }));
        const navState = parseItineraryNavigationState(location.state);
        const si = navState?.structuredItinerary;
        const hasValidState =
          si &&
          typeof si === 'object' &&
          Array.isArray(si.itineraryItems) &&
          (si.itineraryItems as unknown[]).length > 0;
        // Dispatch only on path change (not on same-path state-only re-navigations)
        // to suppress rapid-fire duplicates from applySuccessfulChatResponse +
        // navigateItineraryFromChatExtraData firing setLastItineraryState for the
        // same generation. guestItineraryListener dedupes content-equal entries.
        if (hasValidState && navState) {
          dispatch(setLastItineraryState({ chatId: resolvedChatId, state: navState }));
        }
      }
    }
  }, [location, dispatch, lastFlightPath, lastHotelPath, lastItineraryPath, chatId]);

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: 'instant' });
  }, [location.pathname]);

  const pathname = location.pathname;
  const domain = getContentDomain(pathname);
  const isItinerary = domain === 'itinerary';
  const isFlightsRecommendations = domain === 'flights' && pathname.includes('/recommendations');
  const isFlightsSearch = domain === 'flights' && pathname.includes('/search');
  const isHotelsRecommendations = domain === 'hotels' && pathname.includes('/recommendations');
  const isHotelsSearch = domain === 'hotels' && pathname.includes('/search');
  const useFlexScrollLayout =
    isItinerary || isFlightsRecommendations || isFlightsSearch || isHotelsRecommendations || isHotelsSearch;

  return (
    <Box
      style={{
        flex: LAYOUT.CONTENT_FLEX,
        minWidth: 0,
        minHeight: 0,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* `gap={0}`: MUI `<Stack>` defaults `spacing` to 0; Mantine defaults to "md".
          Override to preserve identical layout pre/post migration. */}
      <Stack
        gap={0}
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
          paddingInline: 24, // MUI `px: 3` (8 × 3)
          paddingBlock: 16,  // MUI `py: 2` (8 × 2)
        }}
      >
        <Box
          ref={scrollContainerRef}
          style={{
            flex: 1,
            minHeight: 0,
            overflow: useFlexScrollLayout ? 'hidden' : 'auto',
            display: useFlexScrollLayout ? 'flex' : 'block',
            flexDirection: useFlexScrollLayout ? 'column' : undefined,
          }}
        >
          <Outlet />
        </Box>
      </Stack>
    </Box>
  );
}
