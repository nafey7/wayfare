# Frontend v2 - Development Guide

## Quick Reference

**Tech Stack**: Vite 6 + React 18.3 + TypeScript 5.7 + Redux Toolkit 2.8 + MUI 7 + **Mantine v7**
**Forms**: react-hook-form + Zod (existing MUI surfaces) / `@mantine/form` (new surfaces)
**Testing**: Vitest + Testing Library

## Design system (hybrid Mantine + MUI)

Voya ships a **hybrid design system**: MUI for existing surfaces, Mantine v7 for new ones. Both coexist; choose based on the surface.

**Quick rules:**
- New surfaces, date pickers, complex primitives → **Mantine** (`@mantine/core`, `@mantine/dates`, `@mantine/form`)
- Existing chat, flight/hotel cards, profile → **MUI** (until ported)
- Raw tokens (palette, shadows, surfaces, typography scales) → `src/theme/tokens.ts`
- Both themes derive from `tokens.ts`; update tokens to change both at once

**Provider rule:** All providers live in **`src/providers/AppProviders.tsx`** — never add `ThemeProvider`, `MantineProvider`, `DatesProvider`, or `LocalizationProvider` ad-hoc.

**Storybook:** Use `StorybookProviders` from `src/providers/AppProviders.tsx` — wraps the same stack without `BrowserRouter`.

**Full guide:** [Foundation/Overview story](src/stories/foundation/Overview.mdx) in Storybook · implementation plan: `local-ops/plans/PLAN_mantine-design-system.md`

