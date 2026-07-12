# Validation Scripts

Standalone validation scripts for manual testing and debugging. These are Python scripts that run independently of the Playwright test suite.

## Scripts

### Booking Flow Validation

- **test_booking_fix.py** - Tests booking endpoint fix for FlightLogic uniqueID reuse issue
- **test_booking_restoration.py** - Tests booking restoration functionality from email links
- **test_booking_security.py** - Security tests for unauthenticated booking access

### Date Validation

- **test_date_logic.py** - Tests date validation logic used in JavaScript
- **test_date_validation.html** - Browser-based interactive date validation testing

### Email & Payment

- **test_gmail_url_handling.py** - Tests Gmail URL wrapping and provides solutions
- **test_payment_auth_fix.py** - Tests payment authentication flow fixes

## Usage

These scripts are self-contained and can be run directly:

```bash
cd testing/validation
python3 test_booking_fix.py
python3 test_date_logic.py
# etc.
```

For HTML test files, open in a browser:
```bash
open test_date_validation.html
```

## Purpose

These scripts were created during debugging sessions to validate specific fixes:
- PR #55/56: FlightLogic configuration improvements
- PR #56/58: Flight details display from chat bookings
- Email payment link functionality
- Date validation edge cases

They serve as:
1. Quick validation tools during development
2. Documentation of how specific features should work
3. Regression testing for critical bug fixes
