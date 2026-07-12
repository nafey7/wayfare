# PII Verification for Viewing Passenger Passport Information (Email OTP MVP)

## Overview

Step-up verification via Email OTP before revealing passport number and expiry in the profile Travel Details section.

## Security & Storage

| Aspect | Specification |
|--------|---------------|
| OTP format | 6-digit code |
| Storage | HMAC only — no raw code. Store `HMAC(server_secret, challenge_id + ":" + code)` |
| Persistence | Primary database with TTL (survives server restarts) |
| Expiry | 10 minutes |
| Max attempts | 5 |
| Invalidation | Immediate on success or when a new OTP is requested |
| PII view token | JWT, ~2 minute expiry, audience `pii-view` |

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/user/me/pii-verification/request` | Generate and email OTP, return `challenge_id`, `masked_email` |
| POST | `/api/user/me/pii-verification/verify` | Verify OTP; on success return short-lived PII View Token |
| GET | `/api/user/me/passengers/{id}?include_sensitive=true` | Requires `X-PII-View-Token` header for decrypted response |

## Phasing

- **Phase 1 (MVP)**: Email OTP only — implemented
- **Phase 2**: SMS via Twilio — deferred
- **Phase 3**: Authenticator App via TOTP — deferred

## Related

- Issue #418: Passenger encryption at rest
