# Flight Booker UI - Development Tool

Comprehensive guide to the Flight Booker UI, a standalone manual testing tool for the Voya flight booking flow.

## Table of Contents
- [Overview](#overview)
- [Purpose and Use Cases](#purpose-and-use-cases)
- [Accessing the Tool](#accessing-the-tool)
- [Features](#features)
- [Complete Booking Flow](#complete-booking-flow)
- [Payment Modes](#payment-modes)
- [Session-Based Workflow](#session-based-workflow)
- [GDS vs LCC Flights](#gds-vs-lcc-flights)
- [Testing Scenarios](#testing-scenarios)
- [Troubleshooting](#troubleshooting)

## Overview

The Flight Booker UI is a single-page web application for manual flight booking testing, providing a visual interface for the complete booking flow without using the AI chatbot.

**Location**: `backend_python/dev_ui/flight-booker/index.html`
**URL**: http://localhost:8000/dev/flight-booker/
**Access**: Dev environment only (`DEBUG=True`, `ENVIRONMENT != "production"`)

**Key Characteristics**:
- ✅ Standalone HTML/JavaScript application (no build step)
- ✅ Session-based booking with 3-hour TTL
- ✅ Two payment modes: Demo (checkbox) and Stripe (real payment)
- ✅ GDS countdown timer for ticket issuance
- ✅ Comprehensive passenger data collection
- ✅ Airport database integration (29,000+ airports)
- ✅ Automatic authentication from URL parameters

## Purpose and Use Cases

### Why Use Flight Booker Instead of Chatbot?

| Feature | Flight Booker UI | AI Chatbot |
|---------|------------------|------------|
| **Testing** | Manual, predictable | Natural language, variable |
| **Payment** | Both demo and real Stripe | Chatbot doesn't handle payment UI |
| **Forms** | Visual passenger forms | Text-based collection |
| **Debugging** | Step-by-step verification | Harder to debug AI flow |
| **Speed** | Direct API calls | AI processing overhead |

### Use Cases

**1. Backend Development**:
- Test flight booking API without frontend integration
- Debug payment flow with Stripe integration
- Test passenger data validation
- Verify booking session persistence

**2. QA Testing**:
- Manual test scenarios (edge cases, error conditions)
- Verify fare rules display
- Test GDS countdown functionality
- Confirm booking data accuracy

**3. Demo/Training**:
- Show complete booking flow to stakeholders
- Train customer support on booking process
- Create test bookings for data verification

**4. Payment Testing**:
- Test Stripe integration with real cards
- Verify payment validation before booking
- Test demo mode for booking flow without payment

## Accessing the Tool

### Direct Access

**URL**: http://localhost:8000/dev/flight-booker/

**Requirements**:
- Backend running (uvicorn or Docker)
- Dev environment (`DEBUG=True`)
- User authentication (auto-login supported)

### Auto-Login from URL

The tool supports automatic authentication via URL parameters:

**Format**:
```
http://localhost:8000/dev/flight-booker/?token=<jwt_token>
```

**Example**:
```
http://localhost:8000/dev/flight-booker/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**How it works**:
1. URL parameter `token` is detected on page load
2. Token is stored in `localStorage`
3. All API calls use this token for authentication
4. User sees authenticated interface immediately

### Session-Based Loading

Load existing booking session from URL:

**Format**:
```
http://localhost:8000/dev/flight-booker/?session_id=<session_id>
```

**Example**:
```
http://localhost:8000/dev/flight-booker/?session_id=flight_session_abc123
```

**What happens**:
1. Booking session data loaded from backend
2. Flight details pre-populated
3. User can continue from passenger details step
4. Payment and booking completion available

## Features

### 1. Flight Search

**Section**: 🔍 Search Flights

**Features**:
- Origin/destination airport selection (29,000+ airports)
- Date picker for departure and return
- Passenger count (adults, children, infants)
- Cabin class selection (economy, premium economy, business, first)
- Direct flights filter
- Quick route shortcuts (Calgary → Austin, etc.)

**Airport Resolution**:
- Type city name or airport code
- Fuzzy matching (e.g., "Lond" → London Heathrow)
- IATA and ICAO code support
- Real-time airport name display

**Example**:
```
Origin: YYC (Calgary International Airport)
Destination: AUS (Austin-Bergstrom International Airport)
Departure: 2025-11-15
Return: 2025-11-22
Adults: 2, Children: 0, Infants: 0
Cabin: economy
Direct flights only: Yes
```

### 2. Flight Results Display

**Section**: ✈️ Select Flight

**Features**:
- Flight options sorted by:
  - Lowest Price 💵
  - Fastest ⚡
  - Best Value ⭐
- Flight details:
  - Flight number, airline
  - Departure/arrival times
  - Duration, stops
  - Cabin baggage, checked baggage
  - Refundability
  - Price breakdown (base fare, taxes, total)
- Select and revalidate flight

**Sorting Logic**:
- **Lowest Price**: Cheapest total fare
- **Fastest**: Shortest total duration
- **Best Value**: Balance of price and duration

### 3. Fare Rules Display

**Section**: 📋 Fare Rules

**Features**:
- Displays fare conditions before booking
- Cancelation policy
- Change fees
- Baggage allowance
- Special conditions
- Booking deadline

**Use case**: Users review rules before passenger data entry

### 4. Passenger Data Collection

**Section**: 👤 Passenger Details

**Features**:
- Dynamic passenger forms (based on search count)
- Required fields:
  - Full name (first, middle, last)
  - Date of birth
  - Gender
  - Email, phone number
- International flight fields:
  - Passport number
  - Passport expiry date
  - Issuing country
- Quick-fill for testing (auto-populate with dummy data)
- Prefill main passenger with logged-in user data

**Validation**:
- Age validation (adult/child/infant)
- Email format validation
- Phone number format validation
- Passport expiry date validation (must be future date)
- Required field checking

### 5. Booking Review

**Section**: 📋 Review Your Booking

**Features**:
- Flight summary (outbound + return)
- Passenger details summary
- Price breakdown (per passenger + total)
- Fare rules reference
- Edit passenger data button

**Example Display**:
```
Flight Summary:
✈️ Outbound: YYC → AUS
   Nov 15, 2025 | 08:00 - 14:30 (6h 30m)
   AC 123 (Economy)

✈️ Return: AUS → YYC
   Nov 22, 2025 | 15:00 - 21:00 (6h 0m)
   AC 456 (Economy)

Passengers:
👤 John Doe (Adult)
👤 Jane Doe (Adult)

Total: $1,234.56 CAD
```

### 6. Payment Integration

**Section**: 💳 Payment

**Features**:
- Two payment modes: Demo and Stripe
- Payment mode switcher
- Payment summary (booking amount, platform fee, total)
- GDS countdown timer (for GDS flights)
- Stripe.js card element integration

**Payment Summary**:
```
Booking Amount: $1,234.56
Platform Fee (5%): $61.73
Total: $1,234.56
```

### 7. Trip Details Display

**Section**: 📋 Trip Details

**Features**:
- Final booking confirmation
- Booking reference (VOYA-XXXXXXXX)
- Flight details
- Passenger manifest
- Payment status
- Booking status
- Issue ticket button (for GDS flights)

## Complete Booking Flow

### Step-by-Step Walkthrough

**Step 1: Search Flights**
1. Open http://localhost:8000/dev/flight-booker/
2. Enter origin/destination airports
3. Select dates and passenger count
4. Click "Search Flights"
5. Wait for results (API call to `/api/flights/search`)

**Step 2: Select Flight**
1. Review flight options (Lowest Price, Fastest, Best Value)
2. Click "Select & Continue" on preferred flight
3. Flight is revalidated (API call to `/api/flights/revalidate`)
4. Proceeds to fare rules display

**Step 3: Review Fare Rules**
1. Review cancelation policy, baggage, etc.
2. Click "Continue to Passenger Details"

**Step 4: Enter Passenger Details**
1. Fill passenger forms (auto-generated based on search)
2. Optional: Click "Quick Fill" for test data
3. Verify email and phone number
4. For international flights, add passport details
5. Click "Continue to Review"

**Step 5: Review Booking**
1. Verify all details are correct
2. Review price breakdown
3. Click "Continue to Payment"

**Step 6: Payment**
1. Choose payment mode:
   - **Demo Mode**: Check "I confirm payment" checkbox
   - **Stripe Mode**: Enter card details and click "Pay Now"
2. For GDS flights: Countdown timer starts (pay before ticket issuance)
3. Payment intent created (API call to `/api/payments/create-intent`)
4. Payment confirmed (Stripe.js processes payment)

**Step 7: Booking Confirmation**
1. Booking created (API call to `/api/flights/create-booking-from-session`)
2. Payment validated on backend
3. Booking confirmation displayed with reference number
4. Trip details shown in "Trip Details" tab

**Step 8: Ticket Issuance** (GDS flights only)
1. Click "Issue Ticket" button
2. Ticket issued (API call to `/api/flights/issue-ticket`)
3. Booking status updated to "TICKETED"

## Payment Modes

### Demo Mode (Checkbox Payment)

**Purpose**: Test booking flow without actual payment processing

**How it works**:
1. Select "Demo Mode (Checkbox)" from payment mode switcher
2. Check "I confirm payment" checkbox
3. Click "Complete Booking"
4. Backend receives `payment_intent_id: "demo_payment_intent"`
5. Backend skips payment validation
6. Booking created immediately

**Use case**:
- Testing booking API
- Debugging passenger data flow
- QA testing without Stripe account

### Stripe Mode (Real Payment)

**Purpose**: Test full payment integration with Stripe

**How it works**:
1. Select "Stripe Integration (Real Payment)" from payment mode switcher
2. Payment summary displayed (booking amount, platform fee)
3. Stripe Card Element loaded
4. Enter card details
5. Click "Pay Now"
6. Stripe.js processes payment
7. Frontend receives `payment_intent_id`
8. Backend validates payment succeeded
9. Booking created with validated payment

**Test Cards** (Stripe test mode):
```
Success: 4242 4242 4242 4242
Decline: 4000 0000 0000 0002
Insufficient Funds: 4000 0000 0000 9995
Expiry: Any future date (e.g., 12/25)
CVC: Any 3 digits
```

**Payment Flow**:
```
1. Create payment intent → Backend returns client_secret
2. Initialize Stripe.js → Frontend mounts card element
3. User enters card → Stripe validates in real-time
4. Click "Pay Now" → Stripe.js confirms payment
5. Payment succeeded → Frontend receives payment_intent_id
6. Create booking → Backend validates payment before booking
7. Booking confirmed → Display confirmation
```

## Session-Based Workflow

### Booking Session Storage

**Collection**: `booking_sessions` (MongoDB)
**TTL**: 3 hours (auto-expires)

**Session Data Structure**:
```python
{
    "session_id": "flight_session_abc123",
    "user_id": "user_123",
    "data": {
        "selected_flight": { ... },  # Revalidated flight data
        "search_params": { ... },    # Original search params
        "fare_rules": { ... },       # Fare conditions
        "passengers": [ ... ],       # Passenger details (after form)
        "payment_intent_id": "pi_...",  # After payment
        "booking_reference": "VOYA-..."  # After booking
    },
    "created_at": ISODate("..."),
    "updated_at": ISODate("..."),
    "expires_at": ISODate("...")  # created_at + 3 hours
}
```

### Session Persistence

**Why 3-hour TTL?**
- Allows page refreshes during payment
- Users can pause and resume booking
- Auto-cleanup of abandoned sessions
- Prevents stale pricing data

**Session Updates**:
- Created after flight revalidation
- Updated with passenger data
- Updated with payment intent ID
- Updated with booking reference
- NOT deleted after booking (kept for full TTL)

### Loading Session from URL

**URL Format**:
```
http://localhost:8000/dev/flight-booker/?session_id=flight_session_abc123
```

**What's Pre-filled**:
- ✅ Flight details
- ✅ Search parameters
- ✅ Fare rules
- ❌ Passenger details (must re-enter for security)
- ❌ Payment info (must re-enter for security)

**Use case**:
- Resume booking after page refresh
- Share booking link for review
- Debug specific booking session

## GDS vs LCC Flights

### Global Distribution System (GDS) Flights

**Characteristics**:
- Requires ticket issuance after booking
- Countdown timer starts after payment
- "Book now, pay later" option (pay before ticket issuance)
- Two-step process: Book → Issue Ticket

**Payment Timing**:
- ✅ **Option 1**: Pay before booking (recommended)
- ✅ **Option 2**: Book first, pay within countdown window (not yet implemented)

**Countdown Timer**:
```
⏰ Time Remaining: 29:45

Complete payment within 30 minutes to secure your booking.
```

**Ticket Issuance**:
1. After booking confirmed
2. Click "Issue Ticket" button
3. API call to `/api/flights/issue-ticket`
4. Booking status updated to "TICKETED"

### Low-Cost Carrier (LCC) Flights

**Characteristics**:
- Instant ticketing (no separate issuance step)
- Payment required before booking
- No countdown timer
- One-step process: Pay → Book (auto-ticketed)

**Payment Timing**:
- ✅ **Mandatory**: Pay before booking

## Testing Scenarios

### Scenario 1: Quick Test Booking (Demo Mode)

**Purpose**: Verify booking flow without payment

**Steps**:
1. Open flight-booker
2. Search: YYC → AUS (Nov 15-22, 2 adults, economy)
3. Select cheapest flight
4. Quick-fill passenger data
5. Review booking
6. Select "Demo Mode"
7. Check "I confirm payment"
8. Complete booking
9. Verify booking reference displayed

**Expected**: Booking created with `VOYA-` reference

### Scenario 2: Real Payment Test (Stripe Mode)

**Purpose**: Test Stripe integration end-to-end

**Steps**:
1. Search and select flight
2. Fill passenger data (real or test)
3. Review booking
4. Select "Stripe Mode"
5. Enter test card: `4242 4242 4242 4242`
6. Click "Pay Now"
7. Wait for payment confirmation
8. Verify booking created

**Expected**: Payment processed, transaction in MongoDB, booking confirmed

### Scenario 3: Payment Declined Test

**Purpose**: Verify error handling for failed payments

**Steps**:
1. Search and select flight
2. Fill passenger data
3. Select "Stripe Mode"
4. Enter decline card: `4000 0000 0000 0002`
5. Click "Pay Now"

**Expected**:
- Payment fails with error message
- Booking NOT created
- User can retry with different card

### Scenario 4: Session Persistence Test

**Purpose**: Verify session survives page refresh

**Steps**:
1. Search and select flight
2. Fill passenger data
3. Before payment, copy URL with `session_id` parameter
4. Refresh page OR close and reopen with URL
5. Verify flight details pre-loaded
6. Continue to payment and complete booking

**Expected**: Session data restored, booking proceeds normally

### Scenario 5: GDS Countdown Test

**Purpose**: Verify countdown timer for GDS flights

**Steps**:
1. Search for GDS flight (check booking_type === "GDS")
2. Select flight and fill passenger data
3. On payment screen, observe countdown timer
4. Select Demo Mode and complete booking
5. Verify timer shows time remaining

**Expected**: Countdown displays "⏰ Time Remaining: XX:XX"

## Troubleshooting

### Flight Search Returns No Results

**Symptoms**: "No flights found" message

**Checks**:
1. Are dates in the future?
2. Is route valid? (Check origin ≠ destination)
3. Is FlightLogic API accessible?
   ```bash
   # Check backend logs
   docker logs -f voya-backend | grep FlightLogic
   ```
4. Are API keys configured?
   ```bash
   cat .env | grep FLIGHTLOGIC_API_KEY
   ```

### Payment Intent Creation Fails

**Symptoms**: Error when clicking "Pay Now" in Stripe mode

**Solutions**:

1. **Missing Stripe keys**:
   ```bash
   # Check .env
   cat .env | grep STRIPE_SECRET_KEY
   cat .env | grep STRIPE_PUBLISHABLE_KEY
   ```

2. **Backend not running**:
   ```bash
   curl http://localhost:8000/api/health
   ```

3. **Authentication issue**:
   - Check browser console for 401 errors
   - Verify token in localStorage
   - Try auto-login URL with fresh token

### Booking Creation Fails After Payment

**Symptoms**: Payment succeeded but booking not created

**Checks**:

1. **Payment validation failed**:
   ```bash
   # Check backend logs for payment validation errors
   docker logs -f voya-backend | grep "Payment validation"
   ```

2. **Session expired**:
   - Sessions expire after 3 hours
   - Check `expires_at` in MongoDB
   - Restart booking from search

3. **FlightLogic API error**:
   ```bash
   # Check backend logs for FlightLogic errors
   docker logs -f voya-backend | grep FlightLogic
   ```

### Passenger Form Validation Errors

**Symptoms**: "Continue to Review" button disabled

**Solutions**:

1. **Required fields missing**: Fill all marked fields (red asterisks)
2. **Invalid email format**: Check email has `@` and domain
3. **Invalid phone format**: Use international format (`+1 xxx xxx xxxx`)
4. **Passport expiry in past**: Must be future date for international flights
5. **Age validation failed**:
   - Adults must be 18+
   - Children must be 2-17
   - Infants must be <2

### Session Not Loading from URL

**Symptoms**: `?session_id=...` in URL but data not pre-filled

**Checks**:

1. **Session expired**: Check MongoDB for session document
2. **Wrong session ID**: Verify ID matches database
3. **Backend error**: Check logs for session retrieval errors
4. **Authentication required**: Add `?token=...` parameter if not logged in

### Stripe Card Element Not Showing

**Symptoms**: Payment section blank in Stripe mode

**Solutions**:

1. **Stripe.js not loaded**:
   ```javascript
   // Check browser console
   console.log(typeof Stripe);  // Should be "function"
   ```

2. **Network error**: Check browser Network tab for Stripe.js load failure

3. **Publishable key missing**: Backend should return `publishable_key` in payment intent response

## Related Documentation

- **[PAYMENTS.md](PAYMENTS.md)** - Complete Stripe payment integration guide
- **[WEBHOOKS.md](WEBHOOKS.md)** - Webhook setup and testing
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture with booking flow
- **API Docs**: http://localhost:8000/api/docs (Swagger)
- **API Tester**: http://localhost:8000/dev/api-tester.html (all endpoints)

---

**Last Updated**: October 2025
**Maintainer**: Backend Team
**Access**: Dev environment only
**Questions**: Create GitHub issue with label `dev-tools`
