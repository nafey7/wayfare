import type { CSSProperties } from 'react';

/**
 * Card sizing for profile booking strips — matches `SavedItineraryTripCard` carousel
 * layout (horizontal scroll + scroll snap on small viewports). For responsive widths,
 * use the `getProfileBookingCarouselCardStyle(isSm, isMd)` helper which returns
 * the right CSS object for the current breakpoint.
 */
export function getProfileBookingCarouselCardStyle(
  isSm: boolean,
  isMd: boolean,
): CSSProperties {
  const carouselWidth = isMd
    ? 'min(460px, calc((100vw - 64px) / 3 - 11px))'
    : isSm
      ? 'min(460px, calc(50vw - 24px))'
      : 'min(460px, calc(100vw - 32px))';
  return {
    flex: '0 0 auto',
    scrollSnapAlign: 'start',
    width: carouselWidth,
    maxWidth: 460,
    minWidth: isSm ? 280 : 260,
  };
}

export const profileBookingGridCardStyle: CSSProperties = {
  flex: 1,
  minWidth: 280,
  maxWidth: 460,
  width: '100%',
};
