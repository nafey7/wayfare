import { baseApi } from './baseApi';
import type {
  AuthCredentials,
  AuthResponseApi,
  LoginRequest,
  RegisterRequest,
  CompleteRegistrationRequest,
  GoogleAuthRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  CheckEmailResponse,
  TokenResponse,
  TokenResponseApi,
  GoogleConfig,
  GoogleConfigResponseApi,
  RefreshTokenRequest,
} from '@/types/auth';
import {
  transformAuthResponse,
  transformTokenResponse,
  transformGoogleConfig,
} from '@/types/auth';
import type { SuccessResponse } from '@/types/api';

export const authApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Check if email exists in system
     */
    checkEmail: builder.mutation<CheckEmailResponse, { email: string }>({
      query: (body) => ({
        url: '/auth/check-email',
        method: 'POST',
        body,
      }),
    }),

    /**
     * Register new user with email
     */
    register: builder.mutation<SuccessResponse, RegisterRequest>({
      query: (body) => ({
        url: '/auth/register',
        method: 'POST',
        body,
      }),
    }),

    /**
     * Complete registration by setting password
     */
    completeRegistration: builder.mutation<AuthCredentials, CompleteRegistrationRequest>({
      query: (body) => ({
        url: '/auth/complete-registration',
        method: 'POST',
        body,
      }),
      transformResponse: (response: AuthResponseApi) => transformAuthResponse(response),
    }),

    /**
     * Login with email and password
     */
    login: builder.mutation<AuthCredentials, LoginRequest>({
      query: (body) => ({
        url: '/auth/login',
        method: 'POST',
        body,
      }),
      transformResponse: (response: AuthResponseApi) => transformAuthResponse(response),
    }),

    /**
     * Login with Google OAuth
     */
    googleAuth: builder.mutation<AuthCredentials, GoogleAuthRequest>({
      query: (body) => ({
        url: '/auth/google/authenticate',
        method: 'POST',
        body,
      }),
      transformResponse: (response: AuthResponseApi) => transformAuthResponse(response),
    }),

    /**
     * Request password reset email
     */
    forgotPassword: builder.mutation<SuccessResponse, ForgotPasswordRequest>({
      query: (body) => ({
        url: '/auth/forgot-password',
        method: 'POST',
        body,
      }),
    }),

    /**
     * Validate password reset token
     */
    validateResetToken: builder.mutation<SuccessResponse, { token: string }>({
      query: (body) => ({
        url: '/auth/validate-reset-token',
        method: 'POST',
        body,
      }),
    }),

    /**
     * Validate registration token (from email verification link)
     */
    validateRegistrationToken: builder.mutation<SuccessResponse, { token: string }>({
      query: (body) => ({
        url: '/auth/validate-registration-token',
        method: 'POST',
        body,
      }),
    }),

    /**
     * Reset password with token
     */
    resetPassword: builder.mutation<SuccessResponse, ResetPasswordRequest>({
      query: (body) => ({
        url: '/auth/reset-password',
        method: 'POST',
        body,
      }),
    }),

    /**
     * Refresh access token
     */
    refreshToken: builder.mutation<TokenResponse, RefreshTokenRequest>({
      query: (body) => ({
        url: '/auth/refresh',
        method: 'POST',
        body,
      }),
      transformResponse: (response: TokenResponseApi) => transformTokenResponse(response),
    }),

    /**
     * Logout current session
     */
    logout: builder.mutation<SuccessResponse, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
    }),

    /**
     * Get Google OAuth config
     */
    getGoogleConfig: builder.query<GoogleConfig, void>({
      query: () => '/auth/config/google',
      transformResponse: (response: GoogleConfigResponseApi) => transformGoogleConfig(response),
    }),
  }),
});

export const {
  useCheckEmailMutation,
  useRegisterMutation,
  useCompleteRegistrationMutation,
  useLoginMutation,
  useGoogleAuthMutation,
  useForgotPasswordMutation,
  useValidateResetTokenMutation,
  useValidateRegistrationTokenMutation,
  useResetPasswordMutation,
  useRefreshTokenMutation,
  useLogoutMutation,
  useGetGoogleConfigQuery,
} = authApi;
