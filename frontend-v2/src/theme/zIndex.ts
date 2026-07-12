/**
 * Named z-index layers for the app's overlay stack.
 *
 * Ordering: subHeader < stickyFooter < mapOverlay < mobileSheet < navbar < chatSheet < tooltip < detailModal < drawer < authModal
 * Values above 10000 intentionally exceed Mantine's default modal z-index (200)
 * so they stack correctly above all Mantine-managed overlays.
 */
export const zIndex = {
  subHeader: 90,      // sticky sub-headers beneath the navbar (onboarding step bar)
  stickyFooter: 100,  // sticky summary bars (multi-city / multi-stay bottom bars)
  mapOverlay: 900,    // full-screen map views (mobile fixed takeover)
  mobileSheet: 1050,  // bottom-sheet panels and map toggle buttons
  navbar: 1100,       // sticky AppBar
  chatSheet: 1300,    // mobile ChatSheet + portaled Menus rendered inside sheet headers
  tooltip: 1400,      // global Tooltip — sits above chatSheet so it's never occluded
  detailModal: 10000,
  drawer: 20000,
  authModal: 30000,
} as const;
