---
name: test:unit
description: Run unit tests for backend (pytest) and frontend (vitest). Use when user asks to run unit tests or fast tests only.
allowed-tools: Bash(pytest:*), Bash(npm test:*), Bash(npm run test:*)
argument-hint: [backend|frontend|all]
---

# Run Unit Tests

@docs/TESTING.md

Execute unit tests for $ARGUMENTS

## Backend Unit Tests (Python)

```bash
cd backend_python
pytest tests/unit_tests/ -v --cov=app --cov-report=term-missing
```

### Fast tests only (skip slow)
```bash
cd backend_python
pytest tests/unit_tests/ -m "not slow" -v
```

## Frontend Unit Tests (Vite/Vitest)

```bash
cd frontend-v2
npm run test
```

## Coverage Reports

### Backend HTML Report
```bash
cd backend_python
pytest tests/unit_tests/ --cov=app --cov-report=html
# Open: backend_python/htmlcov/index.html
```

### Frontend Coverage
```bash
cd frontend-v2
npm run test:coverage
# Open: frontend-v2/coverage/lcov-report/index.html
```
