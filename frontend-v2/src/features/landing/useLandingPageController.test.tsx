import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { openAuthModal } from '@/store/slices/uiSlice';

import type { ItineraryCardItem } from './components/ExampleItinerariesSection';
import { EXAMPLE_ITINERARY_CARD_PROMPTS } from './components/ExampleItinerariesSection';
import { useLandingPageController } from './useLandingPageController';

const mockNavigate = vi.fn();
const mockDispatch = vi.fn();

let mockSearch = '';
let mockPathname = '/';
let mockIsAuthenticated = true;

vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({
      pathname: mockPathname,
      search: mockSearch,
    }),
  };
});

const mockChatConfig = {
  publicChatEnabled: false,
  chatFeedbackEnabled: false,
  langgraphFlightsEnabled: false,
  langgraphHotelsEnabled: false,
  environment: 'test',
};

let mockConfigLoaded = true;

vi.mock('@/store', () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: (selector: (state: unknown) => unknown) =>
    selector({
      auth: { isAuthenticated: mockIsAuthenticated },
      ui: { authModalOpen: false },
      chat: { config: mockChatConfig, configLoaded: mockConfigLoaded },
    }),
}));

const mockStartNewChat = vi.fn();
vi.mock('@/features/chat/hooks/useStartNewChat', () => ({
  useStartNewChat: () => mockStartNewChat,
}));

vi.mock('@/features/chat/hooks/useGuestNewConversationGuard', () => ({
  useGuestNewConversationGuard: () => ({
    requestNewConversation: (action: () => void) => action(),
    dialogProps: { open: false, onClose: vi.fn(), onSaveChat: vi.fn(), onProceed: vi.fn() },
  }),
}));

const sampleItineraryCard: ItineraryCardItem = {
  tagText: 't',
  tripTitle: '7 Days in Tokyo',
  location: 'Japan',
  duration: '7 days',
  priceRange: '$1',
  travelerType: 'Solo',
  inclusions: [],
};

