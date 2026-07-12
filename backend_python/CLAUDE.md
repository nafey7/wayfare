# Voya Backend - FastAPI Travel Platform

**Context**: You are working in the Python backend. See root `CLAUDE.md` for project-wide information.

## Navigation
📍 **You are here**: Backend Python Development (`backend_python/`)
🔙 **Parent**: [Root CLAUDE.md](../CLAUDE.md) - Project overview and role-based quick starts
📚 **Related docs**:
- [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) - Complete Python coding standards (18K)
- [TESTING_STANDARDS.md](docs/TESTING_STANDARDS.md) - Unit/integration testing patterns
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design and DDD structure
- [FRONTEND_BACKEND_COLLABORATION.md](../docs/FRONTEND_BACKEND_COLLABORATION.md) - API contracts

## Quick Start
```bash
cd backend_python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Development
uvicorn app.main:app --reload --port 8000

# Quality checks
ruff check --fix . && ruff format . && mypy app/
```

## 🚨 YOU MUST: Boy Scout Rule - Leave Code Better Than You Found It

**Pre-commit/Pre-push Hook Policy**:
- ✅ **YOU MUST** fix type errors, lint errors, and security issues in files you modify
- ✅ **YOU MUST** verify your fixes resolved errors before skipping any checks
- ⚠️ **ONLY SKIP WHEN** errors exist in completely unmodified files
- ❌ **NEVER** use `--no-verify` or `SKIP` to avoid fixing your own errors

**Example workflow**:
```bash
# You modified app/api/auth.py, mypy reports errors in:
# - app/api/auth.py (your file) ← MUST FIX
# - app/ai/flight_summary_generator.py (untouched) ← CAN SKIP

# 1. Fix your file first
vim app/api/auth.py

# 2. Verify your fixes work
mypy app/api/auth.py  # Should show no errors

# 3. Only then skip the unrelated file
SKIP=mypy git push
```

See root `CLAUDE.md` for detailed pre-commit hook guidelines.

## Python Version & Tech Stack

**Production Python Version**: 3.12 (see `Dockerfile`)

**Tech Stack**:
- **FastAPI** ≥0.115.6 - Async web framework
- **Motor** ≥3.7.0 - Async MongoDB driver (⚠️ Deprecated May 2025, migrate to PyMongo async by Q2 2026)
- **Pydantic** v2 - Data validation and serialization
- **PyJWT** ≥2.10.1 - Authentication tokens
- **Stripe** ≥12.5.1 - Payments (major version upgrade)
- **Google GenAI** ≥1.0.0 - Unified SDK for Gemini models (via `integrations/llm/`)
- **SendGrid** ≥6.11.0 - Email delivery

## Project Structure
```
app/
├── ai/               # AI conversation handling
│   ├── intent_recognizer.py        # Smart intent detection (BOOK_FLIGHT, BOOK_HOTEL)
│   ├── flight_booking_handler.py   # Flight selection & booking flow
│   ├── enhanced_flight_handler.py  # Flight search & conversation
│   ├── hotel_booking_handler.py    # Hotel selection & booking flow
│   ├── enhanced_hotel_handler.py   # Hotel search & conversation
│   ├── hotel_field_collector.py    # NLP extraction for hotel fields
│   └── conversation_state.py       # Context management
├── api/              # FastAPI route handlers
│   ├── auth.py       # Authentication endpoints
│   ├── chat.py       # Chat/conversation endpoints
│   ├── flights.py    # Flight search endpoints
│   ├── hotels.py     # Hotel search & booking endpoints
│   └── user.py       # User management
├── domains/          # Business logic by domain (DDD)
│   ├── auth/         # Auth service, repository, schemas
│   ├── chat/         # Conversation state management
│   ├── flight/       # Flight operations & schemas
│   ├── hotel/        # Hotel operations, schemas, validators, events
│   ├── user/         # User operations & validation
│   ├── airport/      # Global airport resolution (29K+ airports)
│   └── email/        # Email templates & delivery (flight + hotel)
├── shared/           # Shared utilities
│   └── geocoding.py  # Google Geocoding API for city disambiguation
├── database/         # MongoDB connection & models
├── core/             # Configuration, logging, security
└── main.py           # FastAPI application entry

integrations/         # External API clients
├── flightlogic/      # Flight & hotel API (search, booking)
│   ├── client.py     # API client methods
│   ├── hotel_dto.py  # Hotel API data transfer objects
│   └── hotel_adapter.py  # Domain ↔ DTO conversion
└── sendgrid/         # Email service client
```

