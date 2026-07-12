import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';

import type { HotelBookingState } from '@/store/slices/hotelBookingSlice';
import type { HotelItinerary } from '@/types/hotels';
import { defaultHotelFilterState } from '@/features/hotels/utils/hotelFilters';

import { HotelDetailPage } from './HotelDetailPage';

function renderHotelDetailPage() {
  return render(
    <MantineProvider theme={mantineTheme} env="test">
      <HotelDetailPage />
    </MantineProvider>
  );
}

const mockNavigate = vi.fn();
const mockDispatch = vi.fn();

let mockTokenId = 'token-b';

const sampleHotel: HotelItinerary = {
  id: 'h1',
  tokenId: 'token-b',
  name: 'Test Inn',
  address: '1 Main',
  city: 'NYC',
  country: 'US',
  starRating: 4,
  latitude: 40.7,
  longitude: -74,
  startingPrice: { currency: 'USD', amount: 100, perNight: 100 },
};

function buildHotelState(overrides: Partial<HotelBookingState>): HotelBookingState {
  return {
    currentStep: 'rooms',
    searchFormParams: {
      destination: 'NYC',
      checkin: '2026-04-20',
      checkout: '2026-04-21',
      rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
      nationality: 'US',
    },
    searchParams: null,
    sessionId: 'sess-1',
    internalSessionId: null,
    selectedHotel: sampleHotel,
    tokenId: 'token-b',
    productId: 'p1',
    hotelId: 'h1',
    selectedRoom: null,
    rateBasisId: null,
    rateRulesResponse: null,
    roomRatesResponse: { sessionId: 'sess-1', tokenId: 'token-a', rooms: [] },
    guests: [],
    contactEmail: '',
    contactPhone: '',
    specialRequests: '',
    bookingResult: null,
    paymentIntentId: null,
    bookingReference: null,
    loading: false,
    error: null,
    hotelFilters: defaultHotelFilterState,
    searchTriggerFromChips: 0,
    voucherRedemptionId: null,
    voucherDiscountCents: null,
    voucherCheckoutVoyaReference: null,
    voucherAppliedCode: null,
    voucherReservationExpiresAt: null,
    tripType: 'single',
    multistaySegments: [],
    multistayLegs: [],
    multistayGroupReference: null,
    multistayLegBookingResults: [],
    multistayActiveLegTab: 0,
    cachedHotelResults: null,
    cachedHotelResultsTrusted: false,
    hotelResultsCacheTimestamp: null,
    hotelResultsCachedParams: null,
    ...overrides,
  };
}

let mockHotelBookingSlice: HotelBookingState = buildHotelState({});

const getRoomRatesMock = vi.fn(() => ({
  unwrap: () =>
    Promise.resolve({
      rooms: [],
      tokenId: mockTokenId,
      sessionId: 'sess-1',
    }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ tokenId: mockTokenId }),
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock('@/store', () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: (selector: (state: { hotelBooking: HotelBookingState }) => unknown) =>
    selector({ hotelBooking: mockHotelBookingSlice }),
}));

vi.mock('@/api/hotelsApi', () => ({
  useGetRoomRatesMutation: () => [getRoomRatesMock],
  useGetRateRulesMutation: () => [vi.fn(), { isLoading: false }],
}));

vi.mock('@/utils/toast', () => ({
  showErrorToastFromError: vi.fn(),
}));

vi.mock('@/utils/devLog', () => ({ devLog: vi.fn() }));
vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));

vi.mock('../components/hotelDetail', () => ({
  HotelDetailHeader: () => null,
  ImageGallery: () => null,
  HotelAmenities: () => null,
  HotelReserveCard: () => null,
  HotelLocationMap: () => null,
  HotelDetailNavBar: () => null,
  HOTEL_DETAIL_NAV_SECTION_IDS: {
    overview: 'overview',
    photos: 'photos',
    amenities: 'amenities',
    location: 'location',
    rooms: 'rooms',
  },
  HOTEL_DETAIL_NAV_SCROLL_IDS: [],
  HotelRoomsSection: () => null,
}));

describe('HotelDetailPage', () => {
  beforeEach(() => {
    mockTokenId = 'token-b';
    mockHotelBookingSlice = buildHotelState({});
    getRoomRatesMock.mockClear();
    mockNavigate.mockClear();
    mockDispatch.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('does not call getRoomRates when cached room rates match current token and session', async () => {
    mockHotelBookingSlice = buildHotelState({
      roomRatesResponse: { sessionId: 'sess-1', tokenId: 'token-b', rooms: [] },
    });
    renderHotelDetailPage();
    await waitFor(() => {
      expect(getRoomRatesMock).not.toHaveBeenCalled();
    });
  });

  it('calls getRoomRates when URL token matches Redux but cached room rates are for another token', async () => {
    renderHotelDetailPage();

    await waitFor(() => {
      expect(getRoomRatesMock).toHaveBeenCalledWith({
        sessionId: 'sess-1',
        tokenId: 'token-b',
        productId: 'p1',
        hotelId: 'h1',
      });
    });
  });

  it('calls getRoomRates again after route token changes with stale roomRatesResponse', async () => {
    const { rerender } = renderHotelDetailPage();

    await waitFor(() => {
      expect(getRoomRatesMock).toHaveBeenCalledTimes(1);
    });

    mockTokenId = 'token-c';
    mockHotelBookingSlice = buildHotelState({
      tokenId: 'token-c',
      roomRatesResponse: { sessionId: 'sess-1', tokenId: 'token-a', rooms: [] },
    });
    rerender(
      <MantineProvider theme={mantineTheme} env="test">
        <HotelDetailPage />
      </MantineProvider>
    );

    await waitFor(() => {
      expect(getRoomRatesMock).toHaveBeenCalledTimes(2);
      expect(getRoomRatesMock).toHaveBeenLastCalledWith({
        sessionId: 'sess-1',
        tokenId: 'token-c',
        productId: 'p1',
        hotelId: 'h1',
      });
    });
  });
});
