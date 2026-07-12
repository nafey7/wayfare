# Voya Testing Suite

**Test Environment**: Fully isolated from development (separate ports, database, and services)

## Quick Start

```bash
cd testing
npm install
npx playwright install --with-deps

# Start isolated test environment (separate from dev)
docker compose -f ../compose.test.yaml up -d

# Run all automated tests
npm test

# View HTML report
npm run test:report  # Opens at http://localhost:9323
```

## Test Structure

```
testing/
├── api/                      # API-level tests (using request fixtures)
│   ├── auth.spec.js          ✅ 19 tests - Complete auth flow
│   └── flights.spec.js       ⚠️  9 tests - Flight booking API (6/9 passing)
│
├── e2e/                      # End-to-end browser tests
│   └── tests/
│       ├── auth/
│       │   ├── login.spec.js           ✅ Login flows
│       │   └── registration.spec.js    ✅ Registration + email verification
│       └── flights/
│           └── booking-flow.spec.js    ✅ Complete flight booking journey
│
├── manual-tests/             # Manual diagnostic tests (NOT in CI)
│   ├── README.md             📖 Purpose and usage guide
│   ├── chat.spec.js          🔍 AI integration debugging
│   ├── mockdata.spec.js      🔍 Mock data identification
│   ├── profile.spec.js       🔍 Profile display issues
│   ├── settings.spec.js      🔍 Settings functionality
│   ├── trips.spec.js         🔍 Trip management
│   └── navigation.spec.js    🔍 Navigation debugging
│
├── fixtures/                 # Reusable test fixtures
│   ├── auth-fixtures.js      # authenticatedUser, registeredUser, etc.
│   └── test-fixtures.js
│
├── utils/                    # Test utilities
│   ├── database-helper.js    # MongoDB cleanup
│   ├── mailhog-client.js     # Email testing
│   └── constants.js          # URLs, selectors, timeouts
│
└── setup/                    # Global setup/teardown
    ├── global-setup.js       # Database initialization
    └── global-teardown.js    # Cleanup after all tests
```

## Test Commands

### Primary Commands (Happy Flows)
```bash
npm test              # All automated tests (api/ + e2e/)
npm run test:api      # API tests only
npm run test:e2e      # E2E tests only
npm run test:auth     # All auth tests (API + E2E)
npm run test:flights  # All flight tests (API + E2E)
```

### Manual/Debugging Commands
```bash
npm run test:manual   # Run manual diagnostic tests
npm run test:headed   # Run with browser visible
npm run test:debug    # Debug mode (pause on failure)
npm run test:ui       # Interactive UI mode
```

### Reports
```bash
npm run test:report   # Open HTML report (http://localhost:9323)
```

## Test Environment (Isolated)

**All services run on separate ports from development:**

| Service | Dev Port | Test Port | URL |
|---------|----------|-----------|-----|
| Frontend (dev) | 3002 | - | http://localhost:3002 |
| Backend (SPA+API) | 8000 | **8001** | http://localhost:8001 |
| MongoDB | 27017 | **27018** | `voya_test` database |
| MailHog UI | 8025 | **8026** | http://localhost:8026 |
| Mongo Express | 8081 | **8082** | http://localhost:8082 |
| FlightLogic Mock | 8002 | **8004** | http://localhost:8004 |

**Start Test Environment**:
```bash
docker compose -f ../compose.test.yaml up -d
```

**Stop Test Environment**:
```bash
docker compose -f ../compose.test.yaml down
```

## Test Categories

### ✅ API Tests (`api/`)
Fast API-level tests using Playwright request fixtures (no browser).

**`api/auth.spec.js`** (19 tests passing):
- User registration (initiate + complete)
- Email verification
- Login (email/password)
- Password reset flow (request + complete)
- Token refresh
- Protected routes

**`api/flights.spec.js`** (6/9 tests passing):
- Flight search (one-way, round-trip, multi-passenger)
- Fare validation
- Booking creation ⚠️ (revalidate endpoint needs mock implementation)
- Trip details retrieval
- My bookings list
- Error handling (invalid codes, past dates)

### ✅ E2E Tests (`e2e/`)
Full browser tests covering complete user journeys.

**Authentication** (`e2e/tests/auth/`):
- `login.spec.js` - Login flows, validation, OAuth, session persistence
- `registration.spec.js` - Registration + email verification flow

**Flights** (`e2e/tests/flights/`):
- `booking-flow.spec.js` - Complete booking journey (search → select → book → confirm)

### 🔍 Manual Tests (`manual-tests/`)
**NOT** run in CI/CD - for debugging and issue documentation only.

See `manual-tests/README.md` for detailed descriptions of each test.

**Run with**: `npm run test:manual <test-file>`

## Key Testing Patterns

