import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { store } from '@/store';
import { clearAuth, setCredentials } from '@/store/slices/authSlice';
import { closeAuthModal } from '@/store/slices/uiSlice';
import type { AuthCredentials } from '@/types/auth';
import { ItineraryResultMessage } from './ItineraryResultMessage';
import type { ChatMessage } from '@/types/chat';
import { trackEvent } from '@/utils/gtm';

vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Avoid `importOriginal` for @mui/icons-material — it loads the full icon package and can hit EMFILE.
// Stub barrel imports for ItineraryResultMessage + ItineraryDetailsComponent (and shared chips).
const nullIcon = vi.hoisted(() => () => null);
vi.mock('@mui/icons-material', () => ({
  __esModule: true,
  Map: nullIcon,
  Place: nullIcon,
  LocalDining: nullIcon,
  AccountBalanceWallet: nullIcon,
  ExpandMore: nullIcon,
  ExpandLess: nullIcon,
  AccessTime: nullIcon,
  Star: nullIcon,
  DirectionsBus: nullIcon,
  LocalTaxi: nullIcon,
  DirectionsCar: nullIcon,
  DirectionsWalk: nullIcon,
  LocalAirport: nullIcon,
  LightbulbOutlined: nullIcon,
  FlightTakeoff: nullIcon,
  Hotel: nullIcon,
  Close: nullIcon,
  Remove: nullIcon,
  Add: nullIcon,
  AddCircleOutline: nullIcon,
  ChevronLeft: nullIcon,
  ChevronRight: nullIcon,
  CalendarMonth: nullIcon,
  Payments: nullIcon,
}));

const mediaQueryState = vi.hoisted(() => ({ isMdUp: true }));
vi.mock('@mui/material', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mui/material')>();
  return { ...actual, useMediaQuery: () => mediaQueryState.isMdUp };
});
vi.mock('@/hooks/useIsMdUp', () => ({
  useIsMdUp: () => mediaQueryState.isMdUp,
}));

function makeTestCredentials(): AuthCredentials {
  return {
    accessToken: 'test-access-token',
    refreshToken: 'test-refresh-token',
    tokenType: 'bearer',
    expiresIn: 3600,
    sessionId: 'sess-1',
    isNew: false,
    user: {
      id: 'u1',
      email: 't@example.com',
      firstName: 'T',
      lastName: 'User',
      emailVerified: true,
      createdAt: '',
      updatedAt: '',
    },
  };
}

function TestWrapper({
  children,
  initialPath = '/',
}: {
  children: ReactNode;
  initialPath?: string;
}) {
  return (
    <Provider store={store}>
      <MemoryRouter initialEntries={[initialPath]}>
        <MantineProvider theme={mantineTheme}>{children}</MantineProvider>
      </MemoryRouter>
    </Provider>
  );
}

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    _id: 'msg-1',
    content: { messages: [{ text: "Here's your 3-day trip to Barcelona!" }] },
    from: 'bot',
    type: 'itinerary_results',
    contentType: 'message',
    timestamp: new Date().toISOString(),
    extraData: { destination: 'Barcelona', session_id: 's1' },
    ...overrides,
  };
}

