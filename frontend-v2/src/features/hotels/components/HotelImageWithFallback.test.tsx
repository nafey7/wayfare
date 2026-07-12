import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { HotelImageWithFallback } from './HotelImageWithFallback';
import { useAppSelector } from '@/store';
import type { RootState } from '@/store';

const triggerMock = vi.fn();

vi.mock('@/api/placesApi', () => ({
  useLazyGetPlaceImageUrlQuery: () => [triggerMock],
}));

vi.mock('@/store', () => ({
  useAppSelector: vi.fn(),
}));

vi.mock('./AuthenticatedImage', () => ({
  AuthenticatedImage: ({ alt }: { alt: string }) => <img src="places-fallback" alt={alt} />,
}));

function mockAuthToken(token: string | null) {
  vi.mocked(useAppSelector).mockImplementation((selector) =>
    selector({ auth: { token } } as unknown as RootState),
  );
}

describe('HotelImageWithFallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthToken('jwt');
    triggerMock.mockReturnValue({
      unwrap: () => Promise.resolve({ imageUrl: '/api/places/resolved' }),
    });
  });

  it('renders primary image when URL is valid', () => {
    render(
      <HotelImageWithFallback
        primaryUrl="https://example.com/h.jpg"
        hotelName="H"
        fallbackSrc="data:image/svg+xml,<svg/>"
        alt="Hotel"
      />,
    );
    expect(screen.getByRole('img', { name: 'Hotel' })).toHaveAttribute(
      'src',
      'https://example.com/h.jpg',
    );
    expect(triggerMock).not.toHaveBeenCalled();
  });

  it('requests Places fallback when primary is missing', async () => {
    render(
      <HotelImageWithFallback
        primaryUrl={null}
        hotelName="Grand Hotel"
        city="Paris"
        fallbackSrc="data:image/svg+xml,<svg/>"
        alt="Hotel"
      />,
    );

    await waitFor(() => {
      expect(triggerMock).toHaveBeenCalledWith({
        place: 'Grand Hotel, Paris',
        maxWidthPx: 400,
      });
    });
  });
});
