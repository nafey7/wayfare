# Voya Documentation Map

Complete guide to all documentation in the Voya project, organized by role and topic.

---

## 🚀 Quick Start by Role

### 🐍 Backend Developer
**Start here**: [`backend_python/CLAUDE.md`](../backend_python/CLAUDE.md)

**Your reading list** (~30K tokens):
1. Root `CLAUDE.md` - Project overview (15 min)
2. `backend_python/CLAUDE.md` - Python/FastAPI quick start (10 min)
3. `backend_python/docs/CODING_STANDARDS.md` - Complete Python standards (60 min reference)
4. `backend_python/docs/TESTING_STANDARDS.md` - Unit testing patterns (20 min)
5. `docs/ARCHITECTURE.md` - System design and DDD (30 min)

### ⚛️ Frontend Developer
**Start here**: [`docs/FRONTEND_BACKEND_COLLABORATION.md`](FRONTEND_BACKEND_COLLABORATION.md)

**Your reading list** (~28K tokens):
1. Root `CLAUDE.md` - Project overview (15 min)
2. `frontend-v2/` + `docs/FRONTEND_BACKEND_COLLABORATION.md` - API contracts and React patterns (30 min)
3. `docs/ARCHITECTURE.md` - System design (30 min)

### 🧪 QA/Testing Developer
**Start here**: [`testing/CLAUDE.md`](../testing/CLAUDE.md)

**Your reading list** (~20K tokens):
1. Root `CLAUDE.md` - Project overview (15 min)
2. `testing/CLAUDE.md` - Playwright E2E patterns (20 min)
3. `docs/TESTING.md` - Testing strategy (10 min)
4. `backend_python/docs/TESTING_STANDARDS.md` - Unit testing (20 min)

### 🔧 Full-stack Developer
**Start here**: [Root `CLAUDE.md`](../CLAUDE.md)

**Your reading list** (~42K tokens):
1. Root `CLAUDE.md` - Complete overview (20 min)
2. All subdirectory CLAUDE.md files (40 min)
3. `docs/ARCHITECTURE.md` - System design (30 min)
4. `docs/TROUBLESHOOTING.md` - Common issues (reference as needed)

### 🔐 DevOps/Platform Engineer
**Start here**: [`docs/CI_CD.md`](CI_CD.md)

**Your reading list**:
1. Root `CLAUDE.md` - Project overview (15 min)
2. `docs/CI_CD.md` - GitHub Actions workflows (20 min)
3. `docs/CODE_QUALITY.md` - Tool configuration (15 min)
4. `docs/LOCAL_DEVELOPMENT.md` - Docker setup (15 min)

---

## 📚 Documentation by Category

### 🎯 Getting Started (5-15 min read)

#### Navigation Hub
- **[CLAUDE.md](../CLAUDE.md)** (11.5K)
  - Role-based quick starts
  - Documentation map
  - Pre-commit hooks (Boy Scout Rule)
  - Slash commands
  - GitHub issue templates

#### Quick Start Guides
- **[README.md](../README.md)** (GitHub landing page)
  - Features overview
  - Docker quick start
  - Architecture summary
- **[backend_python/CLAUDE.md](../backend_python/CLAUDE.md)** (9.9K)
  - Python/FastAPI setup
  - Development commands
  - Boy Scout Rule summary
- **[docs/FRONTEND_BACKEND_COLLABORATION.md](FRONTEND_BACKEND_COLLABORATION.md)** - React/API integration
- **[testing/CLAUDE.md](../testing/CLAUDE.md)** (10.8K)
  - Playwright E2E setup
  - Test environment configuration
- **[admin/CLAUDE.md](../admin/CLAUDE.md)** (5.4K)
  - Admin dashboard setup

---

### 🏗️ Architecture & Design (30-60 min read)

- **[ARCHITECTURE.md](ARCHITECTURE.md)** (12K) ⭐ **Comprehensive**
  - System overview and data flow
  - Domain-Driven Design (DDD) structure
  - Sticky intent system (0.9+ confidence threshold)
  - Airport resolution system (29K+ airports)
  - Flight booking flow
  - State management patterns

