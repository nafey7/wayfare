import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import type { MulticityLegSelection } from '@/store/slices/flightBookingSlice';
import { trackEvent } from '@/utils/gtm';
import { PaymentPage } from './PaymentPage';

function renderPaymentPage() {
  return render(
    <MantineProvider theme={mantineTheme}>
      <PaymentPage />
    </MantineProvider>
  );
}

const mockNavigate = vi.fn();
const mockDispatch = vi.fn();
const mockIssueTicket = vi.fn();
const mockBookFlight = vi.fn();
const mockCheckBookingExpiry = vi.fn();
const mockGetRevolutTransaction = vi.fn();

let mockState: Record<string, unknown>;
let mockLocationState: Record<string, unknown>;

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: mockLocationState }),
    useParams: () => ({}),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock('@/store/hooks', () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: (selector: (state: Record<string, unknown>) => unknown) => selector(mockState),
}));

vi.mock('@/hooks/useEmailLinkAuth', () => ({
  useEmailLinkAuth: () => ({
    authDone: true,
    wrongAccount: false,
  }),
}));

vi.mock('@/api/paymentsApi', () => ({
  useCheckBookingExpiryMutation: () => [
    (args: unknown) => ({ unwrap: () => mockCheckBookingExpiry(args) }),
  ],
}));

vi.mock('@/api/revolutPaymentsApi', () => ({
  useCreateRevolutOrderMutation: () => [vi.fn(), { isLoading: false }],
  useLazyGetExistingRevolutOrderQuery: () => [vi.fn(), { isFetching: false }],
  useLazyGetRevolutTransactionQuery: () => [
    (orderId: string) => ({ unwrap: () => mockGetRevolutTransaction(orderId) }),
  ],
  useGetRevolutTransactionsByBookingQuery: () => ({ data: undefined }),
}));

vi.mock('@/api/flightsApi', () => ({
  useBookFlightMutation: () => [
    (args: unknown) => ({ unwrap: () => mockBookFlight(args) }),
  ],
  useIssueTicketMutation: () => [
    (args: unknown) => ({ unwrap: () => mockIssueTicket(args) }),
  ],
  useExchangeBookingTokenMutation: () => [vi.fn()],
  useGetTripDetailsMutation: () => [vi.fn()],
  useReportMulticityPartialBookingMutation: () => [vi.fn().mockResolvedValue(undefined)],
}));

vi.mock('@/api/usersApi', () => ({
  useLazyGetMeQuery: () => [vi.fn()],
}));

vi.mock('@/api/vouchersApi', () => ({
  useReleaseVoucherMutation: () => [
    (_args: { redemptionId: string }) => ({ unwrap: () => Promise.resolve({ released: true }) }),
  ],
}));

vi.mock('@/utils/toast', () => ({
  showErrorToast: vi.fn(),
  showInfoToast: vi.fn(),
  showSuccessToast: vi.fn(),
}));

vi.mock('@/utils/devLog', () => ({ devLog: vi.fn() }));
vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));
vi.mock('../utils/bookingRequest', () => ({
  buildBookingRequest: vi.fn(() => ({ mocked: true })),
}));
vi.mock('../utils/redirectToSearch', () => ({
  buildFlightSearchRedirectTarget: vi.fn(() => '/flights/search'),
}));

vi.mock('@/components/revolut', () => ({
  RevolutPaymentForm: ({
    onSuccess,
    onBeforeSubmit,
  }: {
    onSuccess: (paymentId: string) => void | Promise<void>;
    onBeforeSubmit?: () => Promise<void>;
  }) => (
    <button
      type="button"
      onClick={() => {
        void (async () => {
          if (onBeforeSubmit) await onBeforeSubmit();
          await onSuccess('pi_test_123');
        })();
      }}
    >
      Complete payment
    </button>
  ),
}));

