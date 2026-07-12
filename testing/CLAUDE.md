# Voya E2E Testing - Playwright

**Context**: You are working on end-to-end tests. See root `CLAUDE.md` for project-wide information.

## Navigation
📍 **You are here**: E2E Testing (`testing/`)
🔙 **Parent**: [Root CLAUDE.md](../CLAUDE.md) - Project overview and role-based quick starts
📚 **Related docs**:
- [TESTING.md](../docs/TESTING.md) - Overall testing strategy
- [TESTING_STANDARDS.md](../backend_python/docs/TESTING_STANDARDS.md) - Unit testing patterns
- [CI_CD.md](../docs/CI_CD.md) - GitHub Actions E2E workflow

**Test Environment URLs** (when running):
- Backend serves SPA: http://localhost:8001 (isolated)
- Backend: http://localhost:8001 (isolated)
- MailHog: http://localhost:8026 (email testing)

## Quick Start
```bash
cd testing
npm install
npx playwright install --with-deps
npm run test:all
```

## Tech Stack
- **Playwright** - Cross-browser E2E testing
- **Docker Compose** - Isolated test environment
- **MailHog** - Email testing (SMTP mock)

## Project Structure
```
tests/
├── auth/             # Authentication flows
│   ├── login.spec.js
│   ├── registration.spec.js
│   └── password-reset.spec.js
├── chat/             # Chatbot interactions
│   └── chat-basic.spec.js
├── flights/          # Flight search and booking
│   ├── flight-search.spec.js
│   └── flight-booking.spec.js
├── fixtures/         # Reusable test fixtures
│   └── auth.fixture.js
├── utils/            # Helper functions
│   ├── mailhog.js    # MailHog client
│   └── test-data.js  # Test data generators
└── playwright.config.js
```

## Test Environment

### Isolated Services (Docker)
- **Backend serves SPA**: http://localhost:8001 (separate from dev)
- **Backend**: http://localhost:8001/api (separate from dev)
- **Database**: `voya_test` on port 27018 (separate from dev)
- **MailHog**: http://localhost:8026 (email testing)

### Start Test Environment
```bash
# From project root
docker compose -f compose.test.yaml up -d

# Wait for services to be healthy
docker compose -f compose.test.yaml ps

# Stop test environment
docker compose -f compose.test.yaml down -v
```

### Environment Switching

`TEST_ENV` controls which target environment tests run against:

| `TEST_ENV` | Target | Base URL | Auth | Mocks |
|---|---|---|---|---|
| `local` (default) | Docker test stack | http://localhost:8001 | MailHog (register on the fly) | FlightLogic mock |
| `staging` | Deployed staging | https://staging.myvoya.ai | Dedicated test account (env vars) | FlightLogic test env |
| `dev` | Vite dev server | http://localhost:3002 | MailHog | FlightLogic mock |

```bash
# Local Docker stack (default)
npm run test:all

# Against staging
TEST_ENV=staging npm run test:staging
# Requires: STAGING_TEST_USER_EMAIL, STAGING_TEST_USER_PASSWORD env vars

# Against Vite dev server
npm run test:dev
```

### Test Tagging

Tests can be tagged to run only in certain environments:

```javascript
// Skip on staging (requires MailHog or mock APIs)
test('booking with mock FlightLogic', { tag: '@mock-required' }, async () => { ... });

// Only run on staging
test('health check returns 200', { tag: '@staging' }, async () => { ... });
```

The Playwright config automatically filters via `grepInvert`:
- `local` runs all except `@staging`
- `staging` runs all except `@mock-required`

## Critical Testing Patterns

### Page Objects (`testing/e2e/pages/`)

Voya's Page Object layer is the source of truth for every UI surface a spec touches. Agents and humans alike should read it **before** exploring the DOM.

**What a Page Object owns:**
- Every stable selector for the surface (getters that return Playwright `Locator`s).
- Flow primitives (`submitEmail(email)`, `submitLoginPassword(password)`) that fill + click + wait for the matching response in one call, returning the `Response` so specs can assert status.
- `expect*` helpers for common step-transition assertions (`expectEmailStep`, `expectLoginStep`, `expectDialogClosed`).
- Known UI quirks documented inline at the top of the file (see plan Appendix B pointers in `testing/specs/*.md`).

