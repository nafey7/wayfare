# DX & Testing Strategy: Agent-First Development

> **Status:** Active
> **Date:** 2026-04-10
> **Last Updated:** 2026-04-11
> **Author:** Roel Sadza
> **Companion doc:** [2026-04-10-agent-driven-e2e-testing.md](./2026-04-10-agent-driven-e2e-testing.md) — concrete implementation details (config, YAML, commands)

## Vision

Voya's development workflow is evolving toward **agent-first development**: Claude Code as the primary implementer, tester, and operator, with humans providing direction, review, and approval. This document captures where we are, where we're heading, and the concrete steps to get there.

---

## 1. Current State

### What Claude Code Can Do Today

The Claude Code integration is already deep, covering 14 custom skills, 5 MCP servers, and CI-level automation:

| Domain | Capabilities | Tools |
|---|---|---|
| **Implement** | Read issue, create branch, write code, run tests, create PR | `@claude implement` (claude-review.yml) |
| **Review** | Auto-review every PR, respond to @claude questions, inline comments | claude-review.yml (auto-review + on-demand jobs) |
| **Test** | Run backend pytest, frontend vitest, E2E Playwright | `/test`, skills + Playwright MCP + Playwright CLI |
| **Browse the app** | Snapshot a11y tree, click, fill, navigate, screenshot | Playwright MCP, `playwright-cli` skill, `/screenshot` skill |
| **Inspect components** | Discover components, read prop APIs, generate stories | Storybook MCP (`addon-mcp`) |
| **Code Quality** | Lint, format, type check, security scan | `/lint` skill, pre-commit hooks |
| **Observe** | Production logs, Langfuse traces, weekly trace analysis | `/logs`, `/traces`, `/review-traces` skills + Sentry MCP + Langfuse MCP |
| **Operate** | CloudFlare DNS/cache, GTM tags, CI status | `/cloudflare`, `/ci` skills, GTM MCP |
| **Chat QA** | Test AI chat flows with assertions and timing | `/chat` skill |
| **PR Ops** | Batch parallel PR reviews in worktrees | `/review-prs` skill |

**MCP servers:** Langfuse (traces), GTM (analytics tags), Sentry (errors), Storybook (components), Playwright (browser).

### CI/CD Pipeline

Eight GitHub Actions workflows covering the full lifecycle:

```
PR opened
  +-- CI pipeline (lint, type-check, security, unit tests)    [parallel]
  +-- Claude auto-review                                       [parallel]
  +-- PR labeler (frontend/backend/infra/docs)                 [parallel]
  +-- PR title validation (conventional commits)               [parallel]
  +-- Code coverage PR comment (sticky)                        [parallel]
  +-- Storybook → Cloudflare Pages preview                    [parallel]

Merge to main
  +-- CI passes --> auto-deploy staging
  |     Build Docker --> Run migrations --> Update ECS --> Purge CloudFlare
  |     --> Post-deploy E2E smoke tests against staging.myvoya.ai
  +-- Refresh secrets baseline

Tag push (v*.*.*)
  +-- Deploy production
        Build Docker --> Run migrations --> Update ECS --> Purge CloudFlare

Weekly (Monday 9 AM UTC)
  +-- Automated Langfuse trace review --> GitHub issue with report
```

Additional: Strapi CMS has independent deploy pipelines (staging on push to main with `cms/**` changes, production on `strapi-v*` tags).

### Testing Infrastructure

**What works well:**
- Backend unit tests: pytest with 80% coverage minimum, runs in CI
- Frontend unit tests: vitest, runs in CI
- Docker test isolation: compose.test.yaml with separate DB, MailHog, FlightLogic mock
- Test fixtures: `auth-fixtures.js` with environment-aware auth (MailHog locally, dedicated test account on staging)
- Pre-commit hooks: ruff, mypy, bandit, detect-secrets
- Multi-environment Playwright config (`TEST_ENV=local|staging|dev`)
- Post-deploy E2E smoke tests on staging (run after every staging deploy)
- Storybook 10 with Foundation, Layout, and Marketing stories
- Storybook deployed to Cloudflare Pages on every PR (Cloudflare Access protected, OTP-restricted to `*@myvoya.ai`)
- Code coverage reports as sticky PR comments