describe('useLandingPageController', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockDispatch.mockClear();
    mockStartNewChat.mockClear();
    mockSearch = '';
    mockPathname = '/';
    mockIsAuthenticated = true;
    mockChatConfig.publicChatEnabled = false;
    mockConfigLoaded = true;
  });

  it('auto-submits from ?prompt= and runs again when the prompt value changes', () => {
    mockSearch = '?prompt=first';
    const { rerender } = renderHook(() => useLandingPageController());
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenLastCalledWith('/chat?prompt=first');
    expect(mockStartNewChat).toHaveBeenCalledTimes(1);

    mockSearch = '?prompt=second';
    rerender();
    expect(mockNavigate).toHaveBeenCalledTimes(2);
    expect(mockNavigate).toHaveBeenLastCalledWith('/chat?prompt=second');
    expect(mockStartNewChat).toHaveBeenCalledTimes(2);
  });

  it('handleSearchSubmit resets chat state via startNewChat before navigating', () => {
    const { result } = renderHook(() => useLandingPageController());
    act(() => {
      result.current.handleSearchSubmit('  plan Paris  ');
    });
    expect(mockStartNewChat).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith('/chat?prompt=plan%20Paris');
    // startNewChat must run before navigate so ChatPanel mounts with a clean slate.
    const resetOrder = mockStartNewChat.mock.invocationCallOrder[0]!;
    const navOrder = mockNavigate.mock.invocationCallOrder[0]!;
    expect(resetOrder).toBeLessThan(navOrder);
  });

  it('handleCardPlanClick resets chat state via startNewChat before navigating', () => {
    const { result } = renderHook(() => useLandingPageController());
    act(() => {
      result.current.handleCardPlanClick(sampleItineraryCard);
    });
    expect(mockStartNewChat).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledTimes(1);
  });

  it('does not call startNewChat when unauthenticated user is sent to auth modal', () => {
    mockIsAuthenticated = false;
    const { result } = renderHook(() => useLandingPageController());
    act(() => {
      result.current.handleSearchSubmit('plan Paris');
    });
    expect(mockStartNewChat).not.toHaveBeenCalled();
    expect(mockDispatch).toHaveBeenCalledWith(openAuthModal());
  });

  it.each([
    ['tokyo', EXAMPLE_ITINERARY_CARD_PROMPTS.tokyo],
    ['phuket', EXAMPLE_ITINERARY_CARD_PROMPTS.phuket],
    ['europe', EXAMPLE_ITINERARY_CARD_PROMPTS.europe],
  ] as const)(
    'handleCardPlanClick navigates to /chat with dedicated %s example prompt',
    (_slug, prompt) => {
      const { result } = renderHook(() => useLandingPageController());
      act(() => {
        result.current.handleCardPlanClick({ ...sampleItineraryCard, examplePrompt: prompt });
      });
      expect(mockNavigate).toHaveBeenCalledWith(`/chat?prompt=${encodeURIComponent(prompt)}`);
    },
  );

  it('handleCardPlanClick falls back to title and location when examplePrompt is absent', () => {
    const { result } = renderHook(() => useLandingPageController());
    act(() => {
      result.current.handleCardPlanClick(sampleItineraryCard);
    });
    expect(mockNavigate).toHaveBeenCalledWith(
      '/chat?prompt=Plan%20a%20trip%20like%3A%207%20Days%20in%20Tokyo%2C%20Japan',
    );
  });

  it('does not duplicate auto-submit for the same prompt search string', () => {
    mockSearch = '?prompt=once';
    const { rerender } = renderHook(() => useLandingPageController());
    expect(mockNavigate).toHaveBeenCalledTimes(1);

    rerender();
    expect(mockNavigate).toHaveBeenCalledTimes(1);
  });

  it('allows auto-submit again after the prompt param is cleared then set', () => {
    mockSearch = '?prompt=a';
    const { rerender } = renderHook(() => useLandingPageController());
    expect(mockNavigate).toHaveBeenCalledTimes(1);

    mockSearch = '';
    rerender();
    mockSearch = '?prompt=a';
    rerender();
    expect(mockNavigate).toHaveBeenCalledTimes(2);
  });

  describe('when unauthenticated', () => {
    beforeEach(() => {
      mockIsAuthenticated = false;
    });

    it('auto-submit from ?prompt= opens auth modal when public chat is off', () => {
      mockSearch = '?prompt=hello%20world';
      renderHook(() => useLandingPageController());
      expect(mockNavigate).not.toHaveBeenCalled();
      expect(mockDispatch).toHaveBeenCalledWith(openAuthModal());
    });

    it('waits for config before handling ?prompt= when public chat resolves after load', () => {
      mockChatConfig.publicChatEnabled = false;
      mockConfigLoaded = false;
      mockSearch = '?prompt=hello%20world';
      const { rerender } = renderHook(() => useLandingPageController());
      expect(mockNavigate).not.toHaveBeenCalled();
      expect(mockDispatch).not.toHaveBeenCalledWith(openAuthModal());

      mockConfigLoaded = true;
      mockChatConfig.publicChatEnabled = true;
      rerender();
      expect(mockNavigate).toHaveBeenCalledWith('/public/chat?prompt=hello%20world', {
        replace: true,
      });
      expect(mockDispatch).not.toHaveBeenCalledWith(openAuthModal());
    });

    it('after ?prompt= with auth modal, switching publicChatEnabled to true redirects to public chat without second auth', () => {
      mockChatConfig.publicChatEnabled = false;
      mockConfigLoaded = true;
      mockSearch = '?prompt=hello%20world';
      const { rerender } = renderHook(() => useLandingPageController());
      expect(mockDispatch).toHaveBeenCalledTimes(1);
      expect(mockDispatch).toHaveBeenCalledWith(openAuthModal());
      expect(mockNavigate).not.toHaveBeenCalled();

      mockChatConfig.publicChatEnabled = true;
      rerender();
      expect(mockNavigate).toHaveBeenCalledWith('/public/chat?prompt=hello%20world', {
        replace: true,
      });
      expect(mockDispatch).toHaveBeenCalledTimes(1);
    });

    it('handleSearchSubmit opens auth modal when public chat is off', () => {
      const { result } = renderHook(() => useLandingPageController());
      act(() => {
        result.current.handleSearchSubmit('  plan Paris  ');
      });
      expect(mockNavigate).not.toHaveBeenCalled();
      expect(mockDispatch).toHaveBeenCalledWith(openAuthModal());
    });

    it('handleCtaClick navigates to onboarding', () => {
      const { result } = renderHook(() => useLandingPageController());
      act(() => {
        result.current.handleCtaClick();
      });
      expect(mockNavigate).toHaveBeenCalledWith('/onboarding');
      expect(mockDispatch).not.toHaveBeenCalledWith(openAuthModal());
    });

    it('handleCardPlanClick opens auth modal only', () => {
      const { result } = renderHook(() => useLandingPageController());
      act(() => {
        result.current.handleCardPlanClick(sampleItineraryCard);
      });
      expect(mockNavigate).not.toHaveBeenCalled();
      expect(mockDispatch).toHaveBeenCalledWith(openAuthModal());
    });

    describe('when public chat is enabled', () => {
      beforeEach(() => {
        mockChatConfig.publicChatEnabled = true;
      });

      it('auto-submit from ?prompt= on landing redirects to public chat with replace', () => {
        mockSearch = '?prompt=hello%20world';
        renderHook(() => useLandingPageController());
        expect(mockNavigate).toHaveBeenCalledWith('/public/chat?prompt=hello%20world', {
          replace: true,
        });
        expect(mockDispatch).not.toHaveBeenCalledWith(openAuthModal());
      });

      it('on non-landing pathname ?prompt= uses handleSearchSubmit (public chat → /public/chat)', () => {
        mockPathname = '/home';
        mockSearch = '?prompt=hello%20world';
        renderHook(() => useLandingPageController());
        expect(mockNavigate).toHaveBeenCalledWith('/public/chat?prompt=hello%20world');
      });

      it('handleSearchSubmit navigates to /public/chat with prompt', () => {
        const { result } = renderHook(() => useLandingPageController());
        act(() => {
          result.current.handleSearchSubmit('  plan Paris  ');
        });
        expect(mockNavigate).toHaveBeenCalledWith('/public/chat?prompt=plan%20Paris');
        expect(mockDispatch).not.toHaveBeenCalledWith(openAuthModal());
      });

      it('handleCardPlanClick navigates to /public/chat?prompt= with fallback itinerary prompt', () => {
        const { result } = renderHook(() => useLandingPageController());
        act(() => {
          result.current.handleCardPlanClick(sampleItineraryCard);
        });
        expect(mockNavigate).toHaveBeenCalledWith(
          '/public/chat?prompt=Plan%20a%20trip%20like%3A%207%20Days%20in%20Tokyo%2C%20Japan',
        );
      });

      it('handleCtaClick navigates to onboarding (regardless of public chat state)', () => {
        const { result } = renderHook(() => useLandingPageController());
        act(() => {
          result.current.handleCtaClick();
        });
        expect(mockNavigate).toHaveBeenCalledWith('/onboarding');
      });

      it('handleCardPlanClick uses examplePrompt for public chat when set', () => {
        const { result } = renderHook(() => useLandingPageController());
        const prompt = EXAMPLE_ITINERARY_CARD_PROMPTS.phuket;
        act(() => {
          result.current.handleCardPlanClick({
            ...sampleItineraryCard,
            examplePrompt: prompt,
          });
        });
        expect(mockNavigate).toHaveBeenCalledWith(
          `/public/chat?prompt=${encodeURIComponent(prompt)}`,
        );
      });

    });
  });
});
