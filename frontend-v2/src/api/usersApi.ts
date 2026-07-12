import { baseApi } from './baseApi';
import { toCamelCase, toSnakeCase } from '@/utils/transforms';
import type {
  User,
  UserResponseApi,
  SessionResponse,
  SessionResponseApi,
  PhotoUrls,
} from '@/types/auth';
import { transformUser, transformSession } from '@/types/auth';
import type { UserUpdateRequest } from '@/types/user';
import type { SuccessResponse } from '@/types/api';
import type {
  StoredPassenger,
  PassengerCreateRequest,
  PassengerUpdateRequest,
} from '@/types/passengers';
import type {
  ProfileAggregate,
  UserPreferences,
  PreferencesUpdateRequest,
} from '@/types/profile';

export const usersApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Get current user profile
     */
    getMe: builder.query<User, void>({
      query: () => '/user/me',
      providesTags: ['User'],
      transformResponse: (response: UserResponseApi) => transformUser(response),
    }),

    /**
     * Update current user profile
     */
    updateMe: builder.mutation<User, UserUpdateRequest>({
      query: (body) => ({
        url: '/user/me',
        method: 'PUT',
        // Transform camelCase to snake_case for API
        body: {
          first_name: body.firstName,
          last_name: body.lastName,
          mobile: body.mobile,
          profile_image: body.profileImage,
          timezone: body.timezone,
          address: body.address,
          travel_style_description: body.travelStyleDescription,
        },
      }),
      invalidatesTags: ['User', 'Profile'],
      transformResponse: (response: UserResponseApi) => transformUser(response),
    }),

    /**
     * Upload (or replace) the current user's profile photo.
     */
    uploadProfilePhoto: builder.mutation<
      { photoKey: string; photoUrls: PhotoUrls },
      File
    >({
      query: (file) => {
        const form = new FormData();
        form.append('file', file);
        return {
          url: '/user/me/photo',
          method: 'PUT',
          body: form,
        };
      },
      invalidatesTags: ['User', 'Profile'],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as { photoKey: string; photoUrls: PhotoUrls },
    }),

    /**
     * Delete the current user's profile photo. Idempotent (204 even if absent).
     */
    deleteProfilePhoto: builder.mutation<void, void>({
      query: () => ({
        url: '/user/me/photo',
        method: 'DELETE',
      }),
      invalidatesTags: ['User', 'Profile'],
    }),

    /**
     * Change password
     */
    changePassword: builder.mutation<
      SuccessResponse,
      { oldPassword: string; newPassword: string }
    >({
      query: (body) => ({
        url: '/user/me/change-password',
        method: 'POST',
        // Transform to snake_case for API
        body: {
          old_password: body.oldPassword,
          new_password: body.newPassword,
        },
      }),
    }),

    /**
     * Get user sessions
     */
    getSessions: builder.query<SessionResponse[], void>({
      query: () => '/user/me/sessions',
      transformResponse: (response: SessionResponseApi[]) =>
        response.map(transformSession),
    }),

    /**
     * Delete specific session
     */
    deleteSession: builder.mutation<SuccessResponse, string>({
      query: (sessionId) => ({
        url: `/user/me/sessions/${sessionId}`,
        method: 'DELETE',
      }),
    }),

    /**
     * Logout all sessions
     */
    logoutAllSessions: builder.mutation<SuccessResponse, void>({
      query: () => ({
        url: '/user/me/logout-all',
        method: 'POST',
      }),
    }),

    // -------------------------------------------------------------------------
    // Passenger details storage (issue #418)
    // -------------------------------------------------------------------------

    /**
     * List saved passengers for the current user.
     * Sensitive fields (passport, frequent flyer) are masked in response.
     */
    getPassengers: builder.query<StoredPassenger[], void>({
      query: () => '/user/me/passengers',
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({ type: 'Passengers' as const, id })),
              { type: 'Passengers', id: 'LIST' },
            ]
          : [{ type: 'Passengers', id: 'LIST' }],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as StoredPassenger[],
    }),

    /**
     * Get single passenger.
     * When includeSensitive=true for profile passport view, pass piiViewToken from verify.
     */
    getPassenger: builder.query<
      StoredPassenger,
      {
        passengerId: string;
        includeSensitive?: boolean;
        piiViewToken?: string;
      }
    >({
      query: ({ passengerId, includeSensitive, piiViewToken }) => ({
        url: `/user/me/passengers/${passengerId}`,
        params: includeSensitive ? { include_sensitive: 'true' } : undefined,
        headers: piiViewToken
          ? { 'X-PII-View-Token': piiViewToken }
          : undefined,
      }),
      providesTags: (_, __, { passengerId }) => [
        { type: 'Passengers', id: passengerId },
      ],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as StoredPassenger,
    }),

    /**
     * Request PII verification: sends OTP to user email, returns challenge_id.
     */
    requestPiiVerification: builder.mutation<
      { challengeId: string; maskedEmail: string },
      void
    >({
      query: () => ({
        url: '/user/me/pii-verification/request',
        method: 'POST',
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as { challengeId: string; maskedEmail: string },
    }),

    /**
     * Verify PII OTP; returns short-lived pii_view_token for X-PII-View-Token header.
     */
    verifyPiiOtp: builder.mutation<
      { piiViewToken: string; expiresInSeconds: number },
      { challengeId: string; code: string }
    >({
      query: (body) => ({
        url: '/user/me/pii-verification/verify',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      transformResponse: (response: unknown) =>
        toCamelCase(response) as {
          piiViewToken: string;
          expiresInSeconds: number;
        },
    }),

    /**
     * Create a new saved passenger.
     */
    createPassenger: builder.mutation<StoredPassenger, PassengerCreateRequest>({
      query: (body) => ({
        url: '/user/me/passengers',
        method: 'POST',
        body: toSnakeCase(body),
      }),
      invalidatesTags: [
        { type: 'Passengers', id: 'LIST' },
        'Profile',
      ],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as StoredPassenger,
    }),

    /**
     * Update a saved passenger.
     */
    updatePassenger: builder.mutation<
      StoredPassenger,
      { passengerId: string; body: PassengerUpdateRequest }
    >({
      query: ({ passengerId, body }) => ({
        url: `/user/me/passengers/${passengerId}`,
        method: 'PUT',
        body: toSnakeCase(body),
      }),
      invalidatesTags: (_, __, { passengerId }) => [
        { type: 'Passengers', id: passengerId },
        { type: 'Passengers', id: 'LIST' },
        'Profile',
      ],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as StoredPassenger,
    }),

    /**
     * Delete a saved passenger (GDPR right to deletion).
     */
    deletePassenger: builder.mutation<SuccessResponse, string>({
      query: (passengerId) => ({
        url: `/user/me/passengers/${passengerId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_, __, passengerId) => [
        { type: 'Passengers', id: passengerId },
        { type: 'Passengers', id: 'LIST' },
        'Profile',
      ],
    }),

    // -------------------------------------------------------------------------
    // Profile aggregate (user + preferences + passengers)
    // -------------------------------------------------------------------------

    /**
     * Get full profile for profile page: user + preferences + passengers.
     */
    getProfile: builder.query<ProfileAggregate, void>({
      query: () => '/user/me/profile',
      providesTags: ['User', 'Profile'],
      transformResponse: (response: unknown) =>
        toCamelCase(response) as ProfileAggregate,
    }),

    /**
     * Upsert user preferences (partial update supported).
     * Creates document if missing.
     */
    updatePreferences: builder.mutation<UserPreferences, PreferencesUpdateRequest>(
      {
        query: (body) => ({
          url: '/user/me/preferences',
          method: 'PUT',
          body: toSnakeCase(body),
        }),
        invalidatesTags: ['Profile'],
        transformResponse: (response: unknown) =>
          toCamelCase(response) as UserPreferences,
      }
    ),
  }),
});

export const {
  useGetMeQuery,
  useLazyGetMeQuery,
  useUpdateMeMutation,
  useUploadProfilePhotoMutation,
  useDeleteProfilePhotoMutation,
  useChangePasswordMutation,
  useGetSessionsQuery,
  useDeleteSessionMutation,
  useLogoutAllSessionsMutation,
  useGetPassengersQuery,
  useLazyGetPassengersQuery,
  useGetPassengerQuery,
  useLazyGetPassengerQuery,
  useCreatePassengerMutation,
  useUpdatePassengerMutation,
  useDeletePassengerMutation,
  useGetProfileQuery,
  useUpdatePreferencesMutation,
  useRequestPiiVerificationMutation,
  useVerifyPiiOtpMutation,
} = usersApi;
