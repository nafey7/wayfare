/**
 * Registry of DOM `id` values for the public marketing route (`/`).
 * All ids use the `landing-` page prefix. Do not use these on `/home`.
 *
 * See inline `LANDING_PAGE_IDS` for the full tree; section anchors, headings,
 * CTAs, chips, cards, and supporting copy blocks are registered for analytics and tests.
 *
 * Before adding, renaming, or removing ids, read `docs/LANDING_DOM_IDS.md` (repo path:
 * `frontend-v2/docs/LANDING_DOM_IDS.md`).
 */
export const LANDING_PAGE_IDS = {
  nav: {
    logo: 'landing-nav-logo',
    signIn: 'landing-nav-sign-in',
  },
  signInCard: {
    root: 'landing-sign-in-card',
  },
  hero: {
    section: 'landing-section-hero',
    calloutChip: 'landing-hero-callout',
    heading: 'landing-hero-heading',
    subheadline: 'landing-hero-subheadline',
    ctaPrimary: 'landing-hero-cta-primary',
    flightMiniCard: 'landing-hero-mini-flight',
    hotelMiniCard: 'landing-hero-mini-hotel',
    search: {
      input: 'landing-hero-search-input',
      sendButton: 'landing-hero-search-send',
      suggestionChip: (index: number) => `landing-hero-search-suggestion-${index}`,
    },
  },
  weekendRail: {
    section: 'landing-section-weekend-rail',
    heading: 'landing-weekend-rail-heading',
    tripCard: (index: number) => `landing-weekend-rail-trip-${index}`,
  },
  fromCityRail: {
    section: 'landing-section-from-city-rail',
    heading: 'landing-from-city-rail-heading',
    tripCard: (index: number) => `landing-from-city-rail-trip-${index}`,
  },
  voyaPicks: {
    section: 'landing-section-voya-picks',
    heading: 'landing-voya-picks-heading',
    cta: 'landing-voya-picks-cta',
  },
  interestRail: {
    section: 'landing-section-interest-rail',
    heading: 'landing-interest-rail-heading',
    chip: (index: number) => `landing-interest-rail-chip-${index}`,
    tripCard: (index: number) => `landing-interest-rail-trip-${index}`,
  },
  closingChat: {
    section: 'landing-section-closing-chat',
    heading: 'landing-closing-chat-heading',
    input: 'landing-closing-chat-input',
    sendButton: 'landing-closing-chat-send',
  },
} as const;

export type LandingPageIds = typeof LANDING_PAGE_IDS;
