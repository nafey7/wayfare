/**
 * Manages an array of guest (unauthenticated) itineraries in localStorage.
 *
 * Itineraries are automatically appended whenever a guest generates one through
 * the chat. On login / registration, all entries are synced to the backend by
 * `guestItineraryListener`, and then this key is cleared.
 */

const GUEST_ITINERARIES_KEY = 'voya_guest_itineraries';
const MAX_ENTRIES = 20;
/** 30 days — long enough to survive a "sign up later" flow. */
const TTL_MS = 30 * 24 * 60 * 60 * 1000;

export interface GuestItineraryEntry {
  structuredItinerary: Record<string, unknown>;
  /** Snake_case keys matching ItineraryNavigationState.tripMeta. */
  tripMeta?: {
    origin?: string;
    destination?: string;
    departure_date?: string;
    return_date?: string;
    adults?: number;
    children?: number;
    infants?: number;
    trip_type?: string;
    destination_location?: { latitude: number; longitude: number };
  };
  savedItineraryId?: string;
  /** Unix ms — used for ordering and TTL eviction. */
  createdAt: number;
}

interface Envelope {
  entries: GuestItineraryEntry[];
}

function readEntries(): GuestItineraryEntry[] {
  try {
    const raw = localStorage.getItem(GUEST_ITINERARIES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Envelope;
    if (!parsed || !Array.isArray(parsed.entries)) return [];
    const now = Date.now();
    return parsed.entries.filter(
      (e) =>
        e?.structuredItinerary &&
        typeof e.createdAt === 'number' &&
        now - e.createdAt < TTL_MS,
    );
  } catch {
    return [];
  }
}

function writeEntries(entries: GuestItineraryEntry[]): void {
  try {
    localStorage.setItem(GUEST_ITINERARIES_KEY, JSON.stringify({ entries }));
  } catch {
    // Ignore (private browsing, quota exceeded)
  }
}

/** Returns all non-expired guest itineraries, newest first. */
export function getGuestItineraries(): GuestItineraryEntry[] {
  return readEntries();
}

/**
 * Prepends a new entry to the guest array.
 * Deduplicates by `savedItineraryId` when present so a re-generated itinerary
 * replaces the old entry rather than accumulating duplicates.
 */
export function addGuestItinerary(
  entry: Omit<GuestItineraryEntry, 'createdAt'>,
): void {
  if (!entry.structuredItinerary) return;
  const existing = readEntries();
  const deduped = entry.savedItineraryId
    ? existing.filter((e) => e.savedItineraryId !== entry.savedItineraryId)
    : existing;

  // When there's no savedItineraryId, guard against rapid-fire duplicate dispatches
  // (applySuccessfulChatResponse + navigateItineraryFromChatExtraData + ContentPanel
  // all fire setLastItineraryState for the same generation). Compare content against
  // the most recently stored entry only — different itineraries still get stored.
  if (!entry.savedItineraryId && deduped.length > 0) {
    try {
      const latest = deduped[0];
      if (
        latest &&
        JSON.stringify(latest.structuredItinerary) ===
          JSON.stringify(entry.structuredItinerary)
      ) {
        return;
      }
    } catch {
      // Ignore stringify errors and fall through to store the entry.
    }
  }

  const next: GuestItineraryEntry[] = [
    { ...entry, createdAt: Date.now() },
    ...deduped,
  ].slice(0, MAX_ENTRIES);

  writeEntries(next);
}

/**
 * Removes a single entry from the guest array (used during post-auth sync so
 * that a network failure mid-loop only drops the entries that failed, not all
 * of them). Matches by `savedItineraryId` when present, otherwise falls back to
 * `createdAt` for id-less entries.
 */
export function removeGuestItinerary(entry: GuestItineraryEntry): void {
  const existing = readEntries();
  const filtered = entry.savedItineraryId
    ? existing.filter((e) => e.savedItineraryId !== entry.savedItineraryId)
    : existing.filter((e) => e.createdAt !== entry.createdAt);
  writeEntries(filtered);
}

/**
 * Removes all guest itinerary data.
 *
 * Note: `GuestItinerariesStrip` reads this store on every render with no
 * `storage`-event subscription. This is intentional — the strip lives on the
 * public landing page (`/`) while the guest chat is at `/public/chat/*`.
 * The two routes never render simultaneously, so the component always remounts
 * (and re-reads) when the user navigates back to the landing page after generating
 * an itinerary. If the UX ever changes to show both surfaces at once, wire up a
 * `storage` event listener or lift guest entries into Redux.
 */
export function clearGuestItineraries(): void {
  try {
    localStorage.removeItem(GUEST_ITINERARIES_KEY);
  } catch {
    // Ignore
  }
}
