// Shared utilities for walkthroughs.
//
// Extracted on the third occurrence (rule of three) — these helpers were
// duplicated verbatim across `publicChatFlightSearch.walkthrough.js`,
// `authChatFlightSearch.walkthrough.js`, and now `flightBooking.walkthrough.js`.
// Auto-review on PR #989 flagged the duplication as a future-drift risk; the
// third walkthrough is the right time to consolidate.

/**
 * Polls `window.dataLayer` until an entry with `event === eventName` exists.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} eventName
 * @param {object} [options]
 * @param {number} [options.timeout]
 */
export async function waitForDataLayerEvent(page, eventName, { timeout = 15000 } = {}) {
  await page.waitForFunction(
    (name) => Array.isArray(window.dataLayer) && window.dataLayer.some((e) => e?.event === name),
    eventName,
    { timeout },
  );
}

/**
 * Polls `window.dataLayer` until an entry matches both an event name and a
 * predicate over the entry's payload. Useful when the same event fires more
 * than once with different `source` or `search_session_id` fields and the
 * walkthrough needs to wait for a specific instance (e.g. the
 * `flight_search_results_shown` event fires twice — once with
 * `source: 'chat-inline'` and once with `source: 'recommendations'`).
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} eventName
 * @param {string} predicateString
 *   The predicate as a string source — e.g. `"e => e.source === 'recommendations'"`.
 *   Must be a string (not a function value) because Playwright's
 *   `waitForFunction` serializes arguments across the Node ↔ browser boundary;
 *   functions are not transferable, so we ship the source and `new Function`
 *   it back inside the page.
 * @param {object} [options]
 * @param {number} [options.timeout]
 */
export async function waitForDataLayerEventMatching(
  page,
  eventName,
  predicateString,
  { timeout = 15000 } = {},
) {
  await page.waitForFunction(
    ({ name, predicateSrc }) => {
      const predicate = new Function('e', `return (${predicateSrc})(e);`);
      return (
        Array.isArray(window.dataLayer) &&
        window.dataLayer.some((entry) => entry?.event === name && predicate(entry))
      );
    },
    { name: eventName, predicateSrc: predicateString },
    { timeout },
  );
}

/**
 * Pushes a step name onto the events log, then invokes the caller's onStep
 * callback. Walkthroughs use this to keep `events` and `onStep` in sync.
 *
 * @param {string[]} events
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} onStep
 * @param {string} eventName
 * @param {{ page: import('@playwright/test').Page }} ctx
 */
export async function runStep(events, onStep, eventName, ctx) {
  events.push(eventName);
  await onStep(eventName, ctx);
}

/**
 * Best-effort wait for the page to finish rendering after its "data ready"
 * signal (GTM `*_results_shown` event, page-mount, etc.) has fired.
 *
 * Why this exists: GTM `dataLayer` events fire when *data* arrives, not when
 * the *UI* has finished painting. Hotel/flight cards stream images, the
 * Mantine `<Loader />` for "Loading best options…" lingers until lists
 * hydrate, and Google Maps tiles render via RAF after the script loads.
 * A screenshot taken on the GTM event can show "Loading map…" or skeletons.
 *
 * Each sub-check has its own short timeout and is wrapped in `.catch(()=>{})`
 * because settle is best-effort — if a check overruns, we still proceed and
 * take the screenshot; it will be "more settled" than the pre-settle shot
 * even if not perfect.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {number} [options.networkIdleTimeoutMs=8000]
 * @param {number} [options.subCheckTimeoutMs=5000]
 * @param {number} [options.finalTickMs=1200]
 */
export async function waitForSettled(page, options = {}) {
  const {
    networkIdleTimeoutMs = 8000,
    subCheckTimeoutMs = 5000,
    finalTickMs = 1200,
  } = options;

  // 1. No in-flight network for 500ms — covers image lazy-loads, RTK Query
  //    requests, Google Maps script + tile fetches.
  await page.waitForLoadState('networkidle', { timeout: networkIdleTimeoutMs }).catch(() => {});

  // 2. No Mantine Loader spinners visible (used by the hotel results panel
  //    "Loading best options…" state and the "Loading map…" wrapper).
  await page
    .waitForFunction(() => document.querySelectorAll('.mantine-Loader-root').length === 0, undefined, {
      timeout: subCheckTimeoutMs,
    })
    .catch(() => {});

  // 3. No "Loading X…" copy in the body. Words restricted to the surfaces
  //    we know use this pattern to avoid false positives from user content.
  await page
    .waitForFunction(
      () =>
        !/\bLoading\s+(map|best|hotel|flight|itiner|results|options|trips)/i.test(
          document.body.innerText || '',
        ),
      undefined,
      { timeout: subCheckTimeoutMs },
    )
    .catch(() => {});

  // 4. Final RAF settle — absorbs map tile rendering, image fade-ins, and
  //    other transitions that don't show up in network or DOM signals.
  await page.waitForTimeout(finalTickMs);
}

/**
 * Convenience: wait for the page to settle, then emit a `<eventName>__settled`
 * step (the runner's `onStep` will snapshot it). Pair this with a normal
 * `runStep` to capture both the "data ready" and "UI settled" states for
 * BEFORE/AFTER comparisons.
 *
 * Example:
 *   await runStep(events, onStep, 'hotel_search_results_shown', { page });
 *   await runSettledStep(events, onStep, 'hotel_search_results_shown', { page });
 *
 * Produces two screenshots:
 *   NN-hotel_search_results_shown.png            (loading state)
 *   NN+1-hotel_search_results_shown__settled.png (settled state)
 *
 * @param {string[]} events
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} onStep
 * @param {string} eventName — the event we're settling for; `__settled` is appended
 * @param {{ page: import('@playwright/test').Page }} ctx
 * @param {Parameters<typeof waitForSettled>[1]} [settleOptions]
 */
export async function runSettledStep(events, onStep, eventName, ctx, settleOptions) {
  await waitForSettled(ctx.page, settleOptions);
  await runStep(events, onStep, `${eventName}__settled`, ctx);
}

export function noop() {}
