import { LANDING_TOKENS } from '@/features/landing/landingTokens';

/**
 * Paula review-booking step (guest + price summary) — shared by GuestForm and
 * HotelBookingReviewLayout. Maps Figma colors onto landing/base tokens where they align.
 */
export const HOTEL_REVIEW_BOOKING_TOKENS = {
  base: LANDING_TOKENS.baseColor,
  textMain: LANDING_TOKENS.textColor,
  /** Figma secondary labels — between `text.secondary` and landing `textSecondary` */
  textMuted: '#45474a',
  nationalityMuted: '#76777a',
  borderLight: '#e2e2e6',
  amber: '#f59e0b',
  amberText: '#92400e',
  highlightBg: 'rgba(122, 131, 221, 0.15)',
  highlightBorder: LANDING_TOKENS.baseLight,
  shadowSelected: '0px 2px 8px 0px rgba(107, 114, 183, 0.15)',
} as const;