- **[FRONTEND_BACKEND_COLLABORATION.md](FRONTEND_BACKEND_COLLABORATION.md)** (14.6K) ⭐ **Comprehensive**
  - API contracts (Swagger as Single Source of Truth)
  - Authentication flow (Google OAuth + JWT)
  - Error handling conventions
  - Data transformation (snake_case ↔ camelCase)
  - Request/response patterns

- **[FLIGHT_FEATURES.md](FLIGHT_FEATURES.md)** (5.9K)
  - Advanced flight search features
  - Natural language support
  - Smart date parsing
  - Curated results (Lowest Price, Fastest, Best Value)
  - **Best Value (Best Flights) scoring**: formula, normalization, time penalties — [FLIGHT_FEATURES.md#best-value-best-flights-scoring](FLIGHT_FEATURES.md#best-value-best-flights-scoring)

- **[CAPABILITIES_API_N8N_INTEGRATION.md](CAPABILITIES_API_N8N_INTEGRATION.md)** (NEW)
  - Capabilities API for n8n Itinerary Agent
  - Airport resolution, date parsing, flight search endpoints
  - Authentication and response status types
  - n8n workflow integration details
  - Implementation and deployment guide

---

### 📝 Coding Standards (Reference)

#### Python (Backend)
- **[backend_python/docs/CODING_STANDARDS.md](../backend_python/docs/CODING_STANDARDS.md)** (18K) ⭐ **Comprehensive Reference**
  - Core principles and design philosophy
  - Type hints (required on all public functions)
  - Async/await patterns (CRITICAL - event loop safety)
  - Pydantic v2 models
  - Error handling and retry logic
  - Security best practices
  - Testing patterns
  - Tool configuration (Ruff, MyPy, Bandit)

#### JavaScript/React (Frontend)
- ❌ **Missing**: No dedicated frontend coding standards document
- **Current**: Patterns in `docs/FRONTEND_BACKEND_COLLABORATION.md`
- **Gap**: Need comprehensive JavaScript/React standards equivalent to backend

---

### 🧪 Testing (20-60 min read)

#### Strategy & Overview
- **[TESTING.md](TESTING.md)** (4.3K)
  - Overall testing strategy
  - E2E testing with Playwright
  - Docker test environment

#### Unit & Integration Testing
- **[backend_python/docs/TESTING_STANDARDS.md](../backend_python/docs/TESTING_STANDARDS.md)** (~10K)
  - Unit testing patterns
  - Mocking MongoDB (AsyncMock)
  - Mocking external APIs (httpx_mock)
  - Coverage requirements (80% minimum)

#### E2E Testing
- **[testing/CLAUDE.md](../testing/CLAUDE.md)** (10.8K)
  - Playwright patterns
  - Page object model
  - Email testing with MailHog
  - Cross-browser testing
  - Database cleanup strategies

**Note**: `testing/CLAUDE.md` and `testing/README.md` previously had 60% overlap - now resolved with README as redirect.

---

### 🔧 Development Tools (10-30 min read)

#### Code Quality
- **[CODE_QUALITY.md](CODE_QUALITY.md)** (4.9K)
  - Ruff (linting & formatting)
  - MyPy (type checking)
  - Bandit (security scanning)
  - ESLint (frontend)
  - Tool configuration

#### Frontend Assets & i18n
- **[ASSET_OPTIMIZATION.md](ASSET_OPTIMIZATION.md)** – Image asset guidance (PNG/WebP, when to optimize, hosting options)
- **[FRONTEND_I18N.md](FRONTEND_I18N.md)** – i18n readiness for landing page (prop overrides, translation key structure)

#### CI/CD
- **[CI_CD.md](CI_CD.md)** (8.4K)
  - GitHub Actions workflows
  - Job dependencies and parallelization
  - Caching strategy
  - Troubleshooting CI failures
  - Pre-commit hooks in CI context

#### Local Development
- **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** (5.4K)
  - Docker Compose setup
  - Environment configuration
  - Troubleshooting setup issues

---

### 👥 Team Workflow (15-30 min read)

- **[TEAM_WORKFLOW.md](TEAM_WORKFLOW.md)** (6.6K)
  - Git branching strategy
  - Pull request process
  - Conventional commits
  - Collaboration patterns

- **[CODE_REVIEW.md](CODE_REVIEW.md)** (NEW)
  - Test requirements policy (standard vs urgent bugfix)
  - Review checklist (testing, functionality, security)
  - Approval criteria and process

---

### 🚨 Troubleshooting (Reference as needed)

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** (16K) ⭐ **Comprehensive Reference**
  - Environment setup issues
  - Docker problems
  - Database connection errors
  - Authentication failures
  - API integration issues
  - Testing failures
  - Recent fixes and solutions

---

### 💳 Payments & Webhooks (30-60 min read)

- **[PAYMENTS.md](PAYMENTS.md)** (2.1K) ⭐ **Comprehensive**
  - Complete Stripe payment integration guide
  - Payment flow (frontend → backend → Stripe)
  - 5% platform fee model with Stripe Connect
  - Payment domain structure (service, repository, schemas)
  - API endpoints (/api/payments/*)
  - Frontend Stripe.js integration
  - Demo mode vs production payment
  - Security best practices

- **[WEBHOOKS.md](WEBHOOKS.md)** (2.1K) ⭐ **Comprehensive**
  - Stripe webhook setup and testing
  - 8 event handlers (payment_intent.*, charge.*, transfer.*, account.*)
  - Local testing with ngrok (step-by-step)
  - Testing with Stripe CLI alternative
  - Signature verification
  - Troubleshooting webhook issues
  - Production webhook configuration

- **[FLIGHT_BOOKER_UI.md](FLIGHT_BOOKER_UI.md)** (2.5K)
  - Flight-booker dev tool documentation
  - Purpose and use cases vs AI chatbot
  - 7-step booking flow walkthrough
  - Payment modes (demo checkbox vs Stripe)
  - Session-based workflow (3-hour TTL)
  - GDS vs LCC flight handling
  - Testing scenarios and troubleshooting

---

## 🔍 Documentation by Topic

### Authentication & Security
- **Primary**: `ARCHITECTURE.md` → Authentication section
- **API Flow**: `FRONTEND_BACKEND_COLLABORATION.md` → Authentication
- **Implementation**: `backend_python/CLAUDE.md` → JWT patterns
- **Standards**: `backend_python/docs/CODING_STANDARDS.md` → Security section
- **Public chat Places images** (guest itinerary photos, session JWT, rate limits, Cloudflare): [`PLACES_IMAGE_SECURITY.md`](PLACES_IMAGE_SECURITY.md)
- **Gap**: ❌ No consolidated security guide covering OAuth flow, CORS, general rate limiting (Places image hardening is documented separately above)

### Database (MongoDB)
- **Primary**: `ARCHITECTURE.md` → Data flow
- **Connection**: `backend_python/CLAUDE.md` → MongoDB with Motor
- **Testing**: `backend_python/docs/TESTING_STANDARDS.md` → Mocking MongoDB
- **Gap**: ❌ No database schema documentation (collections, indexes, relationships)

### AI & Chatbot
- **Primary**: `ARCHITECTURE.md` → Sticky intent system
- **Features**: `FLIGHT_FEATURES.md` → Natural language processing
- **Implementation**: `backend_python/CLAUDE.md` → Google Gemini integration
- **Status**: ✅ Well-documented

### Flight Search & Booking
- **Primary**: `FLIGHT_FEATURES.md` (comprehensive)
- **Architecture**: `ARCHITECTURE.md` → Flight booking flow
- **Backend**: `backend_python/CLAUDE.md` → FlightLogic API integration
- **API Reference**: `dev-tools/extern/flightlogic_apis/` (vendor documentation)
  - `flight_availability.md` - Search API schema and examples
  - `flight_booking.md` - Booking API flow
  - `flight_revalidate.md` - Fare revalidation
  - `dev-tools/docs/flightlogic-field-definitions.md` - Field validation rules
- **Implementation**: `backend_python/integrations/flightlogic/`
- **Mock Server**: `backend_python/tests/mocks/flightlogic/` (local testing)
- **Status**: ✅ Well-documented

### Hotel Search & Booking
- **Primary**: `HOTEL_API_INTEGRATION.md` (integration status summary)
- **API Reference**: `.local/dev-tools/extern/flightlogic_apis/hotels/` (not tracked in git)
  - `FLIGHTLOGIC_HOTEL_API_TEST_RESULTS.md` - Test results with sample responses
  - `CURL_EXAMPLES_AND_RESPONSES.md` - Complete curl examples with full JSON responses
  - `01_introduction.md` through `10_errors_and_faqs.md` - Complete API documentation
- **Implementation**: `backend_python/integrations/flightlogic/hotel_client.py`
- **Domain Layer**: `backend_python/app/domains/hotel/` (schemas, service)
- **API Endpoints**: `backend_python/app/api/hotels.py`
- **Status**: ⏳ Phase 1 complete (backend API), Phase 2 pending (chat integration)

### Testing
- **Strategy**: `TESTING.md`
- **E2E**: `testing/CLAUDE.md`
- **Unit**: `backend_python/docs/TESTING_STANDARDS.md`
- **CI/CD**: `CI_CD.md` → E2E workflow
- **Status**: ✅ Well-documented

### Pre-commit Hooks
- **Primary** (SSoT): Root `CLAUDE.md` → Pre-commit Hooks section (comprehensive Boy Scout Rule)
- **Backend Summary**: `backend_python/CLAUDE.md` → References root
- **Tool Config**: `CODE_QUALITY.md` → References root
- **CI Context**: `CI_CD.md` → References root
- **Status**: ✅ Proper SSoT structure

### Payments & Webhooks
- **Primary**: `PAYMENTS.md` (comprehensive Stripe integration guide)
- **Webhooks**: `WEBHOOKS.md` (webhook setup and testing)
- **Dev Tool**: `FLIGHT_BOOKER_UI.md` (flight-booker with payment testing)
- **Architecture**: `ARCHITECTURE.md` → Payment domain in DDD structure
- **API Integration**: `FRONTEND_BACKEND_COLLABORATION.md` → Payment Integration section
- **Local Setup**: `LOCAL_DEVELOPMENT.md` → Stripe Payment Integration Setup
- **Status**: ✅ Well-documented (October 2025 update)

### API Integration
- **Primary**: `FRONTEND_BACKEND_COLLABORATION.md` (comprehensive)
- **Documentation**: Root `CLAUDE.md` → API Documentation URLs
- **Backend**: `backend_python/CLAUDE.md` → API development
- **Frontend**: `docs/FRONTEND_BACKEND_COLLABORATION.md` → API consumption
- **Payment APIs**: `PAYMENTS.md` → Payment endpoints
- **Status**: ✅ Well-documented

### Deployment
- **Quick Start**: `README.md` → Docker deployment
- **Environment**: Root `CLAUDE.md` → Environment Variables section
- **Gap**: ❌ No comprehensive deployment guide (AWS infrastructure, procedures, rollback)

---

## 📊 Documentation Statistics

### By Size
1. **backend_python/docs/CODING_STANDARDS.md** - 18K (largest, comprehensive reference)
2. **TROUBLESHOOTING.md** - 16K (comprehensive troubleshooting)
3. **FRONTEND_BACKEND_COLLABORATION.md** - 14.6K (API contracts)
4. **ARCHITECTURE.md** - 12K (system design)
5. **docs/FRONTEND_BACKEND_COLLABORATION.md** - API integration
6. **CLAUDE.md** (root) - 11.5K
7. **testing/CLAUDE.md** - 10.8K
8. **backend_python/docs/TESTING_STANDARDS.md** - ~10K
9. **backend_python/CLAUDE.md** - 9.9K
10. **CI_CD.md** - 8.4K

### By Type
- **CLAUDE.md files**: 5 files (navigation and role-specific patterns)
- **docs/ files**: 9 files (deep technical documentation)
- **backend_python/docs/ files**: 2 files (Python-specific standards)
- **README.md files**: 4 files (3 redirects, 1 landing page)

### Token Budget by Role
- **Backend Developer**: ~30K tokens (47% of original)
- **Frontend Developer**: ~28K tokens (53% reduction)
- **Testing Developer**: ~20K tokens (60% reduction)
- **Full-stack Developer**: ~42K tokens (30% reduction)

---

## 🚩 Known Gaps

### High Priority
1. ❌ **JavaScript/React Coding Standards** - No frontend equivalent to `CODING_STANDARDS.md`
2. ❌ **Database Schema Documentation** - No MongoDB collection/index reference
3. ❌ **Deployment Guide** - No AWS deployment procedures

### Medium Priority
4. ❌ **Security Consolidated Guide** - Security info scattered across files
5. ❌ **Monitoring & Observability** - CloudWatch mentioned but not documented
6. ❌ **Production Runbook** - No operational troubleshooting for production

### Low Priority
7. ❌ **API Client Generation** - How to generate TypeScript types from OpenAPI
8. ❌ **Performance Benchmarking** - No load testing guide
9. ❌ **Dependency Management** - No upgrade strategy documentation
10. ❌ **Email Templates** - Email system exists but templates not documented

---

## 📖 Documentation Best Practices

### Single Source of Truth (SSoT)
- **Root CLAUDE.md** - Primary navigation hub, pre-commit policy
- **Subdirectory CLAUDE.md** - Role-specific patterns with references to root
- **README.md** - GitHub landing page (user-focused)
- **docs/** - Deep technical documentation

### Cross-References
All CLAUDE.md files now include:
- 📍 Current location
- 🔙 Parent document
- 📚 Related documentation
- Links to deep-dive docs

### Maintenance
- **Last Updated** timestamps in each file
- **Next Review** dates for time-sensitive content (e.g., Google GenAI migration)
- Consistent terminology and naming

---

## 🔄 Recent Improvements

### Phase 1: Critical Fixes (Completed)
- ✅ Fixed Google GenAI EOL date inconsistencies (November 30, 2025)
- ✅ Fixed React version claims (18.2, not 19)
- ✅ Verified pre-commit policy alignment (proper SSoT structure)
- ✅ CRA frontend removed; frontend-v2 (Vite) is the sole frontend
- ✅ Added Motor deprecation notice to CODING_STANDARDS.md

### Phase 2: Consolidation (Completed)
- ✅ Replaced `testing/README.md` with redirect (reduced from 190 to 63 lines)
- ✅ Simplified `CODE_QUALITY.md` to reference root for policy
- ✅ Updated `CI_CD.md` to reference root for pre-commit details
- ✅ Streamlined root `README.md` (removed environment variable duplication)

### Phase 3: Navigation (Completed)
- ✅ Added navigation sections to all subdirectory CLAUDE.md files
- ✅ Created this Documentation Map
- ✅ Fixed remaining "React 19" references in admin/CLAUDE.md

### Results
- **~10K token reduction** (25-30% of redundant content)
- **Improved discoverability** with clear navigation paths
- **Better SSoT adherence** with consistent cross-references
- **Easier maintenance** with changes needed in fewer places

---

## 🎯 Quick Navigation

**Need to...**
- 🚀 **Get started?** → [Root CLAUDE.md](../CLAUDE.md)
- 🐍 **Develop backend?** → [backend_python/CLAUDE.md](../backend_python/CLAUDE.md)
- ⚛️ **Develop frontend?** → [docs/FRONTEND_BACKEND_COLLABORATION.md](FRONTEND_BACKEND_COLLABORATION.md)
- 🧪 **Write tests?** → [testing/CLAUDE.md](../testing/CLAUDE.md)
- 🏗️ **Understand architecture?** → [ARCHITECTURE.md](ARCHITECTURE.md)
- 🔧 **Fix an issue?** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 👥 **Collaborate?** → [TEAM_WORKFLOW.md](TEAM_WORKFLOW.md)
- 🔐 **Set up CI/CD?** → [CI_CD.md](CI_CD.md)

---

**Last Updated**: October 2025
**Maintainer**: Documentation Team
**Feedback**: Create GitHub issue with label `documentation`