**Current Page Objects:**
- `testing/e2e/pages/AuthModalPage.js` — `AuthModal.tsx`. Covers email / registration / login / post-success steps plus the landing-page CTA.

**Why this matters for agent-generated tests:**
- Planner + Generator re-derive page structure on every run. Page Objects encode that knowledge once so the cost is paid once. Before a planner snapshots the DOM or a generator verifies a selector live, it should first `Read testing/e2e/pages/` to see what's already known.
- When a UI change breaks tests, the fix lives in one file, not spread across every spec.

**Shape of a Page Object** (see `AuthModalPage.js` for the full example):

```javascript
import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { openAuthModal } from '../../helpers/auth-helpers.js';
import { navigateToApp } from '../../helpers/navigation-helpers.js';

export class AuthModalPage {
  constructor(page) { this.page = page; }

  // Entry
  async navigate() { await navigateToApp(this.page); }
  async openModal() {
    await openAuthModal(this.page);
    await expect(this.dialog).toBeVisible({ timeout: TIMEOUTS.MODAL_APPEAR });
  }

  // Container + selectors as getters
  get dialog() { return this.page.getByRole('dialog'); }
  get emailField() { return this.dialog.getByLabel('Email Address'); }
  get continueButton() { return this.dialog.getByRole('button', { name: 'Continue' }); }

  // Flow primitives: fill + click + await API + return Response
  async submitEmail(email) {
    await this.emailField.fill(email);
    const [res] = await Promise.all([
      this.page.waitForResponse(r => r.url().includes('/auth/check-email') && r.request().method() === 'POST'),
      this.continueButton.click(),
    ]);
    return res;
  }

  // expect* helpers wrap step-transition assertions
  async expectEmailStep() {
    await expect(this.dialog).toBeVisible();
    await expect(this.emailField).toBeVisible();
    await expect(this.continueButton).toBeEnabled();
  }
}
```

**Shape of a spec using a Page Object:**

```javascript
import { test, expect } from '../../../fixtures/auth-fixtures.js';
import { AuthModalPage } from '../../pages/AuthModalPage.js';

test('should route a new email to the registration step', { tag: '@mock-required' }, async ({ page }) => {
  const auth = new AuthModalPage(page);
  await auth.open();

  const res = await auth.submitEmail('new-user@example.com');
  expect(res.status()).toBe(200);

  await auth.expectRegistrationStep('new-user@example.com');
});
```

**Adding a new Page Object:**
1. Create `testing/e2e/pages/<Surface>Page.js` — start with the selectors already hand-rolled in existing specs for that surface.
2. Refactor existing specs to consume it; each spec should drop to ~15 lines of intent.
3. Document quirks (e.g. "this input is disabled after step 2", "redirects to `/` not `/login`") inline at the top.
4. If multiple Page Objects share selectors (e.g. the site nav), extract to `testing/e2e/selectors/<feature>.js` — single source of truth for that constant.

### Fixtures for Common Setup
```javascript
// ✅ Use fixtures for authentication
import { test as base } from '@playwright/test';

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // Log in before test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'Test123!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/);

    await use(page);

    // Cleanup after test
    await page.context().clearCookies();
  },
});

// Usage
test('view profile', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/profile');
  // Test authenticated features
});
```

### Email Testing with MailHog
```javascript
// ✅ Use MailHog client to verify emails
import { MailHogClient } from '../utils/mailhog';

const mailhog = new MailHogClient('http://localhost:8026');

test('password reset sends email', async ({ page }) => {
  // Clear previous emails
  await mailhog.deleteAll();

  // Request password reset
  await page.goto('/forgot-password');
  await page.fill('input[name="email"]', 'test@example.com');
  await page.click('button[type="submit"]');

  // Wait for email
  await page.waitForTimeout(2000);

  // Verify email received
  const messages = await mailhog.getMessages();
  expect(messages.length).toBe(1);
  expect(messages[0].to).toContain('test@example.com');

  // Extract reset link from email
  const resetLink = await mailhog.extractLink(messages[0]);
  await page.goto(resetLink);

  // Complete password reset
  await page.fill('input[name="password"]', 'NewPassword123!');
  await page.click('button[type="submit"]');
});
```

