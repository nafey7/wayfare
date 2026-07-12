# Flight Booking Flow Documentation

**Purpose**: Complete documentation of the flight booking process with two entry points: chat-based selection and direct flight booker interface.

**Last Updated**: March 30, 2026

---

## Overview

The Voya flight booking system supports **two distinct entry paths**:

1. **Chat Entry Path**: User searches and selects flight via AI chatbot, then redirects to flight booker with pre-selected flight
2. **Direct Entry Path**: User accesses flight booker directly and searches for flights in the interface (required for FlightLogic certification)

Both paths converge at the fare validation step and follow the same booking completion flow.

---

## Multi-city (Circle) — direct flight booker

For `journey_type: Circle` with two or more segments, the backend runs **N parallel OneWay** FlightLogic searches (`backend_python/app/domains/flight/service.py`) so each leg has its own `session_id`. The user selects a fare per leg, pays once (Revolut), and each leg creates a **separate** MongoDB `booking_events` document linked by `parent_voya_booking_reference` (synthetic group id, e.g. `VOYA-MC-…`).

**Rollback / feature flag**

- Environment variable **`MULTICITY_PARALLEL_SEARCH`** (default `true` in `backend_python/app/core/config.py`). When `false`, Circle search uses a **single** legacy FlightLogic Circle request (one combined itinerary list) instead of N OneWay calls.

**Related API**

- **`GET /api/flights/multicity-booking-context?voya_booking_reference=…`** — for the authenticated owner, returns `parent_voya_booking_reference` and all leg summaries from Mongo (used on the flight booking details page).

**E2E**

- Skipped placeholder: `testing/e2e/tests/flights/multicity-booking.spec.js` (enable when the test stack has deterministic multicity search and payment).

---

## Entry Point 1: Chat-Based Flow

**Use Case**: Standard user journey via AI chatbot
**User Experience**: Natural language search → Curated results → Selection → Booking form

### Step 1: Chat Search

**Location**: `frontend-v2/src/features/chat/`
**AI Handler**: `backend_python/app/ai/enhanced_flight_handler.py`

```
User: "I need a flight from Amsterdam to London tomorrow"
    ↓
Intent Recognition (BOOK_FLIGHT)
    ↓
Field Collection (origin, destination, dates, passengers)
    ↓
FlightLogic API Search (/flight_search)
    ↓
Result Curation (Cheapest 💵, Fastest ⚡, Best Value ⭐)
    ↓
Display 3-5 options in chat
```

**Field Collector**: `app/ai/flight_field_collector.py`

- Extracts: origin, destination, departure_date, return_date (optional), adults, children, infants
- Handles relative dates ("tomorrow", "next week", "3 days from now")
- Smart year selection (past dates → next year)

**Search Endpoint**: `POST /api/flights/search`

- Request: `FlightSearchRequest` (origin, destination, dates, passengers, cabin_class)
- Response: `FlightSearchResponse` (itineraries, session_id from FlightLogic)

### Step 2: Chat Selection

**AI Handler**: `backend_python/app/ai/flight_booking_handler.py`

```
User: "book option 1" / "book cheapest" / "book the first one"
    ↓
Selection Parsing (5 pattern levels)
    ↓
MongoDB Session Storage (2-hour TTL)
    ↓
JWT Token Generation (1-minute expiry)
    ↓
Redirect URL: /dev/flight-booker/?preflight=<base64_flight_data>
```

**Selection Patterns** (see `parse_flight_selection()`):

1. "option 1/2/3" → Direct number
2. "cheapest" / "lowest price" → Cheapest option
3. "fastest" → Fastest option
4. "best" / "best value" → Best value option
5. Ordinal numbers: "first", "second", "third" (word form)

**Session Data Stored**:

```python
{
    "session_id": "unique_session_id",
    "user_id": str(user.id),
    "selected_flight": flight_itinerary,
    "search_params": {origin, destination, dates, passengers},
    "booking_stage": "flight_selected",
    "created_at": datetime.utcnow(),
    "expires_at": datetime.utcnow() + timedelta(hours=2)
}
```

### Step 3: Flight Booker Redirect

**Location**: `backend_python/dev_ui/flight-booker/index.html`

