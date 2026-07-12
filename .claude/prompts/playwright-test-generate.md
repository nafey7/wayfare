---
agent: playwright-test-generator
description: Generate a Voya test from a test plan item
---

<!--
TEMPLATE: Replace `auth` below with the feature you're working on (flights, hotels, chat, profile, etc.).
The plan path, output directory, and scenario name should all reference your target feature, not the
authentication-flow placeholders shown here.
-->

Generate a test for the test plan's first scenario (e.g. "1.1 Sign in with valid credentials").

- Test plan: `testing/specs/auth.plan.md`
- Output directory: `testing/e2e/tests/auth/`
- Seed file: `testing/seed.spec.js`

Follow the Voya conventions documented in `.claude/agents/playwright-test-generator.md` and `testing/seed.spec.js`:
JS not TS, imports from `fixtures/auth-fixtures.js`, SELECTORS/TIMEOUTS from constants, helpers for navigation/auth,
`@mock-required` tag for MailHog-dependent tests.