### Database Cleanup
```javascript
// ✅ Clean up test data after tests
import { test } from '@playwright/test';

test.afterEach(async ({ page }) => {
  // Test environment uses separate database (voya_test)
  // Docker compose down -v removes all test data
});

// For specific cleanup during tests
async function cleanupTestUser(email) {
  // Use API or direct database connection
  await fetch('http://localhost:8001/api/test/cleanup', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}
```

### Cross-Browser Testing
```javascript
// playwright.config.js
export default {
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
};

// Run specific browser
// npm run test -- --project=firefox
```

## Development Commands

### Run Tests
```bash
# All tests
npm run test:all

# Specific test file
npm test tests/auth/login.spec.js

# With browser UI (headed mode)
npm test -- --headed

# Debug mode (pause on failure)
npm test -- --debug

# Specific browser
npm test -- --project=chromium
npm test -- --project=firefox
```

### View Reports
```bash
# Generate and view HTML report
npm run test:report

# Report available at http://localhost:9323
```

### Screenshots & Videos
- **Automatic Capture**: On test failure
- **Location**: `test-results/`
- **Screenshots**: `test-results/*/test-failed-*.png`
- **Videos**: `test-results/*/video.webm`

### Update Snapshots
```bash
# Update visual snapshots
npm test -- --update-snapshots
```

## Test Categories

### Authentication Tests
- **Registration**: New user signup with email verification
- **Login**: Email/password and Google OAuth
- **Password Reset**: Email-based password recovery
- **Protected Routes**: Redirect to login if not authenticated

### Chat Tests
- **Welcome Message**: Display on chat open
- **AI Conversation**: Send messages and receive responses
- **Intent Recognition**: Booking intent with context
- **History**: Load previous conversations

### Flight Tests
- **Search**: Origin, destination, date inputs
- **Results Display**: Show flight options
- **Booking Flow**: Select flight and complete booking
- **Validation**: Error handling for invalid inputs

### User Profile Tests
- **View Profile**: Display user information
- **Edit Profile**: Update name, email, preferences
- **Settings**: Update notification preferences

## Best Practices

### Wait for Elements
```javascript
// ✅ Wait for elements to be visible
await page.waitForSelector('text=Search Results', { state: 'visible' });

// ✅ Wait for API responses
await page.waitForResponse(response =>
  response.url().includes('/api/flights/search') && response.status() === 200
);

// ✅ Use built-in auto-waiting
await page.click('button'); // Playwright waits for element automatically
```

### Assertions
```javascript
import { expect } from '@playwright/test';

// ✅ Use Playwright assertions (auto-retry)
await expect(page.locator('h1')).toHaveText('Dashboard');
await expect(page).toHaveURL(/\/dashboard/);

// ✅ Check element visibility
await expect(page.locator('.error-message')).toBeVisible();

// ✅ Check element count
await expect(page.locator('.flight-card')).toHaveCount(3);
```

### Test Isolation
```javascript
// ✅ Each test is independent
test('test 1', async ({ page }) => {
  // Clean state, runs in isolation
});

test('test 2', async ({ page }) => {
  // Doesn't depend on test 1
});

// ❌ Don't share state between tests
let sharedState; // BAD - tests should be isolated
```

### Debugging Tips
```javascript
// ✅ Pause execution to inspect
await page.pause();

// ✅ Take screenshot for debugging
await page.screenshot({ path: 'debug.png' });

// ✅ Print page content
console.log(await page.content());

// ✅ Slow down actions for visibility
await page.click('button', { delay: 100 });
```

## CI/CD Integration

