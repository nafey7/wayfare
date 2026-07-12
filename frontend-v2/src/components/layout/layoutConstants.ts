/**
 * Internal split for the content column (right of the chat panel).
 * LIST = flex weight for the list/cards column, MAP = flex weight for the map.
 * Effective ratio is LIST:MAP (currently 35:65).
 */
export const CONTENT_SPLIT = { LIST: 35, MAP: 65 } as const;

/**
 * Flights-specific override of CONTENT_SPLIT: flight cards need more room
 * than the standard 35:65 list/map split, so the list gets a wider share.
 * Effective ratio is LIST:MAP (currently 55:45).
 */
export const FLIGHTS_CONTENT_SPLIT = { LIST: 55, MAP: 45 } as const;

/**
 * Layout constants for 2-column app layout (30% chat | 70% content)
 * Used by LayoutWithChat and AppLayoutWithChat
 */
export const LAYOUT = {
  CHAT_COLUMN_WIDTH: '30%',
  /** flex shorthand for content column */
  CONTENT_FLEX: 1,
} as const;
