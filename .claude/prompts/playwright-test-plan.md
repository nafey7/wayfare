---
agent: playwright-test-planner
description: Create a Playwright test plan for a Voya feature
---

<!--
TEMPLATE: Replace `authentication flow` and `auth.plan.md` with the feature you're planning. Common targets:
flights, hotels, chat, profile, itinerary. The base URL stays as localhost:8001 for the local Docker test stack
unless you're explicitly planning against staging.
-->

Create a test plan for the **authentication flow** (email check, registration with MailHog, login, password reset)
of the Voya app at `http://localhost:8001`.

- Seed file: `testing/seed.spec.js`
- Test plan: `testing/specs/auth.plan.md`

Note: tests that require MailHog (registration activation, password reset email) should be tagged `@mock-required`
in the plan so they're skipped on staging.
