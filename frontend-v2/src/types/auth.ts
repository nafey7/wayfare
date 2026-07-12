// ============================================================================
// API Types (snake_case - match backend API exactly)
// ============================================================================

/**
 * User response from backend API
 */
export interface PhotoUrlsApi {
  sm: string;
  md: string;
  lg: string;
}

export interface UserResponseApi {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  email_verified: boolean;
  role?: string;
  phone?: string;
  date_of_birth?: string;
  nationality?: string;
  passport_number?: string;
  passport_expiry?: string;
  passport_country?: string;
  photo_key?: string | null;
  photo_urls?: PhotoUrlsApi | null;
  created_at: string;
  updated_at: string;
  last_login?: string;
}

/**
 * Authentication response from API
 */
export interface AuthResponseApi {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: UserResponseApi;
  session_id: string;
  is_new: boolean;
}

/**
 * Token refresh response from API
 */
export interface TokenResponseApi {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

/**
 * Google config response from API
 */
export interface GoogleConfigResponseApi {
  client_id: string;
  enabled: boolean;
}

// ============================================================================
// API Request Types (snake_case - sent to backend)
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
  fingerprint?: string;
}

export interface RegisterRequest {
  email: string;
  first_name: string;
  last_name: string;
}

export interface CompleteRegistrationRequest {
  token: string;
  password: string;
  confirm_password: string;
}

export interface GoogleAuthRequest {
  id_token: string;
  fingerprint?: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface CheckEmailResponse {
  exists: boolean;
  verified: boolean | null;
  message: string;
}

/**
 * Session response from API (snake_case)
 */
export interface SessionResponseApi {
  id: string;
  user_id: string;
  created_at: string;
  last_activity: string;
  ip_address?: string;
  user_agent?: string;
  is_current: boolean;
}

// ============================================================================
// Internal Types (camelCase - used in Redux/React)
// ============================================================================

/**
 * User object for internal use
 */
export interface PhotoUrls {
  sm: string;
  md: string;
  lg: string;
}

export interface User {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  emailVerified: boolean;
  role?: string;
  phone?: string;
  dateOfBirth?: string;
  nationality?: string;
  passportNumber?: string;
  passportExpiry?: string;
  passportCountry?: string;
  photoKey?: string | null;
  photoUrls?: PhotoUrls | null;
  createdAt: string;
  updatedAt: string;
  lastLogin?: string;
}

/**
 * Auth credentials for internal use
 */
export interface AuthCredentials {
  accessToken: string;
  refreshToken: string;
  tokenType: 'bearer';
  expiresIn: number;
  user: User;
  sessionId: string;
  isNew: boolean;
}

/**
 * Token response for internal use
 */
export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: 'bearer';
  expiresIn: number;
}

/**
 * Google config for internal use
 */
export interface GoogleConfig {
  clientId: string;
  enabled: boolean;
}

/**
 * Session info for internal use
 */
export interface SessionResponse {
  id: string;
  userId: string;
  createdAt: string;
  lastActivity: string;
  ipAddress?: string;
  userAgent?: string;
  isCurrent: boolean;
}

// ============================================================================
// Transform Functions (API → Internal)
// ============================================================================

export function transformUser(api: UserResponseApi): User {
  return {
    id: api.id,
    email: api.email,
    firstName: api.first_name,
    lastName: api.last_name,
    emailVerified: api.email_verified,
    role: api.role,
    phone: api.phone,
    dateOfBirth: api.date_of_birth,
    nationality: api.nationality,
    passportNumber: api.passport_number,
    passportExpiry: api.passport_expiry,
    passportCountry: api.passport_country,
    photoKey: api.photo_key ?? null,
    photoUrls: api.photo_urls ?? null,
    createdAt: api.created_at,
    updatedAt: api.updated_at,
    lastLogin: api.last_login,
  };
}

export function transformAuthResponse(api: AuthResponseApi): AuthCredentials {
  return {
    accessToken: api.access_token,
    refreshToken: api.refresh_token,
    tokenType: api.token_type,
    expiresIn: api.expires_in,
    user: transformUser(api.user),
    sessionId: api.session_id,
    isNew: api.is_new,
  };
}

export function transformTokenResponse(api: TokenResponseApi): TokenResponse {
  return {
    accessToken: api.access_token,
    refreshToken: api.refresh_token,
    tokenType: api.token_type,
    expiresIn: api.expires_in,
  };
}

export function transformGoogleConfig(api: GoogleConfigResponseApi): GoogleConfig {
  return {
    clientId: api.client_id,
    enabled: api.enabled,
  };
}

export function transformSession(api: SessionResponseApi): SessionResponse {
  return {
    id: api.id,
    userId: api.user_id,
    createdAt: api.created_at,
    lastActivity: api.last_activity,
    ipAddress: api.ip_address,
    userAgent: api.user_agent,
    isCurrent: api.is_current,
  };
}

// Legacy aliases for backwards compatibility during migration
export type UserResponse = User;
export type AuthResponse = AuthCredentials;
