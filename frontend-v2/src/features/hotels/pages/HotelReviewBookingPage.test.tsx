import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import type { HotelGuestDetails } from '@/types/hotels';
import type { RateRulesResponse, RoomRate } from '@/types/hotels';
import type { HotelItinerary } from '@/types/hotels';

/** Avoid loading heavy MUI icon / layout trees (reduces open file handles in CI). */
vi.mock('../components/GuestForm', () => ({
  GuestForm: () => <div data-testid="guest-form-stub" />,
}));

vi.mock('../components/HotelBookingReviewLayout', () => ({
  HotelBookingReviewLayout: ({
    onContinue,
    footerPrimaryLabel,
    continueLoading,
  }: {
    onContinue: () => void;
    footerPrimaryLabel: string;
    continueLoading?: boolean;
  }) => (
    <button type="button" onClick={onContinue} disabled={continueLoading}>
      {footerPrimaryLabel}
    </button>
  ),
}));

vi.mock('@/components/CountrySelect', () => ({
  CountrySelect: ({
    label,
    value,
    onChange,
  }: {
    label?: string;
    value: string;
    onChange: (v: string) => void;
  }) => (
    <input
      aria-label={label ?? 'country'}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));


import { showErrorToast } from '@/utils/toast';
import { HotelReviewBookingPage } from './HotelReviewBookingPage';

const { mockRevolutMutation } = vi.hoisted(() => ({
  mockRevolutMutation: vi.fn(),
}));

const mockNavigate = vi.fn();
const mockDispatch = vi.fn();

let mockState: Record<string, unknown>;

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/store/hooks', () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: (selector: (state: Record<string, unknown>) => unknown) => selector(mockState),
}));

vi.mock('@/api/usersApi', () => ({
  useGetPassengersQuery: () => ({ data: [] }),
  useUpdatePassengerMutation: () => [vi.fn()],
}));

vi.mock('@/api/revolutPaymentsApi', () => ({
  useCreateRevolutOrderMutation: () => [mockRevolutMutation, { isLoading: false }],
}));

vi.mock('@/api/vouchersApi', () => ({
  useReleaseVoucherMutation: () => [vi.fn()],
}));

vi.mock('@/features/discount/components/PromoCodeField', () => ({
  PromoCodeField: () => null,
}));

vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));

vi.mock('@/utils/toast', () => ({
  showErrorToast: vi.fn(),
}));

vi.mock('../components/hotelDetail', () => ({
  HotelDetailRoomCard: () => <div data-testid="hotel-detail-room-card">Room</div>,
}));

vi.mock('@/features/profile/components/travelDetails/PassengerFormDialog', () => ({
  PassengerFormDialog: () => null,
}));

function buildSelectedHotel(): HotelItinerary {
  return {
    id: 'h1',
    tokenId: 'tok1',
    name: 'Test Hotel',
    address: '1 Main St',
    city: 'NYC',
    country: 'US',
    starRating: 4,
    latitude: 40,
    longitude: -74,
    startingPrice: { currency: 'USD', amount: 250.505, perNight: 125.25 },
    total: 250.505,
  };
}

function buildSelectedRoom(): RoomRate {
  return {
    rateBasisId: 'rb1',
    totalPrice: 250.505,
    currency: 'USD',
  };
}

function buildRateRules(): RateRulesResponse {
  return {
    sessionId: 's1',
    hotelId: 'h1',
    tokenId: 'tok1',
    roomType: 'std',
    description: 'd',
    roomCode: 'c',
    fareType: 'f',
    rateBasisId: 'rb1',
    currency: 'USD',
    netPrice: 250.505,
    boardBasis: 'RO',
    maxOccupancyPerRoom: 2,
    inventoryType: 'i',
    cancellationPolicy: 'n',
    facilities: [],
    images: [],
    remark: '',
    originalNetPrice: 220,
    platformFeePercentage: 10.5,
  };
}

function buildGuest(): HotelGuestDetails {
  return {
    title: 'Mr',
    firstName: 'Jane',
    lastName: 'Doe',
    roomNumber: 1,
    isChild: false,
  };
}

function buildMockState(overrides: {
  hotelGuests?: HotelGuestDetails[];
  contactEmail?: string;
  contactPhone?: string;
  /** When false, user has no names (avoids lead-guest auto-fill clearing validation). */
  userWithProfile?: boolean;
} = {}) {
  const { userWithProfile = true } = overrides;
  const hotel = buildSelectedHotel();
  return {
    auth: {
      user: {
        id: 'u1',
        email: userWithProfile ? 'jane@test.com' : '',
        firstName: userWithProfile ? 'Jane' : '',
        lastName: userWithProfile ? 'Doe' : '',
        phone: userWithProfile ? '+12025550123' : '',
      },
    },
    hotelBooking: {
      searchFormParams: {
        destination: 'NYC',
        checkin: '2026-06-01',
        checkout: '2026-06-03',
        rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }],
        nationality: 'US',
      },
      tokenId: 'tok1',
      selectedHotel: hotel,
      selectedRoom: buildSelectedRoom(),
      rateRulesResponse: buildRateRules(),
      guests: overrides.hotelGuests ?? [buildGuest()],
      contactEmail: overrides.contactEmail ?? 'jane@test.com',
      contactPhone: overrides.contactPhone ?? '+12025550123',
      specialRequests: '',
      tripType: 'single',
      multistayLegs: [],
      multistaySegments: [],
      multistayGroupReference: null,
      multistayLegBookingResults: [],
      multistayActiveLegTab: 0,
    },
  };
}

function renderPage() {
  return render(
    <MantineProvider theme={mantineTheme} env="test">
      <HotelReviewBookingPage />
    </MantineProvider>,
  );
}

describe('HotelReviewBookingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRevolutMutation.mockImplementation(() => ({
      unwrap: () =>
        Promise.resolve({
          orderId: 'ord1',
          publicOrderId: 'pub1',
          amount: 25051,
          currency: 'USD',
          supplierAmount: 22000,
          voyaBookingReference: 'ref1',
        }),
    }));
  });

  it('shows validation error when Continue is clicked with incomplete guest/contact', async () => {
    const user = userEvent.setup();
    mockState = buildMockState({
      userWithProfile: false,
      hotelGuests: [
        {
          title: 'Mr',
          firstName: '',
          lastName: '',
          roomNumber: 1,
          isChild: false,
        },
      ],
      contactEmail: '',
      contactPhone: '',
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Please complete guest and contact details.',
        expect.objectContaining({ autoClose: 12_000 }),
      );
    });
    expect(mockRevolutMutation).not.toHaveBeenCalled();
  });

  it('creates Revolut order with rounded cents and navigates to payment when details are valid', async () => {
    const user = userEvent.setup();
    mockState = buildMockState();

    renderPage();

    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => {
      expect(mockRevolutMutation).toHaveBeenCalled();
    });

    expect(mockRevolutMutation).toHaveBeenCalledWith(
      expect.objectContaining({
        bookingAmount: 25051,
        currency: 'usd',
        orderType: 'hotel',
      }),
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/hotels/payment',
        expect.objectContaining({
          state: expect.objectContaining({
            revolutOrder: expect.objectContaining({ orderId: 'ord1' }),
          }),
        }),
      );
    });
  });

  it('surfaces payment error when Revolut order creation fails', async () => {
    const user = userEvent.setup();
    mockState = buildMockState();
    mockRevolutMutation.mockImplementation(() => ({
      unwrap: () => Promise.reject(new Error('network')),
    }));

    renderPage();

    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'network',
        expect.objectContaining({ autoClose: 12_000 }),
      );
    });
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
