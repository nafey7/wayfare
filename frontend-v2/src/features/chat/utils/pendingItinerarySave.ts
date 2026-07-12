/**
 * Stash / consume itinerary data in localStorage for post-auth auto-save.
 * When a guest clicks "Save Itinerary", the data is stashed before the AuthModal opens.
 * After sign-up/login, the PostAuthConversionTracker consumes it and calls POST /api/itineraries.
 */

const PENDING_ITINERARY_SAVE_KEY = 'voya_pending_itinerary_save';

/** 24-hour TTL for stashed data — discard stale entries to avoid surprising saves. */
const TTL_MS = 24 * 60 * 60 * 1000;

interface PendingItinerarySavePayload {
  structured_itinerary: Record<string, unknown>;
  trip_meta?: Record<string, unknown>;
}

interface PendingItinerarySaveEnvelope {
  data: PendingItinerarySavePayload;
  timestamp: number;
}

export function stashPendingItinerarySave(payload: PendingItinerarySavePayload): void {
  try {
    const envelope: PendingItinerarySaveEnvelope = {
      data: payload,
      timestamp: Date.now(),
    };
    localStorage.setItem(PENDING_ITINERARY_SAVE_KEY, JSON.stringify(envelope));
  } catch {
    // Ignore storage errors (private browsing, quota exceeded, etc.)
  }
}

export function consumePendingItinerarySave(): PendingItinerarySavePayload | null {
  try {
    const raw = localStorage.getItem(PENDING_ITINERARY_SAVE_KEY);
    if (!raw) return null;
    const envelope = JSON.parse(raw) as PendingItinerarySaveEnvelope;
    if (!envelope?.data?.structured_itinerary) {
      localStorage.removeItem(PENDING_ITINERARY_SAVE_KEY);
      return null;
    }
    if (Date.now() - envelope.timestamp > TTL_MS) {
      localStorage.removeItem(PENDING_ITINERARY_SAVE_KEY);
      return null;
    }
    localStorage.removeItem(PENDING_ITINERARY_SAVE_KEY);
    return envelope.data;
  } catch {
    clearPendingItinerarySave();
    return null;
  }
}

export function clearPendingItinerarySave(): void {
  try {
    localStorage.removeItem(PENDING_ITINERARY_SAVE_KEY);
  } catch {
    // Ignore
  }
}
