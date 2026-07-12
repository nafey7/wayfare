import { describe, it, expect, vi, afterEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import { baseApi } from './baseApi';
import { locationApi } from './locationApi';
import authReducer from '@/store/slices/authSlice';

function makeStore() {
  return configureStore({
    reducer: { auth: authReducer, [baseApi.reducerPath]: baseApi.reducer },
    middleware: (gdm) => gdm().concat(baseApi.middleware),
  });
}

const originalFetch = global.fetch;

function mockFetch(impl: typeof fetch) {
  global.fetch = vi.fn(impl) as typeof fetch;
}

describe('locationApi.detectLocation', () => {
  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('returns a DetectedLocation when ipapi responds successfully', async () => {
    mockFetch(async () =>
      new Response(
        JSON.stringify({
          city: 'Berlin',
          country_name: 'Germany',
          country_code: 'DE',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    const store = makeStore();
    const result = await store.dispatch(locationApi.endpoints.detectLocation.initiate());

    expect(result.data).toEqual({
      city: 'Berlin',
      country: 'Germany',
      countryCode: 'DE',
      iata: '',
      currency: 'EUR',
      currencySymbol: '€',
    });
  });

  it('returns an error when ipapi reports failure', async () => {
    mockFetch(async () =>
      new Response(JSON.stringify({ error: true, reason: 'rate-limited' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const store = makeStore();
    const result = await store.dispatch(locationApi.endpoints.detectLocation.initiate());

    expect(result.data).toBeUndefined();
    expect(result.error).toBeDefined();
  });

  it('returns an error when the network call throws', async () => {
    mockFetch(async () => {
      throw new Error('network down');
    });

    const store = makeStore();
    const result = await store.dispatch(locationApi.endpoints.detectLocation.initiate());

    expect(result.data).toBeUndefined();
    expect(result.error).toBeDefined();
  });

  it('returns an error when the payload is missing required fields', async () => {
    mockFetch(async () =>
      new Response(JSON.stringify({ city: '', country_code: '' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const store = makeStore();
    const result = await store.dispatch(locationApi.endpoints.detectLocation.initiate());

    expect(result.data).toBeUndefined();
    expect(result.error).toBeDefined();
  });
});