```javascript
// On page load
checkPreflightData() {
    const urlParams = new URLSearchParams(window.location.search);
    const preflightData = urlParams.get('preflight');

    if (preflightData) {
        // Decode base64 flight data
        const flightData = JSON.parse(atob(preflightData));
        prePopulateFlightData(flightData);
        // Auto-triggers fare validation
    }
}
```

**Preflight Data Structure** (base64 encoded):

```json
{
    "session_id": "FlightLogic_session_id",
    "selected_flight": {...},
    "fare_source_code": "ABC123",
    "inbound_fare_code": "DEF456",
    "search_params": {...}
}
```

---

## Entry Point 2: Direct Flight Booker

**Use Case**: FlightLogic certification, direct access, re-search scenarios
**URL**: `http://localhost:8000/dev/flight-booker/`

### Step 1: Authentication

**Auto-login** (development only):

- Test user account automatically logs in on page load
- Endpoint: `POST /api/auth/login`
- Stores JWT token for subsequent API calls
- See `app/database/seed.py` for test user credentials

**Production**: User must be logged in via Google OAuth or email/password.

### Step 2: Search Interface

**Form Fields**:

- Journey Type: One-way / Return
- Origin: City/airport name (autocomplete from 29K+ airports)
- Destination: City/airport name (autocomplete)
- Departure Date: Date picker (min: today)
- Return Date: Date picker (if round-trip, min: departure date)
- Passengers: Adults (1-9), Children (0-9), Infants (0-9)
- Cabin Class: Economy (default)

**Validation**:

- Total passengers ≤ 9
- Infants ≤ Adults (lap infants)
- Departure date ≥ today
- Return date > departure date (if round-trip)

**Airport Resolution**: `resolveAirport(input)`

- Searches 29K+ airports by IATA code, city name, airport name
- Uses `app/domains/airport/airport_resolver.py`
- Returns IATA code (e.g., "AMS", "LHR")

### Step 3: Search Request

**Endpoint**: `POST /api/flights/search`

**Request Structure**:

```json
{
  "journey_type": "Return",
  "origin_destination_info": [
    {
      "departure_date": "2025-12-25",
      "origin_airport": { "iata_code": "AMS" },
      "destination_airport": { "iata_code": "LHR" }
    },
    {
      "departure_date": "2025-12-30",
      "origin_airport": { "iata_code": "LHR" },
      "destination_airport": { "iata_code": "AMS" }
    }
  ],
  "adults": 1,
  "children": 0,
  "infants": 0,
  "cabin_class": "Economy",
  "direct_flight": 0
}
```

**Backend Flow**:

```
FlightService.search_flights()
    ↓
FlightLogicClient.search_flights()
    ↓
FlightLogic API: POST /flight_search
    ↓
Adapter converts DTOs → Domain models
    ↓
Return: {itineraries: [...], session_id: "..."}
```

**Response**: List of flight itineraries with pricing, session_id from FlightLogic

### Step 4: Results Display

**Frontend Rendering** (see `displaySearchResults()`):

- Shows all available flights from FlightLogic response
- Each option displays:
  - Flight segments (airline, flight number, times, airports)
  - Duration (total + layover time if multi-segment)
  - Stops (direct / 1 stop / 2 stops)
  - Price (with currency)
  - "Select Flight" button

**User Action**: Click "Select Flight" on any option

---

## Converged Flow: Fare Validation to Booking

**Both entry paths converge here** - chat and direct search follow identical steps.

### Step 5: Flight Selection

**Function**: `selectAndRevalidateFlight(itinerary, element)`

**Actions**:

1. Store selected flight globally: `selectedFlight = itinerary`
2. Extract fare codes:
   - `fareSourceCode` (outbound)
   - `inboundFareCode` (return flight, if applicable)
3. Extract session_id from FlightLogic search response
4. Auto-trigger fare validation

### Step 6: Fare Validation (Critical Step)

**Endpoint**: `POST /api/flights/revalidate`
**Function**: `validateFare()`

**Why Required**: Flight prices change rapidly. Validation ensures:

- Fare is still available at the displayed price
- Seat inventory exists
- Get LCC vs GDS determination
- Identify required booking fields (passport, issue date, etc.)

