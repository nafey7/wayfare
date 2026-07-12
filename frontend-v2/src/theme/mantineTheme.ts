import { createTheme } from '@mantine/core';
import { brandScale, accentScale, navyScale, surfaces, typography, shadows } from './tokens';
import { zIndex } from './zIndex';

export const mantineTheme = createTheme({
  primaryColor: 'navy',
  primaryShade: 7,
  colors: {
    brand: brandScale,
    accent: accentScale,
    navy: navyScale,
  },
  autoContrast: true,

  fontFamily: typography.fontFamilyMantine,
  fontFamilyMonospace: typography.fontFamilyMono,
  headings: {
    fontFamily: typography.fontFamilyMantine,
    fontWeight: '700',
    sizes: {
      h1: { fontSize: typography.h1.fontSize, lineHeight: typography.h1.lineHeight },
      h2: { fontSize: typography.h2.fontSize, lineHeight: typography.h2.lineHeight },
      h3: { fontSize: typography.h3.fontSize, lineHeight: typography.h3.lineHeight },
      h4: { fontSize: typography.h4.fontSize, lineHeight: typography.h4.lineHeight },
      h5: { fontSize: typography.h5.fontSize, lineHeight: typography.h5.lineHeight },
      h6: { fontSize: typography.h6.fontSize, lineHeight: typography.h6.lineHeight },
    },
  },

  defaultRadius: 'md',
  shadows,

  // Surface & spacing tokens — access via theme.other in components.
  other: surfaces,

  components: {
    Container: {
      // Mantine's Container has no implicit `width: 100%`; in flex-column parents
      // (e.g. our `<main>` layout) it would shrink to intrinsic content width
      // instead of expanding to its `max-width`. MUI's Container had `width: 100%`
      // baked in — restoring parity here keeps M-track migrations from regressing
      // page widths. See #969.
      defaultProps: {
        w: '100%',
      },
    },
    Button: {
      defaultProps: {
        color: 'navy.7',
        radius: 'xl',
      },
    },
    ActionIcon: {
      defaultProps: {
        color: 'navy.7',
      },
    },
    Loader: {
      defaultProps: {
        color: 'navy.7',
      },
    },
    Checkbox: {
      defaultProps: {
        color: 'navy.7',
      },
    },
    Radio: {
      defaultProps: {
        color: 'navy.7',
      },
    },
    Slider: {
      defaultProps: {
        color: 'navy.7',
      },
    },
    RangeSlider: {
      defaultProps: {
        color: 'navy.7',
      },
    },
    Switch: {
      defaultProps: {
        color: 'navy.7',
      },
    },
    Card: {
      defaultProps: {
        radius: 'lg',
        shadow: 'sm',
        padding: 'lg',
      },
    },
    Badge: {
      defaultProps: {
        radius: 'sm',
      },
    },
    TextInput: {
      defaultProps: {
        radius: 'md',
      },
    },
    Select: {
      defaultProps: {
        radius: 'md',
      },
    },
    Textarea: {
      defaultProps: {
        radius: 'md',
      },
    },
    Chip: {
      defaultProps: {
        radius: 'xl',
      },
    },
    Paper: {
      defaultProps: {
        radius: 'lg',
        shadow: 'sm',
      },
    },
    Modal: {
      defaultProps: {
        radius: 'lg',
      },
    },
    Notification: {
      defaultProps: {
        radius: 'md',
      },
    },
    Tooltip: {
      // Render in a portal above the chat sheet (zIndex.chatSheet = 1300) so
      // tooltips on toolbars inside the sheet (or floating above it) are never
      // occluded. See `src/theme/zIndex.ts` for the canonical stack.
      defaultProps: {
        withinPortal: true,
        zIndex: zIndex.tooltip,
      },
    },
  },
});