describe('ItineraryResultMessage', () => {
  beforeEach(() => {
    mediaQueryState.isMdUp = true;
    mockNavigate.mockClear();
    store.dispatch(clearAuth());
    store.dispatch(closeAuthModal());
  });

  it('renders message text and View itinerary button', () => {
    const msg = makeMessage();
    render(
      <TestWrapper>
        <ItineraryResultMessage message={msg} />
      </TestWrapper>
    );
    expect(screen.getByText("Here's your 3-day trip to Barcelona!")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /view itinerary/i })).toBeInTheDocument();
  });

  describe('when guest', () => {
    it('navigates to public itinerary route when View itinerary is clicked', async () => {
      const msg = makeMessage({ extraData: { session_id: 's1' } });
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view itinerary/i }));
      expect(store.getState().ui.authModalOpen).toBe(false);
      expect(mockNavigate).toHaveBeenCalled();
      const [path] = mockNavigate.mock.calls[0]!;
      expect(path).toBe('/public/chat/itinerary');
    });
  });

  describe('when authenticated', () => {
    beforeEach(() => {
      store.dispatch(setCredentials(makeTestCredentials()));
    });

    it('navigates to /itinerary when View itinerary is clicked (no destination)', async () => {
      const msg = makeMessage({ extraData: { session_id: 's1' } });
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view itinerary/i }));
      const chatId = store.getState().chat.chatId ?? '__anon__';
      expect(store.getState().ui.itineraryStateByChatId[chatId]?.lastItineraryPath).toBe('/itinerary');
      expect(store.getState().ui.itineraryStateByChatId[chatId]?.lastItineraryState).toEqual({
        structuredItinerary: {},
        tripMeta: {
          origin: undefined,
          destination: undefined,
          departure_date: undefined,
          return_date: undefined,
          adults: undefined,
          children: undefined,
          infants: undefined,
          trip_type: undefined,
        },
      });
      expect(mockNavigate).toHaveBeenCalledWith('/itinerary', {
        state: {
          structuredItinerary: {},
          tripMeta: {
            origin: undefined,
            destination: undefined,
            departure_date: undefined,
            return_date: undefined,
            adults: undefined,
            children: undefined,
            infants: undefined,
            trip_type: undefined,
          },
        },
      });
    });

    it('navigates to /itinerary?destination=X with itinerary data in state when destination in extraData', async () => {
      const msg = makeMessage({ extraData: { destination: 'Paris', session_id: 's2' } });
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view itinerary/i }));
      const chatId = store.getState().chat.chatId ?? '__anon__';
      expect(store.getState().ui.itineraryStateByChatId[chatId]?.lastItineraryPath).toBe('/itinerary?destination=Paris');
      expect(store.getState().ui.itineraryStateByChatId[chatId]?.lastItineraryState).toEqual({
        structuredItinerary: {},
        tripMeta: {
          origin: undefined,
          destination: 'Paris',
          departure_date: undefined,
          return_date: undefined,
          adults: undefined,
          children: undefined,
          infants: undefined,
          trip_type: undefined,
        },
      });
      expect(mockNavigate).toHaveBeenCalledWith('/itinerary?destination=Paris', {
        state: {
          structuredItinerary: {},
          tripMeta: {
            origin: undefined,
            destination: 'Paris',
            departure_date: undefined,
            return_date: undefined,
            adults: undefined,
            children: undefined,
            infants: undefined,
            trip_type: undefined,
          },
        },
      });
    });

    it('navigates to /itinerary/:id when saved_itinerary_id is present', async () => {
      const msg = makeMessage({
        extraData: {
          saved_itinerary_id: 'abc123',
          destination: 'Barcelona',
          session_id: 's1',
        },
      });
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view itinerary/i }));
      const chatId1 = store.getState().chat.chatId ?? '__anon__';
      expect(store.getState().ui.itineraryStateByChatId[chatId1]?.lastItineraryPath).toBe('/itinerary/abc123');
      expect(mockNavigate).toHaveBeenCalledWith('/itinerary/abc123', {
        state: {
          structuredItinerary: {},
          savedItineraryId: 'abc123',
          tripMeta: {
            origin: undefined,
            destination: 'Barcelona',
            departure_date: undefined,
            return_date: undefined,
            adults: undefined,
            children: undefined,
            infants: undefined,
            trip_type: undefined,
            destination_location: undefined,
          },
        },
      });
    });

    it('passes structured_itinerary in state when present in extraData', async () => {
      const itinerary = { itineraryItems: [{ day: 1, title: 'Day 1' }] };
      const msg = makeMessage({
        extraData: {
          structured_itinerary: itinerary,
          destination: 'Paris',
          departure_date: '2026-03-20',
          return_date: '2026-03-30',
        },
      });
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view itinerary/i }));
      const chatId2 = store.getState().chat.chatId ?? '__anon__';
      expect(store.getState().ui.itineraryStateByChatId[chatId2]?.lastItineraryState?.structuredItinerary).toEqual(itinerary);
      expect(mockNavigate).toHaveBeenCalledWith('/itinerary?destination=Paris', {
        state: {
          structuredItinerary: itinerary,
          tripMeta: {
            origin: undefined,
            destination: 'Paris',
            departure_date: '2026-03-20',
            return_date: '2026-03-30',
            adults: undefined,
            children: undefined,
            infants: undefined,
            trip_type: undefined,
          },
        },
      });
    });

    it('navigates to /itinerary/:id when saved_itinerary_id is present (minimal extraData)', async () => {
      const msg = makeMessage({
        extraData: {
          saved_itinerary_id: 'abc123',
          session_id: 's3',
        },
      });
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view itinerary/i }));
      const chatId3 = store.getState().chat.chatId ?? '__anon__';
      expect(store.getState().ui.itineraryStateByChatId[chatId3]?.lastItineraryPath).toBe('/itinerary/abc123');
      expect(mockNavigate).toHaveBeenCalledWith('/itinerary/abc123', {
        state: {
          structuredItinerary: {},
          savedItineraryId: 'abc123',
          tripMeta: {
            origin: undefined,
            destination: undefined,
            departure_date: undefined,
            return_date: undefined,
            adults: undefined,
            children: undefined,
            infants: undefined,
            trip_type: undefined,
            destination_location: undefined,
          },
        },
      });
    });

    it('passes destination_location in tripMeta when present and valid in extraData', async () => {
      const msg = makeMessage({
        extraData: {
          destination: 'Paris',
          session_id: 's3',
          destination_location: { latitude: 48.8566, longitude: 2.3522 },
        },
      });
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view itinerary/i }));
      const chatId4 = store.getState().chat.chatId ?? '__anon__';
      expect(store.getState().ui.itineraryStateByChatId[chatId4]?.lastItineraryState?.tripMeta?.destination_location).toEqual({
        latitude: 48.8566,
        longitude: 2.3522,
      });
      expect(mockNavigate).toHaveBeenCalledWith(
        '/itinerary?destination=Paris',
        expect.objectContaining({
          state: expect.objectContaining({
            tripMeta: expect.objectContaining({
              destination_location: { latitude: 48.8566, longitude: 2.3522 },
            }),
          }),
        })
      );
    });
  });

  describe('Save itinerary CTA (public chat)', () => {
    beforeEach(() => {
      vi.mocked(trackEvent).mockClear();
    });

    it('renders Save itinerary for guests on /public/chat/itinerary', () => {
      const msg = makeMessage();
      render(
        <TestWrapper initialPath="/public/chat/itinerary">
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      expect(screen.getByRole('button', { name: /save itinerary/i })).toBeInTheDocument();
    });

    it('does not render Save itinerary on non-public routes (guest)', () => {
      const msg = makeMessage();
      render(
        <TestWrapper initialPath="/chat">
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      expect(screen.queryByRole('button', { name: /save itinerary/i })).not.toBeInTheDocument();
    });

    it('does not render Save itinerary when authenticated, even on /public/chat', () => {
      store.dispatch(setCredentials(makeTestCredentials()));
      const msg = makeMessage();
      render(
        <TestWrapper initialPath="/public/chat/itinerary">
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      expect(screen.queryByRole('button', { name: /save itinerary/i })).not.toBeInTheDocument();
    });

    it('opens auth modal and tracks analytics on click', async () => {
      const msg = makeMessage({
        extraData: { destination: 'Barcelona', session_id: 's1' },
      });
      const user = userEvent.setup();
      render(
        <TestWrapper initialPath="/public/chat/itinerary">
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );

      await user.click(screen.getByRole('button', { name: /save itinerary/i }));

      expect(store.getState().ui.authModalOpen).toBe(true);
      expect(trackEvent).toHaveBeenCalledWith('chat_save_itinerary_clicked', {
        source: 'public_chat',
        session_id: 's1',
        destination: 'Barcelona',
      });
    });
  });

  it('uses default message when content.messages is empty', () => {
    const msg = makeMessage({ content: { messages: [] } });
    render(
      <TestWrapper>
        <ItineraryResultMessage message={msg} />
      </TestWrapper>
    );
    expect(screen.getByText(/here's your itinerary/i)).toBeInTheDocument();
  });

  describe('mobile viewport (below md)', () => {
    beforeEach(() => {
      mediaQueryState.isMdUp = false;
    });

    it('does not render inline day preview even when structured_itinerary is present', () => {
      const itinerary = { itineraryItems: [{ day: 1, title: 'Day 1 — Rome' }] };
      const msg = makeMessage({
        extraData: {
          structured_itinerary: itinerary,
          session_id: 's1',
        },
      });
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      // Mobile now mirrors desktop: message + View itinerary CTA only; no inline day cards.
      expect(screen.queryByText('Day 1 — Rome')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /view itinerary/i })).toBeInTheDocument();
    });

    it('renders message text and View itinerary CTA', () => {
      const msg = makeMessage({
        extraData: { session_id: 's-mobile-plain', destination: 'Barcelona' },
      });
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      expect(screen.getByText("Here's your 3-day trip to Barcelona!")).toBeInTheDocument();
      expect(screen.queryByText(/Day \d+:/)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /view itinerary/i })).toBeInTheDocument();
    });

    it('does not render structured local experiences or trip budget inline', () => {
      const itinerary = {
        itineraryItems: [
          {
            day: 1,
            title: 'Rome',
            description: 'Explore',
            imageUrl: 'https://example.com/day1.jpg',
          },
        ],
        footerSectionTitle: 'Must-Try Local Experiences',
        localExperiences: [
          {
            id: '1',
            imageUrl: 'https://example.com/exp.jpg',
            title: 'Carbonara class',
            description: 'Make pasta with a local chef.',
          },
        ],
        budgetSnapshot: {
          title: 'Trip budget',
          description: 'Expect around $1,500-2,000 USD per person',
        },
      };
      const msg = makeMessage({
        extraData: {
          structured_itinerary: itinerary,
          session_id: 's1',
        },
      });
      render(
        <TestWrapper>
          <ItineraryResultMessage message={msg} />
        </TestWrapper>
      );
      expect(screen.queryByText('Must-Try Local Experiences')).not.toBeInTheDocument();
      expect(screen.queryByText('Carbonara class')).not.toBeInTheDocument();
      expect(screen.queryByText('Trip budget')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /view itinerary/i })).toBeInTheDocument();
    });
  });
});
