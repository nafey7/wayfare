# MUI → Mantine migration pattern

Established in M1 (#908) on the layout shell. M2–M6 should replicate this without re-deriving.

## The rule

**Pure library swap. No design changes.** If a pixel moves, it's a bug in the swap, not an opportunity to improve the design.

## Conversion table

| MUI | Mantine | Notes |
|---|---|---|
| `import { Box, Stack } from '@mui/material'` | `import { Box, Stack } from '@mantine/core'` | Drop-in for the names; APIs differ. |
| `<Box sx={{ ... }}>` | `<Box style={{ ... }}>` | `sx` → `style`. No theme refs in `style` — use CSS vars or literal values. |
| `bgcolor: 'background.default'` | `background: 'var(--mantine-color-body)'` in `style` | Mantine maps body bg via the color scheme; don't hardcode `#fff`. |
| `borderColor: 'divider'` + `border: 1` | `border: '1px solid var(--mantine-color-default-border)'` in `style` | Combine into a single border shorthand; Mantine has no separate `borderColor` token shortcut here. |
| `display: { xs: 'none', md: 'flex' }` on a flex container | `<Flex visibleFrom="md">` | Mantine has `visibleFrom`/`hiddenFrom` for breakpoint-based show/hide. **Use `<Flex>` (not `<Box style={{ display: 'flex' }}>`)**: Mantine's `visibleFrom` rule is `display: none !important` in `@layer mantine`, which would still beat an inline `display: flex`, but the cascade is non-obvious and a future reader will second-guess it. `<Flex>` keeps `display` class-level and self-documents. For non-flex containers (block-level), plain `<Box visibleFrom="md">` is fine — no inline `display` needed. |
| `<Stack spacing={2}>` | `<Stack gap="md">` | `spacing` (number, MUI 8 px scale) → `gap` (named token or px). Mantine's default `Stack` gap is `"md"` (16 px); MUI's is `0`. **If you want zero gap (no inter-child margin), pass `gap={0}` explicitly** — easy to miss. |
| `sx={{ px: 3, py: 2 }}` | `style={{ paddingInline: 24, paddingBlock: 16 }}` | Translate MUI 8 px scale to literal pixels. Don't use `var(--mantine-spacing-*)` — values don't line up (MUI px:3 = 24 px, Mantine `xl` = 32 px). |
| `import Box from '@mui/material/Box'` | `import { Box } from '@mantine/core'` | Mantine has no per-component import paths; always named imports from `@mantine/core`. |
| `<Typography variant="h4">` | `<Title order={4}>` | Headings only. Body text → `<Text>`. |
| `<Typography color="text.secondary">` | `<Text c="dimmed">` | Mantine's `dimmed` is `gray.6` and matches the design intent of `text.secondary`. |

## Story file rules

- Story files (`*.stories.tsx`) follow the same rules. They're tested by `vitest --project=storybook`, so a broken import will surface as a smoke test failure.
- Stories that imported MUI primitives just to render demo content (e.g. `Box`/`Typography` in args) should switch to Mantine equivalents.
- Stories that import from `@mui/icons-material` should switch to **Lucide** (`lucide-react`) — that's the icon library the existing migrated chat components use (PR #916). Don't introduce a third icon library.

## Heading sizes — known asymmetry, NOT a bug

`tokens.typography.{h1..h6}` is Mantine-only. `mantineTheme.ts` reads it via `headings.sizes`; `muiTheme.ts` does **not** override `typography.h*`. So:

- `<Typography variant="h4">Foo</Typography>` (MUI) renders at MUI's default **2.125 rem (~34 px)**.
- `<Title order={4}>Foo</Title>` (Mantine) renders at the token's **1.125 rem (~18 px)**.

This is the production design contract: ~30+ MUI page titles across Admin / Hotels / Flights / Auth / Onboarding currently render at MUI defaults, and "fixing" `muiTheme.ts` to read tokens would shrink every one of them in a single commit.

**For M-ticket migrations:** when you replace `<Typography variant="hN">` with `<Title order={N}>`, the heading size **will** change. This is expected. Do **not** treat it as a regression to revert — but **do** confirm with design (or by comparing to the live staging/prod surface) whether the post-migration size is correct, and call it out in the PR body. If the smaller token size is wrong for the surface, override per-component (`<Title order={N} fz="xl" fw={700}>` etc.) rather than changing tokens.ts (which would also affect every other Mantine surface that reads it).

History: M1 (#919) demo-content `<Typography variant="h4">` → `<Title order={4}>` swap shrank "Page Content" in MainLayout.stories. I initially [misframed it](https://github.com/myvoya/voya/issues/707#issuecomment-4361904786) as a `muiTheme.ts` gap and [retracted](https://github.com/myvoya/voya/issues/707#issuecomment-4362032131) once the production usage audit landed. Don't repeat that mistake.

## Deliberately NOT migrated

- `src/stories/foundation/MuiTheme.stories.tsx` — kept as a deliberate MUI reference until M6 cleanup. Don't touch it in M2–M5.
- The `theme/muiTheme.ts` and the MUI `ThemeProvider` in `AppProviders.tsx` — both stay until M6 removes `@mui/*` from `package.json`.
- Component scope hard-anchored to **production code under each milestone**. Don't swap MUI in any file outside the M-ticket's named scope, even if the diff looks tempting.

## Pre-PR self-check (author)

Before opening the PR, walk through this checklist. M1 (#919) shipped a bug the reviewer caught — `<Box style={{ display: 'flex' }}>` + `visibleFrom`, which contradicts the conversion table four rows up — so "I read the doc" is not a substitute for "I went down the list".

These items are unique to the author's pre-submit pass; the technical gates (grep, smoke, lint, build) live in **Verification** below and are run as part of this same pass.

- [ ] Re-read the **Conversion table** above. Anything in your diff that maps to a row in the table that you did differently?
- [ ] Ran every step in the **Verification** section below — green across the board.
- [ ] Took before/after screenshots of every migrated story at desktop + mobile. Saved under `.local/journal/YYYY-MM-DD/screenshots/storybook-prs/pr-{N}/`.
- [ ] Reviewed the screenshots myself (multimodal `Read` of each PNG) — flagged any visible diff in the PR body, not just the obviously-broken ones.
- [ ] If the migrated component has no story (route shells, layout wrappers): noted in PR body that visual coverage is end-to-end-only, and ran a manual smoke against `localhost:8000`.

## Verification (per M-ticket PR)

The technical gates. Run as part of the pre-PR self-check (author), and revisited by reviewers / CI.

1. **Grep-clean for `@mui/`** in your scope:
   ```bash
   grep -rn "@mui/" src/<scope>/
   ```
   Empty output is the gate.

2. **Smoke tests pass** for any story that touches the migrated files:
   ```bash
   npx vitest run --project=storybook src/<scope>/
   ```

3. **Production build succeeds**:
   ```bash
   npm run build
   ```

4. **Lint + typecheck**:
   ```bash
   npx eslint src/<scope>/ && npx tsc --noEmit
   ```

5. **Visual review** (replaces the dropped pixel-diff VR system, per #884):
   - PR opens → Cloudflare Pages preview deploys → `pr-{N}.voya-storybook.pages.dev`.
   - Take Playwright screenshots of each migrated story at desktop (1280 × 720) and phone (375 × 812) viewports.
   - Claude Code (multimodal) reads each PNG and flags any unintended visual differences in the PR comment thread.

## Locally: dealing with Vite's optimize-deps cache

Swapping MUI imports for Mantine in already-loaded files can leave Vite's optimize-deps cache stale, surfacing as `504 Outdated Optimize Dep` and a blank Storybook iframe. **Restart the Storybook dev server** to refresh; the production build (and CI) is unaffected.
