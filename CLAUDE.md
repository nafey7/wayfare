# Voya Travel Platform - Documentation

This file provides guidance to Claude Code when working with the Voya travel platform repository.

## 🤖 How to Use This Documentation (For Claude Code)

**Before starting any task, follow this workflow:**

1. **Read this CLAUDE.md first** - Understand project structure and where documentation lives
2. **Identify the task domain** - Determine which area the user's request relates to:
   - Backend API/Python → Read `backend_python/CLAUDE.md`
   - Frontend React/UI → Read `frontend-v2/` and `docs/FRONTEND_BACKEND_COLLABORATION.md`
   - Testing/E2E → Read `testing/CLAUDE.md`
   - Admin dashboard → Read `admin/CLAUDE.md`
3. **Consult relevant deep docs** - Use the [Documentation Map](#documentation-map) to find specialized documentation:
   - Architecture questions → `docs/ARCHITECTURE.md`
   - Setup/troubleshooting → `docs/TROUBLESHOOTING.md`
   - Testing patterns → `backend_python/docs/TESTING_STANDARDS.md` or `docs/TESTING.md`
   - API integration → `docs/FRONTEND_BACKEND_COLLABORATION.md`
   - Code standards → `backend_python/docs/CODING_STANDARDS.md`
4. **Check for existing implementations** - Search codebase before creating new solutions
5. **Follow established patterns** - Use patterns from relevant CLAUDE.md files

**Example workflows:**

```
User: "Fix the authentication flow"
Claude:
1. Read backend_python/CLAUDE.md (auth patterns)
2. Read docs/ARCHITECTURE.md (auth architecture section)
3. Read docs/FRONTEND_BACKEND_COLLABORATION.md (JWT flow)
4. Search for existing auth code: grep -r "authenticate" app/
5. Apply fixes following established patterns
```

```
User: "Add a new React component"
Claude:
1. Read docs/FRONTEND_BACKEND_COLLABORATION.md (API contracts, React patterns)
2. Read docs/ARCHITECTURE.md (frontend architecture section)
3. Check existing components for patterns: ls frontend-v2/src/
4. Create component following Material-UI and Redux patterns
```

```
User: "Write tests for the booking flow"
Claude:
1. Read testing/CLAUDE.md (Playwright patterns, test environment)
2. Read backend_python/docs/TESTING_STANDARDS.md (unit test patterns)
3. Read docs/TESTING.md (overall strategy)
4. Check existing test structure: ls testing/tests/
5. Write tests following page object model and fixtures
```

**Complete Documentation Map**: See [docs/DOCUMENTATION_MAP.md](docs/DOCUMENTATION_MAP.md) for comprehensive guide to all documentation, organized by role and topic.

## ⛔ Critical Don'ts - Read This First

**YOU MUST NOT:**
- ❌ Skip pre-commit hooks with `--no-verify` (bypasses ALL checks including your changes)
- ❌ Implement code without reading existing patterns first (investigate → understand → implement)
- ❌ Commit secrets (API keys, passwords, .env files, tokens)
- ❌ Use `sudo` (ask user to run system-level commands)
- ❌ Jump to architectural solutions before understanding root cause
- ❌ Fix multiple unrelated issues simultaneously (one problem at a time)
- ❌ Use conversation history for: API schemas, system state, syntax, library versions
- ❌ Clutter main context with raw grep results (use Task agent for synthesis)

**CRITICAL RULE**: When in doubt, query the live system (`Read`, `Grep`, `Bash`) over assumptions.

## 📋 Communication Style and Investigation Protocol

### Communication Requirements
- **Concise responses**: Under 4 lines unless detail requested
- **Dense information**: Pack details without losing specificity
- **Direct answers**: Minimal preamble, get to the point
- **Comprehensive coverage**: Don't skip relevant details for brevity

### Information Source Priority (Authoritative Order)

When conflicting information exists, trust this hierarchy:

1. **Live System State** (highest authority)
   - File contents, API responses, CLI output at query time
   - `git status`, `docker compose ps`, `pytest` output, actual code
   - "What IS" trumps "what documentation says"

2. **Current Session User Corrections**
   - Direct corrections: "That's camelCase, not snake_case"
   - Implicit corrections: User providing different approach
   - User blocking tool use = wrong assumption made

3. **Project Documentation** (current repository)
   - CLAUDE.md files, docs/ directory, README files
   - Check timestamps - verify freshness before trusting

4. **Global Instructions**
   - ~/.claude/CLAUDE.md and personal preferences
   - Generally current but may not reflect local project specifics

5. **Conversation History** (lowest authority)
   - Useful for context and intent
   - May contain outdated patterns, old schemas, deprecated code
   - NEVER use for: API schemas, system state, syntax, library versions

**Critical Rule**: When in doubt, query the live system. Always prefer `Read`, `Grep`, `Bash` over assumptions.

### Investigation Before Action Protocol

**BEFORE starting any implementation, investigate existing patterns:**

**Required Investigation Steps:**
1. **Read relevant documentation** (CLAUDE.md files, docs/)
2. **Search for existing implementations** (`Grep` for similar features)
3. **Examine related code** (`Read` files that might use similar patterns)
4. **Check for test examples** (tests show actual usage patterns)
5. **Verify system state** (run commands, check files, don't assume)

**Example: "Add flight cancellation feature"**
```
❌ BAD: Immediately start writing cancellation endpoint
✅ GOOD:
1. Read backend_python/CLAUDE.md (async patterns, Pydantic models)
2. Grep for existing booking operations: grep -r "booking" app/domains/
3. Read FlightBookingHandler to understand booking flow
4. Read flight service to see FlightLogic API patterns
5. Check tests: ls tests/ | grep -i booking
6. Then implement following established patterns
```

**Example: "Fix authentication bug"**
```
❌ BAD: Guess at JWT implementation and start patching
✅ GOOD:
1. Read docs/ARCHITECTURE.md (auth flow)
2. Read docs/FRONTEND_BACKEND_COLLABORATION.md (JWT tokens)
3. Read backend_python/CLAUDE.md (security patterns)
4. Grep for JWT usage: grep -r "jwt\|JWT" app/
5. Read auth service and repository files
6. Check actual token validation in middleware
7. Then apply fix following established patterns
```

### When to Use Task Agent for Investigation

**Use Task Agent** (keeps main context clean) when:
- Understanding complex system architecture before creating solution
- Investigating "how does X actually work?" questions
- Root cause analysis for bugs (understand before fixing)
- Cross-cutting concerns (auth flow across frontend-v2/backend)
- Historical context needed (check git history, related issues)

**Task Agent Investigation Template:**
```
"Investigate [system/feature/bug]. Check:
1. Relevant CLAUDE.md files for patterns
2. Related code files in app/domains/ or src/
3. Test files showing actual usage
4. docs/ for architecture and design decisions
5. Recent git commits touching this area

Return concise summary:
- How it currently works
- Key files and patterns used
- Relevant tests or examples
- Any recent changes or caveats
- Recommended approach for [user's task]"
```

**When NOT to Use Task Agent:**
- Simple file reads (use `Read` directly)
- Known patterns from CLAUDE.md (follow instructions)
- Single grep operations (use `Grep` directly)
- File existence checks (use `Bash` or `Glob`)

### Critical Lessons from Past Debugging Sessions

**Lesson 1: Follow the Data Flow Systematically**
```
❌ BAD: Jump between frontend errors and backend routing
✅ GOOD: Trace data step-by-step:
   1. Is data stored correctly? (check DB/logs)
   2. Is data retrieved correctly? (check API response)
   3. Is data transformed correctly? (check frontend state)
   4. Then identify where it breaks
```

**Lesson 2: Read Logs Carefully Before Implementing Fixes**
```
❌ BAD: See error → implement architectural change
✅ GOOD: See error → read logs → understand root cause → minimal fix
```

**Lesson 3: Test Minimal Reproducible Cases**
```
❌ BAD: Implement complex solution hoping it fixes issue
✅ GOOD: Create simple test that reproduces bug → verify fix → then apply
```

**Lesson 4: One Problem at a Time**
```
❌ BAD: Fix MongoDB persistence AND serialization AND user lookup simultaneously
✅ GOOD: Identify root cause → fix that one thing → verify → then next issue
```

**Lesson 5: Simple Fixes Often Win**
```
The "final fix" might be changing one method call (15 minutes work),
but only after spending time understanding why it's wrong (hours of investigation).

Invest time in understanding, then implement minimal fix.
```

### Never Clutter Main Context

**DON'T:**
- Paste raw grep results (use Task agent to synthesize)
- Read multiple files speculatively (read what you need)
- Try multiple approaches without understanding root cause
- Implement architectural changes before understanding current system

**DO:**
- Use Task agent for exploration → get synthesized findings
- Read specific files after identifying what's relevant
- Understand current implementation before proposing changes
- Follow established patterns in codebase

## Table of Contents
- [How to Use This Documentation](#-how-to-use-this-documentation-for-claude-code)
- [Critical Don'ts](#-critical-donts---read-this-first)
- [Communication Style and Investigation Protocol](#-communication-style-and-investigation-protocol)
- [Quick Start by Role](#quick-start-by-role)
- [Project Overview](#project-overview)
- [Pre-commit Hooks (Project-wide)](#pre-commit-hooks-project-wide)
- [Documentation Map](#documentation-map)
- [Token Budget by Role](#token-budget-by-role)
- [Common Commands](#common-commands)
- [Testing Quick Reference](#testing-quick-reference)
- [Environment Variables](#environment-variables)
- [Getting Help](#getting-help)
- [Documentation Maintenance Protocol](#-documentation-maintenance-protocol)

## Quick Start by Role

### 🐍 Backend Developer
**Work from**: `backend_python/`
**Read**: This file + `backend_python/CLAUDE.md`
**Key docs**:
- Testing standards: `backend_python/docs/TESTING_STANDARDS.md`
- Architecture: `docs/ARCHITECTURE.md`
**Quick start**:
```bash
cd backend_python && uvicorn app.main:app --reload
```

### ⚛️ Frontend Developer
**Work from**: `frontend-v2/`
**Read**: This file + `docs/FRONTEND_BACKEND_COLLABORATION.md`
**Key tools**:
- API docs: http://localhost:8000/api/docs (Swagger)
- API tester: http://localhost:8000/dev/api-tester.html
**Quick start**:
```bash
cd frontend-v2 && npm run dev
```

### 🧪 QA/Testing Developer
**Work from**: `testing/`
**Read**: This file + `testing/CLAUDE.md`
**Key docs**: `docs/TESTING.md`
**Quick start**:
```bash
cd testing && npm run test:all
```

### 🔧 Full-stack Developer
**Work from**: Root
**Read**: Everything (this file + all subdirectory CLAUDE.md files)
**Quick start**:
```bash
docker compose up -d
```

## Project Overview

Voya is a travel planning platform with AI-powered chatbot capabilities.

**Structure**:
- **Frontend** (`/frontend-v2`): React 18.2, Redux Toolkit, Material-UI
- **Backend** (`/backend_python`): Python FastAPI, MongoDB (Motor ODM)
- **Admin** (`/admin`): React admin dashboard
- **Testing** (`/testing`): Playwright E2E testing with complete environment isolation

**Key Technologies**:
- AI: Google Generative AI (Gemini)
- Travel Data: FlightLogic API
- Database: MongoDB with Motor async ODM
- Auth: JWT + Google OAuth
- Email: MailHog (dev), SendGrid (prod)
- Observability: Sentry (errors), Langfuse (LLM), CloudWatch (logs)

**Service URLs**:
- Frontend: http://localhost:3002
- Backend API: http://localhost:8000/api
- API Docs: http://localhost:8000/api/docs (Swagger)
- API Tester: http://localhost:8000/dev/api-tester.html
- Database Admin: http://localhost:8081
- Strapi CMS: http://localhost:1337/admin

## Pre-commit Hooks (Project-wide)

**Installation** (if not running):
```bash
pre-commit install && pre-commit install --hook-type pre-push
```

**Hooks**: On commit (<10s): ruff, yaml/json. On push (~30s): mypy, bandit.

**🚨 YOU MUST: Boy Scout Rule**:
- Fix errors in files you modified (no exceptions)
- Verify fixes before skipping
- ONLY skip when errors in completely unmodified files
- Use `SKIP=mypy git push` (NOT `--no-verify`)

**Workflow**:
```bash
# 1. Fix your file
mypy backend_python/app/api/auth.py  # Verify no errors

# 2. Skip unrelated errors only
SKIP=mypy git push
```

**Details**: See `docs/CODE_QUALITY.md` for complete hook configuration.

## Documentation Map

### Project History
- **`CHANGELOG.md`** - Project changelog following [Keep a Changelog](https://keepachangelog.com/) format. Update when making notable changes.

### Subdirectory Context Files
- **`backend_python/CLAUDE.md`** - Python/FastAPI patterns, async, Pydantic, type hints
- **`docs/FRONTEND_BACKEND_COLLABORATION.md`** - React/Redux patterns, API integration
- **`testing/CLAUDE.md`** - E2E/Playwright patterns, test environment, MailHog
- **`admin/CLAUDE.md`** - Admin dashboard specifics

### Deep Technical Docs (`docs/`)
- **`ARCHITECTURE.md`** (12K) - System design, data flow, sticky intents
- **`TROUBLESHOOTING.md`** (16K) - Common issues, recent fixes, debug tips
- **`CI_CD.md`** (8.4K) - GitHub Actions, workflows, debugging
- **`CODE_QUALITY.md`** (4.9K) - Linting, type checking, security
- **`PLACES_IMAGE_SECURITY.md`** - Public chat Places photo proxy: tokens, rate limits, Cloudflare ops
- **`TESTING.md`** (4.3K) - E2E testing with Playwright, Docker
- **`FLIGHT_FEATURES.md`** (5.9K) - Flight search, booking, NLP features. Best Value (Best Flights) calculation: `docs/FLIGHT_FEATURES.md#best-value-best-flights-scoring`
- **`LOCAL_DEVELOPMENT.md`** (5.4K) - Dev environment setup
- **`TEAM_WORKFLOW.md`** (6.6K) - Git workflow, collaboration
- **`CODE_REVIEW.md`** (NEW) - Code review checklist, test requirements policy
- **`FRONTEND_BACKEND_COLLABORATION.md`** (NEW) - API contracts, integration patterns

### Backend-Specific Docs (`backend_python/docs/`)
- **`CODING_STANDARDS.md`** (18K) - Complete Python standards, async, security
- **`TESTING_STANDARDS.md`** (10K) - Unit/integration testing, mocking patterns

## Token Budget by Role

**Efficient context loading per role**:

**🐍 Backend Developer** (~15K):
1. Root CLAUDE.md (this file)
2. `backend_python/CLAUDE.md`
3. `backend_python/docs/CODING_STANDARDS.md` (as reference)

**⚛️ Frontend Developer** (~12K):
1. Root CLAUDE.md (this file)
2. `frontend-v2/` + `docs/FRONTEND_BACKEND_COLLABORATION.md` (API contracts, React patterns)
3. `docs/ARCHITECTURE.md` (system design)

**🧪 Testing Developer** (~10K):
1. Root CLAUDE.md (this file)
2. `testing/CLAUDE.md`
3. `backend_python/docs/TESTING_STANDARDS.md` (unit tests)

**🔧 Full-stack** (~20K):
1. Root CLAUDE.md
2. `backend_python/CLAUDE.md` + `docs/FRONTEND_BACKEND_COLLABORATION.md`
3. `docs/ARCHITECTURE.md` (system design)

**Complete map**: See [docs/DOCUMENTATION_MAP.md](docs/DOCUMENTATION_MAP.md)

## Common Commands

### Start All Services
```bash
docker compose up -d
```

### Backend Development
```bash
cd backend_python
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend-v2
npm run dev
```

### Run Tests
```bash
# Backend unit tests
cd backend_python && pytest tests/unit_tests/ -v --cov=app

# Frontend tests
cd frontend-v2 && npm run test

# E2E tests
cd testing && npm run test:all
npm run test:report  # View HTML report at :9323
```

### Code Quality
```bash
# Backend (Python)
cd backend_python
ruff check --fix . && ruff format . && mypy app/

# Frontend (JavaScript)
cd frontend-v2
npm run lint
```

### CI/CD Status
```bash
gh pr checks        # Current PR status
gh run list         # Recent workflow runs
gh run view --log   # View logs
```

## Testing Quick Reference

**Coverage Requirements**: 80% minimum, 100% for critical paths (auth, payments, security)

**Test Users** (auto-seeded in dev/test):

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| testuser@example.com | Test123! | user | Standard user |
| testadmin@example.com | Admin123! | admin | Admin user |
| flightbooker@example.com | Flight123! | user | Flight booking tests |

**Implementation**: Test users created on startup in `app/database/seed.py`

## Environment Variables

**Backend** (`.env`):
- `MONGODB_URI` - MongoDB connection string
- `SECRET_KEY` - JWT signing key (≥32 chars)
- `GOOGLE_GENERATIVE_AI_API_KEY` - Gemini API key
- `FLIGHTLOGIC_API_KEY` - Travel data API
- `SENDGRID_API_KEY` - Email service (prod)
- `SENTRY_DSN` - Sentry error tracking DSN (optional)
- `SENTRY_TRACES_SAMPLE_RATE` - Performance monitoring rate (0.0-1.0, default 0.1)
- `SLACK_WEBHOOK_URL` - Slack Incoming Webhook URL for booking/ticket API error notifications (optional)
- `PLACES_SESSION_TOKEN_SECRET` - Signing key for guest Places image session JWTs (public chat); see `docs/PLACES_IMAGE_SECURITY.md`
- `PLACES_SESSION_TOKEN_EXPIRE_MINUTES` - Lifetime for guest Places session tokens (default 60)
- `S3_PHOTOS_BUCKET` - Private S3 bucket for user profile photos (e.g. `myvoya-staging-photos`); local dev uses MinIO bucket `myvoya-local-photos`
- `S3_PHOTOS_REGION` - Region for the photos bucket (default `us-east-1`)
- `S3_ENDPOINT_URL` - Override S3 endpoint (e.g. `http://minio:9000` locally); unset in cloud uses real AWS
- `S3_FORCE_PATH_STYLE` - Force path-style S3 addressing (true for MinIO, false in cloud)
- `AVATAR_MAX_BYTES`, `AVATAR_ALLOWED_MIME`, `AVATAR_MAX_DIMENSION` - Profile photo upload limits

**Frontend** (`.env`, frontend-v2 uses `VITE_*` prefix):
- `VITE_GOOGLE_CLIENT_ID` - OAuth client ID
- `VITE_API_URL` - Backend API URL
- `VITE_SENTRY_DSN` - Sentry error tracking DSN (optional)
- `VITE_ENV` - Environment name (development/staging/production)
- `VITE_GOOGLE_MAPS_API_KEY` - Google Maps API key for hotel location map (optional; map shows placeholder when absent)
- Admin **Discounts** UI is gated by `user.role === 'admin'` and server-side `require_admin`; there is no separate feature flag (kill-switch) for that surface in v1.

## Slash Commands

Custom commands in `.claude/commands/` for common workflows:

**Code Quality**:
- `/code` - Apply comprehensive coding standards
- `/code:python` - Python-specific standards
- `/lint` - Run linting and formatting

**Testing**:
- `/test` - Run all test suites
- `/test:unit` - Unit tests only (fast)
- `/test:e2e` - Playwright E2E tests
- `/test:coverage` - Generate coverage reports (80% minimum)

**Git & CI/CD**:
- `/commit` - Create conventional commit with Co-Authored-By
- `/ci:check` - Check GitHub Actions CI status

**GitHub**:
- `/gh:issue` - Create issues with templates (task, bug, feature)

## GitHub Issue Templates

Issue forms in `.github/ISSUE_TEMPLATE/` use a shared structure: reporters describe **current behavior** (what happens today) and **expected behavior** (what should happen), which keeps triage and QA aligned on intent.

```bash
gh issue create --template task.yml
gh issue create --template bug_report.yml
gh issue create --template feature_request.yml
```

**Naming Conventions**:
- Tasks: `[TASK] Add profile fields`
- Bugs: `[BUG] Login fails with OAuth`
- Features: `[FEATURE] Real-time notifications`

**Mandatory Requirements** (all issues):
- Unit tests for new functionality
- Documentation updates (CLAUDE.md, API docs)
- Testing requirements in acceptance criteria

## Key Features

### Airport Resolution System
- **29,000+ airports** worldwide from mwgg/Airports GitHub repository
- **Multi-layered resolution**: IATA/ICAO codes, city names, partial matches
- **Question context awareness**: Resolves ambiguous user inputs based on conversation
- **Location**: `app/domains/airport/airport_resolver.py`

### Flight Booking System
- **End-to-end booking flow**: Search → Results → Selection → Details → Confirmation
- **Natural language support**: "book option 1", "book cheapest", ordinal numbers
- **Smart date parsing**: Auto-selects next year for past dates, word numbers
- **Curated results**: Lowest Price 💵, Fastest ⚡, Best Value ⭐
- **FlightLogic API Reference**: `dev-tools/extern/flightlogic_apis/` (vendor docs), `dev-tools/docs/flightlogic-field-definitions.md`
- **Location**: `app/ai/flight_booking_handler.py`, `app/ai/enhanced_flight_handler.py`
- **Best Value (Best Flights) scoring** (formula, normalization, time penalties): `docs/FLIGHT_FEATURES.md#best-value-best-flights-scoring`

### G2A voucher redemption (manual discount codes)
- **Traveler flow**: On flight/hotel review, enter a pre-generated `VOYA-XXXX-XXXX` code; `POST /api/vouchers/apply` reserves it against the booking reference; payment is created for the discounted USD total; `POST /api/vouchers/release` or TTL clears abandoned holds. Redemption to `used` happens on payment success webhooks (Revolut/Stripe), not on the client.
- **Admin flow**: Profile menu **Discounts** (admin role) → `/admin/discounts` to generate batches, inspect codes, and download CSV for G2A SafeKeys upload. Backend: `require_admin` on `/api/admin/discounts*`.
- **USD only**: Voucher face values and booking totals for this program are USD; see `local-ops/plans/PLAN_g2a-voucher-redemption.md`.
- **Domain**: `backend_python/app/domains/discount/`; migration `006_discounts_collection_indexes.py`.
- **Frontend**: `frontend-v2/src/features/discount/`, `frontend-v2/src/api/vouchersApi.ts`, `frontend-v2/src/api/adminDiscountsApi.ts`.

### Hotel Booking System
- **End-to-end booking flow**: Search → Room Rates → Rate Validation → Guest Details → Payment → Confirmation
- **Natural language support**: "book option 1", "book cheapest", "book highest rated", ordinal numbers
- **Smart date parsing**: Same patterns as flights (relative dates, word numbers, auto-year selection)
- **Curated results**: Best Value ⭐, Lowest Price 💵, Highest Rated 🏆
- **Multi-room support**: 1-5 rooms with configurable adults/children per room
- **City disambiguation**: Google Geocoding API resolves ambiguous city names
- **Two entry paths**: Chat-based (JWT URL) and direct booking interface
- **FlightLogic Hotel API**: Search, room rates, rate rules validation, booking
- **Location**: `app/ai/hotel_booking_handler.py`, `app/ai/enhanced_hotel_handler.py`, `app/domains/hotel/`
- **Documentation**: `docs/HOTEL_BOOKING_CERTIFICATION_PLAN.md`, `docs/HOTEL_API_INTEGRATION.md`

### Sticky Intent System
- **High confidence threshold**: 0.9+ required to establish intent
- **Context persistence**: Maintains BOOK_FLIGHT or BOOK_HOTEL intent for unclear messages
- **Override logic**: Only changes intent with 0.9+ confidence
- **Location**: `app/ai/intent_recognizer.py`

### Chatbot Interface
- **Context management**: Tracks `chat_id` for conversation continuity
- **Welcome message**: Displays immediately for all users
- **Real-time responses**: AI-powered conversation with Google Gemini
- **Location**: `frontend-v2/src/features/chat/`
- **frontend-v2 chat message types**: `message`, `typing`, `flight_search_results`, `hotel_search_results`, `itinerary_results`. Itinerary card (ItineraryResultMessage) shows message + "View itinerary" button → `/itinerary`. Type guard: `isItinerarySearchResults()`. Layout: `LayoutWithChat` = persistent `ChatPanel` (left) + `ContentPanel` (right) with `Outlet` for home/itinerary/flights/hotels.
- **Flight recommendations**: Chat flight results hydrate `cachedFlightResults` in Redux and auto-redirect to `/flights/search`; `FlightSearchPage` detects the cache hit via `areFlightParamsEqual` and renders the cached results without re-fetching. The previous `/flights/recommendations` route + `FlightsPreferencesComponent` have been removed.
- **Hotel recommendations**: Chat hotel results hydrate `cachedHotelResults` in Redux and auto-redirect to `/hotels/search`; `HotelSearchPage` detects the cache hit via `areHotelParamsEqual` and renders the cached results without re-fetching. The previous `/hotels/recommendations` route + `HotelRecommendationsPage` / `HotelsPreferencesComponent` / `HotelRecommendationsMap` / `HotelsMobileMapOverlay` have been removed.
- **Public chat rich results** (`/public/chat/*`): Guest users see the same 2-column layout (chat + content panel) as authenticated users. Route tree: `/public/chat` (standalone chat), `/public/chat/itinerary`, `/public/chat/flights/search`, `/public/chat/hotels/search`. Layout: `PublicChatWithContentLayout` (replaces old `PublicChatLayout`/`PublicChatPage`). CTAs ("View flights/hotels/itinerary") navigate to public content routes instead of gating. "Book Now" and "Save Itinerary" remain auth-gated via `usePublicChatConversionGate`. Post-auth: `PublicRoute` maps `/public/chat/*` → authenticated equivalents; `PublicChatPostAuthConversionTracker` auto-saves stashed itinerary on `itinerary_save` intent. Path helpers: `getContentDomain()`, `getContentRoutePrefix()`, `publicToAuthRoute()`, `isPublicChatContentRoute()` in `features/routing/constants.ts`. **Email registration → verification → `/complete-registration`:** when the guest started from a public *content* route, the authenticated return path is stashed in `voya_public_chat_return_to` (TTL 24h); `CompleteRegistrationPage` and `PublicRoute` consume or peek it so the user lands on the same content area (e.g. `/flights/search`) instead of only `/chat`. Instant login/OAuth still rely on `PublicRoute` + current URL. **Cross-tab data persistence:** both flight and hotel results flow via in-memory Redux caches (`cachedFlightResults`, `cachedHotelResults`) — session-scoped, no localStorage persistence. Cleared on logout via `clearAuth`.

### Itinerary Capabilities API (n8n Integration)
- **Purpose**: Exposes backend's LangGraph tools as HTTP endpoints for n8n workflow
- **Why**: n8n was using Google Places API (incomplete data) and Gemini (non-deterministic) for airport resolution. Backend has 29K+ airports database with proven resolution logic.
- **Authentication**: `X-API-Key` header with `N8N_CAPABILITIES_API_KEY` environment variable
- **Base URL**: `/api/itinerary/capabilities/`

**Endpoints**:
| Endpoint | Purpose | Response Status |
|----------|---------|-----------------|
| `POST /resolve-location` | Airport/city resolution with disambiguation | `resolved`, `needs_user_choice`, `no_own_airport`, `not_found` |
| `POST /parse-dates` | Natural language → ISO dates | `success`, `error` |
| `POST /search-flights` | Curated flight search (cheapest, fastest, best_value) | `success`, `error` |
| `POST /search-hotels` | Placeholder (not yet implemented) | `error` |

**Key Status Types for `/resolve-location`**:
- `resolved`: Single airport found (e.g., "Barcelona" → BCN)
- `needs_user_choice`: City has multiple airports (e.g., "London" → LHR, LGW, STN)
- `no_own_airport`: City has no airport, shows nearest (e.g., "Utrecht" → AMS, RTM)
- `not_found`: Could not resolve location

**Location**: `app/api/itinerary/capabilities.py`, `app/api/itinerary/schemas.py`
**Tests**: `tests/unit_tests/test_api/test_itinerary_capabilities.py` (12 tests)
**Plan Document**: `PLAN_CAPABILITIES_API_N8N_INTEGRATION.md` (detailed implementation history)

### Save Itinerary Feature

- **Purpose**: Persist AI-generated itineraries and access them later
- **Flow**: Chat (itinerary_results) → auto-save on generation in ChatService → MongoDB `saved_itineraries`; response includes `saved_itinerary_id`. No frontend save button. Works for both V1 (LangGraph supervisor) and V2 Supervisor flows.
- **API**:
 | Endpoint | Method | Purpose |
 |----------|--------|---------|
 | `/api/itineraries` | POST | Save itinerary (auth required; kept for future use, e.g. edited itineraries) |
 | `/api/itineraries` | GET | List saved itineraries |
 | `/api/itineraries/:id` | GET | Get one (owner only) |
 | `/api/itineraries/:id` | DELETE | Delete (owner only) |
- **Frontend**: ItineraryResultMessage has "View itinerary" only. When `saved_itinerary_id` exists → navigates to `/itinerary/:id` (fetch from API); otherwise → `/itinerary` with state. Header dropdown "Itineraries" → `/itineraries` list page; View from list → `/itineraries/:id` (no chat). Same ItineraryPage used for both; layout differs (LayoutNoChat vs LayoutWithChat).
- **Booking linkage**: Successful flight/hotel bookings can store `saved_itinerary_id` on `booking_events` (optional client field + server ownership check); itineraries list/detail expose `linked_bookings` for chips; active itinerary id for booking is `activeSavedItineraryIdForBooking` in `uiSlice` (sessionStorage).
- **Location**: `app/domains/saved_itinerary/`, `app/domains/chat/service.py` (auto-save), `app/api/saved_itineraries.py`, `frontend-v2/src/api/itinerariesApi.ts`

## Docker Development

### Docker Compose Architecture

**Project uses modular Docker Compose files**:
- `compose.yaml` - Convenience file (includes compose.dev.yaml)
- `compose.dev.yaml` - Complete dev stack (MongoDB, n8n, frontend, backend, MailHog, mock APIs)
- `compose.test.yaml` - Complete test stack (fully isolated with different ports/networks/volumes)

### Development and Test Environments

**Complete Isolation**: Dev and test environments are fully isolated and can run simultaneously without conflicts.

**Key Differences**:
| Aspect | Development | Test |
|--------|-------------|------|
| Build | Volume mounts (hot-reload) | Production-style (root Dockerfile) |
| Frontend | Live source at `/app` | Built static files |
| Backend | Source mounted, auto-reload | Source at `/app/backend` |
| Purpose | Active development | E2E/integration testing |

**Port Mapping**:
| Service | Dev Port | Test Port |
|---------|----------|-----------|
| Frontend (Vite dev) | 3002 | - |
| Backend API (serves SPA in test) | 8000 | 8001 |
| MongoDB | 27017 | 27018 |
| Mongo Express | 8081 | 8082 |
| MailHog | 8025 | 8026 |
| FlightLogic Mock | 8002 | 8004 |
| FlightLogic Inspector | 8003 | - |
| Strapi CMS | 1337 | - |
| Strapi Postgres | 5433 | - |
| n8n | 5678 | - |
| ngrok | 4040 | - |

```bash
# Development Environment (Frontend 3002, Backend 8000, MongoDB 27017, etc.)
docker compose up -d

# Test Environment (Backend serves SPA at 8001, MongoDB 27018, etc.)
docker compose -f compose.test.yaml up -d

# Run Both Simultaneously (no conflicts - ports are hardcoded)
docker compose up -d && docker compose -f compose.test.yaml up -d

# View logs
docker compose logs -f backend
docker compose -f compose.test.yaml logs -f backend-test

# Stop services
docker compose down
docker compose -f compose.test.yaml down
docker compose -f compose.test.yaml down -v  # + remove volumes
```

**Project Names**:
- Dev: `voya-dev` (all containers prefixed with `voya-dev-`)
- Test: `voya-test` (all containers prefixed with `voya-test-`)

**Networks**:
- Dev: `voya-dev-network`
- Test: `voya-test-network`

**Volumes**:
- Dev: `voya-dev-mongodb-data`, `voya-dev-frontend-vite-node-modules`, etc.
- Test: `mongodb_test_data`, etc.

## Getting Help

- **Issues/Questions**: Create GitHub issue with appropriate template
- **API Reference**: http://localhost:8000/api/docs (Swagger UI)
- **Interactive API Testing**: http://localhost:8000/dev/api-tester.html
- **CI/CD Status**: `gh pr checks` or `gh run list`
- **Troubleshooting**: See `docs/TROUBLESHOOTING.md`

## Integration Points

- Frontend-v2 (Vite) build copied to `backend/static` for serving SPA
- Backend serves React app for unmatched routes (SPA support)
- Chatbot uses Google Generative AI with sticky intent recognition
- Airport resolution integrates with FlightLogic for validated travel data
- Flight booking provides complete search-to-reservation workflow

## Database

- **Python Backend**: MongoDB with Motor (async ODM)
- **Models**: users, trips, chats, chatHistory, counters, bookings
- **Authentication**: JWT tokens (no session storage, 30-min expiry)

---

**Last Updated**: April 2026
**Maintainer**: Team Voya
**Questions**: Create GitHub issue or see role-specific CLAUDE.md files

## 📝 Documentation Maintenance Protocol

**YOU MUST update docs when making changes:**
- Changed architecture/patterns → Update relevant CLAUDE.md or docs/ file
- Added new feature → Update appropriate section (don't append to end)
- Fixed bug/changed behavior → Update affected documentation inline

**❌ NEVER:**
- Append session logs to documentation files (creates bloat)
- Add duplicate information to multiple sections
- Leave outdated information after making changes
- Create new files when existing files should be updated

**✅ ALWAYS:**
- Edit existing sections inline (find the right place, update it)
- Remove outdated information when updating
- Keep documentation concise and current
- Verify changes don't contradict other docs
