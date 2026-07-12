/** Shared `sx` for flight/hotel curated category tab rows (avoid drift). */

export const categoryTabRowSx = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: { xs: 0.25, md: 0.5 },
  py: { xs: 0.25, md: '0.5rem' },
} as const;

export const categoryTabTitleSx = {
  fontSize: { xs: '0.75rem', sm: '0.8125rem', md: 15 },
  lineHeight: 1.2,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: { xs: 0.25, md: 0.5 },
} as const;

export const categoryTabIconSx = { fontSize: { xs: 12, md: 15 } } as const;

export const categoryTabCaptionSx = {
  opacity: 0.8,
  /** At `md+`, `undefined` lets caption typography use the theme default (not the xs/sm overrides). */
  fontSize: { xs: '0.6rem', sm: '0.65rem', md: undefined },
  lineHeight: 1.15,
} as const;
