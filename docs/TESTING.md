# Testing Guide

Comprehensive testing strategy for the Voya travel platform.

## Test Frameworks

### Backend (Python)
- **Pytest** with pytest-asyncio for async testing
- **Coverage**: Minimum 80% for new code, 100% for critical paths
- **Test Markers**: unit, integration, critical, slow

### Frontend (React)
- **Vitest** and React Testing Library
- Component and integration tests
- Snapshot testing for UI consistency

### End-to-End (Playwright)
- **Location**: `/testing` directory
- **Framework**: Playwright with cross-browser support (Chrome, Firefox)
- **Coverage**: Authentication flows, user journeys, API integration, diagnostics
- **Pass Rate**: 85%+

## Quick Commands

### Backend Tests
```bash
cd backend_python
pytest tests/unit_tests/ -v --cov=app --cov-report=term-missing
```

### Frontend Tests
```bash
cd frontend-v2
npm run test
```

### E2E Tests
```bash
cd testing

# Run all tests
npm run test:all

# Specific suites
npm run test:auth        # Authentication tests
npm run test:login       # Login flow tests
npm run test:diagnostics # System diagnostics
npm run test:e2e         # End-to-end tests
```

## Test Environment (E2E)

### Starting Test Environment
```bash
# Start isolated test environment
docker compose -f compose.test.yaml up -d

# Wait for services
sleep 30

# Run tests
cd testing
npm run test:all

# Cleanup
docker compose -f ../compose.test.yaml down -v
```

### Test Environment Features
- **Database Isolation**: Separate `voya_test` database
- **Service Isolation**: Dedicated test ports (8001/27018/8026)
- **Email Testing**: MailHog integration
- **Auto Cleanup**: Database cleanup between test runs

## Test Reports & Debugging

### Playwright Reports
- **HTML Reports**: `http://localhost:9323`
- **Screenshots**: `testing/test-results/*/test-failed-*.png`
- **Videos**: `testing/test-results/*/video.webm`
- **Traces**: `testing/test-results/*/trace.zip`

### View Reports
```bash
cd testing
npm run test:report      # Opens http://localhost:9323
npm run test:run-and-show # Run tests and view report
```

### Debug Mode
```bash
cd testing
npm run test:headed      # See browser during test
npm run test:ui          # Interactive UI mode
npm run test:debug       # Step-by-step debugging
```

## Coverage Requirements

### Minimum Standards
- **All Code**: 80% coverage minimum
- **Critical Paths**: 100% coverage required:
  - Authentication/authorization
  - Payment processing
  - Data validation
  - Security-critical code
  - Error handling

### Generate Coverage Reports
```bash
# Backend HTML report
cd backend_python
pytest tests/unit_tests/ --cov=app --cov-report=html
# Open: backend_python/htmlcov/index.html

# Frontend coverage
cd frontend-v2
npm run test:coverage
# Open: frontend-v2/coverage/lcov-report/index.html
```

## Test Categories (Python Markers)

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # Tests with real dependencies
@pytest.mark.e2e           # End-to-end user flows
@pytest.mark.critical      # Must pass for deployment
@pytest.mark.slow          # Long-running tests (> 1s)
@pytest.mark.flaky         # Known intermittent failures
```

### Run by Marker
```bash
pytest -m critical -v       # Critical tests only
pytest -m "not slow" -v     # Skip slow tests
pytest -m asyncio -v        # Async tests
```

## CI/CD Integration

The CI pipeline runs tests automatically:
1. **Backend Tests**: pytest with coverage (80% minimum)
2. **Admin Tests**: Jest/React Testing Library
3. **E2E Tests**: Full Playwright suite (after build succeeds)

See `docs/CI_CD.md` for full CI configuration.

## Best Practices

### Unit Testing
- Mock external services (never call real APIs)
- Use pytest fixtures for setup/teardown
- Test edge cases (None, empty, boundary conditions)
- Include descriptive test names

### Integration Testing
- Use test containers for real databases
- Test full flows (search → book → pay → confirm)
- Verify side effects (emails, logs, events)
- Test transaction rollback on failure

### E2E Testing
- Test critical user journeys
- Include error scenarios
- Check accessibility
- Verify mobile responsiveness

### Test Maintenance
- Keep tests as clean as production code
- Remove obsolete tests
- Update tests with code changes
- Monitor test execution time