**Request**:

```json
{
  "session_id": "FlightLogic_session_id",
  "fare_source_code": "ABC123",
  "inbound_fare_code": "DEF456",
  "adults": 1,
  "children": 0,
  "infants": 0
}
```

**Backend Flow**:

```
FlightService.revalidate_fare()
    ↓
FlightLogicClient.revalidate_fare()
    ↓
FlightLogic API: POST /revalidate_fare
    ↓
Return: validated_fare_itineraries with updated_pricing
```

**Response Analysis**:

```javascript
{
    is_fare_available: true,
    validated_fare_itineraries: [{
        updated_pricing: {
            fare_type: "WebFare",  // LCC or GDS
            validated_fare_totals: {...},
            fare_breakdown: [...]
        },
        requires_passport: true,
        requires_passport_issue_date: false,
        required_booking_fields: ["passport_number", "passport_expiry", ...]
    }]
}
```

**Frontend Processing**:

- Extract `fare_type`: "WebFare" (LCC) or other (GDS)
- Set `isLCC = (fare_type === 'WebFare')`
- Store `requiresPassport`, `requiresPassportIssueDate`, `requiredBookingFields`
- Store `revalidationResult` globally (for pricing breakdown)
- Display fare rules page with JSON response

**Validation Failure Handling**:

- If `is_fare_available === false`: Show "Fare No Longer Available" error
- Offer "Search Again" button
- Reset selection and return to results

### Step 7: Passenger Information

**UI Section**: Passenger details form (dynamically generated)

**Fields per passenger** (based on validation response):

- **Always required**:

  - Title (Mr/Mrs/Ms/Dr)
  - First Name, Last Name
  - Date of Birth
  - Nationality
  - Gender
  - Passenger Type (Adult/Child/Infant)

- **Conditional (if `requiresPassport === true`)**:

  - Passport Number
  - Passport Country
  - Passport Expiry Date
  - Passport Issue Date (if `requiresPassportIssueDate === true`)

- **Contact Information** (once per booking):
  - Email
  - Country Code + Phone Number

**Validation Rules**:

- Adults: Age ≥ 12 years
- Children: Age 2-11 years
- Infants: Age < 2 years (calculated from DOB)
- Passport expiry must be > 6 months from departure date
- All fields validated before proceeding

**Data Collection**: `collectPassengerData()`

```javascript
{
    adults: [{personal_info, travel_documents}, ...],
    children: [{...}, ...],
    infants: [{...}, ...],
    contact: {email, country_code, phone}
}
```

**Session Persistence**:

```javascript
// Save to sessionStorage for refresh protection
sessionStorage.setItem(`passenger_data_${sessionId}`, JSON.stringify(passengerData));
```

### Step 8: Booking Review

**Function**: `displayBookingReview()`

**Displays**:

1. **Flight Details**:

   - All segments (outbound + return)
   - Departure/arrival times and airports
   - Airline, flight numbers
   - Duration per segment

2. **Passenger Information**:

   - All passengers with names, DOB, nationality
   - Passport details (if provided)

3. **Contact Information**:

   - Email and phone number

4. **Price Summary** (critical - uses `revalidationResult`):
   ```javascript
   // IMPORTANT: Use revalidation pricing, NOT search pricing
   const validatedItinerary = revalidationResult?.validated_fare_itineraries?.[0];
   const pricing = validatedItinerary?.updated_pricing || selectedFlight.pricing;
   ```
   - Base fare per passenger type
   - Taxes and fees breakdown
   - Total fare (validated price)

**Price Breakdown Function**: `buildPriceBreakdownHTML(pricing, currency, adults, children, infants)`

- Extracts fare breakdown from `pricing.fare_breakdown` array
- Separates adult/child/infant fares
- Shows taxes, fees, surcharges
- Displays total with currency

### Step 9: Payment (Stripe Integration)

**Payment Provider**: Stripe (test mode in development)

**Initialization**: `initializeStripePayment()`

```javascript
const stripe = Stripe("pk_test_..."); // Public key
const elements = stripe.elements();
const cardElement = elements.create("card");
cardElement.mount("#card-element");
```

**Payment Flow**:

1. User clicks "Proceed to Payment"
2. Frontend validates card details (Stripe.js)
3. Create PaymentIntent on backend
4. Confirm payment with Stripe
5. On success: Trigger booking creation

**Test Cards** (development):

- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- Requires auth: `4000 0025 0000 3155`

### Step 10: Booking Creation

**Endpoint**: `POST /api/flights/book`
**Function**: `createBooking()`

**Request Structure**:

```json
{
  "session_id": "FlightLogic_session_id",
  "fare_source_code": "ABC123",
  "inbound_fare_code": "DEF456",
  "client_ref": "VOYA-1234567890",
  "contact_information": {
    "email": "user@example.com",
    "country_code": "+31",
    "phone_number": "612345678"
  },
  "passengers": [
    {
      "passenger_type": "Adult",
      "personal_info": {
        "name": {
          "title": "Mr",
          "first_name": "John",
          "last_name": "Doe"
        },
        "date_of_birth": "1990-01-01",
        "nationality": "US",
        "gender": "Male"
      },
      "travel_documents": {
        "passport_number": "AB1234567", // pragma: allowlist secret
        "passport_country": "US",
        "passport_expiry": "2030-12-31",
        "passport_issue_date": "2020-01-01"
      }
    }
  ]
}
```

**Backend Flow**:

```
FlightService.create_booking()
    ↓
Validate payment completed (Stripe)
    ↓
FlightLogicClient.book_flight()
    ↓
FlightLogic API: POST /flight_booking
    ↓
Store booking in MongoDB (bookings collection)
    ↓
Create booking event (BookingCreated)
    ↓
Return: FlightBookingResponse
```

**Response**:

```json
{
    "booking_status": "Confirmed",
    "voya_booking_reference": "VOYA-1234567890",
    "external_booking_reference": "FL-ABC123",
    "pnr": "ABC123",
    "booking_details": {
        "passengers": [...],
        "flights": [...],
        "total_price": 350.00,
        "currency": "EUR"
    }
}
```

**Booking Event Storage** (`app/domains/bookings/schemas.py`):

```python
{
    "voya_booking_reference": "VOYA-xxx",
    "external_booking_reference": "FL-xxx",
    "action": "BOOKED",
    "event_type": "FLIGHT",
    "contact_email": "user@example.com",
    "origin": "AMS",
    "destination": "LHR",
    "departure_date": "2025-12-25"
}
```

### Step 11: LCC Ticket Issuance (if applicable)

**Only for LCC bookings** (`fare_type === "WebFare"`)

**Why Required**: LCC carriers (Ryanair, EasyJet, etc.) require immediate ticket issuance after booking.

**Endpoint**: `POST /api/flights/issue_ticket`
**Timing**: Automatically triggered after successful booking

**Request**:

```json
{
  "session_id": "FlightLogic_session_id",
  "booking_id": "FL-ABC123"
}
```

**Backend Flow**:

```
FlightLogicClient.issue_ticket()
    ↓
FlightLogic API: POST /issue_ticket
    ↓
Return: ticket numbers, e-ticket URLs
```