function buildMockState(fareType: 'Public' | 'WebFare') {
  return {
    auth: {
      isAuthenticated: true,
      user: { firstName: 'Test', lastName: 'User' },
    },
    ui: {
      activeSavedItineraryIdForBooking: null,
    },
    flightBooking: {
      passengers: [
        {
          firstName: 'Jane',
          lastName: 'Doe',
          nationality: 'NL',
        },
      ],
      contact: {
        email: 'jane@example.com',
        country_code: '31',
        phone: '123456789',
      },
      postalCode: null,
      savedPassengerIds: {},
      sessionId: 'session-123',
      fareSourceCode: 'fare-123',
      isLCC: fareType === 'WebFare',
      bookingResult: {
        voyaBookingReference: 'VOYA-GDS-123',
        status: 'pending',
        totalAmount: 45600,
        currency: 'usd',
      },
      revalidationResponse: {
        sessionId: 'session-123',
        fareSourceCode: 'fare-123',
        validatedFareItineraries: [
          {
            pricing: { fareType },
            flightLegs: [{ flightSegments: [] }],
          },
        ],
      },
      searchFormParams: {
        tripType: 'one-way',
        from: 'AMS',
        to: 'LHR',
        date: null,
        returnDate: null,
        travellers: {
          adults: 1,
          children: 0,
          infants: 0,
          cabinClass: 'Economy',
        },
      },
    },
  };
}

function mockMulticityLeg(legIndex: number, totalFare: number, currency: string): MulticityLegSelection {
  return {
    legIndex,
    sessionId: `s-${legIndex}`,
    fareSourceCode: `f-${legIndex}`,
    selectedFlightData: {
      id: `${legIndex}::x`,
      aircraftName: 'A',
      flightNumber: '1',
      tags: [],
      passengers: 1,
      passengerCounts: { adults: 1, children: 0, infants: 0 },
      legs: [],
      price: totalFare,
    },
    revalidateResponse: {
      sessionId: `s-${legIndex}`,
      fareSourceCode: `f-${legIndex}`,
      isFareAvailable: true,
      validatedFareItineraries: [
        {
          flightLegs: [],
          updatedPricing: {
            fareType: 'WebFare',
            fareTotals: {
              totalFare: { amount: String(totalFare), currency },
              platformFeePercentage: 5,
            },
            validatedFareTotals: {
              totalFare: { amount: String(totalFare), currency },
              platformFeePercentage: 5,
            },
          },
        },
      ],
    },
  };
}

/** GDS (non-LCC) multicity leg — fare totals under `pricing` for aggregateMulticityFare */
function mockMulticityLegGds(legIndex: number, totalFare: number, currency: string): MulticityLegSelection {
  return {
    legIndex,
    sessionId: `s-${legIndex}`,
    fareSourceCode: `f-${legIndex}`,
    selectedFlightData: {
      id: `${legIndex}::gds`,
      aircraftName: 'A',
      flightNumber: '1',
      tags: [],
      passengers: 1,
      passengerCounts: { adults: 1, children: 0, infants: 0 },
      legs: [],
      price: totalFare,
    },
    revalidateResponse: {
      sessionId: `s-${legIndex}`,
      fareSourceCode: `f-${legIndex}`,
      isFareAvailable: true,
      validatedFareItineraries: [
        {
          flightLegs: [{ flightSegments: [] }],
          pricing: {
            fareType: 'Public',
            fareTotals: {
              totalFare: { amount: String(totalFare), currency },
              platformFeePercentage: 10.5,
            },
          },
        },
      ],
    },
  };
}

function buildLocationState(bookingRef: string) {
  return {
    bookingResult: {
      voyaBookingReference: bookingRef,
      status: 'pending',
      totalAmount: 45600,
      currency: 'usd',
    },
    searchSessionId: 'session-123',
    revalidateResponse: {
      sessionId: 'session-123',
      fareSourceCode: 'fare-123',
      validatedFareItineraries: [
        {
          pricing: { fareType: 'Public' },
          flightLegs: [{ flightSegments: [] }],
        },
      ],
    },
    revolutOrder: {
      orderId: 'order-123',
      publicOrderId: 'public-order-123',
      amount: 45600,
      currency: 'usd',
      platformFee: 3600,
      supplierAmount: 42000,
    },
  };
}

