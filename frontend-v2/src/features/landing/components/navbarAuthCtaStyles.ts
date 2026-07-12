/**
 * Frosted-glass pill for primary actions on dark/navy backgrounds.
 * Used in: nav bar Sign in/out buttons, auth modal primary actions (Continue, Sign In,
 * Complete Registration). Semi-transparent white fill, blurred backdrop, white border.
 *
 * Shape: Mantine `Button` `styles.root`. Use as:
 *   <Button styles={{ root: navBarAuthCtaButtonStyles }}>…</Button>
 */
export const navBarAuthCtaButtonStyles = {
  paddingInline: 20,
  paddingBlock: 6,
  borderRadius: 9999,
  backgroundColor: 'rgba(255, 255, 255, 0.12)',
  color: 'white',
  fontWeight: 500,
  fontSize: 13,
  lineHeight: 1.43,
  letterSpacing: 0.1,
  border: '1px solid rgba(255, 255, 255, 0.35)',
  backdropFilter: 'blur(8px)',
  boxShadow: 'none',
  '&:hover': {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    boxShadow: 'none',
  },
} as const;

/**
 * Navy pill for Sign in / Sign out inside mobile drawers (white background context).
 * Solid navy (#2A2F5F) fill, white text, pill radius — primary action on light surfaces.
 *
 * Shape: Mantine `Button` `styles.root`. Use as:
 *   <Button styles={{ root: navbarDrawerAuthCtaButtonStyles }}>…</Button>
 */
export const navbarDrawerAuthCtaButtonStyles = {
  paddingInline: 24,
  paddingBlock: 10,
  borderRadius: 9999,
  backgroundColor: '#2A2F5F',
  color: 'white',
  fontWeight: 600,
  fontSize: 14,
  boxShadow: 'none',
  '&:hover': {
    backgroundColor: '#1e2248',
    boxShadow: 'none',
  },
} as const;
