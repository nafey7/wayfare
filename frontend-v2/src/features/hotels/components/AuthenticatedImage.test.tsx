import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthenticatedImage } from './AuthenticatedImage';
import { useAppSelector } from '@/store';
import type { RootState } from '@/store';

vi.mock('@/store', () => ({
  useAppSelector: vi.fn(),
}));

function mockAuthToken(token: string | null) {
  vi.mocked(useAppSelector).mockImplementation((selector) =>
    selector({ auth: { token } } as unknown as RootState),
  );
}

describe('AuthenticatedImage', () => {
  beforeEach(() => {
    mockAuthToken('test-jwt');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows fallback when there is no token', async () => {
    mockAuthToken(null);
    render(
      <AuthenticatedImage url="/api/places/x" alt="x" fallbackSrc="data:image/svg+xml,<svg/>" />,
    );
    await waitFor(() => {
      const img = screen.getByRole('img', { name: 'x' });
      expect(img).toHaveAttribute('src', 'data:image/svg+xml,<svg/>');
    });
  });

  it('fetches with Authorization and renders blob URL', async () => {
    const blob = new Blob(['x'], { type: 'image/png' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(blob),
    });
    vi.stubGlobal('fetch', fetchMock);
    const createUrl = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock');
    const revokeUrl = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    render(
      <AuthenticatedImage url="/api/places/photo" alt="Hotel" fallbackSrc="data:image/svg+xml,<svg/>" />,
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/places/photo'),
        expect.objectContaining({
          headers: { Authorization: 'Bearer test-jwt' },
        }),
      );
    });
    await waitFor(() => {
      expect(screen.getByRole('img', { name: 'Hotel' })).toHaveAttribute('src', 'blob:mock');
    });

    createUrl.mockRestore();
    revokeUrl.mockRestore();
  });
});