### Authentication Fixtures
```javascript
import { test } from '../fixtures/auth-fixtures.js';

test('protected route', async ({ authenticatedUser, request }) => {
  const { accessToken, email } = authenticatedUser;
  // User is already registered, verified, and logged in
  const response = await request.get('/api/protected', {
    headers: { Authorization: `Bearer ${accessToken}` }
  });
  expect(response.ok()).toBeTruthy();
});
```

### Database Cleanup
```javascript
import { DatabaseHelper } from '../utils/database-helper.js';

test.beforeEach(async () => {
  dbHelper = new DatabaseHelper();
  await dbHelper.connect();
});

test.afterEach(async () => {
  await dbHelper.disconnect();
});
```

### Email Testing (MailHog)
```javascript
import { MailHogHelper } from '../utils/mailhog-client.js';

test('sends verification email', async ({ request }) => {
  const mailhog = new MailHogHelper(request);

  // Trigger email
  await request.post('/api/auth/register', { data: { email: 'test@example.com' } });

  // Wait for and verify email
  const email = await mailhog.waitForEmail('test@example.com', 10000);
  const token = mailhog.extractRegistrationToken(email);
  expect(token).toBeTruthy();
});
```

## Test Isolation

**Each test runs in isolation**:
- ✅ Separate test database (`voya_test`)
- ✅ Per-test user creation (unique emails)
- ✅ Automatic cleanup after each test
- ✅ No shared state between tests

**Global Setup/Teardown**:
- `setup/global-setup.js` - Initialize test database, verify services
- `setup/global-teardown.js` - Clean up all test data

## CI/CD Integration

Tests run automatically in GitHub Actions (`.github/workflows/ci.yml`).

**What runs in CI**:
- ✅ All API tests (`api/`)
- ✅ All E2E tests (`e2e/`)
- ❌ Manual tests (`manual-tests/`) are excluded

**Test Reports**:
- HTML report uploaded as artifact (30-day retention)
- Screenshots and videos for failed tests

## Debugging Failed Tests

### View Screenshots
```bash
ls test-results/*/test-failed-*.png
```

### View Videos
```bash
ls test-results/*/video.webm
```

### View Traces
```bash
npx playwright show-trace test-results/*/trace.zip
```

### Run Single Test
```bash
npm test api/auth.spec.js -- --headed --debug
```

### Check Test Environment
```bash
# Backend health
curl http://localhost:8001/health

# FlightLogic mock health (test env uses port 8004)
curl http://localhost:8004/health

# Frontend accessible
curl http://localhost:8001

# MailHog accessible
curl http://localhost:8026/api/v2/messages
```

## Test Users

Pre-seeded test users (auto-created in test environment):

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| testuser@example.com | Test123! | user | Standard user tests |
| testadmin@example.com | Admin123! | admin | Admin tests |
| flightbooker@example.com | Flight123! | user | Flight booking tests |

**Note**: Most tests create unique users per test for isolation.

## Test Coverage Goals

**Current Coverage**:
- ✅ Authentication: ~100% (19 API tests + 2 E2E suites)
- ⚠️ Flights: ~67% (6/9 API tests passing, 1 E2E suite)
- ❌ Profile: 0% (only manual tests exist)
- ❌ Chat: 0% (only manual tests exist)
- ❌ Trips: 0% (only manual tests exist)

**Next Steps** (Priority Order):
1. **Complete flight tests** - Implement revalidate endpoint in mock
2. **Add profile API tests** - Test user data CRUD
3. **Add chat E2E tests** - Test AI conversation flow
4. **Extract stable tests from manual-tests** - Convert to automated

## Common Issues

### Issue: Services Not Ready
```bash
# Check service health
docker compose -f ../compose.test.yaml ps

# View logs
docker logs voya-test-backend
docker logs voya-test-flightlogic-mock
```

### Issue: Database Connection Failed
```bash
# Restart MongoDB
docker compose -f ../compose.test.yaml restart mongodb-test

# Check connection
docker exec voya-test-mongodb mongosh --eval "db.adminCommand('ping')"
```

### Issue: FlightLogic Mock Not Responding
```bash
# Check mock server logs
docker logs voya-test-flightlogic-mock

# Restart mock
docker compose -f ../compose.test.yaml restart flightlogic-mock-test
```

## Documentation

- **`CLAUDE.md`** - Comprehensive testing guide for Claude Code
- **`manual-tests/README.md`** - Manual test documentation
- **`TEST_INVENTORY.md`** - Complete test inventory and consolidation analysis
- **`../docs/TESTING.md`** - Overall testing strategy
- **`../docs/CI_CD.md`** - GitHub Actions workflow

---

**Last Updated**: October 2025
**Test Framework**: Playwright 1.40.0
**Status**: Active development - focus on happy flows
