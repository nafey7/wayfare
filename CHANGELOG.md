# Changelog

All notable changes to the Voya travel platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **User profile photos**: Authenticated users can upload, replace, and delete a profile photo via `PUT /api/user/me/photo` (multipart) / `DELETE /api/user/me/photo`. Originals live in a private S3 bucket (`myvoya-${env}-photos`) accessed only by ECS task roles; imgproxy + CloudFlare serve sized variants. Backend stores `users.photo_key`; user responses include `photo_urls.{sm,md,lg}` so the frontend never builds imgproxy URLs itself. EXIF (incl. GPS) is stripped on re-encode; uploads are validated for MIME, size (5 MiB), and dimensions (4096 px, decompression-bomb guard). Local dev runs MinIO (`compose.dev.yaml` + `compose.test.yaml`) as a drop-in S3 replacement — no AWS credentials required. Terraform module `photos_bucket` wired into staging/prod; imgproxy task role granted `s3:GetObject`. New shared `<VoyaAvatar>` and `<AvatarUpload>` components consume `photo_urls`. Migration `011` defensively initializes `photo_key=null`. Plan: `local-ops/plans/PLAN_user-profile-photos.md`.

- **G2A / manual voucher redemption (USD)**: Pre-generated `VOYA-XXXX-XXXX` codes in MongoDB `discounts` collection (migration 006). Travelers apply on flight/hotel review (`/api/vouchers/apply` / `release`); booking events store `voucher_redemption_id` and discount cents; payment webhooks redeem reserved vouchers atomically. Admins manage batches and CSV export under `/api/admin/discounts*` and `frontend-v2` `/admin/discounts`. Structured logs and Sentry events scrub voucher-shaped `code` fields and `voucher_code` / `discount_code` / `promo_code`. Plan: `local-ops/plans/PLAN_g2a-voucher-redemption.md`.

### Changed

- **Public chat post-signup redirect**: Email registration from a public content route (`/public/chat/flights/*`, `/hotels/*`, `/itinerary`, etc.) stores the authenticated equivalent path in `voya_public_chat_return_to`; after `/complete-registration`, navigation uses it (with TTL and path validation) so users rejoin the same surface as instant login. `PublicRoute` peeks the same key as a fallback for authenticated `/complete-registration`. Hotel recommendation data (`lastHotelRecommendationsData`) is persisted to localStorage so the verification tab has content to display; cleared on logout. Flight recommendations now flow through `cachedFlightResults` in Redux (session-scoped, no localStorage persistence) — `FlightSearchPage` reads the cache when chat-driven params match.

- **Authenticated app shell**: Replaced `MainLayout`’s text **`Header`** with **`NavbarHome`** (`variant="app"`, theme gradient). **`/home`** keeps **`NavbarHome`** `variant="home"` (frosted bar). **`/public/chat`** (guest) shows the gradient bar without account actions. Removed `components/layout/Header.tsx`.
- **Public guest chat default**: `VOYA_FEATURE_FLAG_PUBLIC_CHAT` defaults to **on** in application settings and in Terraform ECS env for **test** and **production** (staging was already on). Set `VOYA_FEATURE_FLAG_PUBLIC_CHAT=false` to disable.

### Added

