# E2E walkthroughs (staging happy-flow drivers)

Reusable Playwright "walkthroughs" that drive a real user journey end-to-end on **staging**.
The original purpose was to capture **BEFORE / AFTER screenshots** for Mantine migration PRs
(M4-3, M5, M6) where the dev backend can't return real flight/hotel results, but the same
infra is useful for any PR that needs to verify a deployed-staging flow without re-discovering
selectors each time.

## Why these exist (and how they're different from `testing/e2e/tests/`)

| | `testing/e2e/tests/*.spec.js` | `testing/e2e/walkthroughs/*.walkthrough.js` |
|---|---|---|
| Run by | Playwright test runner (`npm test`) | Imported by ad-hoc scripts or other specs |
| Pass / fail | Yes — assertions throw | No — return result objects, caller decides |
| Output | Test report + automatic failure screenshots | Screenshots at chosen moments + return value |
| Used for | Regression / CI gates | Migration screenshot capture, manual verification |

The two are **complementary**. A walkthrough wraps the same Page Object selectors a spec
would use, but exposes them as a function any caller can drive. M-track migration PRs call a
walkthrough twice — once on `origin/main` staging (BEFORE), once on the post-deploy staging
of the PR (AFTER) — and diff the resulting screenshots.

## Phasing

| Phase | Walkthrough | Status |
|---|---|---|
| 1 (pilot) | `flightSearch.walkthrough.js` — auth-first search-bar → search results (44 flight cards) | ✅ |
| 1 (pilot) | `publicChatFlightSearch.walkthrough.js` — un-auth public-chat → recommendations panel | ✅ |
| 2A | `authChatFlightSearch.walkthrough.js` — auth-first chat → recommendations panel (most-popular real-user path) | ✅ |
| 2B | `flightBooking.walkthrough.js` — full booking through review (stops before Pay now to avoid Revolut sandbox / GDS booking residue) | ✅ |
| 3A | `hotelChatSearch.walkthrough.js` — auth chat → /hotels/recommendations | ✅ |
| 3B | `hotelBooking.walkthrough.js` — auth chat → recommendations → rooms → review-booking (stops at page mount; no Quick Fill exists for hotels) | ✅ |
| 4 | `itinerary.walkthrough.js` — auth chat → /itinerary/&lt;id&gt; (auto-saved) | ✅ |
| 5A | `publicChatHotelSearch.walkthrough.js` — guest /public/chat → /public/chat/hotels/recommendations | ✅ |
| 5B | `publicChatItinerary.walkthrough.js` — guest /public/chat → /public/chat/itinerary?destination=&lt;city&gt; | ✅ |

Three different flows reach the flight recommendations surface — same panel, three entry points:

| Walkthrough | Entry | Why it exists |
|---|---|---|
| `publicChatFlightSearch` | `/public/chat` (guest) | Verifies guest path; fires `flight_search_results_shown` (source: `recommendations`) |
| `authChatFlightSearch` | `/chat` (auth) | Most-popular real-user path. Fires `flight_search_results_shown` twice (source: `chat-inline` + `recommendations`) — both intentional, same `search_session_id` |
| `flightSearch` (auth-first) | `/flights/search` search bar (auth) | Less-trafficked surface but still important. Doesn't fire `flight_search_results_shown` consistently (per [#954](https://github.com/myvoya/voya/issues/954)) — falls back to "44 flights found" header text |

Each phase is its own PR. Don't bundle.

## Running locally

Walkthroughs run against **staging** (`https://staging.myvoya.ai`) and need two env vars:

| Var | Purpose | Source |
|---|---|---|
| `STAGING_TEST_USER_EMAIL` | Pre-existing staging user | GitHub secret |
| `STAGING_TEST_USER_PASSWORD` | Password for that user | GitHub secret |