## AI Output Verification (AI-CHAT-011)

After each supervisor turn, `verify_agent_output()` in `app/ai/graph/output_verification.py` runs a deterministic check that the agent's claimed result type (`itinerary_results` / `flight_search_results` / `hotel_search_results`) is backed by the corresponding artifact (`structured_itinerary` / non-empty `flights` / non-empty `hotels`). When the structural mismatch fires:

- **Telemetry** (always on): `logger.warning("ai_chat_011.false_completion_detected ...")` — pivot on this in CloudWatch.
- **Retry** (kill-switch gated): re-dispatch the active agent ONCE with a `SystemMessage` naming the missing tool. Strict 1-retry budget — no loops. Enabled by default; set `AI_CHAT_011_VERIFICATION_ENABLED=false` to disable as a rollback escape hatch.
- **Honest fallback** (when retry also fails): replace the response with *"I'm having trouble completing that right now — could you try rephrasing..."* and tag `error_class=verification_failed`. Better to ask the user to rephrase than ship a second hallucination.

Coverage: `tests/unit_tests/test_ai/test_graph/test_output_verification.py` (detector) + `test_verification_retry.py` (wiring + retry + fallback).

## Critical Python Patterns

### Async Patterns (CRITICAL - Event Loop Safety)
```python
# ✅ CORRECT - Use async def with actual async I/O
async def search_flights(origin: str, destination: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/flights?from={origin}&to={destination}")
    return response.json()

# ✅ CORRECT - Use def for blocking operations (FastAPI runs in threadpool)
def process_payment(amount: int):
    # Stripe SDK is synchronous - use regular def
    return stripe.PaymentIntent.create(amount=amount)

# ❌ WRONG - Never use time.sleep() in async functions
async def bad_handler():
    time.sleep(5)  # BLOCKS ENTIRE EVENT LOOP!

# ✅ CORRECT - Use asyncio.sleep()
async def good_handler():
    await asyncio.sleep(5)  # Non-blocking

# ❌ WRONG - Missing await
async def bad_db_call():
    user = db.users.find_one({"_id": user_id})  # Returns coroutine, not data!

# ✅ CORRECT - Always await async calls
async def good_db_call():
    user = await db.users.find_one({"_id": user_id})
```

### Type Hints (REQUIRED - MyPy with Pydantic Plugin)
```python
# ✅ All functions must have type hints
async def get_user(user_id: str) -> dict:
    return await db.users.find_one({"_id": user_id})

# ✅ Use proper return types for async functions
async def create_booking(data: BookingCreate) -> BookingResponse:
    result = await bookings_collection.insert_one(data.model_dump())
    return BookingResponse(**result)

# ✅ Use consistent type annotation style
from typing import Optional, Union, Generic, TypeVar

def process_data(value: Optional[str]) -> Union[dict, list]:
    pass
```

### Pydantic Models (v2 Patterns)
```python
from pydantic import BaseModel, Field, field_validator

# ✅ Separate input and output models
class BookingCreate(BaseModel):
    passenger_name: str = Field(min_length=2, max_length=100)
    flight_number: str = Field(pattern=r'^[A-Z]{2}\d{3,4}$')

    @field_validator('passenger_name')
    @classmethod  # Required in Pydantic v2
    def validate_name(cls, v: str) -> str:
        if not v.replace(' ', '').isalpha():
            raise ValueError('Name must contain only letters')
        return v

# ✅ Use .model_dump() for database operations
@app.post("/bookings/", response_model=BookingResponse)
async def create_booking(booking: BookingCreate):
    doc = booking.model_dump()  # Convert to dict
    result = await db.bookings.insert_one(doc)
    return await db.bookings.find_one({"_id": result.inserted_id})
```

