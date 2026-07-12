# Chat → Nav Bar Sync (Search Params + Cached Results)

How the unified flight / hotel nav-bar search params and Redux result caches
behave when a user interacts with chat rich-result bubbles (View Flights, View
Hotels, View Itinerary).

## The single rule

> **Form params always reflect what the user just clicked.** Whether the search
> page renders cached results or fetches fresh is governed by a `trusted` flag
> on the cache itself — set when a live-chat hydrator populated the cache, and
> reset when the cache is cleared or a page-side fetch writes new results.

That's the whole model.

## Why a flag, not a params-equality check

The first iteration tried to compare the new form params against the cached
params and only honor the cache when they matched. That works in theory but
breaks when the backend ships slightly different shapes for the same trip
across the two payload sources (e.g. itinerary metadata says `adults: 2`
while the prefetched flight side-search results were fetched for `adults: 1`).
The page would then refetch even though the cache was the right answer.

The flag avoids that entire class of problem by capturing **intent** instead of
inferring from data: *if a live chat response stored this cache, it's the
authoritative answer for the trip the user just clicked.*

## Building blocks

| Concept | Where it lives |
|---|---|
| `searchFormParams` (flights) | `store/slices/flightBookingSlice.ts` |
| `searchFormParams` (hotels) | `store/slices/hotelBookingSlice.ts` |
| `cachedFlightResults` + `flightResultsCachedParams` + **`cachedFlightResultsTrusted`** | `flightBookingSlice` |
| `cachedHotelResults` + `hotelResultsCachedParams` + **`cachedHotelResultsTrusted`** | `hotelBookingSlice` |
| Chat hydrators | `features/chat/utils/hydrate*FromChatResponse.ts` |
| Itinerary sync | `store/thunks/syncItineraryToSearchParams.ts` |
| Cross-populate | `features/chat/utils/crossPopulateNavBarParams.ts` |

## Default / fresh-chat state

On a new chat, both slices return their `getDefaultSearchFormParams()`:
`tripType: null`, empty `from` / `to`, null dates, null travellers. Cache is
null and `cachedXxxResultsTrusted` is `false`. The nav-bar chips show
placeholders. **Nothing in this document fires until a chat result payload
arrives** — a brand-new session is never touched.

## The `trusted` flag — lifecycle

| Event | Flag |
|---|---|
| Live-chat hydrator stores cache (`hydrateFlightSearchResultsFromPayload`, `hydrateFlightSideSearchFromItinerary`, `hydrateHotelSearchResultsFromPayload`, `hydrateHotelSideSearchFromItinerary`, multicity / date-range variants) | `true` |
| `commitItineraryRichResultToUiState` re-runs the side-search hydrators when the itinerary payload carries prefetched results, or clears the caches when it doesn't | `true` / `false` accordingly |
| `clearCachedXxxResults` (e.g. logout, history-message click that runs `*ForFreshSearch`) | `false` |
| Page-side fetch writes results back into cache (`setCachedXxxResults` from `FlightSearchPage` / `HotelSearchPage`) | `false` (omitted `trusted` arg defaults to false) |

## How the search page uses it

```ts
const cacheHit =
  Boolean(cachedResults) &&
  !cacheExpired &&
  (cachedResultsTrusted || strictParamsMatch);
```

- **Trusted live-chat cache → instant render**, even when the cache's stored
  params differ slightly from the current form (e.g. inconsistent backend
  `adults`).
- **Untrusted cache + matching params → instant render** (return-from-details
  navigation, browser back, etc.).
- **Otherwise → cache miss → fetch fresh.**

## Scenarios

### A. Fresh chat — flight / hotel / itinerary result arrives

- Hydrator stores cache + form from the payload, sets `trusted: true`.
- User clicks View Flights / Hotels / Itinerary → navigates to clean
  `/flights/search` or `/hotels/search` (no `?q=`).
- Search page mount-only effect sees `trusted: true` → **instant render, no API
  call.**

### B. User clicks View on an earlier message in the same chat session

- That bubble's `extraData` still holds its full payload.
- Hydrator rewrites cache + form from that message's payload, `trusted: true`.
- Same outcome as Scenario A. **Instant render, no API call.**

### C. User opens a different conversation from history (`_isFromHistory: true`)

- The history variant (`hydrateFlightSearchParamsForFreshSearch` /
  `hydrateHotelSearchParamsForFreshSearch`) runs:
  - calls `clearCachedXxxResults` → cache cleared, `trusted: false`,
  - sets form params from the message,
  - sets `lastXxxPath` to an encoded `?q=` route.
- Page mount → no cache → **fresh API call.**

### D. Opposite-side populate (cross-populate)

- Flight result arrives → flight cache + form set with `trusted: true`; hotel
  side gets form params overwritten (no opposite cache touched).
- Hotel side: existing cache (if any) keeps its existing trust flag. New form
  may or may not match the cache's stored params:
  - If hotel cache was trusted from earlier in the session → **render cache**
    (same trust honored on the hotel tab).
  - If hotel cache is untrusted and params don't match → **refetch.**

### E. View Itinerary

- `syncItineraryToSearchParams` overwrites both `searchFormParams` slices from
  the itinerary payload. The flight branch fires whenever `destination` is
  present — origin may be empty (itineraries without a stated departure
  city), and `fromAirport` / `toAirport` are explicitly cleared so a previous
  itinerary's IATA doesn't bleed through.
- The thunk picks the destination path off the `trusted` flag, not by reading
  the cache back into the form:
  - `cachedXxxResultsTrusted === true` → `lastXxxPath` is set to the clean
    `/flights/search` or `/hotels/search` (no `?q=`) so the mount-only
    cache-hit check runs and renders cache.
  - Otherwise → an encoded `?q=` path is emitted so the URL-restoration
    effect fetches.
- If the prefetched side-searches (`hydrateXxxSideSearchFromItinerary`, run
  via `commitItineraryRichResultToUiState`) already populated cache + flag =
  true for this itinerary → both tabs render cached results instantly.
- If the itinerary had no prefetched results, the caches are cleared (flag =
  false) and the page fetches fresh.

## What this *doesn't* change

- The slice initial state and `getDefaultSearchFormParams()` are untouched —
  fresh chat still renders placeholders.
- Same-side, same-payload hydrators still dispatch cache + form together.
- TTL'd localStorage for form params unchanged.

## File map

| Concern | File |
|---|---|
| Trust flag + cache actions | `src/store/slices/flightBookingSlice.ts`, `src/store/slices/hotelBookingSlice.ts` |
| Flight hydrators (set `trusted: true`) | `src/features/chat/utils/hydrateFlightRecommendationsFromChatResponse.ts`, `src/features/chat/utils/hydrateItinerarySideSearches.ts` |
| Hotel hydrators (set `trusted: true`) | `src/features/chat/utils/hydrateHotelRecommendationsFromChatResponse.ts`, `src/features/chat/utils/hydrateItinerarySideSearches.ts` |
| Cross-populate (no cache writes) | `src/features/chat/utils/crossPopulateNavBarParams.ts` |
| Itinerary sync | `src/store/thunks/syncItineraryToSearchParams.ts` |
| Search-page cache check | `src/features/flights/pages/FlightSearchPage.tsx`, `src/features/hotels/pages/HotelSearchPage.tsx` |

## Mental model for reviewers

> **Form params = "what the user is currently asking for."**
> **Cached results = "what we last fetched (or were handed by chat) for some
> specific trip."**
> **`trusted` flag = "did this cache come from a live chat response?"**
>
> Render the cache if it's trusted OR if its params strictly match the form.
> Otherwise, fetch.