- Profile and itinerary flight lists: **origin, destination, and marketing airline** from persisted `booking_events` snapshots (one-way, round-trip with optional return IATAs, multi-city per leg). `GET /api/flights/my-bookings` returns typed `BookingEventResponse` rows (not raw Mongo); new bookings and trip-details sync populate `arrival_airport_iata`, optional return leg IATAs, and `primary_marketing_airline_name` (#666).
- "Pending" status chip on saved itinerary cards when no flight/hotel bookings are linked; existing "Confirmed" chip remains for itineraries with linked bookings (#667)
- **Public landing guest chat** (feature-flagged): unauthenticated chat on `/` via `POST /api/public/chat/message` with `X-Public-Chat-Session`, per-IP rate limits, and guest session persistence; frontend config exposes `public_chat_enabled`. Post–sign-in conversion intent from gated CTAs is emitted to GTM as `public_chat_post_auth_conversion` when applicable.
- **Full-page public chat** (`/public/chat`): guest chat route with explicit **View flights / View hotels** CTAs (no auto-redirect to flight recommendations); post–sign-in navigation to `/chat` via `PublicRoute`. Guest `sessionStorage` clearing policy documented (clear on guest “new chat” or a future claim API—not on every login). Docs: `docs/FRONTEND_BACKEND_COLLABORATION.md`, `docs/ARCHITECTURE.md`.

- **Public chat rich results** (#744): Guest users on `/public/chat` see the same 2-column layout (chat sidebar + content panel) as authenticated users — flight/hotel recommendations, full search results, itineraries, and Google Maps. New `PublicChatWithContentLayout` replaces `PublicChatLayout`/`PublicChatPage`. "View flights/hotels/itinerary" CTAs navigate to public content routes; "Book Now" and "Save Itinerary" remain auth-gated. Post-auth redirect maps public routes to authenticated equivalents; `itinerary_save` intent auto-saves stashed itinerary. Path helpers: `getContentDomain()`, `getContentRoutePrefix()`, `publicToAuthRoute()`, `isPublicChatContentRoute()`. No backend changes.

### Infrastructure

- Docker/CI: Prod & staging deploy workflows now read `VITE_STRAPI_URL` from GitHub secrets (`VITE_STRAPI_URL_PROD` / `VITE_STRAPI_URL_STAGING`) instead of hardcoding the URL; test deploy adds both `VITE_STRAPI_URL` and `VITE_STRAPI_API_TOKEN` build args (using staging secret names).
- Terraform (ECS task env): `VOYA_FEATURE_FLAG_PUBLIC_CHAT` (default **on** in all envs), `PUBLIC_CHAT_MESSAGES_PER_MINUTE` for staging, test, and production.

## [v2026.4.1] - 2026-04-03 - GDS Book-Before-Pay, Ticket Alerts, AI Optimization, Strapi CMS & Landing Redesign

### Added

#### GDS Booking Flow (#586)
- Book-before-pay: flight booking is completed via `POST /flights/book` after card validation and before Revolut capture; HTTP **409 Conflict** shown as non-dismissible inline error with Pay button disabled
- PENDING booking status with deferred Booking API; pre-supplier resolution, ownership checks, and Mongo sync failure handling
- Skip FlightLogic ticket issue when trip details already show TICKETED; normalize GDS enum fields
- Centralized FlightLogic ticket status parsing with admin GDS retry tests

#### GDS Ticket Time Limit Alerts (#591)
- Hourly ECS job scans `booking_events` for GDS flight bookings whose ticket time limit falls within a configurable window before expiry
- Slack warnings with lease-based deduplication (`--dry-run` and `--limit` supported on the job CLI)
- New `booking_events` domain with repository and alert service; MongoDB index migration

#### Flight Search & Booking (#592)
- `FlightSearchRequest` journey rules (OneWay / Return / Circle) with Pydantic validation; legacy `RoundTrip` and single `origin_destination_info` with `return_date` normalized server-side (see `docs/FLIGHT_FEATURES.md`)
- Booking session `search_params` use shared helpers in `app/domains/flight/journey_params.py` (topology inference, legacy coercion)
- Circle journey leg rows, labels, and modal mapping in search UI
- No-results message when all flights fail revalidation (#601)
- Auto-redirect to recommendations page in book-everything auto-chain flow (#624)

#### AI / LLM Optimization (#584, #593)
- Multi-provider LLM factory with per-component model config (`app/ai/graph/llm_factory.py`)
- Itinerary agent optimization: reduced redundant tool calls and latency
- Cross-intent handoff fix: itinerary agent hands back to supervisor on mid-collection flight/hotel intent switch (#612)
- Passenger recognition and trip duration fixes

#### Landing Page & Strapi CMS (#610, #623)
- Public landing (`/`) vs authenticated home (`/home`) split with stable marketing DOM ids (`LANDING_PAGE_IDS`), semantic sections, and `Navbar`
- Shared layout via `LandingPageSections` and `useLandingPageController`
- Strapi headless CMS integration for landing/home hero and sections (opt-in via `VITE_STRAPI_URL`); CSS-safe background URL validation; `console.warn` on Strapi fetch failures
- CI job for frontend lint, type-check, build, and tests
- **Note:** Strapi production environment deployment scheduled for 2026-04-08

#### Other
- PII verification for viewing passport details: email OTP step-up verification before revealing passport number/expiry in profile Travel Details. New `pii_verification` domain with HMAC-only OTP storage, 10-min expiry, 5 max attempts, and short-lived PII view token (#519)
- Google Places hotel image fallback with `HotelImageWithFallback` and `AuthenticatedImage` components (#555)
- Chat flight results: recommendations map with origin/destination markers from backend coordinates, fallback to known city/IATA coordinates, blue route line
- Chat flight results: auto-redirect to `/flights/recommendations` with two-column layout
- Search-to-chat redirect: landing search stores intent; post-auth redirect to `/chat?prompt=...`
- Shared auth redirect utilities (`authRedirectUtils`) and constants

### Changed

- Revolut cleanup on pending GDS failure and 409 book-before-pay handling; gate LCC-only confirmation emails
- Supervisor V2 updates for multi-agent routing
- detect-secrets baseline improvement to avoid merge conflicts
- PR review docs: added Terraform/infra checklist, emphasized self-review before PR submission

### Fixed

- Restored automatic prompt replay after landing/home search by mounting embedded `ChatBot` on `/chat`
- Fixed `AttributeError` in FlightLogic airport resolution fallback path: `_resolve_via_flightlogic` now uses `airport_resolver.get_airport_info` for coordinate lookup
- Fixed flight results showing as plain text in auto-chain flow (#621)
- Fixed empty results card when all flights fail revalidation (#600)
- Fixed itinerary agent not handing back to supervisor on mid-collection intent switch (#611)
- Fixed flaky `parse_dates` test using future-relative dates

### Infrastructure

- Strapi CMS: Dockerfile, local dev environment with Content-Type Builder, deploy workflows for staging and prod
- Terraform: Strapi modules (`strapi`, `strapi-rds`, `strapi-media`, `strapi-secrets`), LLM model config env vars, `OPENAI_API_KEY` in secrets module, IAM and security module updates
- New `secrets-baseline-refresh` GitHub Actions workflow
- Frontend CI checks added to PR pipeline

## [v2026.2.5] - 2026-02-27 - Frontend-v2 Hotel Booker, Chat Filters, Revolut Payments & GTM Migration

### Added

#### Hotel Booker (frontend-v2) (#375, #376)
- Full hotel booking flow in frontend-v2: search, room rates, guest details, payment, confirmation (#375)
- Hotel filters and sorting in frontend-v2 (price, rating, property type, refundable, facilities, distance, locality) (#375)
- Chat hotel filters: price range, star rating, property type, refundable, facilities, distance, locality (#375)
- Google Maps map view for hotel search results
- Hotel confirmation email uses frontend-v2 `view-booking` link and booking details page matching flights
- Hotel chat results now route to frontend-v2 instead of dev_ui
- Aligned hotel guest title options and types with backend (adult/child)
- Aligned hotel search results in chat with select/redirect API and room_configuration
- Default 2 adults for hotel search

#### Flight Booker (frontend-v2) (#359, #433)
- Flight booking filters in chat interface (#359)
- City-wise flight search with multi-city IATA validation (#433)
- Return leg airport filters and airport name display
- Chat flight UX aligned with frontend: in-app flow, segment/layover display, typed utils
- Parallel airport resolution, URL restore constants, airline logo display
- Shared filter styles, generic toggles, unified airport helpers

#### AI / Planning Agent (#345, #350, #356, #376, #379, #406)
- Langfuse tracing and prompt management for `general_travel_handler` (#345)
- First-layer AI handling for broad travel queries and missing filters (#350)
- `DECLINING_TO_ANSWER` intent with infinite-loop guard for planning agent clarification flow (#376, #379)
- Optional origin in planning agent, skip on first decline (#379)
- Itinerary arrival/departure days are now time-agnostic; day scheduling syncs with flight times (#406)
- Improved prompt and model upgrade for general travel handler (#356)
- UX improvements for unsupported features and destination preferences

#### Admin Bookings
- Admin bookings list and detail view with hotel support
- `MyVoya` admin role migration (`set_myvoya_admin_role.py`, run-once, `@myvoya.ai` users get admin)
- Admin role included in auth JWT
- Post-retry emails, PNR issuance, and TravelNext links on booking detail pages
- Hotel booking-details error surfacing, retry confirmation dialogs

#### Payments (Revolut) (#438)
- Replaced Stripe with Revolut in frontend-v2 reusable payment flow
- Revolut mode depends on `VITE_ENV` with sandbox default
- Revolut order created on review step and passed via navigation state
- Payment errors displayed in toast instead of alert banner (#438)

#### Tracking & Analytics
- Reddit Pixel integration for frontend-v2 conversion tracking (signup, Google OAuth)
- dataLayer / GTM: replaced Reddit Pixel with GTM/Hotjar scripts and migrated all tracking to dataLayer events
- Intermediate funnel events for GTM dataLayer

#### Email & Notifications
- Slack notifications for flight/hotel booking and ticket order API errors (#346)
- Authenticated email links for flight tickets issued and booking confirmation
- `useEmailLinkAuth` hook for frontend-v2 authenticated email link handling
- Fallback `hotel_name` in booking confirmation email

#### Other
- `logo-light2.png` UI asset with gitignore exception
- `parseCoord` utility for coordinate parsing
- Flight duration and preferred airline filter support in chat (#359)

### Changed

#### Frontend-v2 Architecture
- Normalized API boundary to camelCase via RTK Query `transformResponse` and `toSnakeCase(body)`
- Normalized flight types to camelCase across API, filters, and tests
- Centralized fare parsing and currency formatting across flight and hotel features (`flightUtils`)
- Locale-aware currency formatting with `Intl.NumberFormat` for flight booking amounts (cents and major units)
- Reduced `as any` usage across flight features with typed backend types
- `FlightDetailsPage`: stricter typing for segment details with camelCase/snake_case alignment
- Facilities filter uses AND logic; Revolut no-fallback mode
- Voya chat aligned with frontend: centering, header, send behavior

#### Backend
- Documented and applied cents vs base-currency convention for flight and hotel amounts
- Hotel price display uses backend-derived amounts on payment page; `total` preferred over `originalTotal` in filters
- Clear `skipped_fields` when user adds origin via modification flow
- Restored "Preference + Country Combined" section in `flight_agent` prompt
- Meta-instruction moved out of template to prevent leaking into AI output
- Refundable filter now excludes hotels with unknown `fare_type`
- `BookingEventModel` extended with optional fields for hotel support, LCC, dates, amounts, email tracking

### Fixed

#### Hotel Booker (frontend-v2)
- Fixed duplicate room rates API calls by caching response when navigating to rooms page
- Fixed duplicate `create-order` API call on hotel payment page
- Fixed room rates duplicate fetches on refresh
- Fixed hotel rooms persistence on page refresh
- Fixed `GuestInfo` redirect issue

#### Flight Booker (frontend-v2)
- Fixed round-trip flight segment splitting for city-wise search
- Fixed chat flight/hotel filters not populated on booker pages after redirect (#431)
- Fixed chat flight/hotel filter issues from tester feedback (#439)
- Fixed redirect URL filter behavior (#359)

#### AI / Backend
- Fixed fallback prompt `KeyError` when Langfuse is unavailable
- Fixed PR review issues for `general_travel_handler` (#345)
- Addressed code review findings for flight filtering, hotel chat filters, and general travel handler

#### Auth & Tracking
- Fixed Google auth for frontend-v2 by using ID token credential flow (#416)
- Fixed Reddit pixel re-initialization on navigation
- Resolved GTM dataLayer missing intermediate funnel events

### Infrastructure
- **Dockerfile switched from frontend (CRA) to frontend-v2 (Vite)**, production builds now use Vite (#422)
- CI deploy workflows: `REACT_APP_GOOGLE_CLIENT_ID` build arg renamed to `VITE_GOOGLE_CLIENT_ID`
- New optional env var: `SLACK_WEBHOOK_URL` (Slack webhook for booking/ticket API error notifications)
- New DB migration: `set_myvoya_admin_role.py` (run-once, sets `@myvoya.ai` users to admin role)
- `compose.dev.yaml`: frontend-v2 service now loads `.env` file
- Updated secrets baseline

### Tests
- Added backend unit tests for admin bookings (`BookingService` and API endpoints)
- Added smart date parsing unit tests
- Fixed unit test mocks for conftest, smart date parsing, hotel events, payment webhooks
- Fixed smart date parsing test by patching `utc_date` in both modules
- Unit test fixes: conftest Sentry stub, date parser patches, hotel fallback assertions, Revolut booking mocks

---

## [2025.12.7] - 2025-12-29 - Round-Trip Flights, Hotel Platform Fee & UI Enhancements

### Added

#### Round-Trip Flight Support (#174)
- Full round-trip flight display in search results with outbound and return legs
- Return flight information displayed on flight cards
- Departure date shown in search results summary
- Flight prices visible on result cards
- Redesigned expanded flight card layout with better price visibility

#### Hotel Platform Fee (#198)
- **10.5% platform fee** for hotel bookings (vs 5% for flights)
- Platform fee fields added to `HotelSearchResult` and `HotelRateRulesResponse` schemas
- Room-level pricing with `original_price_per_night`, `original_total_price`, `platform_fee_percentage`
- Platform fee breakdown display in hotel-booker review step
- Updated payment service to support different fees by booking type

#### Hotel Booker UI Enhancements (#203)
- Comprehensive filtering: price range, property type, rating, fare type, distance, facilities, locality
- Sorting: price low-to-high and high-to-low
- Collapsible filter panel with active filters display and clear all functionality
- Enhanced image handling with camelCase/snake_case support and fallback
- Results count showing filtered vs total hotels
- Google Maps integration

#### Flight Filters (#200, #201)
- **Separate outbound/return stops filters** for round-trip flights (direct, 1 stop, 2+ stops)
- **Duration filters include layover time** for accurate total travel time
- Dynamic slider max values based on actual search results (no hardcoded 24h limit)
- Active filter badges with remove functionality for return leg filters

#### Legal & Compliance (#183)
- Terms of Use and Privacy Policy modal dialogs
- Footer component with legal document links
- Structured legal document content in `termsData.js` and `privacyData.js`
- Footer integrated into flight-booker and hotel-booker pages

#### Booking Flow Improvements (#185, #199)
- **Cancellation policy display** in flight and hotel booking confirmation emails
- Cancellation policy stored in database for email fallback
- **Auth tokens in email links** (12-hour expiry) to prevent user mismatch errors
- Booking-auth endpoint creates session and returns refresh_token
- Flight-booker URL parameter preservation during authentication

#### Platform Fee Display (#170)
- `original_total_fare` field in FlightSummaryDTO
- Platform fee breakdown in FlightDetailsModal and FlightBookingSummary
- Platform fee breakdown in flight-booker dev UI
- Fixed hotel name row rendering in payment confirmation emails

### Fixed

#### LangGraph Flight Search (d807052)
- **Fixed frontend crash** when displaying LangGraph flight search results
- Added `search_params` extraction from tool calls for frontend compatibility
- Added airport name enrichment using AirportResolver (city/airport names were empty)
- Added `duration`, `departure_date`, `arrival_date` to segment info
- Frontend now supports both `origin_*` (legacy) and `departure_*` (LangGraph) field names
- Added null check in duration parsing to prevent crashes

#### Hotel Filters (#205)
- Fixed fare type filter showing 0 results when both refundable and non-refundable selected
- Filter now skips filtering when both options are checked

#### Flight Display (#174)
- Fixed bug in 3-segmented flights display
- Fixed return flight durations calculation
- Show dates when outbound/return dates differ
- Grammar improvements in flight descriptions

#### Email & Events (#170)
- Fixed HTML attribute duplication in email transaction ID row
- Resolved circular import in hotel event handler using lazy import
- Enhanced hotel event handler logging (debug → warning)

### Changed
- Payment service now accepts `booking_type` parameter for fee calculation
- Separated `FLIGHTS_PLATFORM_FEE_PERCENTAGE` (5%) and `HOTELS_PLATFORM_FEE_PERCENTAGE` (10.5%)
- Hotel-booker passes `booking_type` to payment intent creation

### Tests
- Added unit tests for payment confirmation email builder with hotel name scenarios
- Added unit tests for hotel event handler enrichment logic
- Updated hotel test dates to March 2026
- Updated flight pricing test to verify `original_total_fare` field

---

## [2025.12.6] - 2025-12-19 - LangGraph Hotels & Flight Revalidation

### Added
- Vendor-agnostic `LLMService` protocol in `integrations/llm/` module (#131)
- `GeminiLLMService` implementation with proper error handling (#131)
- 29 unit tests for LLM service layer (#131)
- Email routing with stored contact email for guest bookings (#44)
- Fare enrichment from both LCC and GDS sources (#44)
- GET /api/bookings/{reference} endpoint (#44)
- FlightLogic API credential validation on startup (#46)
- Date of birth validation for adult passengers (#47)
- Passenger count validation (max 9, infant ratios) (#47)
- Clickable navigation for flight booker steps (#48)
- Enhanced error message extraction (#49)
- Duplicate booking prevention (#49)
- Race condition prevention for booking button (#49)
- Direct payment access via email links (#50)
- Auto-authentication for email link users (#50)
- Backend passenger age validation for adults (≥18), children (2-11), infants (<2) (#51)
- Booking reference input validation with regex pattern (#52)

### Changed
- Migrated from deprecated `google-generativeai` SDK to `google-genai` (#131)
- `IntentRecognizer` now uses `LLMService` protocol via dependency injection (#131)
- Email button text: "View Details" → "Proceed to Checkout" (#44, #50)
- Booking API returns cached data (avoids FlightLogic reuse errors) (#50)
- Refactored fare enrichment method into 4 testable methods (#52)
- Replaced brittle HTML template string replacement with placeholders (#52)

### Fixed
- Email routing for guest users uses stored contact email (#44)
- TypeError when FlightLogic SequenceNumber is None (#46)
- "[object Object]" error messages replaced with meaningful text (#49)
- Duplicate bookings when navigating back from payment (#49)
- Test files relocated to correct directory structure (#51)
- Type errors in fare enrichment and booking validation (#52)
- Debug console logging removed from flight-booker using debugLog wrapper (#53)
- Timezone assumptions fixed to use UTC for consistent date validation (#53)
## [2025-10-28] - Staging Environment Configuration & Deployment

### Added
- **Staging Terraform Configuration Updates**:
  - Added Stripe secrets to secrets module (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`)
  - ECS task definition dynamically loads Stripe secrets when available
  - Updated `FRONTEND_URL` to production domain (`https://staging.myvoya.ai`)
  - Replaced logs module with CloudWatch log group data source

### Changed
- **Staging Infrastructure**:
  - Email activation links now use correct domain (`https://staging.myvoya.ai` instead of ALB placeholder)
  - MongoDB Atlas whitelist updated to full VPC CIDR (`10.0.0.0/16`)
  - MongoDB connects via HTTPS through NAT Gateway (no custom security group rules needed)
  - Stripe webhook configured for staging environment

### Documentation
- **Added `terraform/environments/staging/DEPLOYMENT_GUIDE.md`** - Complete staging deployment guide covering:
  - Initial infrastructure deployment
  - Secrets configuration (all 10 required secrets)
  - Stripe setup (keys and webhook)
  - MongoDB Atlas IP whitelisting
  - Security group configuration
  - API whitelisting (Google, FlightLogic)
  - Docker image build and deployment
  - Post-deployment configuration
  - Troubleshooting guide
  - Disaster recovery procedures
- **Updated `terraform/environments/staging/README.md`** - Added reference to deployment guide and secrets checklist

### Infrastructure
- **Staging NAT Gateway IP**: `98.89.125.207` (for API whitelisting)
- **Stripe Webhook**: Configured for `https://staging.myvoya.ai/api/webhooks/stripe`
- **MongoDB Connection**: Working with VPC peering and security group rules
- **SSL Certificate**: ACM certificate configured for `staging.myvoya.ai`

### Notes
- Manual AWS CLI actions (secret values, webhook configuration) are documented in deployment guide
- MongoDB connects via HTTPS/NAT Gateway (default security group rules sufficient)
- VPC peering exists but is not required for MongoDB connectivity
- Stripe webhook must be recreated if staging environment is destroyed

## [2025-10-20] - Stripe Payment Integration & Security Enhancements

### Added

#### Stripe Payment Integration (Issues #29, #33)
- **Payment API Endpoints**:
  - `POST /api/payments/create-intent` - Create payment intent with 5% platform fee
  - `GET /api/payments/transaction/{payment_intent_id}` - Retrieve transaction details
  - `POST /api/payments/payouts/release` - Admin-only payout release to suppliers
- **Stripe Webhook Handler**:
  - Webhook endpoint at `/webhooks/stripe` with signature verification
  - 8 event handlers: `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.succeeded`, `charge.failed`, `transfer.created`, `transfer.updated`, `account.updated`, `account.application.deauthorized`
  - Production-enforced signature verification, development mode allows skipping
- **Payment Domain Architecture**:
  - Complete domain structure: service, repository, schemas, enums, exceptions
  - Transaction model for MongoDB payment tracking
  - Platform fee calculation (5% automatic deduction)
  - Stripe Connect transfers to supplier accounts (FlightLogic)
- **Flight Booking Payment Integration**:
  - Payment validation in booking confirmation flow
  - Optional payment at booking creation (GDS flights pay before ticket issuance)
  - Required payment for LCC flights
  - Demo payment mode: `payment_intent_id: 'demo_payment_intent'`
  - Booking-payment linking via `payment_id` field
- **Flight-Booker UI Enhancements**:
  - Stripe.js integration with secure card element
  - Payment mode selector: Demo (checkbox) vs Stripe (real payment)
  - Payment summary: Flight Price + Platform Service Fee (5%) = Total to Pay
  - Real-time card validation and error handling
  - Payment confirmation and retry logic
- **API Tester Payment Interface**:
  - New Payments tab in `/dev/api-tester.html`
  - Test payment intent creation, transaction retrieval, payout release
  - Payment flow documentation and examples
- **Configuration Options**:
  - `STRIPE_WEBHOOK_SECRET` - Webhook signature verification secret
  - `STRIPE_USE_CONNECT_TRANSFERS` - Toggle Connect transfers for testing

#### Comprehensive Payment Documentation
- **`docs/PAYMENTS.md`** (2,088 words) - Complete Stripe integration guide
  - Payment flow diagrams
  - Platform fee model (5% to Voya, 95% to supplier)
  - Payment domain structure (DDD)
  - API endpoints with examples
  - Frontend Stripe.js integration patterns
  - Security best practices
- **`docs/WEBHOOKS.md`** (2,083 words) - Webhook setup and testing guide
  - Consolidated from 3 existing webhook docs
  - 8 webhook event handlers reference
  - Local testing with ngrok (step-by-step)
  - Stripe CLI testing alternative
  - Signature verification and troubleshooting
- **`docs/FLIGHT_BOOKER_UI.md`** (2,515 words) - Flight-booker dev tool documentation
  - 7-step booking flow walkthrough
  - Demo vs Stripe payment modes
  - Session-based workflow (3-hour TTL)
  - GDS vs LCC flight handling
- **Updated Documentation**:
  - `docs/ARCHITECTURE.md` - Payment domain in DDD structure
  - `docs/FRONTEND_BACKEND_COLLABORATION.md` - Payment Integration section (1K words)
  - `docs/LOCAL_DEVELOPMENT.md` - Stripe Payment Integration Setup
  - `docs/DOCUMENTATION_MAP.md` - New Payments & Webhooks sections

### Changed

#### Booking Session Enhancements
- Session TTL increased from 2 to 3 hours
- Sessions no longer deleted immediately after booking (allows payment page refreshes)
- Session auto-expires after TTL instead of immediate deletion
- Added `payment_id` field to booking request schema

#### Security Improvements
- **Webhook Signature Verification**: Enforced in production, optional in development
- Environment-based security controls (`settings.ENVIRONMENT`)
- Payment validation before booking creation
- Stripe Connect secure fund transfers

#### Code Quality Improvements
- Fixed deprecated `datetime.utcnow()` → `datetime.now(UTC)` in booking sessions
- Moved logging imports to module level in `flights.py`
- Consolidated payment variable naming (`paymentIntentId` used consistently)
- Ruff formatting applied to 3 files (webhooks, payment service, tests)

#### UX Improvements
- Clearer payment summary display: Flight Price ($95) + Platform Fee ($5) = Total ($100)
- Renamed "Booking Amount" → "Flight Price" for clarity
- Added "Platform Service Fee (5%)" label
- Changed "Total" → "Total to Pay" for explicitness

### Fixed
- **CRITICAL SECURITY**: Webhook signature verification vulnerability (webhooks now rejected in production without valid signature)
- Timezone-aware datetime handling in booking session service (deprecated `utcnow()` removed)
- Payment intent ID variable naming inconsistencies in flight-booker UI
- Session expiration calculation using deprecated UTC methods
- Payment summary display ambiguity (users confused about platform fee calculation)

### Security
- 🔒 **Production webhook signature verification enforced** (HTTP 401 if missing)
- 🔒 Payment data validation before booking creation
- 🔒 Stripe Connect secure fund transfers (never touch customer funds directly)
- 🔒 PCI-compliant payment processing via Stripe.js (no card data on servers)

### Related GitHub Issues
- ✅ Addresses #29 (Backend Stripe Connect payment infrastructure) - ~80% complete
  - Missing: Automated Monday 16:00 CET payout scheduling (#38)
- ✅ Addresses #33 (Flight booking payment integration) - **COMPLETE**
- ⚠️ Partially addresses #31 (Customer payment UI) - Implemented in HTML flight-booker
  - Needs: React/Redux migration, PSD2/SCA verification, refund/dispute UI
- 📋 Requires #37 (FlightLogic supplier onboarding) - Configuration pending
- 📋 Requires #38 (Automated Monday payouts) - Not yet implemented

## [2025-09-23] - Enhanced Flight Search & Parsing

### Added

#### Enhanced Date Range Parsing & Field Validation
- **Natural Date Ranges**: Flight search now supports expressions like "anytime between 11 and 15 Oct"
- **Enhanced Flight Results Display**: Added calendar symbols (📅) and departure dates to flight options
- **Robust Field Validation**: Improved handling of date objects, strings, and dictionaries
- **Better Error Handling**: Enhanced exception handling for authentication tokens and flight handlers

#### Differentiated Flight Search Results (Issue #8)
- **Curation Algorithm**: Flight search results now provide 3 distinct options:
  1. **💵 LOWEST PRICE** - Absolute cheapest flight regardless of other factors
  2. **⚡ FASTEST** - Shortest total travel time (including connections and layovers)
  3. **⭐ BEST VALUE** - Cheapest flight meeting quality constraints
- **Smart Deduplication**: When cheapest equals fastest, only shows 2 options to avoid unnecessary duplication
- **Quality Constraints for Best Value**:
  - Similar number of stops as fastest option (within 1)
  - Maximum 1 hour longer than fastest flight
  - Departure: 9:00 AM - 8:00 PM local time
  - Arrival: 9:00 AM - 8:00 PM local time

## [2025-09-22] - Natural Language Enhancements

### Added

#### Natural Language Return Date Support (Issue #11)
- **Word Number Support**: Round-trip return dates now support natural language with both numeric digits and word numbers
- **Enhanced Expression Types**:
  - Duration (numeric): "2 weeks later", "5 days later", "1 month later"
  - **Duration (words)**: "two weeks later", "three days later", "five days later" ✨ NEW
  - **Alternative phrasings**: "returning two weeks", "back three days", "in five days" ✨ NEW
  - **Articles**: "a week later", "an hour later" ✨ NEW
  - Weekdays: "following Friday", "next Monday"
  - Weeks/Weekends: "next week", "following weekend", "week after"
- **Smart Calculation**: Return dates calculated from departure date, not today's date
- **Examples**:
  - Departure: Oct 15, "two weeks later" → Oct 29 (+14 days)
  - Departure: Oct 15, "returning three days" → Oct 18 (+3 days)
  - Departure: Oct 15 (Wed), "following Friday" → Oct 17

#### Question Context-Aware Flight Field Assignment
- **Problem Fixed**: User responses like "Paris" were ambiguous - could be origin or destination
- **Smart Context Tracking**: Enhanced flight handler now tracks question context for accurate field mapping
- **Enhanced Field Assignment**: System considers which question was asked to properly assign user responses

## [Earlier] - Smart Date Parsing

### Added

#### Smart Date Parsing (Issue #6)
- **Auto-select Next Year for Past Dates**: When users enter dates without year that would be in the past (e.g., "Feb 14" in October), system automatically selects next year's occurrence
- **Examples**:
  - "Feb 14" (when today is Oct 8, 2025) → 2026-02-14
  - "Dec 25" (when today is Oct 8, 2025) → 2025-12-25 (still future)
  - "Feb 14 2027" → 2027-02-14 (explicit year preserved)
- **Edge Cases Handled**: Leap years (Feb 29), year boundaries (Dec/Jan), explicit years preserved
- **Context-aware** for round trip return dates

### Known Limitations
- **All-in-one messages**: Field extraction may require follow-up questions (~60% accuracy)
  - Example: "London to JFK Oct 15" may extract destination as "JFK Oct"
  - **Workaround**: Question-answer flow has ~95% accuracy and always works correctly
- **Recommendation**: For complex bookings, let chatbot ask questions step-by-step for best results
