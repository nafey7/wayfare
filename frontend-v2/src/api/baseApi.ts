import {
  createApi,
  fetchBaseQuery,
  type BaseQueryFn,
  type FetchArgs,
  type FetchBaseQueryError,
} from '@reduxjs/toolkit/query/react';
import type { AppDispatch, RootState } from '@/store';
import { clearAuth, setTokens } from '@/store/slices/authSlice';
import type { TokenResponseApi } from '@/types/auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Base query with auth token injection
 */
const rawBaseQuery = fetchBaseQuery({
  baseUrl: API_BASE_URL,
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.token;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    headers.set('Content-Type', 'application/json');
    return headers;
  },
});

/**
 * Mutex to prevent multiple simultaneous refresh attempts
 */
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token
 * Returns true if refresh succeeded, false otherwise
 */
async function performTokenRefresh(
  dispatch: AppDispatch,
  getState: () => RootState
): Promise<boolean> {
  const refreshToken = getState().auth.refreshToken;

  if (!refreshToken) {
    return false;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return false;
    }

    const data: TokenResponseApi = await response.json();
    dispatch(
      setTokens({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      })
    );
    return true;
  } catch {
    return false;
  }
}

/**
 * Mutex-backed refresh shared with {@link baseQueryWithAuth} and non-RTK callers
 * (e.g. authenticated image blob fetch).
 */
export async function runAuthRefresh(
  dispatch: AppDispatch,
  getState: () => RootState
): Promise<boolean> {
  if (!isRefreshing) {
    isRefreshing = true;
    refreshPromise = performTokenRefresh(dispatch, getState);
  }

  const refreshSuccess = await (refreshPromise as Promise<boolean>);
  isRefreshing = false;
  refreshPromise = null;

  return refreshSuccess;
}

/**
 * Custom base query with:
 * - 401 handling with automatic token refresh
 * - Retry original request after successful refresh
 * - Clear auth on refresh failure
 *
 * NOTE: snake_case ↔ camelCase is applied per-endpoint in API slices
 * (flightsApi, paymentsApi, hotelsApi) via transformResponse and toSnakeCase(body).
 */
const baseQueryWithAuth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  // Handle 401 Unauthorized - attempt token refresh
  if (result.error && result.error.status === 401) {
    // Check if this is the refresh endpoint itself (avoid infinite loop)
    const url = typeof args === 'string' ? args : args.url;
    if (url === '/auth/refresh') {
      api.dispatch(clearAuth());
      window.dispatchEvent(new CustomEvent('auth:expired'));
      return result;
    }

    const refreshSuccess = await runAuthRefresh(api.dispatch, api.getState as () => RootState);

    if (refreshSuccess) {
      // Retry the original request with new token
      result = await rawBaseQuery(args, api, extraOptions);
    } else {
      // Refresh failed - clear auth and notify
      api.dispatch(clearAuth());
      window.dispatchEvent(new CustomEvent('auth:expired'));
    }
  }

  return result;
};

/**
 * RTK Query base API
 *
 * All API slices should inject endpoints into this base API.
 * Provides automatic caching, refetching, and cache invalidation.
 */
export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithAuth,
  tagTypes: [
    'User',
    'Profile',
    'Chat',
    'Flights',
    'Hotels',
    'Trips',
    'Bookings',
    'Config',
    'Passengers',
    'SavedItineraries',
    'Conversations',
    'AdminDiscounts',
    'AdminDiscountBatches',
  ],
  endpoints: () => ({}),
});
