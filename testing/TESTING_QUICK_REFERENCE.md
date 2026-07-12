# 🧪 Voya Testing Quick Reference

## 🚀 Quick Start

```bash
cd testing
npm install
npm run test:run-and-show  # Run all tests + open report
```

**View Results**: http://localhost:9323

## 📋 Common Commands

### Run Tests
```bash
# All tests
npm run test:all

# Specific test suites
npm run test:auth         # Authentication tests only
npm run test:login        # Login flow tests only
npm run test:e2e          # End-to-end tests
npm run test:diagnostics  # System diagnostics

# Specific test file
npx playwright test e2e/tests/auth/login.spec.js
```

### View Reports
```bash
# Open HTML report (after running tests)
npm run test:report       # Opens http://localhost:9323

# One-liner: run tests + show report
npm run test:run-and-show
```

### Debug Tests
```bash
# Interactive UI mode (best for debugging)
npm run test:ui

# See browser during test execution
npm run test:headed

# Step-by-step debugging
npm run test:debug

# Run specific test with debugging
npx playwright test login.spec.js --debug
```

## 📊 Understanding Test Reports

### Report Features
- **📈 Summary**: Total, passed, failed, flaky, skipped counts
- **📸 Screenshots**: Automatic capture on failure
- **🎥 Videos**: Full test execution recordings
- **🔍 Error Details**: Stack traces and failure context
- **🌐 Cross-Browser**: Chrome and Firefox results

### File Locations
- **HTML Report**: `playwright-report/index.html`
- **Screenshots**: `test-results/*/test-failed-*.png`
- **Videos**: `test-results/*/video.webm`
- **Traces**: `test-results/*/trace.zip`

## 🔧 Troubleshooting

### Report Not Loading
```bash
# Kill existing report server
pkill -f "playwright.*show-report"

# Start fresh
npm run test:report
```

### No Test Results
```bash
# Run tests first
npm run test:all

# Check if results exist
ls -la test-results/
```

### Test Environment Issues
```bash
# Ensure services are running
docker compose up -d

# Check service health
curl http://localhost:3000  # Frontend
curl http://localhost:8000/health  # Backend
```

## 📝 Test Structure

```
testing/
├── e2e/                 # End-to-end tests
│   ├── tests/auth/     # Authentication flows
│   └── utils/          # Test helpers
├── diagnostics/         # System diagnostics
│   ├── api/            # API integration tests
│   └── diagnostics/    # UI diagnostics
├── package.json        # Test dependencies & scripts
└── playwright.config.js # Playwright configuration
```

## 🎯 Test Categories

### Authentication Tests (`test:auth`)
- Login/logout flows
- Email verification
- Password validation
- Google OAuth integration
- Session management

### Diagnostic Tests (`test:diagnostics`)
- Profile functionality
- Navigation integrity
- Chat system integration
- Trip planning flows
- Settings persistence
- Mock data detection

### API Tests
- Backend endpoint validation
- Authentication flows
- Error handling
- Email integration (MailHog)

## ⚡ Pro Tips

### Development Workflow
```bash
# Quick feedback loop
npm run test:login && npm run test:report

# Debug failing test
npx playwright test failing-test.spec.js --ui

# Run tests in headed mode to see what's happening
npm run test:headed
```

### CI/CD Integration
```bash
# Headless mode (default)
npm run test:all

# Generate reports for CI
npx playwright test --reporter=html,json,junit
```

### Performance
```bash
# Run tests in parallel (default)
npm run test:all

# Single worker for debugging
npx playwright test --workers=1
```

---

**💡 Need help?** Check the full documentation in `README.md` or the testing section in `CLAUDE.md`