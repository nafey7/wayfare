import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';

const mockScrollTo = vi.fn();
const mockPathname = vi.fn(() => '/');
const mockDispatch = vi.fn();

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: mockPathname(), search: '', state: null }),
  Outlet: () => null,
}));

vi.mock('@/store', () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: () => null,
}));

vi.mock('@/store/slices/uiSlice', () => ({
  setLastFlightPath: vi.fn((v) => ({ type: 'ui/setLastFlightPath', payload: v })),
  setLastHotelPath: vi.fn((v) => ({ type: 'ui/setLastHotelPath', payload: v })),
  setLastItineraryPath: vi.fn((v) => ({ type: 'ui/setLastItineraryPath', payload: v })),
  setLastItineraryState: vi.fn((v) => ({ type: 'ui/setLastItineraryState', payload: v })),
  selectLastFlightPath: vi.fn(),
  selectLastHotelPath: vi.fn(),
  selectLastItineraryPath: vi.fn(),
}));

vi.mock('@/store/slices/chatSlice', () => ({
  selectChatId: vi.fn(),
}));

vi.mock('@/features/itinerary/utils/navigationState', () => ({
  parseItineraryNavigationState: () => null,
}));

vi.mock('@/features/routing', () => ({
  getContentDomain: () => '',
}));

vi.mock('./layoutConstants', () => ({
  LAYOUT: { CONTENT_FLEX: 1 },
}));

import { ContentPanel } from './ContentPanel';

function renderPanel() {
  return render(
    <MantineProvider>
      <ContentPanel />
    </MantineProvider>
  );
}

describe('ContentPanel scroll behaviour', () => {
  beforeEach(() => {
    mockScrollTo.mockClear();
    mockDispatch.mockClear();
    mockPathname.mockReturnValue('/');
    HTMLElement.prototype.scrollTo = mockScrollTo;
  });

  it('scrolls inner container to top on mount', () => {
    renderPanel();
    expect(mockScrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'instant' });
  });

  it('scrolls again when pathname changes', () => {
    const { rerender } = renderPanel();
    expect(mockScrollTo).toHaveBeenCalledTimes(1);

    mockPathname.mockReturnValue('/flights/search');
    rerender(
      <MantineProvider>
        <ContentPanel />
      </MantineProvider>
    );
    expect(mockScrollTo).toHaveBeenCalledTimes(2);
  });

  it('scrolls on back navigation (POP) when pathname changes', () => {
    const { rerender } = renderPanel();
    expect(mockScrollTo).toHaveBeenCalledTimes(1);

    mockPathname.mockReturnValue('/flights/search');
    rerender(
      <MantineProvider>
        <ContentPanel />
      </MantineProvider>
    );
    expect(mockScrollTo).toHaveBeenCalledTimes(2);
  });
});
