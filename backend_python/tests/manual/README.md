# Manual Test Scripts

This directory contains ad-hoc test scripts for manual testing and debugging during development.

These scripts are **not** part of the automated test suite (pytest). They are utility scripts you can run manually to test specific features or debug issues.

## Directory Structure

```
manual/
├── email/            # Email-related testing
├── pdf/              # PDF generation and validation
├── flightlogic/      # FlightLogic API testing
└── serialization/    # MongoDB serialization testing
```

## Usage

Run scripts from the `backend_python` directory:

```bash
# Example: Test email with PDF attachment
python tests/manual/email/test_email_with_pdf.py

# Example: Test PDF generation
python tests/manual/pdf/test_pdf_generation.py

# Example: Test FlightLogic session endpoint
python tests/manual/flightlogic/test_session_endpoint.py
```

## When to Use These Scripts

- 🔧 **Debugging**: Isolate and test specific features
- 📧 **Email Testing**: Verify email templates and attachments
- 📄 **PDF Validation**: Check PDF generation and formatting
- 🛫 **API Testing**: Test external API integrations manually
- 🐛 **Bug Reproduction**: Create minimal reproducible examples

## Adding New Scripts

When adding a new manual test:

1. Place in appropriate category folder (create new folder if needed)
2. Add clear docstring explaining what the script tests
3. Make it runnable standalone (no complex setup required)
4. Add comments for any non-obvious behavior
5. Update this README if adding a new category

## Note

These scripts may contain **hardcoded test data** and **dummy values**. They are not suitable for production use and should only be run in development or test environments.
