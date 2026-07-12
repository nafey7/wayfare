import type { ReactElement } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { useAppSelector } from '@/store';
import type { RootState } from '@/store';
import { ImageGallery } from './ImageGallery';

const triggerSearchPlaceMock = vi.fn();

vi.mock('@/api/placesApi', async () => {
  const actual =
    await vi.importActual<typeof import('@/api/placesApi')>('@/api/placesApi');
  return {
    ...actual,
    useLazySearchPlaceQuery: () => [triggerSearchPlaceMock],
  };
});

vi.mock('@/store', () => ({
  useAppSelector: vi.fn(),
}));

vi.mock('../AuthenticatedImage', () => ({
  AuthenticatedImage: ({ url, alt }: { url: string; alt: string }) => (
    <img data-testid="places-tile" src={url} alt={alt} />
  ),
}));

function mockAuthToken(token: string | null) {
  vi.mocked(useAppSelector).mockImplementation((selector) =>
    selector({ auth: { token } } as unknown as RootState),
  );
}

function renderWithTheme(ui: ReactElement) {
  return render(
    <MantineProvider theme={mantineTheme} env="test">
      {ui}
    </MantineProvider>,
  );
}

describe('ImageGallery — Places multi-photo flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthToken('jwt');
    triggerSearchPlaceMock.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          places: [
            {
              id: 'p1',
              displayName: 'Grand Hotel',
              photos: [
                { name: 'places/p1/photos/a' },
                { name: 'places/p1/photos/b' },
                { name: 'places/p1/photos/c' },
                { name: 'places/p1/photos/d' },
                { name: 'places/p1/photos/e' },
                { name: 'places/p1/photos/f' },
              ],
            },
          ],
        }),
    });
  });

  it('eagerly fetches Places photos when no primary images are provided', async () => {
    renderWithTheme(
      <ImageGallery images={[]} hotelName="Grand Hotel" city="Paris" />,
    );

    await waitFor(() => {
      expect(triggerSearchPlaceMock).toHaveBeenCalledWith({
        textQuery: 'Grand Hotel, Paris',
        pageSize: 1,
      });
    });

    const tiles = await screen.findAllByTestId('places-tile');
    // Hero + 4 side slots, capped at MAX_TILES (5).
    expect(tiles).toHaveLength(5);
    expect(tiles[0]).toHaveAttribute(
      'src',
      '/api/places/photos/places/p1/photos/a/media?max_width_px=800',
    );
    expect(tiles[4]).toHaveAttribute(
      'src',
      '/api/places/photos/places/p1/photos/e/media?max_width_px=800',
    );
  });

  it('does not call searchPlace when the user has no auth token', () => {
    mockAuthToken(null);
    renderWithTheme(
      <ImageGallery images={[]} hotelName="Grand Hotel" city="Paris" />,
    );

    expect(triggerSearchPlaceMock).not.toHaveBeenCalled();
  });

  it('falls back to address (first segment) when city is missing', async () => {
    renderWithTheme(
      <ImageGallery
        images={[]}
        hotelName="Grand Hotel"
        address="123 Main St, Paris, France"
      />,
    );

    await waitFor(() => {
      expect(triggerSearchPlaceMock).toHaveBeenCalledWith({
        textQuery: 'Grand Hotel, 123 Main St',
        pageSize: 1,
      });
    });
  });
});
