import { describe, expect, it, vi } from 'vitest';

// Mock heavy dependencies — we only care about the tripMeta shape
vi.mock('@/store/slices/uiSlice', () => ({
  setTripMeta: vi.fn((v) => ({ type: 'ui/setTripMeta', payload: v })),
  setLastItineraryPath: vi.fn((v) => ({ type: 'ui/setLastItineraryPath', payload: v })),
  setLastItineraryState: vi.fn((v) => ({ type: 'ui/setLastItineraryState', payload: v })),
}));

// Note: capturedTripMeta reads payload.meta since setTripMeta now takes { chatId, meta }
vi.mock('@/store/slices/flightBookingSlice', () => ({
  clearCachedFlightResults: vi.fn(() => ({ type: 'flight/clear' })),
}));
vi.mock('@/store/slices/hotelBookingSlice', () => ({
  clearCachedHotelResults: vi.fn(() => ({ type: 'hotel/clear' })),
}));
vi.mock('@/features/chat/utils/hydrateItinerarySideSearches', () => ({
  hydrateFlightSideSearchFromItinerary: vi.fn(),
  hydrateHotelSideSearchFromItinerary: vi.fn(),
}));
vi.mock('@/api/itinerariesApi', () => ({
  itinerariesApi: { util: { invalidateTags: vi.fn(() => ({ type: 'invalidate' })) } },
}));
vi.mock('@/features/routing', () => ({
  itineraryView: (id: string) => `/itinerary/${id}`,
}));

import { commitItineraryRichResultToUiState } from './itineraryNavigateFromChatExtraData';

function capturedTripMeta(dispatch: ReturnType<typeof vi.fn>) {
  const call = dispatch.mock.calls.find(
    ([action]) => action?.type === 'ui/setTripMeta',
  );
  // payload is now { chatId, meta } — return the meta object
  return call?.[0]?.payload?.meta as Record<string, unknown> | undefined;
}

describe('commitItineraryRichResultToUiState — buildTripMeta', () => {
  it('passes origin_location from extraData into tripMeta', () => {
    const dispatch = vi.fn();
    const extraData = {
      origin: 'Paris',
      destination: 'London',
      origin_location: { latitude: 48.857, longitude: 2.351 },
      destination_location: { latitude: 51.507, longitude: -0.127 },
    };

    commitItineraryRichResultToUiState(dispatch, extraData);

    const meta = capturedTripMeta(dispatch);
    expect(meta?.origin_location).toEqual({ latitude: 48.857, longitude: 2.351 });
  });

  it('passes destination_location into tripMeta', () => {
    const dispatch = vi.fn();
    const extraData = {
      destination: 'London',
      destination_location: { latitude: 51.507, longitude: -0.127 },
    };

    commitItineraryRichResultToUiState(dispatch, extraData);

    const meta = capturedTripMeta(dispatch);
    expect(meta?.destination_location).toEqual({ latitude: 51.507, longitude: -0.127 });
  });

  it('omits origin_location from tripMeta when not present in extraData', () => {
    const dispatch = vi.fn();
    const extraData = { destination: 'London' };

    commitItineraryRichResultToUiState(dispatch, extraData);

    const meta = capturedTripMeta(dispatch);
    expect(meta?.origin_location).toBeUndefined();
  });
});
