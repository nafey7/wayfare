# Manual Diagnostic Tests

**Purpose**: These tests are for manual debugging, exploration, and issue documentation. They are **NOT** run in CI/CD pipelines.

## Overview

This directory contains exploratory tests that were created to:
- Debug specific UI issues
- Document known problems
- Identify mock data and non-functional features
- Test edge cases and error handling

## Test Files

### `chat.spec.js` (472 lines)
**Purpose**: Debug chat and Gemini AI integration
- Basic chat UI elements and interactions
- Gemini AI response generation
- Trip planning trigger analysis
- Flight search via chat
- Chat history persistence
- Multiple chat handling
- Error handling and edge cases

**Use Cases**:
- Debugging chat interface issues
- Verifying AI integration is working
- Testing conversation flow

**Run**: `npm run test:manual chat.spec.js`

---

### `mockdata.spec.js` (628 lines)
**Purpose**: Identify and document mock/dummy data
- Main page mock data detection
- Dream destinations dummy content
- Premium plan/billing mock data (Premium Explorer)
- API vs frontend data comparison
- Static assets analysis
- Feature completeness assessment

**Use Cases**:
- Documenting which data is real vs mock
- Identifying non-functional UI elements
- Tracking technical debt

**Run**: `npm run test:manual mockdata.spec.js`

---

### `profile.spec.js` (327 lines)
**Purpose**: Profile page issue identification
- "undefined undefined" name display bug
- API data vs frontend data mapping
- Travel preferences functionality
- Flight preferences settings
- Timezone update functionality
- Account & billing display

**Use Cases**:
- Debugging profile data display issues
- Verifying data mapping correctness
- Testing settings updates

**Run**: `npm run test:manual profile.spec.js`

---

### `settings.spec.js` (706 lines)
**Purpose**: Settings page functionality testing
- Similar diagnostic approach to profile tests
- Settings update flows
- Preference management

**Use Cases**:
- Debugging settings functionality
- Verifying user preference persistence

**Run**: `npm run test:manual settings.spec.js`

---

### `trips.spec.js` (609 lines)
**Purpose**: Trip planning and management diagnostics
- Trip creation flows
- Trip display and management
- Data persistence

**Use Cases**:
- Debugging trip-related features
- Testing trip CRUD operations

**Run**: `npm run test:manual trips.spec.js`

---

### `navigation.spec.js` (488 lines)
**Purpose**: Navigation and header button functionality
- "How to Use" button testing
- "Likes" button functionality
- "New Chat" button
- Sidebar navigation
- Profile menu interactions
- Header action buttons
- "Plan New Trip" button
- Dream destinations "View Details"
- Travel survey button
- Route integrity (404 detection)

**Use Cases**:
- Identifying non-functional navigation elements
- Testing button click handlers
- Verifying routing works correctly

**Run**: `npm run test:manual navigation.spec.js`

---

## Running Manual Tests

### Individual Test
```bash
npm run test:manual <test-file>
```

### All Manual Tests
```bash
npm run test:manual
```

### With Browser UI (for debugging)
```bash
HEADED=true npm run test:manual <test-file>
```

## Key Characteristics

**These tests**:
- ✅ Take screenshots for manual inspection
- ✅ Log detailed debug information
- ✅ Test edge cases and error conditions
- ✅ Document known issues
- ❌ Are NOT suitable for CI/CD
- ❌ Do NOT have strict pass/fail criteria
- ❌ May contain exploratory/experimental code

## Converting to Automated Tests

When issues are fixed or features stabilize, extract the useful assertions into proper automated tests:

**Example**:
```javascript
// From manual-tests/profile.spec.js
test('should not display "undefined undefined"', async ({ page }) => {
  // ... exploratory code with screenshots ...
});

// Convert to api/profile.spec.js or e2e/tests/profile/display.spec.js
test('should display user full name correctly', async ({ authenticatedUser, page }) => {
  await page.goto('/profile');
  const name = await page.locator('h4').textContent();
  expect(name).not.toContain('undefined');
  expect(name).toBe(`${authenticatedUser.firstName} ${authenticatedUser.lastName}`);
});
```

## Maintenance

- Keep manual tests when they provide debugging value
- Remove tests for fixed issues once automated coverage exists
- Update test descriptions when new issues are discovered
- Document findings in GitHub issues, not just in tests

---

**Last Updated**: October 2025
**Status**: Active debugging tests
