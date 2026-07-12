/**
 * Shared design tokens for landing page sections.
 * Extracted from Figma design nodes to centralize brand colors.
 */
export const LANDING_TOKENS = {
  baseColor: '#6b72b7',
  baseColor10: 'rgba(122, 131, 221, 0.1)',
  baseColor20: 'rgba(107, 114, 183, 0.2)',
  baseLighter: '#d4d8fd',
  baseLight: '#c0c6f4',
  highlight: '#7a83dd',
  textColor: '#1f2937',
  textPrimary: '#121421',
  textSecondary: '#3e4774',
  textMuted: 'rgba(0, 0, 0, 0.6)',
  textMuted70: 'rgba(0, 0, 0, 0.7)',
  textLight: 'white',
  textLightBase: '#f1f1f4',
  textLight95: 'rgba(241, 241, 244, 0.95)',
  textLight80: 'rgba(241, 241, 244, 0.8)',
  navBorder: '#f0f1f5',
  bg: 'rgba(240, 241, 245, 0.5)',
  border: '#d1d4e0',
  borderLight: 'rgba(209, 212, 224, 0.3)',
  borderDivider: 'rgba(209, 212, 224, 0.5)',
  buttonBg: '#6b72b7',
  buttonText: 'white',
  shadow: '0px 10px 15px -3px rgba(0,0,0,0.1), 0px 4px 6px -4px rgba(0,0,0,0.1)',
  confirmColor: '#20a957',
  confirmLight: '#d2eedd',
  /** Saved itinerary hero chip — Pending (no linked flight/hotel refs yet). */
  pendingColor: '#e6a317',
  pendingChipTextColor: 'white',
  textHighlight: '#5d5e61',
  alertLight: '#f9dad8',
  tickGreen: '#22c55e',
  crossRed: '#ef4444',
  gradient:
    'linear-gradient(90deg, rgba(15, 20, 46, 0.2) 0%, rgba(15, 20, 46, 0) 50%, rgba(15, 20, 46, 0.2) 100%), linear-gradient(126.87deg, rgb(19, 26, 57) 0%, rgb(74, 32, 96) 50%, rgb(26, 34, 77) 100%)',
  fontFamily: {
    display: '"Proxima Nova", sans-serif',
    body: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    mono: 'monospace',
  },
} as const;

/** In-page anchor offset so sections clear the fixed navbar (`domIds` / public landing only). */
export const LANDING_SECTION_SCROLL_MARGIN_TOP = {
  xs: '72px',
  md: '88px',
} as const;