**What's still in flight:**
- Most E2E test specs are still hand-written; agent test generation is the next phase
- Storybook coverage of feature modules (Chat, Flights, Hotels, Profile) not yet started
- Some staging E2E tests blocked on dedicated test account credentials (#714)
- A handful of pre-existing test discrepancies between local and staging (e.g., logout returns 401 on staging vs 403 expected)

### Discovered Tech Debt (April 2026)

The Phase 1-3 rollout surfaced several real issues that should be tracked rather than fixed inline:

| Item | Discovery | Tracked |
|---|---|---|
| Two MUI theme files: `src/theme.ts` (production: Lato, #BFC6F4) vs `src/theme/index.ts` (aspirational: Inter, #667eea); hundreds of inline overrides instead of theme tokens | Foundation stories caught it on day one ([#682](https://github.com/myvoya/voya/issues/682)) | [#707](https://github.com/myvoya/voya/issues/707) |
| `auth.spec.js` logout test expects 403 but staging returns 401 | PR #715 staging E2E run | (file separate issue) |
| `login.spec.js` has duplicated selectors inline alongside `SELECTORS` constants | Investigation for #686 seed test | (cleanup followup) |
| Stale `public-landing-chat` E2E test references removed `#landing-chat` element | Test infrastructure fix #678 | [#716](https://github.com/myvoya/voya/issues/716) |
| `dbHelper.connect()` in `beforeEach` blocks fails on staging (no MongoDB) | PR #715 review feedback | Fixed in PR #715, pattern documented (see Section 4) |

### The Gaps (Now Closed)

The two domains where Claude could not yet operate effectively when this doc was first written are now substantially closed:

**1. UI/Design** ✅ — Storybook + addon-mcp + `/screenshot` skill let Claude discover components, generate stories, take and view screenshots, and verify visual changes. Remaining: stories for the rest of the feature modules.

**2. E2E Confidence** ✅ partial — Playwright MCP + `playwright-cli` skill + post-deploy staging smoke tests give Claude exploratory and verification capability. Remaining: Playwright agent test generation pipeline (#686, #687).

---

## 2. Target State

### The Agent-First Workflow

```
Human                          Claude Code
  |                               |
  |  "Add hotel price filter"     |
  |------------------------------>|
  |                               |  1. Read issue, understand context
  |                               |  2. Storybook MCP: check existing filter components
  |                               |  3. Implement the component
  |                               |  4. Generate/update Storybook story
  |                               |  5. /screenshot story, verify visually
  |                               |  6. Playwright MCP: explore the live app
  |                               |  7. Generate E2E test for the new filter
  |                               |  8. Run all tests (unit + E2E)
  |                               |  9. Create PR
  |                               |
  |  CI runs automatically:       |
  |    - Lint, type-check, tests  |
  |    - Coverage PR comment      |
  |    - Storybook build -->      |
  |      pr-123.voya-storybook.   |
  |      pages.dev (Access-gated) |
  |    - Claude auto-review       |
  |                               |
  |  Review Storybook preview     |
  |  Review PR diff               |
  |  Approve & merge              |
  |------------------------------>|
  |                               |
  |  Auto-deploy staging          |
  |  Post-deploy E2E passes       |
  |                               |
  |  Tag for production           |
  |------------------------------>|
```

### MCP Server Strategy

Claude Code's MCP servers form a complete development toolkit:

| MCP Server | Purpose | Status |
|---|---|---|
| **Langfuse** | Production trace analysis, LLM observability | ✅ Configured |
| **GTM** | Google Tag Manager configuration | ✅ Configured |
| **Sentry** | Error tracking, issue search | ✅ Configured |
| **Storybook** (`addon-mcp`) | Component discovery, prop APIs, story generation | ✅ Configured (PR #691) |
| **Playwright** | Browser interaction, snapshot, click, fill, screenshot | ✅ Configured (PR #713) |

The two new servers (Storybook + Playwright) close the loop: Claude can now understand components (Storybook), interact with the running app (Playwright), and verify its own changes visually and functionally.

### Browser Automation: MCP + CLI (Both)

A nuance discovered after the initial MCP rollout: Playwright ships **two** agent-friendly tools, and they serve different purposes. Both are now installed and actively used.

| Tool | Strength | When to use |
|---|---|---|
| **Playwright MCP** (`@playwright/mcp@0.0.70`) | Loads 32+ browser tools into Claude's context as schemas; supports agentic loops (snapshot → reason → click → snapshot) | Multi-step exploration, test generation, self-healing — anywhere the agent needs to react to what it just saw |
| **`@playwright/cli`** (`0.1.6`) + named sessions | No tool schemas in context (token-efficient); persistent sessions keep cookies/auth across invocations | One-shot ops: take a screenshot, get a cookie, evaluate JS, smoke check a URL. Used by the `/screenshot` skill. |

Both ship in the same repo:
- MCP server config in [.mcp.json](.mcp.json)
- CLI as a devDep in [testing/package.json](testing/package.json), wrapped at [bin/playwright-cli](bin/playwright-cli) so any working directory in the repo can call it
- The `/screenshot` skill (in `.claude/skills/screenshot/`) uses CLI named sessions (`voya-storybook`, `voya-staging`, `voya-prod`, `voya-local`, `voya-custom`) so login state persists across screenshots

The Playwright team explicitly recommends CLI + SKILL for coding agents because of the token cost of MCP tool schemas. Voya uses both.

### Testing Pyramid

| Layer | Tool | Speed | Runs In | What It Catches |
|---|---|---|---|---|
| **Static** | ruff, mypy, bandit, eslint, tsc | Seconds | Pre-commit + CI | Syntax, types, security, style |
| **Unit** | pytest, vitest | Seconds | CI | Logic, domain rules, edge cases |
| **Component** | Storybook + Claude visual review (`/screenshot`) | Seconds | Local + CI (Cloudflare Pages preview) | Design regressions, prop issues, theme, a11y |
| **E2E (local)** | Playwright + compose.test.yaml | Minutes | Local (Docker) | Full user flows with mocks (FlightLogic, MailHog) |
| **E2E (staging)** | Playwright against staging.myvoya.ai | Minutes | Post-deploy on main | Real services, integration, deployments |
| **Exploratory** | Claude + Playwright MCP | Minutes | Local (on demand) | New feature validation, edge cases, UX issues |

### CI/CD Pipeline (Target → Mostly Achieved)

```
PR opened
  +-- CI pipeline (lint, type-check, security, unit tests)    [existing]
  +-- Claude auto-review                                       [existing]
  +-- PR labeler                                               [existing]
  +-- PR title validation                                      [existing]
  +-- Storybook build --> Cloudflare Pages preview              ✅ shipped (#685)
  +-- Code coverage PR comment                                  ✅ shipped (#700)

Merge to main
  +-- Deploy staging                                           [existing]
  +-- Post-deploy E2E against staging.myvoya.ai                 ✅ shipped (#684)

Tag push
  +-- Deploy production                                        [existing]
```

**Why no Docker E2E in CI?** Running compose.test.yaml in GH Actions requires building MongoDB, FlightLogic mock, backend, and frontend images, adding ~5-10 min to every PR. The staging post-deploy E2E provides the same integration confidence with zero CI overhead. Docker E2E in CI ([#683](https://github.com/myvoya/voya/issues/683)) is deferred to Phase 5, to be re-evaluated after staging E2E is proven.

---

## 3. Storybook: Component Layer

### Why

- 175 component files across 12 feature modules, zero documentation
- No Figma; Claude Code is the primary UI modifier
- MUI 7.1.0 with centralized theme (palette, typography, component overrides)
- Vite 6.0.4 (Storybook 10's native builder, zero config)

### How Claude Uses It

`@storybook/addon-mcp` (official, v0.5.0) runs an MCP server alongside Storybook at `http://localhost:6006/mcp`. It exposes:

- `list-all-documentation` - discover all components and their prop types
- `get-documentation` - read specific component props, examples, usage patterns
- `get-storybook-story-instructions` - understand how to write stories
- `run-story-tests` - execute interaction and a11y tests
- `preview-stories` - render stories for visual inspection

This means Claude can: understand a component's API before modifying it, generate stories for new components, and run tests against them.

### Visual Review Without Chromatic

Claude Code is multimodal. Instead of pixel-diff services:

1. Storybook renders stories (dev server or static build)
2. Claude takes screenshots via the `/screenshot` skill (uses `playwright-cli` with the `voya-storybook` named session)
3. Claude views and compares them with intent awareness

This is better than pixel-diff for agent-driven workflows: Claude understands *why* something changed ("padding increased because we added a subtitle") rather than just flagging any pixel difference. And it's free.

For CI without Claude in the loop, Playwright's `toHaveScreenshot()` provides free baseline comparison if needed later.

### `/screenshot` Skill

The `/screenshot` skill abstracts the playwright-cli invocation per environment:

| Argument | Target | Named session |
|---|---|---|
| `storybook <story-id>` | `localhost:6006/iframe.html?id=...` | `voya-storybook` |
| `staging` | `staging.myvoya.ai` | `voya-staging` |
| `prod` | `www.myvoya.ai` | `voya-prod` |
| `local` | `localhost:3002` | `voya-local` |
| `<url>` | Any URL | `voya-custom` |

Screenshots land in `.local/journal/YYYY-MM-DD/screenshots/`. Sessions persist across calls so auth state is preserved.

### Storybook Deployments via Cloudflare Pages

Three deployment tiers, all via Cloudflare Pages:

| Deployment | Trigger | URL Pattern | Purpose |
|---|---|---|---|
| **PR preview** | PR opened/updated | `pr-{N}.voya-storybook.pages.dev` | Review design changes before merge |
| **Main** | Merge to main | `main.voya-storybook.pages.dev` | Current design system, always up to date |
| **Release** | Tag push (v*.*.*) | `v2026-4-3.voya-storybook.pages.dev` | Historical reference, compare across versions |

All three deployment tiers ship in a single workflow ([#685](https://github.com/myvoya/voya/issues/685)) using one Cloudflare Pages project (`voya-storybook`) with branch-based isolation. **Cloudflare Access** restricts access to team emails via OTP, configured with a wildcard policy for `*@myvoya.ai` (excluding `roelsadza@gmail.com` and the plaintech.* contractor domain to keep contractor access scoped through Roel).

Cloudflare Pages chosen over GitHub Pages because: already using Cloudflare, automatic cleanup for PR previews, works for private repos on free plan, supports Access integration for free.

### Theme Discovery (Lesson Learned)

During Storybook setup, Foundation stories immediately revealed that the theme wasn't applying correctly. Investigation uncovered:

- Two theme files: `src/theme.ts` (production: Lato, #BFC6F4) and `src/theme/index.ts` (aspirational: Inter, #667eea)
- Components use hundreds of inline style overrides instead of theme tokens
- Chat components wrap content in their own `ThemeProvider` with a separate palette

Storybook now uses the production theme (`src/theme.ts`) to match staging. Theme unification tracked in [#707](https://github.com/myvoya/voya/issues/707). This validates the Foundation stories concept: they caught a real inconsistency on day one.

---

## 4. Playwright E2E: Application Layer

### Two Environments

| Environment | Trigger | Target | Auth | Mocks |
|---|---|---|---|---|
| **Local** | Developer / agent via docker compose | `localhost:8001` | MailHog (register on the fly) | FlightLogic mock |
| **Staging** | Post-deploy on main | `staging.myvoya.ai` | Dedicated test account ([#714](https://github.com/myvoya/voya/issues/714)) | FlightLogic test env |

Local E2E (compose.test.yaml) is for development and agent test generation. Staging E2E is the CI-level confidence layer that runs after every deploy. Docker E2E in CI is a future option ([#683](https://github.com/myvoya/voya/issues/683), Phase 5).

### How Claude Uses It

Two complementary tools, both shipped:

1. **Playwright MCP** — 32+ browser tools available as schemas, default snapshot mode uses the accessibility tree (2-5KB per snapshot, cheap and fast). Best for **multi-step agentic loops**: explore the app, react to what's on the page, generate tests.

2. **`playwright-cli`** + named sessions — token-efficient one-shots without loading tool schemas. Best for **deterministic operations**: take a screenshot, get a cookie, smoke check a URL. Sessions persist across invocations so auth state is preserved.

Claude uses these for:
- **Exploratory testing**: browse the app, understand the current UI state (MCP)
- **Test generation**: explore a feature, write a test for it (MCP)
- **Verification**: after implementing a change, navigate the app to confirm it works (MCP)
- **Visual review**: take and view screenshots (CLI via `/screenshot` skill)
- **Debugging**: when a test fails, interact with the page to understand why (MCP)

### Required Convention: `IS_STAGING` Guards

A pattern the PR #715 staging E2E rollout established as a hard requirement: **any test that touches MailHog, MongoDB directly, or other local-only services must guard those calls with `IS_STAGING`**.

```javascript
import { IS_STAGING } from '../utils/constants.js';

test.beforeEach(async ({ request }) => {
  // Initialize helpers (MailHog/DB only available on local; staging uses real services)
  if (!IS_STAGING) {
    mailhog = new MailHogHelper(request);
    dbHelper = new DatabaseHelper();
    await dbHelper.connect();
  }

  // API calls work in both environments
  const health = await request.get(URLS.BACKEND + URLS.HEALTH);
  expect(health.ok()).toBeTruthy();

  // Local-only cleanup
  if (!IS_STAGING) {
    await mailhog.clearEmails();
    await dbHelper.clearTestUsers();
  }
});
```

**Why:** `DatabaseHelper.connect()` has a 5s `serverSelectionTimeoutMS` and **rethrows** on failure. Without the guard, every `beforeEach` blocks for 5s and fails before any assertion runs, breaking entire test files in the staging E2E job. PR #715 caught this on the first staging E2E run and was fixed before merge.

If a whole test file relies on MailHog/MongoDB and can't reasonably guard, tag the file with `@mock-required` instead.

### Test Tagging

```javascript
// Tests that need mock services (skip on staging)
test('booking with mock FlightLogic', { tag: '@mock-required' }, async () => { ... });

// Tests that work everywhere
test('user can log in', async () => { ... });

// Staging-only tests
test('health check returns 200', { tag: '@staging' }, async () => { ... });
```

Config filters via `grepInvert` in `playwright.config.js`:
- `local` runs all except `@staging`
- `staging` runs all except `@mock-required`
- `dev` runs all except `@staging` and `@mock-required` (uses different ports than `compose.test.yaml`)

**Examples of `@mock-required` in the current suite (post PR #715):**
- `e2e/tests/auth/registration.spec.js`, `e2e/tests/auth/login.spec.js` — full UI registration with MailHog activation
- `e2e/tests/flights/*.spec.js` (most) — booking with mock FlightLogic
- `e2e/tests/hotels/booking-flow.spec.js` — booking with mock FlightLogic
- `api/auth.spec.js` Flow B test — uses `mailhog.waitForEmail` directly
- `api/auth.spec.js` Password Reset tests that register synthetic users — would pollute staging DB and trigger real SendGrid sends to bogus addresses
- `api/email-payment-*.spec.js`, `api/payment-security.spec.js` — email content tests

### Playwright Test Agents (v1.56+)

Three built-in agents that automate the test lifecycle:

| Agent | Input | Output | Use Case |
|---|---|---|---|
| **Planner** | App URL + optional PRD | Markdown test plans in `specs/` | Explore app, discover what to test |
| **Generator** | Test plan + seed test | Executable test files | Convert plans to running tests |
| **Healer** | Failing test name | Patched test (or skip) | Fix selector drift, timing issues |

Initialized with `npx playwright init-agents --loop=claude`. The seed test encodes Voya's conventions (fixtures, POM, constants, `IS_STAGING` guards) so generated tests match the existing style.

**Healer in CI**: Not yet. We validate the basic setup first, then enable Healer to auto-fix flaky tests in a later phase.

### Stale Tests Strategy

Pre-rollout suite: 36% pass rate (54 failures). Rather than manually fixing each broken test:

1. ✅ Fix infrastructure issues (`.env.testing` URLs, broken imports) — done in [#678](https://github.com/myvoya/voya/issues/678)
2. ✅ Keep tests that pass today (31 tests, mostly auth + API)
3. ✅ Tag broken tests so they don't block CI
4. ⏳ Use Planner/Generator to create fresh tests from the current app state (Phase 4)
5. ⏳ Retire stale tests as agents replace them

---

## 5. `@claude implement` Enhancement

The existing `@claude implement` workflow (claude-review.yml) creates branches and PRs from issues. Today it runs lint, type-check, and unit tests before creating the PR.

With the new infrastructure, the quality bar rises:

| Check | Today | Where |
|---|---|---|
| Lint + format | ✅ Yes | CI |
| Type check | ✅ Yes | CI |
| Unit tests | ✅ Yes | CI |
| Code coverage report | ✅ Yes | CI (sticky PR comment, #700) |
| Storybook build | ✅ Yes (verifies components compile) | CI (Cloudflare Pages preview, #685) |
| Storybook story | ⏳ Per task (for frontend changes, via MCP) | Agent locally |
| Visual verification | ✅ Yes (`/screenshot` skill) | Agent locally |
| E2E tests on staging | ✅ Yes (post-deploy, #684) | Staging deploy workflow |

The flow: Claude implements locally (with Storybook MCP for visual verification) → pushes PR → CI validates (lint, types, unit tests, Storybook build, coverage) → team reviews Storybook preview + auto-review → merge to main → deploy staging → post-deploy E2E catches integration issues.

---

## 6. Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Visual regression | Claude screenshots (no Chromatic) | Free, intent-aware, agent is the modifier |
| Storybook previews | Cloudflare Pages | Already using Cloudflare, free, auto-cleanup |
| Storybook preview access control | Cloudflare Access OTP, `*@myvoya.ai` wildcard | Free with Access, no SSO setup needed, scoped to team domain |
| E2E on feature branches | Local only (compose.test.yaml), not in CI | Docker stack too heavy for CI (~5-10 min); staging is the safety net |
| E2E on staging | Playwright directly (no Docker), post-deploy | Real services, real API, dedicated test account; primary E2E confidence layer |
| Docker E2E in CI | Deferred to Phase 5 | Re-evaluate after staging E2E proven and agent tests in suite |
| **Browser automation** | **Playwright MCP _and_ `@playwright/cli` (both)** | **MCP for agentic loops, CLI for token-efficient one-shots and persistent sessions; recommended by Playwright team** |
| **Local-only services in tests** | **`IS_STAGING` guards in `beforeEach`, or `@mock-required` tag for whole-file mocks** | **PR #715 caught the case where unguarded `dbHelper.connect()` blocked staging E2E for 5s and failed before any assertion** |
| Agent-generated tests | Alongside hand-written | Single suite, shared fixtures, no duplication |
| Stale tests | Tag and retire, let agents regenerate | 64% failure rate, manual fixes not worth the effort |
| Healer in CI | Deferred | Validate basic setup first |
| Storybook builder | Vite (Storybook 10 default) | Matches frontend-v2 stack, zero extra config |
| MCP snapshot mode | Accessibility tree (default) | 10-100x cheaper than vision, more stable selectors |

---

## 7. Implementation Roadmap

### Phase 1: Fix Foundation ✅ DONE

Fix the broken test infrastructure so we have a working baseline.

- ✅ Fix `.env.testing` URLs (`FRONTEND_URL`, `VITE_API_URL`)
- ✅ Fix broken imports (`public-landing-chat.spec.js`)
- ✅ Remove dead test files (empty `booking-flow.spec.js`)
- ✅ Add top-level `name: voya-test` to `compose.test.yaml`
- ✅ Update Playwright to 1.59
- ✅ Multi-environment playwright config (`TEST_ENV=local|staging|dev`)
- ✅ Environment-aware constants and auth fixtures
- ✅ Add Playwright MCP to Claude Code settings
- ✅ Add `playwright-cli` skill alongside MCP

**Shipped in:** [#697](https://github.com/myvoya/voya/pull/697) (#678), [#712](https://github.com/myvoya/voya/pull/712) (#679), [#713](https://github.com/myvoya/voya/pull/713) (#680), [#718](https://github.com/myvoya/voya/pull/718) (#717)

### Phase 2: Storybook ✅ MOSTLY DONE

Set up Storybook as the component development and documentation layer.

- ✅ Initialize Storybook 10 with Vite builder in `frontend-v2/`
- ✅ MUI theme decorator (ThemeProvider + CssBaseline)
- ✅ Redux Provider wrapper for connected components
- ✅ `@storybook/addon-mcp` for Claude Code
- ✅ Add Storybook MCP to Claude Code settings
- ✅ Foundation stories (theme, colors, buttons, typography) — caught the theme split immediately
- ✅ Layout & Marketing stories
- ⏳ Chat stories ([#703](https://github.com/myvoya/voya/issues/703))
- ⏳ Flights & Hotels stories ([#704](https://github.com/myvoya/voya/issues/704))
- ⏳ Profile, Itinerary & Shared stories ([#705](https://github.com/myvoya/voya/issues/705))
- ⏳ Theme unification ([#707](https://github.com/myvoya/voya/issues/707), tech debt)

**Shipped in:** [#691](https://github.com/myvoya/voya/pull/691) (#681), [#706](https://github.com/myvoya/voya/pull/706) (#682), [#710](https://github.com/myvoya/voya/pull/710) (#702)

### Phase 3: Staging E2E & Storybook in CI ✅ DONE

Wire post-deploy E2E and Storybook deployments into CI/CD.

- ✅ Add post-deploy E2E to `deploy-staging.yml` (Playwright against staging.myvoya.ai)
- ⏳ Create dedicated staging test account, store credentials in GitHub secrets ([#714](https://github.com/myvoya/voya/issues/714))
- ✅ Test tagging strategy (`@mock-required` skipped on staging, `@staging` included)
- ✅ Add Storybook preview deployment workflow (build + Cloudflare Pages)
- ✅ Create Cloudflare Pages project (`voya-storybook`)
- ✅ Deploy Storybook for main branch (permanent URL) and PR previews (with Cloudflare Access)
- ✅ Deploy Storybook for production releases (versioned URL)
- ✅ Code coverage as sticky PR comments

**Shipped in:** [#711](https://github.com/myvoya/voya/pull/711) (#685), [#715](https://github.com/myvoya/voya/pull/715) (#684), [#701](https://github.com/myvoya/voya/pull/701) (#700)

### Phase 4: Agent Test Generation 🟡 ACTIVE

Use Playwright agents to regenerate test coverage from the current app.

- ⏳ Resolve [#714](https://github.com/myvoya/voya/issues/714) staging test account (unblocks 6 staging E2E flight tests)
- ⏳ Initialize Playwright agents (`npx playwright init-agents --loop=claude`) — [#686](https://github.com/myvoya/voya/issues/686)
- ⏳ Create seed test encoding Voya conventions (fixtures, constants, helpers, `IS_STAGING` guard, `@mock-required` tagging) — [#686](https://github.com/myvoya/voya/issues/686)
- ⏳ Run Planner against the live app to generate test specs — [#687](https://github.com/myvoya/voya/issues/687)
- ⏳ Run Generator to convert specs to executable tests — [#687](https://github.com/myvoya/voya/issues/687)
- ⏳ Review and commit agent-generated tests
- ⏳ Tag or retire stale hand-written tests that agents have replaced
- ⏳ Target: comprehensive coverage for auth, flights, hotels, chat, profile

**Outcome**: Test suite reflects the current app state. Coverage gaps filled by agent exploration.

### Phase 5: Docker E2E in CI, Self-Healing, and Exploratory ⏸ FUTURE

Mature the testing workflow once Phases 1-4 are proven.

- **Docker E2E in CI** ([#683](https://github.com/myvoya/voya/issues/683)): Add compose.test.yaml to GH Actions for PR-level E2E validation. Re-evaluate once staging E2E is stable and the added ~5-10 min CI time is justified.
- Enable Healer in CI for self-healing selectors on flaky tests ([#688](https://github.com/myvoya/voya/issues/688))
- Exploratory testing: Planner on staging after deploys to discover new test opportunities ([#689](https://github.com/myvoya/voya/issues/689))
- FlightLogic test coverage on staging (real test environment)
- Storybook interaction tests for complex components
- Consider `toHaveScreenshot()` baselines for automated visual regression in CI

**Outcome**: Full E2E coverage at every stage. Tests maintain themselves. New features get test coverage automatically.

---

## 8. Key Metrics

| Metric | Pre-Phase-1 (Apr 9) | Phase 3 done (now) | Phase 4 target | Phase 5 target |
|---|---|---|---|---|
| E2E pass rate (local, untagged) | 36% (31/85) | ~80% (broken tests tagged) | 90%+ (agent-generated) | 95%+ (self-healing) |
| E2E specs runnable on staging | 0 | 15 (1 homepage + 8 auth API + 6 flight API) | 30+ | 50+ |
| E2E in CI | No | Staging only | Staging only | Re-evaluate (#683) |
| Storybook stories | 0 | Foundation + Layout + Marketing | + Chat, Flights, Hotels, Profile | 50+ |
| Storybook in CI | No | Yes (Cloudflare Pages, Access-gated) | Yes | Yes |
| Claude MCP servers | 3 | 5 (+ Storybook + Playwright) | 5 | 5 |
| Claude skills | 12 | 14 (+ screenshot + playwright-cli) | 14+ | 14+ |
| `@claude implement` quality | Lint + unit | + Storybook + staging E2E + visual review + coverage | + auto-generated tests | + auto-healed tests |

---

## 9. GitHub Issues

### E2E / Playwright Track

| Issue | Title | Phase | Status |
|---|---|---|---|
| [#678](https://github.com/myvoya/voya/issues/678) | Fix E2E test infrastructure | 1 | ✅ Done |
| [#679](https://github.com/myvoya/voya/issues/679) | Update Playwright 1.56+ and multi-env config | 1 | ✅ Done |
| [#680](https://github.com/myvoya/voya/issues/680) | Add Playwright MCP to Claude Code | 1 | ✅ Done |
| [#717](https://github.com/myvoya/voya/issues/717) | Add `@playwright/cli` skill alongside MCP | 1 | ✅ Done |
| [#684](https://github.com/myvoya/voya/issues/684) | Post-deploy E2E on staging | 3 | ✅ Done |
| [#714](https://github.com/myvoya/voya/issues/714) | Dedicated staging test accounts | 4 | 🟡 Open |
| [#716](https://github.com/myvoya/voya/issues/716) | Stale `public-landing-chat` test cleanup | 4 | 🟡 Open |
| [#686](https://github.com/myvoya/voya/issues/686) | Init Playwright agents + seed test | 4 | 🟡 Open |
| [#687](https://github.com/myvoya/voya/issues/687) | Generate E2E tests for core flows | 4 | ⏸ Blocked by #686 |
| [#683](https://github.com/myvoya/voya/issues/683) | Docker E2E in CI (deferred) | 5 | ⏸ Future |
| [#688](https://github.com/myvoya/voya/issues/688) | Enable Healer in CI | 5 | ⏸ Future |
| [#689](https://github.com/myvoya/voya/issues/689) | Exploratory testing on staging | 5 | ⏸ Future |

### Storybook / Design Track

| Issue | Title | Phase | Status |
|---|---|---|---|
| [#681](https://github.com/myvoya/voya/issues/681) | Initialize Storybook 10 with MUI + MCP | 2 | ✅ Done |
| [#682](https://github.com/myvoya/voya/issues/682) | Foundation stories (theme verification) | 2 | ✅ Done |
| [#702](https://github.com/myvoya/voya/issues/702) | Layout & Marketing stories | 2 | ✅ Done |
| [#703](https://github.com/myvoya/voya/issues/703) | Chat stories with mock messages | 2 | 🟡 Open |
| [#704](https://github.com/myvoya/voya/issues/704) | Flights & Hotels stories | 2 | 🟡 Open |
| [#705](https://github.com/myvoya/voya/issues/705) | Profile, Itinerary & Shared stories | 2 | 🟡 Open |
| [#685](https://github.com/myvoya/voya/issues/685) | Deploy Storybook to Cloudflare Pages | 3 | ✅ Done |

### CI / DX Improvements

| Issue | Title | Status |
|---|---|---|
| [#692](https://github.com/myvoya/voya/issues/692) | Prevent accidental @claude implement triggers | ✅ Done |
| [#700](https://github.com/myvoya/voya/issues/700) | Code coverage PR comments | ✅ Done |
| [#707](https://github.com/myvoya/voya/issues/707) | Unify MUI theme with actual design | 🟡 Open (technical debt) |
| [#709](https://github.com/myvoya/voya/issues/709) | npm audit GH Action workflow | 🟡 Open |
| [#719](https://github.com/myvoya/voya/issues/719) | Refresh DX strategy + agent-driven E2E proposal docs | 🟡 Open (this PR) |

### Parallel Execution

```
E2E Track:     #678 ✓ → #679 ✓ + #680 ✓ → #717 ✓ → #684 ✓ → #714 + #686 → #687 → #683 + #688 + #689
Storybook:     #681 ✓ → #682 ✓ → #702 ✓ + #703 + #704 + #705 → (parallel)
                                  #685 ✓ (deploy) shipped alongside
```

---

## 10. Open Questions

1. **Staging test account**: ⏳ Pending. Tracked in [#714](https://github.com/myvoya/voya/issues/714). Decision still needed: regular user with mutations enabled, or read-only health-check user? Currently 6 flight API tests fail on staging because the env vars are not yet set.

2. **Storybook scope**: ✅ Decided. Bottom-up by feature module. Foundation → Layout/Marketing → Chat → Flights/Hotels → Profile/Shared. Three story PRs in flight.

3. **Team design review**: ✅ Mostly decided. Cloudflare Pages PR previews protected by Cloudflare Access (OTP for `*@myvoya.ai`). Frequency of review still TBD with Ross/Martijn. Claude visual review remains the primary loop for now.

4. **Agent-generated test review**: ⏳ Open. Phase 4 will start with human review of every agent-generated test, then we can decide whether to relax that based on quality.

5. **Docker E2E in CI ([#683](https://github.com/myvoya/voya/issues/683))**: ⏸ Deferred. Re-evaluate after Phase 4 (agent tests in suite). Question becomes "is the ~5-10 min CI overhead justified?"

6. **`@playwright/cli` version pinning**: ✅ Decided. Pin exact (`0.1.6`, no caret) per PR #718 review feedback, since the package is pre-1.0 and the `^` semver rule accepts any `0.x.y`. Update deliberately on the next install audit.

---

## Appendix: Current Stack Reference

### Frontend
- React 18.3, TypeScript 5.7, Vite 6.0
- MUI 7.1 (Material-UI) with custom theme (production: Lato, #BFC6F4)
- Redux Toolkit 2.8 + RTK Query
- React Hook Form 7.54 + Zod 3.24
- Framer Motion 12.26
- 175 component files across 12 feature modules

### Backend
- Python 3.12, FastAPI
- MongoDB with Motor (async ODM)
- Pydantic v2
- Google Generative AI (Gemini), LangGraph
- Sentry, Langfuse, Stripe, SendGrid

### Infrastructure
- AWS ECS (Fargate), ECR, ALB
- Terraform (modules: networking, ecs, alb, ecr, iam, security, secrets, strapi, imgproxy)
- CloudFlare (CDN, DNS, caching, WAF, Pages, Access)
- GitHub Actions (CI/CD, Claude review, secrets baseline, trace review, Storybook deploy, staging deploy with E2E, prod deploy)

### Testing
- Backend: pytest + coverage (80% minimum)
- Frontend: vitest
- E2E: Playwright 1.59, multi-environment config
- Docker: compose.test.yaml (isolated test environment)
- Mock: FlightLogic mock server, MailHog (email)
- Component: Storybook 10 with MUI ThemeProvider + Redux Provider decorators

### Claude Code
- 14 custom skills (`chat`, `ci`, `cloudflare`, `commit`, `docs`, `gh`, `lint`, `logs`, `playwright-cli`, `review-prs`, `review-traces`, `screenshot`, `test`, `traces`)
- 5 MCP servers (Langfuse, GTM, Sentry, Storybook, Playwright)
- CI integration (auto-review, on-demand, implement-from-issue)
- Weekly automated trace review
- Batch PR review in parallel worktrees
- Cloudflare Access via OTP for Storybook previews
