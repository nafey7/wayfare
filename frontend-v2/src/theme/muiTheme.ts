import { createTheme } from '@mui/material/styles';
import { palette, typography } from './tokens';

// Module augmentations for custom palette fields — kept co-located with the theme.
declare module '@mui/material/Chip' {
  interface ChipPropsVariantOverrides {
    boldAction: true;
  }
}

declare module '@mui/material/styles' {
  interface Palette {
    chat: {
      botMessage: string;
      userMessage: string;
    };
    /** Paula/Figma purple for landing + hotel detail; aligns with `LANDING_TOKENS.baseColor`, not `primary.main`. */
    figmaBase: string;
  }
  interface PaletteOptions {
    chat?: {
      botMessage?: string;
      userMessage?: string;
    };
    figmaBase?: string;
  }
  interface TypeBackground {
    gradient?: string;
  }
}

export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: palette.primary,
    secondary: palette.secondary,
    success: palette.success,
    info: palette.info,
    warning: palette.warning,
    error: palette.error,
    text: palette.text,
    background: palette.background,
    chat: palette.chat,
    figmaBase: palette.figmaBase,
  },
  typography: {
    fontFamily: typography.fontFamilyApp,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        // Stops stray horizontal scroll from mis-sized children; can clip wide focus rings or
        // full-bleed visuals—prefer fixing the overflow source when that appears.
        // Note: `overflow-x: hidden` on `html` can interfere with `position: sticky` in some
        // Chromium builds (new scroll containment). The app shell uses fixed navbars, not sticky
        // sub-headers; if sticky regions are added later, fix overflow at the offending subtree
        // or avoid hiding overflow on `html` for those routes.
        html: {
          overflowX: 'hidden',
        },
        body: {
          overflowX: 'hidden',
        },
      },
    },
    MuiChip: {
      variants: [
        {
          props: { variant: 'boldAction' },
          style: ({ theme: t }) => ({
            backgroundColor: t.palette.primary.dark,
            color: t.palette.common.white,
            fontSize: '0.8rem',
            fontWeight: 500,
            height: 34,
            borderRadius: 17,
            paddingLeft: t.spacing(1),
            paddingRight: t.spacing(1),
            transition: 'all 0.15s ease',
            '&:hover': {
              backgroundColor: t.palette.secondary.dark,
            },
          }),
        },
      ],
    },
  },
});

// not yet tokenised — dark palette is out of scope for the initial Mantine integration PR.
// Add a darkPalette section to tokens.ts and replace these hardcoded values when dark mode ships.
export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#050000', // not yet tokenised
    },
    secondary: {
      main: '#303133', // not yet tokenised
    },
    text: {
      primary: '#fff',
      secondary: 'rgba(255, 255, 255, 0.7)',
    },
    background: {
      default: '#050000', // not yet tokenised
      paper: '#050000',   // not yet tokenised
    },
    chat: palette.chat,
    figmaBase: palette.figmaBase,
  },
  typography: {
    fontFamily: typography.fontFamilyApp,
  },
});

/** Default export: light theme (production). */
export const muiTheme = lightTheme;
