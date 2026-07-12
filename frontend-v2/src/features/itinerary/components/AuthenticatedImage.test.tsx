import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MantineProvider } from '@mantine/core';
import { store } from '@/store';
import { clearAuth, setTokens } from '@/store/slices/authSlice';
import { clearPlacesSessionToken } from '@/store/slices/uiSlice';
import { AuthenticatedImage } from './AuthenticatedImage';

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <MantineProvider env="test">
      <Provider store={store}>{ui}</Provider>
    </MantineProvider>,
  );
}

describe('AuthenticatedImage', () => {
  const createObjectURLMock = vi.fn(() => 'blob:protected-image');
  const revokeObjectURLMock = vi.fn();

  /** Fetch + optional RTK refresh schedule updates outside RTL's act(); React still logs. */
  const origConsoleError = console.error.bind(console);

  beforeEach(() => {
    store.dispatch(clearAuth());
    store.dispatch(clearPlacesSessionToken());
    vi.restoreAllMocks();
    vi.spyOn(console, 'error').mockImplementation((...args) => {
      const joined = args.map(String).join(' ');
      if (joined.includes('not wrapped in act') && joined.includes('AuthenticatedImage')) {
        return;
      }
      origConsoleError(...args);
    });
    global.fetch = vi.fn();
    URL.createObjectURL = createObjectURLMock;
    URL.revokeObjectURL = revokeObjectURLMock;
    createObjectURLMock.mockClear();
    revokeObjectURLMock.mockClear();
  });

  afterEach(() => {
    store.dispatch(clearAuth());
    store.dispatch(clearPlacesSessionToken());
  });

  it('fetches a protected image with the auth header and renders the blob URL', async () => {
    store.dispatch(
      setTokens({
        accessToken: 'jwt-token',
        refreshToken: 'refresh-token',
      })
    );

    const blob = new Blob(['image-bytes'], { type: 'image/jpeg' });
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(blob, {
        status: 200,
        headers: { 'Content-Type': 'image/jpeg' },
      })
    );

    const { unmount } = renderWithProviders(<AuthenticatedImage src="/api/places/photos/example/media" alt="Protected" />);

    await waitFor(() =>
      expect(screen.getByRole('img', { name: 'Protected' })).toHaveAttribute(
        'src',
        'blob:protected-image'
      )
    );

    expect(global.fetch).toHaveBeenCalledWith('/api/places/photos/example/media', {
      headers: {
        Authorization: 'Bearer jwt-token',
      },
      signal: expect.any(AbortSignal),
      cache: 'default',
    });
    expect(createObjectURLMock).toHaveBeenCalledTimes(1);

    unmount();

    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:protected-image');
  });

  it('renders the fallback and skips fetch when there is no auth token', () => {
    renderWithProviders(
      <AuthenticatedImage
        src="/api/places/photos/example/media"
        alt="Protected"
        fallback={<span>fallback image</span>}
      />
    );

    expect(screen.getByText('fallback image')).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('renders fallback when the image request fails', async () => {
    store.dispatch(
      setTokens({
        accessToken: 'jwt-token',
        refreshToken: 'refresh-token',
      })
    );

    vi.mocked(global.fetch).mockResolvedValue(new Response(null, { status: 500 }));

    renderWithProviders(
      <AuthenticatedImage
        src="/api/places/photos/example/media"
        alt="Protected"
        fallback={<span>load failed</span>}
      />
    );

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(await screen.findByText('load failed')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'Protected' })).not.toBeInTheDocument();
  });

  it('refreshes the session on 401 and loads the image on retry', async () => {
    store.dispatch(
      setTokens({
        accessToken: 'expired-token',
        refreshToken: 'refresh-token',
      })
    );

    const blob = new Blob(['image-bytes'], { type: 'image/jpeg' });
    let imageCalls = 0;
    vi.mocked(global.fetch).mockImplementation((input) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.includes('/auth/refresh')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: 'jwt-new',
              refresh_token: 'refresh-new',
              token_type: 'bearer',
              expires_in: 3600,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } }
          )
        );
      }
      imageCalls += 1;
      if (imageCalls === 1) {
        return Promise.resolve(new Response(null, { status: 401 }));
      }
      return Promise.resolve(
        new Response(blob, {
          status: 200,
          headers: { 'Content-Type': 'image/jpeg' },
        })
      );
    });

    renderWithProviders(<AuthenticatedImage src="/api/places/photos/example/media" alt="Protected" />);

    await waitFor(() =>
      expect(screen.getByRole('img', { name: 'Protected' })).toHaveAttribute(
        'src',
        'blob:protected-image'
      )
    );

    expect(imageCalls).toBe(2);
    expect(createObjectURLMock).toHaveBeenCalledTimes(1);
  });
});
