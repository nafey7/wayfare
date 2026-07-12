---
name: test
description: Run test suites for the project (backend pytest, frontend vitest, E2E playwright). Use when user asks to run tests or check test results.
allowed-tools: Bash(pytest:*), Bash(npm test:*), Bash(npm run test:*), Bash(npx playwright:*), Read
argument-hint: [backend|frontend|e2e|all]
---

# Run Tests

@docs/TESTING.md

Execute test suites for the Voya travel platform: $ARGUMENTS

## Quick Test Commands

### Backend (Python)
```bash
cd backend_python
pytest tests/unit_tests/ -v --cov=app --cov-report=term-missing
```

### Frontend (Vite/Vitest)
```bash
cd frontend-v2
npm run test
```

### E2E (Playwright)
```bash
cd testing
npm run test:all
```

## Specialized Commands

For more specific test scenarios:
- `/test:unit` - Run only unit tests
- `/test:e2e` - Run only E2E tests with Docker environment
- `/test:coverage` - Generate full coverage reports
