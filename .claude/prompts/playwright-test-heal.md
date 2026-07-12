---
agent: playwright-test-healer
description: Run the Voya test suite and fix failing tests
---

Run the Voya Playwright suite and patch failing tests one at a time. Specifically:

- **Scope**: Run `testing/e2e/` and `testing/api/` (both directories). The seed test
  `testing/seed.spec.js` is also part of the suite — if it fails, fix it last (it's
  the reference for conventions, so other failures may be caused by the same root issue).
- **Do not modify tests that were already passing**. Healing means fixing genuine
  failures, not "improving" green tests.
- **Do not silence known bugs.** If a failure looks like it matches an open issue
  (e.g. the logout 401 vs 403 mismatch is tracked in #721), do NOT mark the test as
  `test.fixme()` or rewrite the assertion. Add a code comment linking the issue and
  leave the failure visible. The healer's job is to fix selector drift, timing issues,
  and stale assertions caused by UI changes — not to paper over backend bugs.
- **Conventions**: Any patches must follow the conventions in `testing/seed.spec.js`
  (imports from `fixtures/auth-fixtures.js`, SELECTORS/TIMEOUTS constants, helpers
  for navigation/auth, `IS_STAGING` guard for MailHog/MongoDB code).
- **Environment**: Run with `TEST_ENV=local` against the Docker test stack
  (`compose.test.yaml`). If the user is running against staging, `@mock-required`
  tests will already be skipped and should not be touched.

After all healing is complete, report:
- Which tests were patched and what changed
- Any failures left untouched and why (e.g. linked to open issue)
