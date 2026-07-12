import { LANDING_TOKENS } from '@/features/landing/landingTokens';

/**
 * Paula/Figma hotel detail screens share the landing palette (`LANDING_TOKENS`), not
 * `theme.palette.primary` (see `theme.palette.figmaBase` in `@/theme`). Prefer these
 * tokens or MUI keys (`background.paper`, `text.primary`) where they match design.
 */
export const HOTEL_DETAIL_TOKENS = {
  ...LANDING_TOKENS,

  /** Room card borders, disabled reserve button background */
  neutralHighlight: '#e2e2e6',
  /** Nav inactive tab, muted secondary labels */
  navInactive: '#76777a',
  navInactiveHover: '#5c5d60',
  /** Primary button hover */
  basePurpleDark: '#5a61a3',
  black20: 'rgba(0, 0, 0, 0.2)',
  dividerSubtle: 'rgba(0, 0, 0, 0.1)',
  overlayDark: 'rgba(0, 0, 0, 0.6)',
  overlayDarkHover: 'rgba(0, 0, 0, 0.72)',
  baseColorHover04: 'rgba(107, 114, 183, 0.04)',
  reserveCardShadow: '0px 2px 20px 0px rgba(0,0,0,0.12)',
  /** Low-inventory scarcity label (Paula / Figma) */
  scarcityAlert: '#e0473d',
} as const;