Staging does not currently bot-block headless Playwright traffic — `CF_TEST_BYPASS_TOKEN` is set up as a GitHub secret for the regular E2E suite but is not consumed here. If staging starts requiring it, see the [Troubleshooting](#troubleshooting) section.

To run a walkthrough yourself:

```bash
# Source the staging creds (or export STAGING_TEST_USER_EMAIL/_PASSWORD manually)
source .local/test-credentials/staging-test-user.env

# Run — TEST_ENV=staging MUST be set in the shell, not in JS, because
# testing/utils/constants.js resolves the base URL at module-load time
cd testing
TEST_ENV=staging node e2e/walkthroughs/run-flight-search.js

# Limit to one flow + tag the output dir
TEST_ENV=staging node e2e/walkthroughs/run-flight-search.js --flow=public-chat --label=before
TEST_ENV=staging node e2e/walkthroughs/run-flight-search.js --flow=auth-chat --label=after

# Phase 2B — full booking through /flights/review-booking (stops before Pay now)
TEST_ENV=staging node e2e/walkthroughs/run-flight-booking.js --label=after
TEST_ENV=staging node e2e/walkthroughs/run-flight-booking.js --entry=searchbar --label=after

# Phase 3A — chat → /hotels/recommendations
TEST_ENV=staging node e2e/walkthroughs/run-hotel-search.js --label=after

# Phase 3B — chat → /hotels/review-booking (stops at page mount)
TEST_ENV=staging node e2e/walkthroughs/run-hotel-booking.js --label=after

# Phase 4 — chat → /itinerary/<saved_itinerary_id> (slow, ~2-3 minutes)
TEST_ENV=staging node e2e/walkthroughs/run-itinerary.js --label=after

# Phase 5 — guest public-chat → hotel or itinerary (no login required)
TEST_ENV=staging node e2e/walkthroughs/run-public-chat.js --flow=hotel --label=after
TEST_ENV=staging node e2e/walkthroughs/run-public-chat.js --flow=itinerary --label=after
```

Output goes to `.local/journal/<date>/screenshots/walkthroughs/<branch>/[<label>/]<flow>/`.

## Authoring conventions

### 1. Each walkthrough exports one async function

```js
// flightSearch.walkthrough.js
export async function walkFlightSearch(page, options = {}) {
  const { onStep = () => {}, label = 'flight-search' } = options;
  // ... interaction ...
  await onStep('flight_search_results_shown', { url: page.url() });
  return { events: [...], finalUrl: page.url() };
}
```

The `onStep(eventName, ctx)` callback fires after each user-visible state transition. Callers
that want screenshots pass an `onStep` that calls `page.screenshot(...)`. Callers that just
want to drive the flow pass nothing.

### 2. Verification handles use `dataLayer` events from the [GTM tracking plan](../../../docs/GTM_TRACKING_PLAN.md)

Don't wait on selectors when you can wait on a `dataLayer` event. `flight_search_results_shown`
firing means the search-results component has actually rendered with data — much more stable
than waiting for an arbitrary text element to appear:

```js
await page.waitForFunction(
  () => window.dataLayer?.some(e => e?.event === 'flight_search_results_shown'),
  { timeout: 15000 },
);
```

If the GTM event isn't firing on a route, fall back to a stable test-id selector and
**document the gap** (open an issue against [#954](https://github.com/myvoya/voya/issues/954)
so the reconciliation work picks it up).

### 3. Reuse Page Object selectors

The auth modal already has `testing/e2e/pages/AuthModalPage.js`. Walkthroughs should import
that, not re-declare selectors. When a walkthrough hits a route that doesn't have a Page
Object yet, **add one** rather than inlining.

### 4. Document non-obvious steps

Each walkthrough has a header comment listing every user action (button name, field label).
That comment is the working spec for the flow — if a click breaks because someone renamed a
button, the fix lives in one file.

## Contracts

### `onStep(eventName, ctx)`

Called by the walkthrough at meaningful checkpoints. Caller decides what to do.

| Argument | Type | Description |
|---|---|---|
| `eventName` | string | Either a GTM `dataLayer` event name (`flight_search_results_shown`) or a synthetic step name (`opened_auth_modal`, `submitted_email`) — synthetic names are prefixed `__` |
| `ctx.url` | string | `page.url()` at the moment the step completed |
| `ctx.page` | Page | Playwright Page (caller can take its own screenshots) |

### Return value

```js
{
  events: string[],     // ordered list of step names invoked
  finalUrl: string,     // page.url() at end
  durationMs: number,   // wall-clock walk duration
}
```

## Adding a new walkthrough

1. Pick a flow from the table above.
2. Add `<flow>.walkthrough.js` that exports `walk<Flow>(page, options)`.
3. Add `run-<flow>.js` — a thin script that creates a Playwright page, calls the walkthrough,
   dumps screenshots into `.local/journal/...`, prints the event log.
4. Update this README's Phasing table.
5. Open a PR.

## Troubleshooting

- **"strict mode violation" on a button**: substring matching on `getByRole('button', { name: '...' })`
  resolves to multiple elements. Use `{ name: '...', exact: true }` (see `testing/e2e/pages/AuthModalPage.js`
  for the canonical example after fix #952).
- **Cloudflare blocks the navigation**: not currently happening on staging, but if it does
  the fix is to inject the existing `CF_TEST_BYPASS_TOKEN` GitHub secret into the request
  headers when creating the Playwright context (`browser.newContext({ extraHTTPHeaders: { 'cf-bypass': process.env.CF_TEST_BYPASS_TOKEN } })`). Add this to `run-flight-search.js`
  if the symptom appears.
- **`dataLayer` is undefined on staging**: shouldn't happen (GTM is loaded on `*.myvoya.ai`),
  but if it does, the page hasn't fully loaded yet. Add `page.waitForLoadState('networkidle')`.
- **Login completes but the redirect URL is wrong**: `PublicRoute` chooses `/home` vs `/chat`
  based on stashed return paths. See `AuthModalPage.expectPostLoginRedirect()` for the regex.

## Related

- Tracking plan: [`docs/GTM_TRACKING_PLAN.md`](../../../docs/GTM_TRACKING_PLAN.md) — event taxonomy.
- Tracking reconciliation: [#954](https://github.com/myvoya/voya/issues/954) — drift items
  to resolve.
- Page Objects: [`../pages/`](../pages/) — selector source of truth per surface.
- Migration discipline (loops): see root `CLAUDE.local.md` and the `feedback_pr_preflight.md`
  memory for why staging BEFORE/AFTER matters.
