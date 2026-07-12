/**
 * Canonical theme barrel — import from here or from '@/theme'.
 *
 * Exports:
 *   muiTheme      — MUI light theme (production, Lato font, lavender primary)
 *   darkTheme     — MUI dark theme
 *   mantineTheme  — Mantine v7 theme (Inter font, brand/navy/accent scales)
 *   tokens        — raw design tokens (palette, typography, shadows, surfaces)
 *   theme         — alias for muiTheme (backwards-compatible default)
 *   lightTheme    — alias for muiTheme (backwards-compatible)
 */
export { muiTheme, darkTheme, lightTheme } from './muiTheme';
export { mantineTheme } from './mantineTheme';
export * as tokens from './tokens';
export { zIndex } from './zIndex';

// Backwards-compatible default alias used by existing `import { theme } from '@/theme'` callers.
export { muiTheme as theme } from './muiTheme';
// Keep the named lightTheme re-export so tests using `import { lightTheme } from '@/theme'` work.