### Error Handling & Retry Logic
```python
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential

# ✅ Raise HTTPException with specific status codes
@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    booking = await db.bookings.find_one({"_id": booking_id})
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking

# ✅ Implement retry logic for external APIs
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_flight_api(params: dict):
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(API_URL, json=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, "Flight API timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"Flight API error: {e.response.status_code}")
```

## Critical Migrations Needed

### 🚨 Immediate Actions Required
1. **Security**: ✅ **python-multipart upgraded to 0.0.20** (CVE-2024-53981 fixed)
2. **Compatibility**: ✅ **bcrypt pinned to 4.0.1** (passlib compatibility maintained)

### ✅ Recently Completed
1. **google-generativeai → google-genai**: Migrated to unified SDK via `integrations/llm/` module

### 📅 Planned Migrations (Next 6 Months)
1. **Motor deprecation**: Plan PyMongo async migration by Q2 2026
3. **Passlib replacement**: Migrate to pwdlib[argon2] for modern password hashing

## Development Commands

### Development Server
```bash
# Local development
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Docker development
docker compose up -d
```

### Quality Assurance
```bash
# Code formatting & linting (fast)
ruff check . --fix        # Auto-fix issues
ruff format .             # Format code

# Type checking (with Pydantic plugin)
mypy app/                 # Full type validation

# Security scanning
bandit -r app/ -ll -c pyproject.toml

# All quality checks
ruff check --fix . && ruff format . && mypy app/ && bandit -r app/ -ll
```

### Testing
```bash
# Unit tests with coverage
pytest tests/unit_tests/ -v --cov=app --cov-report=html

# Integration tests
pytest tests/integration_tests/ -v -m integration

# Specific test categories
pytest -m "not slow"      # Fast tests only
pytest -m critical       # Critical path tests
```

## Developer Tools

- **API Docs**: http://localhost:8000/api/docs (Swagger UI)
- **API Tester**: http://localhost:8000/dev/api-tester.html (interactive testing with Google OAuth)
- **OpenAPI JSON**: http://localhost:8000/openapi.json (generate types/client code)

## Key Integrations

