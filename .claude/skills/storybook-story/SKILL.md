---
name: storybook-story
description: Create Storybook stories for a component following Voya conventions, verify they render, and optionally compare against staging. Use when adding stories for components that don't have them yet, or when a `/loop` over several components is opened (issue #703, #704, #705, etc.).
allowed-tools: Bash(npm run:*), Bash(npx vitest:*), Bash(npx tsc:*), Bash(./bin/playwright-cli:*), Bash(mkdir:*), Bash(date:*), Bash(curl:*), Bash(find:*), Bash(grep:*), Read, Edit, Write, Glob, Grep
argument-hint: [component-path-or-feature]
---

# Create Storybook stories

@frontend-v2/CLAUDE.md

For: $ARGUMENTS

Story files live **co-located** with the component (`Component.stories.tsx` next to `Component.tsx`). The global decorators in `.storybook/preview.tsx` already inject the MUI theme and a fresh Redux store per story — you only add decorators the specific component needs (router, context provider, etc.).

## The ritual

### 1. Orient before writing

Read these first, in order — skipping steps here is how you end up with fixtures that *look* right but render wrong on staging:

1. The component source — note which hooks it uses (`useNavigate`, `useAppDispatch`, custom context) so you know which decorators the story needs.
2. The co-located test file (`Component.test.tsx`) if one exists — tests already contain valid fixture shapes. Reuse them.
3. `frontend-v2/CLAUDE.md` "Storybook" section — title hierarchy, template, theme notes.
4. One sibling `*.stories.tsx` nearby — for local patterns (e.g. `SuggestedReplies.stories.tsx` in the chat folder showed the `fn()` + `chatBotTheme` decorator pattern).

### 2. Match fixtures to the live data contract, not just the TS type

`ChatMessage.extraData` is typed as `Record<string, unknown>` — TypeScript will accept almost anything. But the render functions read specific nested fields. For PR #703 the hotel summary text template reads `summary.nights` + `price_range.currency`; omitting them produced *"1 night. Prices start from £85"* where staging showed *"7 nights. Prices start from €85"*.

**Rule:** check the *render util* (e.g. `messageUtils.ts:getHotelSearchMessageSummary`), not the type. Or screenshot-compare against staging (step 6).

### 3. Shared fixtures go in `__fixtures__/`

When the same mock is used by multiple stories (e.g. the `ChatPanel` transcript reuses the flight/hotel/itinerary fixtures), put them in `components/__fixtures__/mockXyzData.ts` rather than inlining in each story.

### 4. Story template

```tsx
import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn, within } from 'storybook/test';     // for event handlers + DOM assertions
import { MemoryRouter } from 'react-router-dom'; // only if component uses useNavigate
import { MyComponent } from './MyComponent';

const meta: Meta<typeof MyComponent> = {
  title: 'Feature/MyComponent',  // sidebar hierarchy — see CLAUDE.md for the map
  component: MyComponent,
  args: {
    onSomething: fn(),
  },
  decorators: [
    (Story) => <MemoryRouter><Story /></MemoryRouter>,
  ],
};

export default meta;
type Story = StoryObj<typeof MyComponent>;

export const Default: Story = {
  args: { /* ... */ },
  // Assert what a successful render of THIS story looks like.
  // The Storybook vitest runner executes this in headless Chromium.
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Use helpers from @/stories/helpers/playAssertions.ts when one fits;
    // otherwise raw `expect(canvas.getByText(...))` is fine.
  },
};
```

For components that need a context (e.g. `ChatPanel` uses `useChatContext`), write a story-only `MockProvider` that supplies the context value inline — do **not** use the real provider, which does API calls and localStorage reads. There's a stub helper at `@/stories/helpers/stubChatContextValue.ts` that covers `useChatContext` consumers.

### 4a. Write a `play` function for every data story

Stories that render data must declare what "correct render" means via an assertion in `play`. This is the gate that catches the PR #852 class — fixture is shape-compatible with TypeScript but doesn't supply what the component reads, so visible cards show `N/A` / `0h 0m`. The render-only smoke test (#857) misses this; play functions catch it because they assert the actual rendered text.

Reusable assertions live in `frontend-v2/src/stories/helpers/playAssertions.ts`:

| Helper | Asserts |
|---|---|
| `expectAirportCode(canvas, 'AMS')` | IATA visible at least once |
| `expectAirportPair(canvas, origin, destination)` | Both codes visible |
| `expectDurationPresent(canvas)` | A `2h 15m`-style duration is on screen |
| `expectPricePresent(canvas, '€'?)` | A currency-prefixed price is on screen |
| `expectNoPlaceholderText(canvas, { naBudget?, durationBudget? })` | No `N/A` / `0h 0m` leaked through |
| `expectFlightCardPopulated(canvas, { outbound, inbound? })` | Composite: airports + duration + price + no placeholders |

