import { palette, navyScale, brandScale, surfaces } from '@/theme/tokens';

// ── From design tokens (exact matches) ────────────────────────────────────────

/** Deep navy — identity colour for borders, interactive elements, headings */
export const C_NAVY       = palette.secondary.dark;       // #171B63
/** Default border / selected chip background */
export const C_BORDER     = surfaces.borderDefault;       // #E4E6F5
/** Mid-tone navy — secondary text, inactive icons */
export const C_NAVY_MID   = navyScale[5] as string;       // #636e9d
/** Light navy — separators, de-emphasised text */
export const C_NAVY_LIGHT = navyScale[3] as string;       // #9aa2c5
/** Connector pill resting background */
export const C_PILL_BG    = brandScale[0] as string;      // #eef0fd
/** Connector pill hover / active background */
export const C_PILL_HOVER = brandScale[1] as string;      // #dde1fb

// ── Itinerary-specific surfaces (no exact token match; declared once here) ────

/** Muted label / chip text */
export const C_LABEL      = '#525874';
/** Stop-row hover fill */
export const C_ROW_HOVER  = '#EDEEFA';
/** Header border-bottom and timeline rule */
export const C_DIVIDER    = '#eef0f8';
/** Skip-day button hover background */
export const C_BTN_HOVER  = '#fafbff';
/** Star rating fill */
export const C_STAR       = '#f5a623';

// ── Overlays / shadows — rgb(23,27,99) = C_NAVY ───────────────────────────────

/** Day-chip semi-opaque backdrop */
export const C_CHIP_OVERLAY  = 'rgba(23,27,99,0.92)';
/** Card resting shadow colour */
export const C_SHADOW_CARD   = 'rgba(23,27,99,0.04)';
/** Row / small-element hover shadow colour */
export const C_SHADOW_HOVER  = 'rgba(23,27,99,0.08)';
/** Card expanded shadow colour */
export const C_SHADOW_ACTIVE = 'rgba(23,27,99,0.10)';
/** Collapse-button shadow colour */
export const C_SHADOW_BTN    = 'rgba(23,27,99,0.12)';
/** Connector pill hover shadow colour */
export const C_SHADOW_PILL   = 'rgba(23,27,99,0.18)'; // used by ConnectorPill :hover state
/** Card hovered shadow colour */
export const C_SHADOW_CARD_HV = 'rgba(23,27,99,0.20)';
/** Expand-button shadow colour */
export const C_SHADOW_BTN_EX  = 'rgba(23,27,99,0.30)';

// ── navyBlue (surfaces.navyBlue = #2A2F5F) ────────────────────────────────────
// This is a distinct brand colour from C_NAVY (#171B63): used for CTA buttons,
// dark map/sheet surfaces, and day-header titles (navyScale[7]).

/** CTA / dark-surface navy — buttons, floating pills, day-header title text */
export const C_NAVY_BLUE         = surfaces.navyBlue;             // #2A2F5F
/** Drag-handle pill background — navyScale[1] */
export const C_DRAG_PILL         = navyScale[1] as string;        // #d4d8ea
/** Bottom-sheet drop shadow */
export const C_SHADOW_SHEET      = 'rgba(42,47,95,0.12)';
/** Floating Map button drop shadow */
export const C_SHADOW_MAP_BTN    = 'rgba(42,47,95,0.35)';