- **FlightLogic API**: `integrations/flightlogic/` - Flight & hotel search, room rates, booking
- **Google AI**: `app/ai/` - Intent recognition (BOOK_FLIGHT, BOOK_HOTEL), conversation handling
- **Google Geocoding**: `app/shared/geocoding.py` - City disambiguation for hotel searches
- **Google Places**: `integrations/googleplaces/` - Place discovery (Text Search) and photo retrieval
- **MongoDB**: `app/database/` - Motor async ODM. See [Database Migrations](#database-migrations) below.
- **SendGrid**: `integrations/sendgrid/` - Email delivery (flight & hotel confirmations)

### Hotel API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/hotels/search` | POST | Search hotels by city/geo/codes |
| `/api/hotels/room-rates` | POST | Get room pricing options |
| `/api/hotels/rate-rules` | POST | Validate rate before booking |
| `/api/hotels/book` | POST | Create booking with Stripe payment |
| `/api/hotels/session/{id}` | GET | Retrieve session for booking form |

See `docs/HOTEL_API_INTEGRATION.md` for complete API documentation.

### Flight API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/flights/search` | POST | Search flights by origin/destination |
| `/api/flights/select` | POST | Select flight and create booking session |
| `/api/flights/session/{id}` | GET | Retrieve session for booking form |
| `/api/flights/book` | POST | Create booking with passenger details |
| `/api/flights/my-bookings` | GET | List current user's flight bookings (`BookingEventResponse`; route IATA snapshots for profile / lists) |

See `docs/FLIGHT_FEATURES.md` for flight booking features documentation.

### Voucher API (G2A / manual discount codes)

Authenticated users only (`require_authenticated`). USD-only apply path; reservation TTL and sweeper return stale holds to `active`.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/vouchers/apply` | POST | Reserve a code against `voya_booking_reference`; returns `redemption_id`, `discount_cents`, `new_total_cents` |
| `/api/vouchers/release` | POST | Release a reservation by `redemption_id` |

**Location**: `app/api/vouchers.py`, `app/domains/discount/`

### Admin discount / batch API (G2A SafeKeys)

All routes require `require_admin`. Batch CSV export streams one code per line (no header) for G2A upload.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/discounts` | GET | List voucher docs (filters: `status`, `batch_id`, `source`, `search`, pagination) |
| `/api/admin/discounts/{id}` | GET | Single voucher doc |
| `/api/admin/discounts/{id}/disable` | POST | Set status disabled |
| `/api/admin/discounts/batches` | GET | List batches with aggregate counts |
| `/api/admin/discounts/batches` | POST | Generate batch (`count`, `amount_cents`, `source`, optional `prefix` / `expires_at`; currency stored as USD) |
| `/api/admin/discounts/batches/{batch_id}` | GET | Batch metadata + paginated codes |
| `/api/admin/discounts/batches/{batch_id}/export.csv` | GET | Stream CSV of codes |

**Location**: `app/api/admin_discounts.py` (mounted under admin router), `app/database/migrations/006_discounts_collection_indexes.py`

### Passenger Storage API (Issue #418)

Stored passenger/guest details per authenticated user with field-level encryption for sensitive PII.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/user/me/passengers` | POST | Store passenger details (sensitive fields encrypted at rest) |
| `/api/user/me/passengers` | GET | List saved passengers (sensitive fields masked, e.g. `****4589`) |
| `/api/user/me/passengers/{id}` | GET | Get single passenger (masked by default; `?include_sensitive=true` requires PII verification token for passport view) |
| `/api/user/me/passengers/{id}` | PUT | Update passenger |
| `/api/user/me/passengers/{id}` | DELETE | Permanently delete passenger (GDPR right to deletion) |

**PII handling**:
- **Encrypted at rest** (Fernet): `passport_number`, `passport_expiry`, `frequent_flyer_number`
- **Stored plain** (standard personal data): `first_name`, `last_name`, `title`, `date_of_birth`, `nationality`, `email`, `phone`
- GET responses mask sensitive fields (e.g. `passport_number: "****4589"`, `passport_expiry: "2028-**-**"`). Full passport values from the single-passenger GET require `include_sensitive=true` plus a valid `X-PII-View-Token`.

**Config**: `PASSENGER_ENCRYPTION_KEY` (Fernet key). In development, falls back to key derived from `SECRET_KEY` if unset.

**Location**: `app/domains/passenger/`, `app/api/user.py` (passenger endpoints)

### PII Verification (Email OTP for passport view)

Step-up verification required before viewing passport number/expiry in profile Travel Details.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/user/me/pii-verification/request` | POST | Send 6-digit OTP to user email; return `challenge_id`, `masked_email` |
| `/api/user/me/pii-verification/verify` | POST | Verify OTP; return short-lived `pii_view_token` |
| `/api/user/me/passengers/{id}?include_sensitive=true` | GET | Requires `X-PII-View-Token` header |

**Rate limiting**: `POST /pii-verification/request` is limited to 3 requests per 5 minutes per user to prevent email spam. Returns 429 when exceeded.

**Location**: `app/domains/pii_verification/`, `app/api/user.py`

### Profile API (frontend-v2 profile page)

Single aggregate endpoint for the full profile page; preferences stored in `user_preferences` collection.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/user/me/profile` | GET | Aggregate: user + preferences + passengers (primary first) |
| `/api/user/me/preferences` | PUT | Upsert preferences (partial update supported) |
| `/api/user/me/photo` | PUT | Upload (or replace) profile photo — multipart `file`. Returns `photo_key` + signed imgproxy URLs for `sm`/`md`/`lg` |
| `/api/user/me/photo` | DELETE | Remove profile photo (idempotent — 204 even when none) |

**Passengers**: Use `is_primary: true` for the account owner (self); one primary per user. Primary passenger appears first in profile aggregate.

**Profile photos**: Originals are stored in a private S3 bucket (`myvoya-${env}-photos`; locally MinIO `myvoya-local-photos`) via the backend ECS task role. imgproxy reads `s3://` sources and renders sized variants behind CloudFlare. Uploads are validated (size/MIME/dimensions), re-encoded to strip EXIF, and old objects are deleted synchronously on replace.

**Location**: `app/domains/user_preferences/`, `app/domains/user/service.py` (get_profile), `app/domains/user/photo_service.py`, `app/shared/s3.py`, `app/api/user.py`

### Places API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/places/search` | POST | Search places by text (Text Search API) |
| `/api/places/photos/{resource_name}/media` | GET | Stream place photo (backend proxies to hide API key) |
| `/api/places/image-url` | GET | Get proxy image URL for top place by name (search + first photo) |

Uses `GOOGLE_API_KEY` or `GOOGLE_MAPS_API_KEY`. Photos are fetched server-side so the key stays hidden.

### Database Migrations

Lightweight async MongoDB migration runner in `app/database/migrate.py`.

**Usage**:
```bash
python -m app.database.migrate           # Run pending migrations
python -m app.database.migrate --dry-run  # List pending without executing
```

**File convention**: `app/database/migrations/` — files named `NNN_description.py` or `YYYYMMDD_NNN_description.py`. Each file must have `async def up(db)`; `async def down(db)` is optional.

**Rules**:
- Migrations must be **idempotent** (safe to run twice)
- No interactive prompts
- **Backwards-compatible**: migrations must not break currently running code; use two-phase deploys for breaking changes
- **Imports**: Do **not** import `app.domains.*` from migration files — package `__init__` chains cause circular imports at migrate load time (staging/prod ECS migrate task). Use `app.database.constants`, inline literals, or duplicated index specs per `docs/MIGRATIONS.md`.
- **Unit tests**: New or changed migrations should include tests per `docs/MIGRATIONS.md` (*Unit tests for migrations*): assert full index specs for `up()`, and exercise `down()` including defensive error paths when applicable.

**CI/CD**: Migrations run automatically before ECS service update in deploy-staging and deploy-prod workflows.

**Full reference**: `docs/MIGRATIONS.md`

## Documentation

### Coding Standards
See `docs/CODING_STANDARDS.md` for comprehensive Python coding standards:
- Core principles and design philosophy
- Type hints, async patterns, Pydantic v2
- Code organization and naming conventions
- Error handling, security, and testing patterns
- Tool configuration (Ruff, MyPy, Bandit)

### Pre-commit Hooks
See root `CLAUDE.md` for pre-commit configuration (project-wide).

### Database Migrations
See `backend_python/docs/MIGRATIONS.md` for file convention, idempotency, **imports / circular-dependency rules**, **unit-test expectations**, CI/CD, and retrofit steps.

### Testing Standards
See `backend_python/docs/TESTING_STANDARDS.md` for:
- Mocking MongoDB (AsyncMock)
- Mocking external APIs (httpx_mock)
- Unit vs integration testing
- Coverage requirements (80% minimum)

### Frontend Integration
See `docs/FRONTEND_BACKEND_COLLABORATION.md` for:
- API contracts and schemas (Swagger as SSoT)
- Authentication flow
- Error handling conventions
- Data transformation patterns (snake_case ↔ camelCase)

### Architecture
See `docs/ARCHITECTURE.md` for:
- System design
- Domain-driven design (DDD) structure
- Sticky intent system (BOOK_FLIGHT, BOOK_HOTEL)
- Airport resolution system
- Hotel booking flow

### CI/CD
See `docs/CI_CD.md` for:
- GitHub Actions workflows
- Pre-commit hooks in CI
- Troubleshooting failed builds

---

**Last Updated**: April 2026
**Status**: Production ready with modern tooling
**Action Required**: Google GenAI migration before November 30, 2025