**Theme files (resolved — was issue #707):**
- `src/theme/tokens.ts` — raw design tokens (single source of truth for palette + font families). Note: heading sizes in `tokens.typography.{h1..h6}` are **Mantine-specific** (small Inter-font scale for new surfaces) and are read only by `mantineTheme.ts`. MUI surfaces use MUI defaults — see `MANTINE_MIGRATION_PATTERN.md` "Heading sizes" for the asymmetry that this implies during M-ticket migrations.
- `src/theme/muiTheme.ts` — MUI theme derived from tokens (palette + font family). Does NOT override `typography.h*` by design — production page titles depend on MUI defaults.
- `src/theme/mantineTheme.ts` — Mantine theme derived from tokens; reads `typography.{h1..h6}` for the new Mantine surfaces.
- `src/theme/index.ts` — canonical barrel (`import { muiTheme, mantineTheme, tokens, theme } from '@/theme'`)
- `src/theme.ts` — thin re-export shim for legacy paths; migrate callers to `@/theme` and delete.

## Project Structure

```
src/
├── api/                 # RTK Query endpoints
│   ├── baseApi.ts       # Base config with auth middleware
│   ├── authApi.ts       # Auth endpoints (login, register, OAuth)
│   ├── chatApi.ts       # Chat endpoints
│   ├── flightsApi.ts    # Flight search/booking endpoints
│   ├── hotelsApi.ts     # Hotel search/booking endpoints
│   └── usersApi.ts      # User profile endpoints
├── components/layout/   # Shared layout components
├── features/            # Feature modules (self-contained)
│   ├── auth/            # Login, Register, Password flows
│   ├── booking/         # Shared booking components (Phase 2+)
│   ├── chat/            # Chat widget + flight/hotel results
│   ├── flights/         # Flight booking (Phase 2)
│   ├── hotels/          # Hotel booking (Phase 3)
│   ├── landing/         # Public landing (`/`) + home (`/home`) — see below
│   └── profile/         # User profile (`FlightBookingsSection`, `HotelBookingsSection` on `/profile`)
├── hooks/               # Shared hooks
├── store/
│   └── slices/          # Redux slices
│       ├── authSlice.ts         # Auth + localStorage persistence
│       ├── chatSlice.ts         # Chat messages
│       ├── uiSlice.ts           # UI state
│       └── flightBookingSlice.ts # Flight booking wizard
├── types/               # TypeScript types
├── utils/               # Utility functions
└── theme/               # MUI theme config
```

## Landing vs home (`/` vs `/home`)

- **`PublicLandingPage`** (`/`) — public marketing; **`UnifiedHeader`** + **`LandingPageSections`** with **`LANDING_PAGE_IDS`** so the DOM has stable `landing-*` ids (anchors, analytics, E2E). Registry and naming live in `features/landing/landingPageIds.ts` (kebab-case, `landing-` prefix).
- **`HomePage`** (`/home`, authenticated) — same sections and behavior via **`useLandingPageController`** and **`LandingPageSections`**, but **no** `ids` prop: do not add marketing `id` attributes on `/home`.
- **Authenticated shell**: **`UnifiedHeader`** + **`BottomNav`** on **`/home`**; **`MainLayout`** (with `UnifiedHeader` in `variant="app"` mode) for all other post-login routes (`/chat`, profile, booking flows, etc.). Guest **`/public/chat`** uses `MainLayout` without auth actions.
- Shared UI is composed in **`LandingPageSections`**; optional `domIds` on section components are only passed from the public page.

**Landing DOM ids (add, wire, stability)**: see **[docs/LANDING_DOM_IDS.md](docs/LANDING_DOM_IDS.md)** — follow this when editing the public landing or `LANDING_PAGE_IDS`.

## Key Patterns

### 1. RTK Query API Slices

All API slices inject into `baseApi` for shared auth handling:

```typescript
// api/flightsApi.ts
import { baseApi } from './baseApi';

export const flightsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    searchFlights: builder.mutation<FlightSearchResponse, FlightSearchRequest>({
      query: (body) => ({ url: '/flights/search', method: 'POST', body }),
    }),
  }),
});

export const { useSearchFlightsMutation } = flightsApi;
```

**Auto-refresh**: `baseApi` handles 401 responses with automatic token refresh using a mutex pattern.

### 2. Redux Slices with localStorage

Auth state persists to localStorage:

```typescript
// Load on init
const persistedState = loadAuthState(); // reads from localStorage

// Persist on change
setCredentials: (state, action) => {
  state.token = action.payload.accessToken;
  localStorage.setItem('Authorization', action.payload.accessToken);
}
```

### 3. Feature Module Structure

Each feature is self-contained:

```
features/chat/
├── components/          # UI components
│   └── flights/         # Flight result display
├── context/             # ChatContext + useChatContext
├── hooks/               # useChatScroll, useChatSound
├── styles/              # chatTheme.ts
└── index.ts             # Public exports
```

**Chat flight/hotel search bubbles**: `FlightResultMessage` and `HotelResultMessage` render a **short summary + primary CTA only** (no inline curated lists). Tapping **View flights** hydrates `cachedFlightResults` and navigates to `/flights/search` (which detects the cache hit and renders without re-fetching). **View hotels** mirrors the same pattern: hydrates `cachedHotelResults` and navigates to `/hotels/search`.

**Chat → nav-bar sync rules** (View Flights / View Hotels / View Itinerary, including cross-populating the *opposite* side): see **[docs/CHAT_NAV_BAR_SYNC.md](docs/CHAT_NAV_BAR_SYNC.md)**. One rule governs all three buttons: form params always reflect the clicked payload; cached results are kept only when the cache's trip canonically matches the new form params, otherwise the cache is cleared so the destination page refetches.

### 4. Type Conventions

**API types** (snake_case): Match backend OpenAPI schema

```typescript
// types/api.ts or api.generated.ts
interface TokenResponseApi {
  access_token: string;
  refresh_token: string;
}
```

**Internal types** (camelCase): Used throughout the app

```typescript
// types/auth.ts
interface AuthCredentials {
  accessToken: string;
  refreshToken: string;
  user: User;
}
```

**Transform at API boundary** in RTK Query `transformResponse` or component code.

### 5. Form Pattern (react-hook-form + Zod)

```typescript
const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Min 8 characters'),
});

const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(schema),
});
```

## Commands

```bash
# Development
npm run dev              # Start dev server (http://localhost:3000)
npm run build            # Production build
npm run preview          # Preview production build

# Quality
npm run lint             # ESLint
npm run type-check       # TypeScript check (tsc --noEmit)
npm run test             # Vitest
npm run test:coverage    # Coverage report

# API Types
npm run generate-api-types       # From running backend
npm run generate-api-types:file  # From openapi.json file
```

## Booking Architecture

For detailed booking implementation (Phase 2 flights, Phase 3 hotels):

See **[docs/BOOKING_ARCHITECTURE.md](docs/BOOKING_ARCHITECTURE.md)**

## Path Aliases

Configured in `tsconfig.json`:

```typescript
import { useAppSelector } from '@/store/hooks';
import type { MappedFlight } from '@/types/flight';
```

- `@/` → `src/`

## Environment Variables

```bash
# .env
VITE_API_URL=/api              # Backend API URL
VITE_GOOGLE_CLIENT_ID=...      # Google OAuth
VITE_STRIPE_PUBLIC_KEY=...     # Stripe (Phase 2+)
```

## Storybook

Storybook is the component design system. Use it to view components in isolation, verify theme changes, and iterate on UI without running the full app.

### Running

```bash
npm run storybook          # Dev server at http://localhost:6006
npm run build-storybook    # Static build (for CI / Cloudflare Pages)
```

### Hosted Storybook

Storybook is auto-deployed to Cloudflare Pages on every PR, on merge to main, and on production tags:

| Deployment | URL Pattern |
|---|---|
| **Main branch** | https://voya-storybook.pages.dev |
| **PR previews** | https://pr-{N}.voya-storybook.pages.dev |
| **Production releases** | https://v2026-4-3.voya-storybook.pages.dev |

Workflow: `.github/workflows/storybook-deploy.yml`

### Sidebar Structure

| Section | What's in it |
|---|---|
| **Foundation/** | Theme verification: Colors, Typography, Buttons, Inputs, Cards, Chips |
| **Layout/** | App shell: MainLayout, UnifiedHeader, BottomNav, ContentPanel, LayoutWithChat |
| **Marketing/** | Landing page: Hero, LandingPageSections, Footer |
| **Chat/** | Chat UI: messages, input, result cards |
| **Flights/** | FlightCard, SearchBar, Filters, TravellersSelector |
| **Hotels/** | HotelCard, RoomCard, SearchBar, GuestForm |
| **Profile/** | ProfileHeader, BookingCards |
| **Shared/** | CountrySelect, RevolutPaymentForm |

### Writing Stories

Stories are **co-located** with their component:

```
features/flights/components/FlightCard.tsx
features/flights/components/FlightCard.stories.tsx   <-- next to it
```

Foundation stories are the exception (not tied to one component):

```
src/stories/foundation/Colors.stories.tsx
src/stories/foundation/Buttons.stories.tsx
```

Shared fixtures that more than one story reuses go in `__fixtures__/` next to the stories (e.g. `features/chat/components/__fixtures__/mockChatData.ts`). Don't inline the same mock across multiple files.

**Match fixtures to the live data contract, not the TS type.** `extraData: Record<string, unknown>` will accept almost anything, but the render util reads specific nested fields. For chat rich-results, `getHotelSearchMessageSummary` reads `summary.nights` and `price_range.currency`; omitting them produces text that doesn't match staging. Rule: check the render util (e.g. `features/chat/utils/messageUtils.ts`) before trusting the type.

**When verifying a component visually, compare it in its production wrapper.** Components like `FlightResultMessage` have their own styling (white, pointed corner) — but when rendered inside `ChatPanel` (how staging uses it) the result looks identical to staging. The isolated-component story and the in-panel story can both be correct even when they look different; use the in-panel story as the staging comparison.

### Story Template

```tsx
import type { Meta, StoryObj } from '@storybook/react-vite';
import { MyComponent } from './MyComponent';

const meta: Meta<typeof MyComponent> = {
  title: 'Flights/MyComponent',    // sidebar hierarchy
  component: MyComponent,
};

export default meta;
type Story = StoryObj<typeof MyComponent>;

export const Default: Story = {
  args: {
    label: 'Example',
    variant: 'primary',
  },
};

export const WithCustomProps: Story = {
  args: {
    label: 'Custom',
    disabled: true,
  },
};
```

### Theme

All stories are wrapped with the Voya MUI theme automatically via `.storybook/preview.tsx`:
- `ThemeProvider` with `src/theme.ts` (Lato font, #BFC6F4 lavender primary, production theme)
- `CssBaseline` for consistent baseline styles
- Redux `Provider` with a fresh store per story (no state leaking)

Note: `src/theme.ts` is the production theme. A separate aspirational theme exists at `src/theme/index.ts` (Inter, #667eea) but is not fully applied. Theme unification is tracked in #707.

To verify theme changes, check the **Foundation/** stories.

### Story assertions (`play` functions)

Stories that render data should include a `play` function that asserts what a *correct* render looks like. The Storybook vitest runner executes these in headless Chromium; a failed `expect()` fails the test.

This is what catches the "story renders, but the visible card is full of N/A because the fixture doesn't supply what the component reads" class — fixture-shape bugs that TypeScript can't see and that the render-only smoke test (#857) doesn't notice.

```tsx
import { within } from 'storybook/test';
import { expectFlightCardPopulated } from '@/stories/helpers/playAssertions';

export const Default: Story = {
  args: { /* ... */ },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'AMS', destination: 'BCN' },
      inbound: { origin: 'BCN', destination: 'AMS' },
    });
  },
};
```

Reusable assertions live in [`src/stories/helpers/playAssertions.ts`](src/stories/helpers/playAssertions.ts):
- `expectAirportCode(canvas, 'AMS')` — IATA visible
- `expectAirportPair(canvas, origin, destination)` — both codes visible
- `expectDurationPresent(canvas)` — at least one `2h 15m`-style duration
- `expectPricePresent(canvas, '€'?)` — currency-prefixed price
- `expectNoPlaceholderText(canvas, { naBudget?, durationBudget? })` — no `N/A` / `0h 0m` leaked
- `expectFlightCardPopulated(canvas, { outbound, inbound? })` — composite check for flight cards

Add a domain-specific helper when you start a new story track (e.g. `expectHotelCardPopulated`) rather than scattering raw `getByText` calls. Story authors get cleaner stories; CI gives sharper failure messages ("expected airport code AMS to be visible" vs "renders empty").

When a story is genuinely empty/placeholder by design (e.g. `Empty`, `NoResults`, header-only), the play function should still exist — but it asserts the empty-state copy, not populated data.

**Async-rendering components** (anything that renders behind RTK Query / `useEffect` / lazy loaders) need `await waitFor(() => ...)` rather than synchronous calls. Bare `expect(canvas.getByText(...))` runs before the data arrives and silently passes against the loading skeleton:

```tsx
import { waitFor } from 'storybook/test';