### GitHub Actions
Tests run automatically in CI/CD pipeline (`.github/workflows/ci.yml`):
```yaml
test-e2e:
  name: Playwright E2E Tests
  runs-on: ubuntu-latest
  steps:
    - name: Start Test Environment
      run: docker compose -f compose.test.yaml up -d
    - name: Run Playwright Tests
      working-directory: testing
      run: npm run test:all
    - name: Upload Test Report
      uses: actions/upload-artifact@v4
      with:
        name: playwright-report
        path: testing/playwright-report/
```

### Test Reports in CI
- HTML report uploaded as artifact
- Screenshots and videos available for failed tests
- Retention: 30 days

## Common Issues

### Issue: Services Not Ready
**Solution**: Add health checks before running tests
```bash
# Wait for backend health (backend serves SPA at 8001 in test env)
timeout 120 bash -c 'until curl -f http://localhost:8001/health; do sleep 2; done'
```

### Issue: Database Conflicts
**Solution**: Use isolated test database (`voya_test` on port 27018)
```yaml
# compose.test.yaml
services:
  mongodb-test:
    image: mongo:7.0
    environment:
      - MONGO_INITDB_DATABASE=voya_test
    ports:
      - "27018:27017"
```

### Issue: Flaky Tests
**Causes**:
- Network delays
- Race conditions
- Shared state between tests

**Solutions**:
- Use Playwright auto-waiting (built-in retries)
- Add explicit waits for API responses
- Ensure test isolation
- Use stable selectors (data-testid)

### Issue: Email Not Received
**Solution**: Check MailHog logs and add delay
```javascript
// Wait for email to arrive
await page.waitForTimeout(2000);

// Check MailHog is running
const mailhogHealth = await fetch('http://localhost:8026/api/v2/messages');
console.log('MailHog status:', mailhogHealth.status);
```

## Browser Automation: CLI vs MCP

Claude Code has **two complementary tools** for browser automation:

