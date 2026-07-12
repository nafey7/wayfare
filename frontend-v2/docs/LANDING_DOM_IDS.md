# Public landing DOM ids (`landing-*`)

This document describes how stable `id` attributes on the **public marketing route** (`/`) are defined, wired, and maintained. **Read this before changing** `features/landing/`, especially `landingPageIds.ts`, `PublicLandingPage`, `LandingPageSections`, or section components that accept `domIds`.

## Why these ids exist

- **Anchors / hash navigation** — URLs like `/#landing-section-how-it-works` scroll to section roots.
- **Analytics and product instrumentation** — external tools may key off predictable element ids.
- **E2E and automation** — tests can target stable selectors.

Only **`/`** uses these ids. **`/home`** reuses the same UI via `LandingPageSections` **without** passing `ids` so authenticated home does not expose marketing `landing-*` ids.

## Registry and naming

- **Source of truth**: `src/features/landing/landingPageIds.ts` — export **`LANDING_PAGE_IDS`**.
- **Prefix**: every value must start with **`landing-`** (kebab-case remainder).
- **Shape**: nested object tree mirroring sections; use **functions** for repeated UI (indexed segments such as `landing-example-itinerary-cta-0`) or slug-based ids where appropriate (e.g. footer links).

## Adding a new id

1. Add the string or function to **`LANDING_PAGE_IDS`** in `landingPageIds.ts`, following existing naming for that section.
2. Extend the section’s optional **`…DomIds`** interface in that component and set **`id={domIds?.…}`** on the target element (or pass through to a child).
3. If the element lives outside **`LandingPageSections`** (e.g. **`Navbar`**), pass the matching slice from **`LANDING_PAGE_IDS`** in **`PublicLandingPage`** (or wherever that subtree is rendered for `/`).
4. For **dynamic** ids (chips, cards, list items), add a registry function; extend **`collectFunctionSampleIds`** in **`landingPageIds.test.ts`** so the uniqueness test exercises representative indices.

## Stability — do not change id strings casually

Published `landing-*` values are a **stable contract**. Renaming or removing an id can break:

- Bookmarks and shared links that use hash fragments.
- Analytics dashboards or tags that reference the old id.
- Automated tests or scripts outside this repo.

**Prefer additive changes** (new ids for new elements). If you must rename or remove an id:

1. Confirm the need (e.g. coordinated migration with analytics/QA).
2. Search the codebase and any external docs for the old string.
3. Update **`landingPageIds.test.ts`** and any E2E or tooling that references the id.

## Related files

| Area | File |
|------|------|
| Registry | `src/features/landing/landingPageIds.ts` |
| Uniqueness / prefix tests | `src/features/landing/landingPageIds.test.ts` |
| Public page wiring | `src/features/landing/PublicLandingPage.tsx` |
| Shared sections + `ids` prop | `src/features/landing/LandingPageSections.tsx` |
| Authenticated home (no marketing ids) | `src/features/landing/HomePage.tsx` |

## Frontend guide

High-level **Landing vs home** summary: [`../CLAUDE.md`](../CLAUDE.md) (section “Landing vs home”).
