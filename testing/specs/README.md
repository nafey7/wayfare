# Test plans (specs)

This directory holds Markdown test plans produced by the `playwright-test-planner` agent.

Each plan is a structured list of scenarios that the `playwright-test-generator` agent reads and converts into
runnable Playwright test files under `e2e/tests/<feature>/`.

## Convention

```
testing/specs/
├── README.md
├── auth.plan.md          ← Authentication flow scenarios
├── flights.plan.md       ← Flight search/booking scenarios
├── hotels.plan.md        ← Hotel search/booking scenarios
└── chat.plan.md          ← Chat conversation scenarios
```

## Workflow

1. **Plan**: Run the planner via `/playwright-test-plan` (or directly invoke the
   `playwright-test-planner` agent). It explores the live app and writes a plan here.
2. **Generate**: Run the generator via `/playwright-test-generate`. It reads a plan
   item and writes a corresponding `.spec.js` file under `e2e/tests/<feature>/`.
3. **Heal**: Run the healer via `/playwright-test-heal`. It runs the suite and patches
   failures (selector drift, timing).

The full pipeline is `/playwright-test-coverage <feature-name>`.

## Seed reference

The seed test at [`testing/seed.spec.js`](../seed.spec.js) demonstrates the conventions every generated test must
follow: JS not TS, imports from `fixtures/auth-fixtures.js`, SELECTORS/TIMEOUTS from constants, IS_STAGING guards
for local-only services, `@mock-required` tag when MailHog is needed.