| Tool | Best for | Token cost | State |
|---|---|---|---|
| [`playwright-cli`](https://github.com/microsoft/playwright-cli) skill | One-off ops, debugging, smoke tests, screenshots | Low (no schema loaded) | Persistent via named sessions |
| [`@playwright/mcp`](https://github.com/microsoft/playwright-mcp) | Test generation, exploratory loops, self-healing | High (loads schema + snapshots into context) | Persistent in same session |

**When to use which** (per Playwright team's official guidance):

- **CLI**: token-efficient, agent reads `playwright-cli --help` once. Best for high-throughput coding agents that balance browser automation with large codebases.
- **MCP**: relevant for "specialized agentic loops that benefit from persistent state, rich introspection, and iterative reasoning over page structure, such as exploratory automation, self-healing tests, or long-running autonomous workflows."

For Voya specifically:
- One-off screenshots, debugging failing tests, smoke tests → **CLI** (use the `screenshot` or `playwright-cli` skill)
- Test generation (#686, #687), self-healing (#688), exploratory testing (#689) → **MCP**

## Playwright CLI Skill

The `playwright-cli` skill at `.claude/skills/playwright-cli/` exposes [`@playwright/cli`](https://github.com/microsoft/playwright-cli) to Claude Code. It's installed as a devDep in `testing/` and accessed via `./bin/playwright-cli` (a thin wrapper).

### Setup (one-time)

The CLI is installed via `npm ci` in `testing/`. Browsers must be downloaded:

```bash
./bin/playwright-cli install-browser chromium
```

### Usage

```bash
# Open a session (named, persistent across invocations)
./bin/playwright-cli -s=voya-staging open https://staging.myvoya.ai

# Navigate, take snapshot, screenshot, interact
./bin/playwright-cli -s=voya-staging snapshot
./bin/playwright-cli -s=voya-staging screenshot --filename=staging.png
./bin/playwright-cli -s=voya-staging click e15

# Manage sessions
./bin/playwright-cli list
./bin/playwright-cli close-all
./bin/playwright-cli show  # visual dashboard with live previews
```

The skill includes 9 reference docs covering test generation, request mocking, tracing, video recording, sessions, storage state, etc. See `.claude/skills/playwright-cli/references/`.

## Playwright MCP Server (for Claude Code)

Claude Code also has the [Playwright MCP server](https://github.com/microsoft/playwright-mcp) configured in `.mcp.json`. It exposes 32+ browser control tools to Claude Code (navigate, click, type, verify elements, take screenshots, generate locators).

**Snapshot mode** (default): uses the accessibility tree (~2-5KB per snapshot, cheap and stable). Handles ~95% of web automation. The `--caps testing` flag enables additional verification tools (`browser_verify_element_visible`, `browser_verify_text_visible`, `browser_generate_locator`).

### When to Use Playwright MCP (vs the CLI)

- **Test generation pipelines**: Planner/Generator/Healer loops where the agent needs continuous browser context
- **Self-healing**: long-running autonomous workflows that diagnose and patch failing tests
- **Exploratory automation**: deep iterative reasoning over DOM structure

### Configuration

Already in `.mcp.json`:

```json
{
  "playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@0.0.70", "--caps", "testing"]
  }
}
```

The MCP server starts on demand when Claude Code uses a `browser_*` tool.

**One-time setup**: Playwright browsers must be installed locally. From `testing/`:

```bash
npx playwright install chromium --with-deps
```

You only need to do this once (or after a Playwright upgrade). The MCP server uses the same browsers as the test suite.

### Example: Exploratory Testing

When investigating a UI bug, ask Claude Code to:
1. `browser_navigate` to the page
2. `browser_snapshot` to see the accessibility tree
3. `browser_click` on elements to interact
4. `browser_take_screenshot` for visual verification
5. Synthesize findings into a test case

This is the agent equivalent of running `npm test -- --debug` interactively.

## Playwright Test Agents (Planner / Generator / Healer)

In addition to the general-purpose Playwright MCP, the project has the **Playwright test-runner MCP** wired up
specifically for the agent test generation pipeline. Three specialized agents drive it:

| Agent | Role | Output |
|---|---|---|
| `playwright-test-planner` | Explore an app via the browser, design test scenarios | Markdown plan in `testing/specs/<feature>.plan.md` |
| `playwright-test-generator` | Convert plan items into runnable Playwright tests | New `.spec.js` files under `testing/e2e/tests/<feature>/` |
| `playwright-test-healer` | Run the suite and fix failing tests by patching selectors/timings | Edits to existing `.spec.js` files |

All three live in [`.claude/agents/`](../.claude/agents/) at the repo root and reference the seed test
[`testing/seed.spec.js`](seed.spec.js) for Voya conventions (JS not TS, fixtures import, IS_STAGING guards,
@mock-required tagging, SELECTORS/TIMEOUTS constants, helpers). The Generator reads the seed for style; it does
not execute it.

### Triggering an agent

Slash-command-style prompts live in [`.claude/prompts/`](../.claude/prompts/):

| Prompt | What it does |
|---|---|
| `/playwright-test-plan` | Plan a feature with the planner |
| `/playwright-test-generate` | Generate tests for a single plan item |
| `/playwright-test-coverage` | Full pipeline: plan → generate → heal (default agent orchestrates) |
| `/playwright-test-heal` | Run the suite, fix failing tests |

These are starting points. Edit them to point at the feature you're working on (the templates default to the
authentication flow as an example).

### MCP server

The agents need a separate MCP server (`playwright-test`) from the general Playwright MCP because it exposes
test-runner-specific tools (`test_run`, `test_debug`, `generator_setup_page`, `planner_save_plan`, etc.). It's
configured at the repo root in `.mcp.json`:

```json
{
  "playwright-test": {
    "command": "./bin/playwright-test-mcp",
    "args": []
  }
}
```

The wrapper script [`bin/playwright-test-mcp`](../bin/playwright-test-mcp) handles `cd testing` so the server
finds `testing/playwright.config.js` and `testing/node_modules/`. Without the wrapper, the server would try to
discover the Playwright project from whatever directory Claude Code happened to launch from.

### Convention reference: `seed.spec.js`

[`testing/seed.spec.js`](seed.spec.js) is the canonical example of how Voya tests should be structured. It contains
three tests demonstrating:

1. **Smoke test** that runs in BOTH local and staging (homepage hero CTA assertion using `getByRole`)
2. **Auth modal flow** tagged `@mock-required` (uses MailHog locally, skipped on staging)
3. **Authenticated API request** using the staging-aware `authenticatedUser` fixture (works in both environments)

The seed runs as part of the normal `npm test` suite — if conventions break, the seed breaks first.

To run only the seed:

```bash
npx playwright test seed.spec.js
TEST_ENV=staging STAGING_TEST_USER_EMAIL=... STAGING_TEST_USER_PASSWORD=... npx playwright test seed.spec.js
```

## Playwright Screenshots

Use Playwright CLI to take screenshots of any environment. Useful for visual review, debugging, and comparing Storybook vs live app.

### Quick Commands

```bash
# Storybook story (iframe URL, no Storybook chrome)
npx playwright screenshot --wait-for-timeout 2000 --full-page --viewport-size 800,1200 \
  "http://localhost:6006/iframe.html?id=foundation-buttons--default&viewMode=story" \
  screenshot.png

# Staging homepage
npx playwright screenshot --wait-for-timeout 3000 --viewport-size 1280,900 \
  "https://staging.myvoya.ai" \
  screenshot.png

# Production homepage
npx playwright screenshot --wait-for-timeout 3000 --viewport-size 1280,900 \
  "https://www.myvoya.ai" \
  screenshot.png

# Local dev
npx playwright screenshot --wait-for-timeout 2000 --viewport-size 1280,900 \
  "http://localhost:3002" \
  screenshot.png

# Full page (scrolls to capture everything)
npx playwright screenshot --wait-for-timeout 3000 --full-page \
  "https://staging.myvoya.ai" \
  full-page.png
```

### Storybook Story IDs

Story IDs follow the pattern: `title-lowered--story-name`

| Story Title | Story ID |
|---|---|
| `Foundation/Colors` | `foundation-colors--default` |
| `Foundation/Buttons` | `foundation-buttons--default` |
| `Flights/FlightCard` | `flights-flightcard--default` |
| `Chat/ChatMessage` | `chat-chatmessage--default` |

### Useful Flags

| Flag | Purpose |
|---|---|
| `--wait-for-timeout 3000` | Wait for page to load (ms) |
| `--full-page` | Capture entire scrollable area |
| `--viewport-size 1280,900` | Set browser viewport |

### Advanced: Interactive Screenshots with Playwright Script

For more control (click buttons, fill forms, navigate), use a Node script:

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  await page.goto('https://staging.myvoya.ai');
  await page.waitForTimeout(2000);

  // Click Log in (header CTA) to open modal
  await page.locator('text=Log in').first().click();
  await page.waitForTimeout(1000);

  await page.screenshot({ path: 'login-modal.png' });

  // Check computed styles
  const styles = await page.evaluate(() => {
    const btn = document.querySelector('.MuiButton-containedPrimary');
    const cs = getComputedStyle(btn);
    return { bgColor: cs.backgroundColor, borderRadius: cs.borderRadius };
  });
  console.log(styles);

  await browser.close();
})();
```

### Screenshot Storage Convention

Store screenshots in `.local/journal/YYYY-MM-DD/screenshots/`:

```bash
mkdir -p .local/journal/$(date +%Y-%m-%d)/screenshots
npx playwright screenshot --wait-for-timeout 2000 \
  "http://localhost:6006/iframe.html?id=foundation-colors--default&viewMode=story" \
  .local/journal/$(date +%Y-%m-%d)/screenshots/storybook-colors.png
```

## Documentation

### E2E Testing Guide
See `docs/TESTING.md` for:
- Writing effective E2E tests
- Test data management
- Performance testing
- Debugging strategies

### Backend Testing
See `backend_python/docs/TESTING_STANDARDS.md` for unit/integration testing patterns.

### CI/CD Pipeline
See `docs/CI_CD.md` for GitHub Actions workflow details.

### Pre-commit Hooks
See root `CLAUDE.md` for pre-commit hook configuration (project-wide).

---

**Last Updated**: April 2026
**Questions**: Create GitHub issue with label `testing`
