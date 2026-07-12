import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import authReducer from '@/store/slices/authSlice';
import type { InspirationRailsData } from '@/api/strapi/mapInspirationRails';
import type { DetectedLocation } from '@/types/onboarding';
import { LandingPageSections } from './LandingPageSections';
import { LANDING_PAGE_IDS } from './landingPageIds';

interface DetectQueryResult {
  data: DetectedLocation | undefined;
  isLoading: boolean;
  isError: boolean;
}

const mockUseGetLandingPageQuery = vi.hoisted(() => vi.fn(() => ({ data: undefined })));
const mockUseDetectLocationQuery = vi.hoisted(() =>
  vi.fn<() => DetectQueryResult>(() => ({ data: undefined, isLoading: false, isError: false })),
);

vi.mock('@/api/strapiApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/strapiApi')>();
  return {
    ...actual,
    useGetLandingPageQuery: mockUseGetLandingPageQuery,
  };
});

vi.mock('@/api/locationApi', () => ({
  useDetectLocationQuery: mockUseDetectLocationQuery,
}));

vi.mock('./components/HomeHero', () => ({ HomeHero: () => null }));
vi.mock('./components/HomeSignInCard', () => ({ HomeSignInCard: () => null }));
vi.mock('./components/TripsRail', () => ({
  TripsRail: ({ title, subtitle }: { title: string; subtitle: string }) => (
    <div data-testid="trips-rail">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  ),
}));
vi.mock('./components/EditorialCard', () => ({ EditorialCard: () => null }));

function buildStore() {
  // Hooks are mocked, so the rendered tree never dispatches real actions —
  // a minimal store with just the auth slice is enough to satisfy <Provider>.
  return configureStore({ reducer: { auth: authReducer } });
}

function renderSections(props: Partial<Parameters<typeof LandingPageSections>[0]> = {}) {
  return render(
    <Provider store={buildStore()}>
      <MantineProvider theme={mantineTheme}>
        <LandingPageSections onSearchSubmit={vi.fn()} onCtaClick={vi.fn()} {...props} />
      </MantineProvider>
    </Provider>,
  );
}

const stubRails: InspirationRailsData = {};

describe('LandingPageSections — default query skip behaviour', () => {
  beforeEach(() => {
    mockUseGetLandingPageQuery.mockClear();
    mockUseDetectLocationQuery.mockReturnValue({ data: undefined, isLoading: false, isError: false });
  });

  it('fires the default getLandingPage query when strapiData is absent', () => {
    renderSections();
    expect(mockUseGetLandingPageQuery).toHaveBeenCalledWith(
      undefined,
      expect.objectContaining({ skip: false }),
    );
  });

  it('skips the default getLandingPage query when strapiData prop is present', () => {
    renderSections({ strapiData: stubRails });
    expect(mockUseGetLandingPageQuery).toHaveBeenCalledWith(
      undefined,
      expect.objectContaining({ skip: true }),
    );
  });
});

describe('LandingPageSections — closing chat section', () => {
  beforeEach(() => {
    mockUseGetLandingPageQuery.mockClear();
  });

  it('renders the closing chat input + send button with the registered landing ids', () => {
    renderSections({ ids: LANDING_PAGE_IDS });

    expect(screen.getByRole('heading', { name: /ready when you are/i })).toHaveAttribute(
      'id',
      LANDING_PAGE_IDS.closingChat.heading,
    );
    expect(screen.getByRole('textbox', { name: /chat with voya ai/i })).toHaveAttribute(
      'id',
      LANDING_PAGE_IDS.closingChat.input,
    );
    expect(screen.getByRole('button', { name: /send to voya ai/i })).toHaveAttribute(
      'id',
      LANDING_PAGE_IDS.closingChat.sendButton,
    );
  });

  it('forwards the closing-chat submit to the shared onSearchSubmit handler', async () => {
    const user = userEvent.setup();
    const onSearchSubmit = vi.fn();
    renderSections({ onSearchSubmit, ids: LANDING_PAGE_IDS });

    const input = screen.getByRole('textbox', { name: /chat with voya ai/i });
    await user.type(input, 'Weekend in Porto');
    await user.click(screen.getByRole('button', { name: /send to voya ai/i }));

    expect(onSearchSubmit).toHaveBeenCalledTimes(1);
    expect(onSearchSubmit).toHaveBeenCalledWith('Weekend in Porto');
  });
});

describe('LandingPageSections — from-city rail reflects detected location', () => {
  beforeEach(() => {
    mockUseGetLandingPageQuery.mockReturnValue({ data: undefined });
  });

  it('uses detected city in the from-city rail when detection succeeds', () => {
    mockUseDetectLocationQuery.mockReturnValue({
      data: {
        city: 'Berlin',
        country: 'Germany',
        countryCode: 'DE',
        iata: '',
        currency: 'EUR',
        currencySymbol: '€',
      },
      isLoading: false,
      isError: false,
    });

    renderSections();
    expect(screen.getByText('From Berlin')).toBeInTheDocument();
    expect(screen.getByText(/detected automatically/)).toHaveTextContent('Berlin');
  });

  it('shows a neutral title and honest subtitle when detection fails', () => {
    mockUseDetectLocationQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    renderSections();
    expect(screen.getByText('Inspiration trips')).toBeInTheDocument();
    expect(screen.queryByText(/detected automatically/)).not.toBeInTheDocument();
    expect(screen.getByText('Curated trips from popular hubs')).toBeInTheDocument();
  });

  it('lets a Strapi-provided title override detection', () => {
    mockUseDetectLocationQuery.mockReturnValue({
      data: {
        city: 'Berlin',
        country: 'Germany',
        countryCode: 'DE',
        iata: '',
        currency: 'EUR',
        currencySymbol: '€',
      },
      isLoading: false,
      isError: false,
    });

    renderSections({
      strapiData: {
        fromCityRail: {
          title: 'Curator picks',
          subtitle: 'Hand-picked by our travel team',
          trips: [],
        },
      },
    });
    expect(screen.getByText('Curator picks')).toBeInTheDocument();
    expect(screen.getByText('Hand-picked by our travel team')).toBeInTheDocument();
  });
});