**GDS Bookings**: Require payment before ticket issuance; see [GDS Ticket Issuance Flow](#gds-ticket-issuance-flow-trip-details-gate).

### GDS Ticket Issuance Flow (Trip Details Gate)

**Purpose**: For GDS (Private/Public fare) bookings, tickets are issued after payment. The system calls **trip details** before the **ticket order API** and uses `ticket_status` to gate the call.

**Call Order**:
1. `POST /api/flights/trip-details` — Returns booking state including `ticket_status`
2. `POST /api/flights/issue_ticket` — Issues tickets via FlightLogic (only when needed)

**Ticket Status Gate**: If `ticket_status` is `Cancelled` or `Ticketed`, the ticket order API is **not** called. This avoids:
- Unnecessary FlightLogic API calls
- Errors from re-issuing already-issued tickets
- Wasted external API quota

**Scope**: GDS flows only. LCC (WebFare) issues tickets at booking time.

**Implementation**: `app/domains/flight/service.py` (`issue_tickets`), `app/api/admin.py` (GDS retry). See `PLAN_GDS_TICKET_STATUS_GATE` for full plan.

### Step 12: Confirmation & Email

**Confirmation Page Display**:

- ✅ Booking Confirmed!
- VOYA Reference: `VOYA-1234567890`
- Supplier Confirmation: `FL-ABC123` (or PNR)
- Flight details summary
- Total price paid
- Passenger names
- Download e-tickets (LCC) or booking confirmation (GDS)

**Email Confirmation** (`app/domains/email/`):

- Template: Flight booking confirmation
- Includes:
  - VOYA and supplier references
  - Flight itinerary (all segments)
  - Passenger names
  - Total price
  - Check-in instructions
  - Support contact (support@myvoya.ai)

**Email Builder Logic** (`app/domains/email/builder.py`):

```python
def _build_booking_confirmation(context):
    # Detects flight vs hotel by checking booking_details
    is_flight = "origin" in booking_details or "flight_number" in booking_details

    if is_flight:
        # Check for LCC vs GDS (FSC)
        fare_type = booking_details.get("fare_type")
        is_lcc = fare_type == "WebFare"

        # Use appropriate email template
        if is_lcc:
            return build_lcc_flight_email(context)
        else:
            return build_gds_flight_email(context)
```

**Email Delivery**: SendGrid (production) or MailHog (development)

---

## API Endpoints Summary

### Flight Search & Booking

| Endpoint                    | Method | Purpose                    | Request Model             | Response Model             |
| --------------------------- | ------ | -------------------------- | ------------------------- | -------------------------- |
| `/api/flights/search`       | POST   | Search flights             | `FlightSearchRequest`     | `FlightSearchResponse`     |
| `/api/flights/revalidate`   | POST   | Validate fare availability | `FlightRevalidateRequest` | `FlightRevalidateResponse` |
| `/api/flights/fare-rules`   | POST   | Get fare rules             | `FlightFareRulesRequest`  | `FlightFareRulesResponse`  |
| `/api/flights/book`         | POST   | Create booking             | `FlightBookingRequest`    | `FlightBookingResponse`    |
| `/api/flights/issue_ticket` | POST   | Issue LCC ticket           | `TicketOrderRequest`      | `TicketOrderResponse`      |
| `/api/flights/cancel`       | POST   | Cancel booking             | `FlightCancelRequest`     | `FlightCancelResponse`     |
| `/api/flights/session/{id}` | GET    | Retrieve booking session   | -                         | Session data               |

### Authentication

| Endpoint           | Method | Purpose            |
| ------------------ | ------ | ------------------ |
| `/api/auth/login`  | POST   | User login (JWT)   |
| `/api/auth/google` | POST   | Google OAuth login |

---

## State Management

### Global Variables (Frontend)

```javascript
// Session & Flight Data
let sessionId = null; // FlightLogic session ID
let selectedFlight = null; // Selected flight itinerary
let selectedFlightData = null; // Full selection context
let searchResults = null; // Search results from API

// Fare & Validation
let fareSourceCode = null; // Outbound fare code
let inboundFareCode = null; // Return fare code (if round-trip)
let revalidationResult = null; // Validated pricing (CRITICAL for booking)
let fareRules = null; // Fare rules response

// Booking Type & Requirements
let isLCC = false; // WebFare = true, GDS = false
let requiresPassport = false; // Passport required?
let requiresPassportIssueDate = false; // Issue date required?
let requiredBookingFields = []; // Dynamic field requirements

// Authentication
let accessToken = null; // JWT token
let currentUser = null; // User data
```

### MongoDB Collections

**Bookings** (`bookings` collection):

```javascript
{
    _id: ObjectId,
    voya_booking_reference: "VOYA-xxx",
    external_booking_reference: "FL-xxx",
    action: "BOOKED",
    event_type: "FLIGHT",
    user_id: ObjectId,
    contact_email: "user@example.com",
    booking_details: {...},
    created_at: ISODate,
    updated_at: ISODate
}
```

**Chat Sessions** (if from chat):

```javascript
{
    _id: ObjectId,
    session_id: "unique_session_id",
    user_id: ObjectId,
    selected_flight: {...},
    search_params: {...},
    booking_stage: "flight_selected",
    created_at: ISODate,
    expires_at: ISODate  // 2 hours TTL
}
```

### SessionStorage (Browser)

```javascript
// Passenger data (refresh protection)
sessionStorage.setItem(`passenger_data_${sessionId}`, JSON.stringify({
    adults: [...],
    children: [...],
    infants: [...],
    contact: {...}
}));
```

---

## Error Handling

### Common Errors & Recovery

**1. Fare No Longer Available**

- **When**: Validation returns `is_fare_available: false`
- **Recovery**: Show "Search Again" button, reset selection
- **User Action**: Re-search with same or modified criteria

**2. Token Expired (JWT)**

- **When**: 401 Unauthorized on any API call
- **Recovery**: Prompt user to reload page or re-login
- **Function**: `fetchWithTokenCheck()` handles this automatically

**3. Payment Failed**

- **When**: Stripe payment declined
- **Recovery**: Allow retry with different card
- **Logging**: Payment error logged to console

**4. Booking API Error**

- **When**: FlightLogic booking fails (5xx, 4xx)
- **Recovery**: Show error message, contact support
- **Retry**: Tenacity retry (3 attempts with exponential backoff)

**5. Session Expired (FlightLogic)**

- **When**: 2+ hours since search, session_id invalid
- **Recovery**: Force new search
- **User Message**: "Session expired, please search again"

---

## FlightLogic Certification Requirements

**Purpose**: Demonstrate complete booking flow for FlightLogic API certification

**Required Path**: Direct Flight Booker (Entry Point 2)

**Certification Checklist**:

- ✅ Search flights via `/flight_search` API
- ✅ Display all results (not just curated)
- ✅ Allow user selection from results
- ✅ Validate fare via `/revalidate_fare` API
- ✅ Handle validation failure gracefully
- ✅ Collect passenger information (all required fields)
- ✅ Create booking via `/flight_booking` API
- ✅ Issue ticket for LCC via `/issue_ticket` API (if WebFare)
- ✅ Display confirmation with PNR/booking reference
- ✅ Handle errors and edge cases

**Test Scenarios**:

1. **One-way Economy**: AMS → LHR, 1 adult, Economy
2. **Round-trip**: AMS ⇄ LHR, 2 adults + 1 child, Economy
3. **LCC Booking**: Select WebFare (e.g., Ryanair), verify ticket issuance
4. **GDS Booking**: Select traditional carrier (e.g., KLM), verify PNR
5. **Validation Failure**: Select fare, wait, let it expire, re-search

**FlightLogic Test Credentials**: See `.env` for `FLIGHTLOGIC_API_KEY`

---

## Code References

### Backend

- **Flight Service**: `backend_python/app/domains/flight/service.py:45-250`
- **FlightLogic Client**: `backend_python/integrations/flightlogic/client.py:150-450`
- **Flight API Routes**: `backend_python/app/api/flights.py:41-700`
- **AI Flight Handler**: `backend_python/app/ai/enhanced_flight_handler.py:1-450`
- **Flight Booking Handler**: `backend_python/app/ai/flight_booking_handler.py:1-350`
- **Field Collector**: `backend_python/app/ai/flight_field_collector.py:1-300`

### Frontend

- **Flight Booker UI**: `backend_python/dev_ui/flight-booker/index.html:1-5550`
- **Chat Interface**: `frontend-v2/src/features/chat/`

### Schemas

- **Flight Schemas**: `backend_python/app/domains/flight/schemas.py:1-400`
- **Booking Schemas**: `backend_python/app/domains/bookings/schemas.py:1-150`

---

## Testing

### Unit Tests

```bash
# Flight service tests
pytest backend_python/tests/unit_tests/domains/test_flight/test_flight_service.py -v

# AI handler tests
pytest backend_python/tests/unit_tests/test_ai/test_enhanced_flight_handler.py -v
pytest backend_python/tests/unit_tests/test_ai/test_flight_booking_handler.py -v
```

### E2E Tests

```bash
# Playwright tests (from testing directory)
cd testing
npm run test:all

# Specific flight booking test
npm run test:e2e -- flight-booking.spec.ts
```

### Manual Testing

**Chat Flow**:

1. Visit http://localhost:3000
2. Login as `testuser@example.com` / `Test123!`
3. Chat: "I need a flight from Amsterdam to London tomorrow"
4. Chat: "book option 1"
5. Fill passenger form, complete payment

**Direct Flow**:

1. Visit http://localhost:8000/dev/flight-booker/
2. Auto-login as `flightbooker@example.com`
3. Search: AMS → LHR, tomorrow, 1 adult
4. Select any flight
5. Fill passenger form, complete payment

**Test Cards**: See Stripe documentation (4242...)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ENTRY POINTS                                │
├─────────────────────────┬───────────────────────────────────────────┤
│                         │                                            │
│   CHAT-BASED FLOW       │        DIRECT FLIGHT BOOKER               │
│   (Standard User)       │        (Certification Required)           │
│                         │                                            │
│   User Message          │        Search Form                        │
│        ↓                │             ↓                              │
│   Intent Recognition    │        Airport Resolution                 │
│        ↓                │             ↓                              │
│   Field Collection      │        POST /api/flights/search           │
│        ↓                │             ↓                              │
│   Flight Search API     │        Display Results                    │
│        ↓                │             ↓                              │
│   Curate 3-5 Options    │        User Selects Flight                │
│        ↓                │             ↓                              │
│   "book option 1"       │                                            │
│        ↓                │                                            │
│   MongoDB Session       │                                            │
│        ↓                │                                            │
│   JWT Token (1 min)     │                                            │
│        ↓                │                                            │
│   Redirect to Flight    │                                            │
│   Booker with preflight │                                            │
│        │                │                                            │
└────────┼────────────────┴────────────────────────────────────────────┘
         │                                 │
         └─────────────┬───────────────────┘
                       ↓
              ┌─────────────────┐
              │ CONVERGED FLOW  │
              └─────────────────┘
                       ↓
            ╔══════════════════════╗
            ║  Fare Validation     ║
            ║  (CRITICAL STEP)     ║
            ╚══════════════════════╝
                       ↓
            POST /api/flights/revalidate
                       ↓
         ┌─────────────┴─────────────┐
         │                           │
    ✅ Available               ❌ Not Available
         │                           │
         ↓                           ↓
    Show Fare Rules           "Search Again"
         ↓
    Passenger Form
    (Dynamic Fields)
         ↓
    Booking Review
    (Validated Pricing)
         ↓
    Stripe Payment
         ↓
    POST /api/flights/book
         ↓
    ┌────┴────┐
    │         │
  LCC       GDS
    │         │
    ↓         ↓
Issue     Skip Ticket
Ticket    Issuance
    │         │
    └────┬────┘
         ↓
    Confirmation
         ↓
    Email Sent
```

---

## Key Takeaways

### Critical Success Factors

1. **Always use revalidation pricing** for booking review and payment (not search pricing)
2. **Validate fare availability** before accepting payment (prices change!)
3. **Detect LCC vs GDS** to determine ticket issuance requirement
4. **Collect required fields** dynamically based on validation response
5. **Handle session expiry** gracefully (FlightLogic sessions expire after 2 hours)

### Common Pitfalls

❌ **Using search pricing for booking** → Price mismatch, booking failures
✅ **Use revalidation result pricing** → Accurate, validated prices

❌ **Skipping fare validation** → Book unavailable/changed fares
✅ **Always revalidate** → Ensure fare exists at current price

❌ **Hardcoding passenger fields** → Missing required fields, API errors
✅ **Dynamic field requirements** → Use `required_booking_fields` from validation

❌ **Forgetting LCC ticket issuance** → Booking incomplete, unusable tickets
✅ **Check `fare_type === "WebFare"`** → Issue ticket immediately for LCC

### Performance Considerations

- Airport autocomplete: Debounced search (300ms delay)
- Search results: Display immediately (no artificial delays)
- Fare validation: Show loading indicator (can take 2-5 seconds)
- Payment: Stripe handles loading states automatically

---

**Document Maintainer**: Development Team
**Related Documentation**:

- `docs/ARCHITECTURE.md` - System architecture
- `backend_python/docs/CODING_STANDARDS.md` - Python coding standards
- `docs/FRONTEND_BACKEND_COLLABORATION.md` - API contracts
- `CLAUDE.md` - Project overview
