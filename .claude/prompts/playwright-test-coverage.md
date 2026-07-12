---
agent: default
description: Produce Playwright test coverage for a Voya feature (plan → generate → heal)
---

Parameters:
- Task: the feature/flow to cover (e.g. "authentication flow", "flight search and booking")
- Seed file (optional): defaults to `testing/seed.spec.js`
- Test plan file (optional): defaults to `testing/specs/<feature>.plan.md`

1. Call #playwright-test-planner subagent with prompt:

<plan>
  <task-text><!-- the task --></task-text>
  <seed-file>testing/seed.spec.js</seed-file>
  <plan-file>testing/specs/<feature>.plan.md</plan-file>
</plan>

2. For each test case from the test plan file (1.1, 1.2, ...), one after another, not in parallel, call #playwright-test-generator subagent with prompt:

<generate>
  <test-suite><!-- Verbatim name of the test spec group w/o ordinal like "Authentication" --></test-suite>
  <test-name><!-- Name of the test case without the ordinal like "should sign in with valid credentials" --></test-name>
  <test-file><!-- Name of the file to save the test into, like testing/e2e/tests/auth/should-sign-in-with-valid-credentials.spec.js --></test-file>
  <seed-file>testing/seed.spec.js</seed-file>
  <body><!-- Test case content including steps and expectations --></body>
</generate>

3. Call #playwright-test-healer subagent with prompt:

<heal>Run all tests and fix the failing ones one after another. Do not modify tests that are passing. Do not mark tests as test.fixme() for known backend bugs (add a code comment linking the issue instead).</heal>