If your domain doesn't have a helper yet (hotels, itinerary, profile, etc.), add one to `playAssertions.ts` rather than scattering raw `getByText` calls. The point of named helpers is sharper failure messages and reuse across stories in the same domain.

Stories that *are* an empty / placeholder state by design (`Empty`, `NoResults`, `ErrorFallback`) should still have a play function — but assert the empty-state copy is visible (`expect(canvas.getByText(/no results/i))`), not populated data.

### 5. Verify render (required gate)

```bash
cd frontend-v2
npx tsc --noEmit                          # types clean
npx vitest run --project storybook 2>&1 | tail -20
```

The `storybook` vitest project mounts every story in headless chromium and runs each story's `play` function. Failures here block the PR. **This also runs in CI as the `Frontend Storybook Story Smoke Tests` job, which is blocking** — don't open a PR until it passes locally.

Common failure patterns this catches:
- **`useChatContext must be used within a ChatProvider`** (or any other context error) — the component (or something it transitively imports) reads a context, and your story doesn't supply it. Wrap with a story-only `MockProvider`, or pick a different component boundary if the dependency is accidental.
- **"Cannot read properties of undefined"** — fixture is missing a field the component reads. Check the component source for what it reads and add it to the fixture.
- **Unhandled promise rejection in render** — component kicks off an RTK Query on mount that has no base URL set. Either provide a network mock or stub the hook.
- **`expected airport code "AMS" to be visible at least once`** (or similar play-assertion failure) — the story rendered, but the `play` function couldn't find the data the fixture should produce. Most often the fixture is shape-compatible with the TS type but doesn't carry the nested fields the render util reads (e.g. `flight.segments`, `summary.nights`). See step 2.

### 6. Visual compare against staging (when the component has a production counterpart)

This is how you catch fixture-shape bugs that vitest can't. Skip it if the component isn't live yet.

```bash
# Start Storybook in the background
npm run storybook &

# Drive staging through the relevant flow
./bin/playwright-cli -s=voya-staging open https://staging.myvoya.ai
# ...navigate, interact, screenshot

# Screenshot each story (quote the URL — ? trips shell glob)
./bin/playwright-cli -s=voya-storybook goto \
  "http://localhost:6006/iframe.html?id=<story-id>&viewMode=story"
./bin/playwright-cli -s=voya-storybook screenshot \
  --filename=".local/journal/$(date +%Y-%m-%d)/screenshots/storybook-<name>.png"
```

**Compare the component *in its production wrapper*, not in isolation.** For PR #703, `FlightResultMessage` has its own white/pointed-corner styling — but when rendered inside `ChatPanel` (which is how staging uses it), the styling stands. The isolated-component story and the panel-context story can both be right even when they look different; use the wrapper story as the staging comparison.

See the `screenshot` skill for session-persistence details and the `playwright-cli` skill for full CLI reference.

### 7. Close the loop

When using `/loop` (multiple Storybook issues in a track), after each issue:
- Commit the stories for that component
- Skip `.claude/settings.json` changes (they leak machine-specific paths)
- Verify `npm run build-storybook` still succeeds before moving on — a broken build affects every subsequent story

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Story renders blank, console error about `useNavigate` | Component uses router, no decorator | Add `MemoryRouter` decorator |
| Story throws "X must be used within a Y Provider" | Component reads a custom context | Add a story-only `MockProvider` that supplies the context value |
| `play` function fails: `expected airport code "AMS" to be visible at least once` (or similar) | Story rendered but the data the assertion expects isn't visible — fixture is shape-compatible with the type but missing nested fields the render util reads | Fix the fixture; check the render util (e.g. `flightMapper`, `getHotelSearchMessageSummary`) for what it reads. Don't loosen the assertion. |
| Summary text in rich-result card differs from staging | Fixture missing a field the render util reads | Open the util in `features/chat/utils/messageUtils.ts` and match its reads, not just the TS type |
| Screenshot loop captures 0 bytes | Shell ate the `?` in the iframe URL | Quote the URL |
| `vitest --project storybook` hangs on unrelated stories | Pre-existing failures in other files | Grep for your own story names only |

## Related skills

- `/screenshot` — session-persistent screenshots for Storybook/staging/prod
- `/playwright-cli` — full browser automation reference
- `/test` — run vitest/pytest suites