describe('PaymentPage', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockDispatch.mockReset();
    mockIssueTicket.mockReset();
    mockBookFlight.mockReset();
    mockCheckBookingExpiry.mockReset();
    mockGetRevolutTransaction.mockReset();
    vi.mocked(trackEvent).mockReset();

    mockState = buildMockState('Public');
    mockLocationState = buildLocationState('VOYA-GDS-123');
    mockBookFlight.mockResolvedValue({
      voyaBookingReference: 'VOYA-GDS-123',
      externalBookingReference: 'EXT-GDS',
      status: 'confirmed',
      totalAmount: 45600,
      currency: 'usd',
    });
  });

  it('redirects GDS payment success to the booking details page', async () => {
    mockCheckBookingExpiry.mockResolvedValue({ isValid: true });
    mockGetRevolutTransaction.mockResolvedValue({ status: 'succeeded' });
    mockIssueTicket.mockResolvedValue({
      success: true,
      externalBookingReference: 'EXT123',
    });

    renderPaymentPage();

    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /complete payment/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/flights/bookings/VOYA-GDS-123', {
        replace: true,
      });
    });
  });

  it('redirects LCC payment success to the booking details page', async () => {
    mockState = buildMockState('WebFare');
    mockLocationState = {
      ...buildLocationState('VOYA-LCC-PENDING'),
      revalidateResponse: {
        sessionId: 'session-123',
        fareSourceCode: 'fare-123',
        validatedFareItineraries: [
          {
            pricing: { fareType: 'WebFare' },
            flightLegs: [{ flightSegments: [] }],
          },
        ],
      },
    };
    mockBookFlight.mockResolvedValue({
      voyaBookingReference: 'VOYA-LCC-123',
      externalBookingReference: 'EXT456',
      status: 'confirmed',
      totalAmount: 45600,
      currency: 'usd',
    });

    renderPaymentPage();

    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /complete payment/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/flights/bookings/VOYA-LCC-123', {
        replace: true,
      });
    });
  });

  it('emits multicity partial analytics when payment succeeds but a later leg fails', async () => {
    const leg0 = mockMulticityLeg(0, 100, 'USD');
    const leg1 = mockMulticityLeg(1, 200, 'USD');
    mockState = {
      auth: {
        isAuthenticated: true,
        user: { firstName: 'Test', lastName: 'User' },
      },
      ui: {
        activeSavedItineraryIdForBooking: null,
      },
      flightBooking: {
        passengers: [
          {
            firstName: 'Jane',
            lastName: 'Doe',
            nationality: 'NL',
          },
        ],
        contact: {
          email: 'jane@example.com',
          country_code: '31',
          phone: '123456789',
        },
        postalCode: null,
        savedPassengerIds: {},
        sessionId: 'session-mc',
        fareSourceCode: 'fare-0',
        isLCC: true,
        bookingResult: {
          voyaBookingReference: 'VOYA-MC-PENDING',
          status: 'pending',
          totalAmount: 30000,
          currency: 'usd',
        },
        revalidationResponse: leg0.revalidateResponse,
        multicitySelectedLegs: {
          0: leg0,
          1: leg1,
        },
        multicityGroupReference: 'VOYA-MC-testgroup',
        multicityLegBookingResults: null,
        searchFormParams: {
          tripType: 'multi-city',
          from: 'AMS',
          to: 'LHR',
          date: null,
          returnDate: null,
          segments: [{ from: 'AMS', to: 'JFK' }, { from: 'JFK', to: 'AMS' }],
          travellers: {
            adults: 1,
            children: 0,
            infants: 0,
            cabinClass: 'Economy',
          },
        },
      },
    };
    mockLocationState = {
      multicityMode: true,
      multicityGroupReference: 'VOYA-MC-testgroup',
      searchSessionId: 'session-mc',
      revalidateResponse: leg0.revalidateResponse,
      revolutOrder: {
        orderId: 'order-mc',
        publicOrderId: 'public-order-mc',
        amount: 31500,
        currency: 'usd',
        platformFee: 1500,
        supplierAmount: 30000,
      },
    };

    mockBookFlight
      .mockResolvedValueOnce({
        voyaBookingReference: 'VOYA-MC-LEG-0',
        externalBookingReference: 'EXT0',
        status: 'confirmed',
        totalAmount: 10000,
        currency: 'usd',
      })
      .mockRejectedValueOnce(new Error('Second leg supplier error'));

    renderPaymentPage();

    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /complete payment/i }));

    await waitFor(() => {
      expect(vi.mocked(trackEvent)).toHaveBeenCalledWith(
        'multicity_booking_partial_after_payment',
        expect.objectContaining({
          multicity_group_reference: 'VOYA-MC-testgroup',
          legs_booked_count: 1,
          legs_total: 2,
          last_error: 'Second leg supplier error',
        })
      );
    });

    expect(vi.mocked(trackEvent)).toHaveBeenCalledWith(
      'flight_payment_completed',
      expect.objectContaining({
        booking_type: 'multicity',
        multicity_status: 'partial',
      })
    );
  });

  it('GDS multicity (partial legs): pays without book-before-pay then books each selected leg', async () => {
    const leg0 = mockMulticityLegGds(0, 100, 'USD');
    const leg1 = mockMulticityLegGds(1, 200, 'USD');
    mockState = {
      auth: {
        isAuthenticated: true,
        user: { firstName: 'Test', lastName: 'User' },
      },
      ui: {
        activeSavedItineraryIdForBooking: null,
      },
      flightBooking: {
        passengers: [
          {
            firstName: 'Jane',
            lastName: 'Doe',
            nationality: 'NL',
          },
        ],
        contact: {
          email: 'jane@example.com',
          country_code: '31',
          phone: '123456789',
        },
        postalCode: null,
        savedPassengerIds: {},
        sessionId: leg0.sessionId,
        fareSourceCode: leg0.fareSourceCode,
        isLCC: false,
        bookingResult: null,
        revalidationResponse: leg0.revalidateResponse,
        multicitySelectedLegs: {
          0: leg0,
          1: leg1,
        },
        multicityGroupReference: 'VOYA-MC-gds-group',
        multicityLegBookingResults: null,
        searchFormParams: {
          tripType: 'multi-city',
          from: 'AMS',
          to: 'LHR',
          date: null,
          returnDate: null,
          segments: [
            { from: 'AMS', to: 'JFK' },
            { from: 'JFK', to: 'LHR' },
            { from: 'LHR', to: 'AMS' },
          ],
          travellers: {
            adults: 1,
            children: 0,
            infants: 0,
            cabinClass: 'Economy',
          },
        },
      },
    };
    mockLocationState = {
      multicityMode: true,
      multicityGroupReference: 'VOYA-MC-gds-group',
      searchSessionId: leg0.sessionId,
      revalidateResponse: leg0.revalidateResponse,
      revolutOrder: {
        orderId: 'order-mc-gds',
        publicOrderId: 'public-order-mc-gds',
        amount: 33150,
        currency: 'usd',
        platformFee: 3150,
        supplierAmount: 30000,
      },
    };

    mockBookFlight
      .mockResolvedValueOnce({
        voyaBookingReference: 'VOYA-MC-GDS-0',
        externalBookingReference: 'EXT0',
        status: 'confirmed',
        totalAmount: 10000,
        currency: 'usd',
      })
      .mockResolvedValueOnce({
        voyaBookingReference: 'VOYA-MC-GDS-1',
        externalBookingReference: 'EXT1',
        status: 'confirmed',
        totalAmount: 20000,
        currency: 'usd',
      });
    mockIssueTicket.mockResolvedValue({ success: true, externalBookingReference: 'TIX' });

    renderPaymentPage();

    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /complete payment/i }));

    expect(mockCheckBookingExpiry).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(mockBookFlight).toHaveBeenCalledTimes(2);
    });
    expect(mockIssueTicket).toHaveBeenCalledTimes(2);
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/flights/bookings/VOYA-MC-GDS-0', {
        replace: true,
        state: expect.objectContaining({
          multicityGroupReference: 'VOYA-MC-gds-group',
        }),
      });
    });
  });
});
