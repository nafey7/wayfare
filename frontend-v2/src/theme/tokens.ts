/**
 * Design tokens — single source of truth for both MUI (muiTheme.ts) and Mantine (mantineTheme.ts).
 * Values mirror current production hex values; update here and both themes stay in sync.
 */
import type { MantineColorsTuple } from '@mantine/core';

// ─── Palette ──────────────────────────────────────────────────────────────────

export const palette = {
  primary: {
    light: '#F3F5FE',
    main: '#BFC6F4',
    dark: '#7C83D0',
    contrastText: 'rgba(0, 0, 0, 0.87)',
  },
  secondary: {
    light: '#E8EAFC',
    main: '#7C83D0',
    dark: '#171B63',
    contrastText: '#fff',
  },
  success: {
    light: '#EEFCD4',
    main: '#70C92C',
    dark: '#1A6008',
    contrastText: '#fff',
  },
  info: {
    light: '#D7FEFA',
    main: '#37D5FC',
    dark: '#0A4278',
    contrastText: '#fff',
  },
  warning: {
    light: '#FEF8CB',
    main: '#FCC500',
    dark: '#785300',
    contrastText: '#fff',
  },
  error: {
    light: '#FFE8D4',
    main: '#FF4E2B',
    dark: '#7A0818',
    contrastText: '#fff',
  },
  text: {
    primary: '#050000',
    secondary: 'rgba(0, 0, 0, 0.6)',
  },
  background: {
    default: '#fff',
    paper: '#fff',
    gradient: 'linear-gradient(to right, #7c83d0, #5f65a3)',
  },
  /** Chat bubble colours */
  chat: {
    botMessage: '#CCCBFCC2',
    userMessage: '#E7FBBC',
  },
  /** Paula/Figma purple for landing + hotel detail */
  figmaBase: '#6b72b7',
} as const;

// ─── Brand (Mantine-only colour scales) ────────────────────────────────────────

/** Brand indigo — identity, nav, links, focus rings (#667eea = index 6) */
export const brandScale: MantineColorsTuple = [
  '#eef0fd', // 0
  '#dde1fb', // 1
  '#bcc3f6', // 2
  '#9aa4f2', // 3
  '#7e8dee', // 4
  '#7086ec', // 5
  '#667eea', // 6 — brand.main
  '#556bd8', // 7
  '#4356c5', // 8
  '#2c3ea8', // 9
];

/** Accent lime — highlights, badges, prices (#E7FBBC = index 2) */
export const accentScale: MantineColorsTuple = [
  '#f5fee8', // 0
  '#edfcd4', // 1
  '#e7fbbc', // 2 — limeAccent
  '#d4f78e', // 3
  '#bcea64', // 4
  '#a2d840', // 5
  '#84c01e', // 6
  '#69a012', // 7
  '#4f800a', // 8
  '#365c06', // 9
];

/** Navy — CTA buttons, dark surfaces (#2A2F5F = index 7) */
export const navyScale: MantineColorsTuple = [
  '#eceef5', // 0
  '#d4d8ea', // 1
  '#b8bed8', // 2
  '#9aa2c5', // 3
  '#7d87b0', // 4
  '#636e9d', // 5
  '#4d5a8a', // 6
  '#2A2F5F', // 7 — navyBlue (Button Blue per brand doc)
  '#1e2248', // 8
  '#131630', // 9
];

// ─── Surfaces & borders (Mantine `theme.other`) ────────────────────────────────

export const surfaces = {
  surfacePage: '#F4F5FF',    // cool off-white page background
  surfaceCard: '#FFFFFF',    // card / modal surface
  surfacePanel: '#ECEEFF',   // tinted sidebar / info panels
  surfaceInput: '#F8F9FF',   // input field background
  borderDefault: '#E4E6F5',  // default border with brand tint
  borderStrong: '#C8CCF0',   // emphasized border
  navyBlue: '#2A2F5F',       // CTA buttons, dark surfaces
  limeAccent: '#E7FBBC',     // highlights, badges, prices
  indigoMain: '#667eea',     // brand identity
  gradientBrand: 'linear-gradient(135deg, #848bd4 0%, #2A2F5F 100%)',
} as const;

// ─── Typography ────────────────────────────────────────────────────────────────

export const typography = {
  fontFamilyApp: "'Lato', sans-serif",       // MUI production font
  fontFamilyMantine: 'Inter, sans-serif',    // Mantine/new surfaces font
  fontFamilyMono: 'ui-monospace, monospace',
  h1: { fontSize: '2.25rem', lineHeight: '1.2' },
  h2: { fontSize: '1.75rem', lineHeight: '1.25' },
  h3: { fontSize: '1.375rem', lineHeight: '1.3' },
  h4: { fontSize: '1.125rem', lineHeight: '1.35' },
  h5: { fontSize: '1rem', lineHeight: '1.4' },
  h6: { fontSize: '0.875rem', lineHeight: '1.4' },
} as const;

// ─── Shadows (Mantine — brand-tinted) ─────────────────────────────────────────

export const shadows = {
  xs: '0 1px 3px rgba(102, 126, 234, 0.08)',
  sm: '0 2px 8px rgba(102, 126, 234, 0.10)',
  md: '0 4px 16px rgba(102, 126, 234, 0.12)',
  lg: '0 8px 32px rgba(102, 126, 234, 0.14)',
  xl: '0 16px 48px rgba(102, 126, 234, 0.18)',
} as const;