play: async ({ canvasElement }) => {
  const canvas = within(canvasElement);
  await waitFor(() => expectAirportPair(canvas, 'AMS', 'BCN'));
},
```

For stories with synchronous fixtures (props passed inline, no API calls), the bare form is correct — that's why the existing flight stories don't `await`. When in doubt, prefer `waitFor` — it's a no-op cost when the data is already there.

### Using Storybook to Understand Components

Before modifying a component, check if it has a story:

```bash
# Find stories for a component
find src -name "*.stories.tsx" | grep -i flightcard
```

If a story exists, open it in Storybook to see:
- What props it accepts (Controls panel)
- How it looks in different states
- Whether it uses the theme correctly

If no story exists, create one. This helps you understand the component's API and serves as documentation for the next person.

### Taking Screenshots

Use Playwright to screenshot stories for visual review:

```bash
npx playwright screenshot --wait-for-timeout 2000 --full-page \
  "http://localhost:6006/iframe.html?id=foundation-buttons--default&viewMode=story" \
  screenshot.png
```

Story ID format: `title-lowered--story-name` (e.g., `Foundation/Buttons` becomes `foundation-buttons--default`).

Always **quote the iframe URL** — zsh (the default shell here) treats `?` as a glob and silently skips the command when no match is found, leaving you with zero-byte screenshots.

Prefer the `screenshot` skill (session-persistent) or the `storybook-story` skill (creates + verifies + screenshot-compares against staging) over raw playwright calls.

See `testing/CLAUDE.md` for full screenshot reference.

### MCP Integration

When Storybook is running, the `@storybook/addon-mcp` serves component metadata at `http://localhost:6006/mcp`. Claude Code can use this to discover components, read their prop APIs, and generate stories.

## Key Files

| File | Purpose |
|------|---------|
| `src/api/baseApi.ts` | RTK Query config, auth middleware, 401 refresh |
| `src/store/slices/authSlice.ts` | Auth state + localStorage persistence |
| `src/store/slices/flightBookingSlice.ts` | Flight booking wizard state |
| `src/types/flight.ts` | Flight domain types |
| `src/types/hotels.ts` | Hotel domain types |
| `src/features/chat/context/ChatContext.tsx` | Chat state management |
