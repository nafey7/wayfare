import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { mantineTheme } from '@/theme';
import { PublicLandingPage } from './PublicLandingPage';

const mockUseGetLandingPageBySlugQuery = vi.hoisted(() => vi.fn());

vi.mock('@/api/strapiApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/strapiApi')>();
  return {
    ...actual,
    useGetLandingPageBySlugQuery: mockUseGetLandingPageBySlugQuery,
  };
});

vi.mock('@/components/layout/UnifiedHeader', () => ({
  UnifiedHeader: () => <div data-testid="unified-header" />,
}));
vi.mock('@/components/layout/BottomNav', () => ({
  BottomNav: () => <div data-testid="bottom-nav" />,
}));
const mockLandingPageSections = vi.hoisted(() =>
  vi.fn((_props: Record<string, unknown>) => <div data-testid="landing-page-sections" />),
);
vi.mock('./LandingPageSections', () => ({
  LandingPageSections: mockLandingPageSections,
}));
vi.mock('@/features/auth/components/AuthModal', () => ({
  AuthModal: () => null,
}));
vi.mock('./useLandingPageController', () => ({
  useLandingPageController: () => ({
    authModalOpen: false,
    handleSearchSubmit: vi.fn(),
    handleCtaClick: vi.fn(),
    openAuthModal: vi.fn(),
    closeAuthModal: vi.fn(),
  }),
}));
vi.mock('@/hooks', () => ({
  useBottomNavHidden: () => false,
}));
vi.mock('./components/RecentItinerariesStrip', () => ({
  RecentItinerariesStrip: () => null,
}));

function renderAtPath(path: string) {
  return render(
    <MantineProvider theme={mantineTheme}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/l/:slug" element={<PublicLandingPage />} />
          <Route path="/" element={<div data-testid="home-page" />} />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe('PublicLandingPage slug redirect', () => {
  beforeEach(() => {
    mockUseGetLandingPageBySlugQuery.mockReset();
    mockLandingPageSections.mockClear();
  });

  it('redirects to / when Strapi returns null for the slug', () => {
    mockUseGetLandingPageBySlugQuery.mockReturnValue({
      data: null,
      isSuccess: true,
      isLoading: false,
    });

    renderAtPath('/l/nonexistent-campaign');

    expect(screen.getByTestId('home-page')).toBeInTheDocument();
    expect(screen.queryByTestId('landing-page-sections')).not.toBeInTheDocument();
  });

  it('renders landing content when the slug resolves to Strapi data', () => {
    mockUseGetLandingPageBySlugQuery.mockReturnValue({
      data: {},
      isSuccess: true,
      isLoading: false,
    });

    renderAtPath('/l/summer-campaign');

    expect(screen.getByTestId('landing-page-sections')).toBeInTheDocument();
    expect(screen.queryByTestId('home-page')).not.toBeInTheDocument();
  });

  it('does not redirect while the slug query is still loading', () => {
    mockUseGetLandingPageBySlugQuery.mockReturnValue({
      data: undefined,
      isSuccess: false,
      isLoading: true,
    });

    renderAtPath('/l/loading-slug');

    expect(screen.getByTestId('landing-page-sections')).toBeInTheDocument();
    expect(screen.queryByTestId('home-page')).not.toBeInTheDocument();
  });

  it('does not redirect and passes undefined (not null) when query is done but isSuccess is false', () => {
    // Simulates a stale null cached value during a refetch (isSuccess: false, isLoading: false, data: null).
    // The component must not redirect (slugQueryDone is false) and must not leak null into strapiData.
    mockUseGetLandingPageBySlugQuery.mockReturnValue({
      data: null,
      isSuccess: false,
      isLoading: false,
    });

    renderAtPath('/l/stale-slug');

    expect(screen.getByTestId('landing-page-sections')).toBeInTheDocument();
    expect(screen.queryByTestId('home-page')).not.toBeInTheDocument();
    const lastCall = mockLandingPageSections.mock.calls.at(-1)?.[0];
    expect(lastCall?.strapiData).toBeUndefined();
  });
});
