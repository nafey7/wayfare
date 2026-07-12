import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import { encodeStrapi5Populate, strapiApi } from './strapiApi';
import { getStrapiBaseUrl, strapiRequestHeaders } from './strapi/strapiHttp';

// Hoisted — replaces ./strapi/strapiHttp for all consumers including strapiApi.ts
vi.mock('./strapi/strapiHttp', () => ({
  getStrapiBaseUrl: vi.fn(),
  strapiRequestHeaders: vi.fn(() => ({ Accept: 'application/json' })),
  strapiApiUrl: vi.fn(),
}));

function buildStore() {
  return configureStore({
    reducer: { [strapiApi.reducerPath]: strapiApi.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(strapiApi.middleware),
  });
}

describe('encodeStrapi5Populate', () => {
  it('builds indexed populate params from dot paths', () => {
    const qs = encodeStrapi5Populate(['hero', 'hero.avatarImage', 'footer.quickLinks']);
    expect(qs).toBe(
      'populate[0]=hero&populate[1]=hero.avatarImage&populate[2]=footer.quickLinks',
    );
  });

  it('returns empty string for empty array', () => {
    expect(encodeStrapi5Populate([])).toBe('');
  });

  it('preserves dots unencoded (required by Strapi 5 dot-path notation)', () => {
    const qs = encodeStrapi5Populate(['intro.testimonials.userAvatar']);
    expect(qs).toContain('intro.testimonials.userAvatar');
    expect(qs).not.toContain('%2E');
  });

  it('does not produce v4-style bracket chains', () => {
    const qs = encodeStrapi5Populate(['hero', 'hero.avatarImage']);
    expect(qs).not.toContain('[populate]=*');
    expect(qs).not.toContain('[populate][');
  });
});

describe('getLandingPageBySlug', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch');
    vi.mocked(strapiRequestHeaders).mockReturnValue({ Accept: 'application/json' });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty data when Strapi base URL is not configured', async () => {
    vi.mocked(getStrapiBaseUrl).mockReturnValue(undefined);

    const store = buildStore();
    const result = await store.dispatch(strapiApi.endpoints.getLandingPageBySlug.initiate('summer-sale'));

    expect(result.data).toEqual({});
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('returns mapped data on a successful Strapi response', async () => {
    vi.mocked(getStrapiBaseUrl).mockReturnValue('https://cms.example.com');
    fetchSpy.mockResolvedValue(
      new Response(JSON.stringify({ data: [{ id: 1, weekendTrips: [] }] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const store = buildStore();
    const result = await store.dispatch(strapiApi.endpoints.getLandingPageBySlug.initiate('summer-sale'));

    expect(fetchSpy).toHaveBeenCalledOnce();
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain('filters[slug][$eq]=summer-sale');
    expect(calledUrl).toContain('status=published');
    expect(result.data).toBeDefined();
  });

  it('returns null when Strapi returns an empty data array (slug not found)', async () => {
    vi.mocked(getStrapiBaseUrl).mockReturnValue('https://cms.example.com');
    fetchSpy.mockResolvedValue(
      new Response(JSON.stringify({ data: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const store = buildStore();
    const result = await store.dispatch(strapiApi.endpoints.getLandingPageBySlug.initiate('nonexistent-slug'));

    expect(result.data).toBeNull();
  });

  it('returns empty data when Strapi responds with a non-OK status', async () => {
    vi.mocked(getStrapiBaseUrl).mockReturnValue('https://cms.example.com');
    fetchSpy.mockResolvedValue(new Response('Server Error', { status: 500, statusText: 'Internal Server Error' }));

    const store = buildStore();
    const result = await store.dispatch(strapiApi.endpoints.getLandingPageBySlug.initiate('unknown-slug'));

    expect(result.data).toEqual({});
  });

  it('returns empty data when fetch throws a network error', async () => {
    vi.mocked(getStrapiBaseUrl).mockReturnValue('https://cms.example.com');
    fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

    const store = buildStore();
    const result = await store.dispatch(strapiApi.endpoints.getLandingPageBySlug.initiate('any-slug'));

    expect(result.data).toEqual({});
  });

  it('encodes special characters in the slug parameter', async () => {
    vi.mocked(getStrapiBaseUrl).mockReturnValue('https://cms.example.com');
    fetchSpy.mockResolvedValue(
      new Response(JSON.stringify({ data: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const store = buildStore();
    await store.dispatch(
      strapiApi.endpoints.getLandingPageBySlug.initiate('slug with spaces & special=chars'),
    );

    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain('slug%20with%20spaces%20%26%20special%3Dchars');
  });

  it('uses per-slug cache keys so two different slugs are stored independently', async () => {
    vi.mocked(getStrapiBaseUrl).mockReturnValue('https://cms.example.com');
    fetchSpy.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ data: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    const store = buildStore();
    await store.dispatch(strapiApi.endpoints.getLandingPageBySlug.initiate('slug-a'));
    await store.dispatch(strapiApi.endpoints.getLandingPageBySlug.initiate('slug-b'));

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    const state = store.getState();
    const resultA = strapiApi.endpoints.getLandingPageBySlug.select('slug-a')(state);
    const resultB = strapiApi.endpoints.getLandingPageBySlug.select('slug-b')(state);
    expect(resultA.status).toBe('fulfilled');
    expect(resultB.status).toBe('fulfilled');
    expect(resultA.requestId).not.toBe(resultB.requestId);
  });
});
