# Architecture Guide

System architecture and implementation details for the Voya travel platform.

## System Overview

### Core Components
- **Frontend**: React 18.2 with Redux Toolkit state management
- **Backend**: Python FastAPI with Motor (MongoDB async ODM)
- **Admin**: React admin dashboard
- **AI Engine**: Google Generative AI (Gemini) for chatbot
- **External APIs**: FlightLogic for travel data, SendGrid for emails

### Integration Architecture
```
Frontend (React) <--> Backend (FastAPI) <--> MongoDB
                           |
                           ├--> Google AI (Gemini)
                           ├--> FlightLogic API
                           ├--> SendGrid/MailHog
                           └--> Stripe (payments + webhooks)
                                 ├─ Payment Intents (5% platform fee)
                                 ├─ Stripe Connect (supplier transfers)
                                 └─ Webhooks (payment status updates)
```

## Airport Resolution System

### Overview
Comprehensive airport/city resolution with 29,000+ airports worldwide.

**Source**: mwgg/Airports GitHub repository
**Location**: `app/domains/airport/airport_resolver.py`
**Auto-updating**: Downloads latest data on first use, caches locally

### Resolution Strategies (Multi-layered)

1. **Primary**: Comprehensive database lookup (IATA/ICAO codes, city names, airport names)
2. **Fallback**: Manual mapping for 50+ critical cities
3. **Pattern Matching**: Partial string matching for misspelled cities
4. **Code Recognition**: Direct IATA (3-letter) and ICAO (4-letter) code handling

### Supported Input Formats

**City Names**:
- "Calgary" → YYC
- "Eindhoven" → EIN
- "New York" → JFK

**Airport Names**:
- "John F Kennedy International" → JFK

**IATA Codes**:
- "YYC", "AUS", "EIN" (direct recognition)

**ICAO Codes**:
- "CYYC" → YYC
- "KJFK" → JFK (converted to IATA)

**Partial Matches**:
- "Lond" → LHR
- "Amster" → AMS

### Enhanced Field Extraction

**Pattern Recognition**: Supports "take me from X to Y", "fly from X to Y", "X to Y"
**Async Processing**: Uses comprehensive database for better accuracy
**Sync Fallback**: Falls back to manual mapping if database unavailable
**Question Context Awareness**: Considers the last question asked to resolve ambiguous field assignments

**Location**: `app/ai/flight_field_collector.py`

### Question Context-Aware Field Assignment

**Problem**: User replies like "Paris" could be either origin or destination depending on the question asked

**Solution**: Enhanced field extraction that considers conversation context

**Implementation**:
- Session tracking of `waiting_for_field`, `last_question`, and `question_field_map`
- Context refinement function `_refine_fields_with_question_context()`
- Smart reassignment for ambiguous responses based on question context

**Examples**:
- Question: "Which city are you departing from?" → Reply: "Paris" → Assigned to `origin`
- Question: "Where would you like to fly to?" → Reply: "Paris" → Assigned to `destination`

**Location**: `app/ai/enhanced_flight_handler.py`, `app/ai/flight_field_collector.py`

## Sticky Intent System

### Intent Persistence Rules

- **High Confidence Threshold**: 0.9+ confidence required to establish BOOK_FLIGHT intent
- **Sticky Behavior**: Once established, maintains BOOK_FLIGHT context for unclear messages
- **Override Logic**: Only changes intent if new intent detected with 0.9+ confidence
- **Context Tracking**: Stores previous intents with confidence levels in conversation history

### Implementation

**Context Building**: `_build_intent_context()` retrieves last 10 messages with intent data
**Intent Storage**: User messages stored with intent and confidence in MongoDB
**Decision Logic**: `_finalize_intent()` applies sticky logic with fallback to heuristics

**Location**: `app/ai/intent_recognizer.py`, `app/domains/chat/service.py`

## Flight Booking System

### Complete End-to-End Booking Flow

The flight booking system provides a seamless experience from search to confirmed reservation through the AI chatbot interface.

### Architecture Components

- **EnhancedFlightHandler** (`app/ai/enhanced_flight_handler.py`): Main flight search and conversation flow
- **FlightBookingHandler** (`app/ai/flight_booking_handler.py`): Dedicated booking flow management
- **FlightService** (`app/domains/flight/service.py`): FlightLogic API integration and booking execution
- **Airport Resolution** (`app/domains/airport/airport_resolver.py`): 29,000+ airports with priority mappings

### Booking Flow Stages

1. **Flight Search**: Collect origin, destination, dates, passenger counts
2. **Results Display**: Show flight options with clear booking call-to-action
3. **Flight Selection**: Parse user selection ("book option 1", "book cheapest", etc.)
4. **Passenger Details**: Collect full name, date of birth, passport info (if international)
5. **Booking Confirmation**: Present summary and get user confirmation
6. **Execution**: Create actual booking via FlightLogic API
7. **Confirmation**: Provide booking reference and success message

### User Experience Features

- **Simple Selection**: Users can say "book option 1" or "book cheapest flight"
- **Natural Language**: Supports various selection patterns (ordinal, label-based, numbers)
- **Clear Guidance**: Prominent call-to-action after flight results with examples
- **Progress Tracking**: Session-based booking state management
- **Error Handling**: Graceful handling of invalid selections and booking failures
- **Profile Integration**: Link to profile page for passenger information management

### Flight Selection Patterns Supported

- **Numbered Options**: "book option 1", "select 2", "choose option 3"
- **Ordinal Words**: "book the first flight", "select the second one"
- **Label-Based**: "book cheapest", "select best value", "choose direct flight"
- **Direct Numbers**: "book 1", "take 3", or just "2"

### Technical Implementation

- **Session Management**: Booking sessions stored in `FlightBookingHandler.booking_sessions`
- **State Tracking**: Comprehensive booking stage management (flight_selected, passenger_details, etc.)
- **FlightLogic Integration**: Direct API calls to `/api/flights/book` endpoint
- **Schema Mapping**: Converts session data to `FlightBookingRequest` format
- **Error Recovery**: Handles API failures, invalid selections, and partial bookings

### Testing

- **Unit Tests**: Comprehensive test suite in `tests/unit_tests/test_ai/test_flight_booking_handler.py`
- **Test Coverage**: Flight selection parsing, passenger details, booking execution, error handling
- **Mock Integration**: Tests use mocked FlightService to avoid external API calls

### Location Files

- **Main Handler**: `app/ai/flight_booking_handler.py` (639 lines)
- **Integration**: `app/ai/enhanced_flight_handler.py` (lines 419-448)
- **Unit Tests**: `tests/unit_tests/test_ai/test_flight_booking_handler.py`
- **Schemas**: `app/domains/flight/schemas.py` (FlightBookingRequest, PassengerGroups, etc.)

## Frontend Architecture

### State Management (Redux Toolkit)

**Slices**:
- `auth`: Authentication state (user, tokens)
- `chatbot`: Chat messages, context, history
- `trips`: Trip planning and itineraries
- `users`: User management
- `voya`: Global app state

### ChatBot System

**Global Component**: Available on all routes (except `/complete-registration`)

**Landing vs authenticated entrypoints**:
- **Public landing (`/`)**: When `VOYA_FEATURE_FLAG_PUBLIC_CHAT` is enabled, the landing page can embed chat for **guests** via `POST /api/public/chat/message` (no JWT; `X-Public-Chat-Session` + per-IP rate limits). Rich-result actions (itinerary, flight/hotel drill-down) are gated to sign-up.
- **Full-page guest chat (`/public/chat`)**: Same guest API and `ChatPanel` UX as `/chat`, without JWT; gated CTAs match embedded chat. After sign-in, routing sends users to **`/chat`** (see `docs/FRONTEND_BACKEND_COLLABORATION.md` public chat section).
- **Authenticated app**: `POST /api/chat/message` and related `/api/chat/*` routes require JWT; this remains the primary chat path after login.

**Welcome Message**: Displays immediately for all users (authenticated or not)

**Authentication Flow**: On routes that use authenticated chat only, users see welcome message → try to chat → prompted to sign in. On `/`, guests may use public chat until limits or gated actions trigger sign-up.

**Message Format**: Frontend expects `{_id, content: {messages: [{text}]}, from: "bot", ...}` structure

**Conversation Continuity**:
- Tracks `chat_id` from backend responses to maintain AI context across messages
- Sticky Intent System: Maintains BOOK_FLIGHT context until 0.9+ confidence override
- Message Transformation: Converts backend snake_case responses to frontend expected format
- Guest sessions store `guest_session_id` / guest `chat_id` in `sessionStorage` for same-tab continuity; guest history is not synced across devices

### Key Features

- **AI chatbot integration** with context management
- **Trip planning** with calendar integration (@fullcalendar)
- **Google Maps integration** (@react-google-maps/api)
- **Google OAuth authentication** (@react-oauth/google)
- **Real-time chat** with sound notifications

## Backend Architecture

### Domain-Driven Design

Separate modules for different business domains:

- **Auth** (`app/domains/auth/`): Authentication service, repository, schemas
- **User** (`app/domains/user/`): User operations & validation
- **Chat** (`app/domains/chat/`): Conversation state management
- **Flight** (`app/domains/flight/`): Flight operations & schemas
- **Hotel** (`app/domains/hotel/`): Hotel search, room rates, booking, validators, events
- **Airport** (`app/domains/airport/`): Global airport resolution
- **Email** (`app/domains/email/`): Email templates & delivery (flight + hotel confirmations)
- **Payment** (`app/domains/payment/`): Stripe payment integration, transaction tracking, payout management

### AI Components

- **Intent Recognition** (`app/ai/intent_recognizer.py`): Smart intent detection with sticky logic (BOOK_FLIGHT, BOOK_HOTEL)
- **Flight Handlers** (`app/ai/enhanced_flight_handler.py`, `app/ai/flight_booking_handler.py`): End-to-end flight booking flow
- **Hotel Handlers** (`app/ai/enhanced_hotel_handler.py`, `app/ai/hotel_booking_handler.py`): End-to-end hotel booking flow
- **Hotel Field Collector** (`app/ai/hotel_field_collector.py`): NLP extraction for hotel search fields
- **Conversation State** (`app/ai/conversation_state.py`): Context management
- **Response Generation** (`app/ai/response_generator.py`): AI response generation

### External Integrations

**FlightLogic API**:
- Flight search & booking
- Hotel search, room rates, rate validation & booking
- Activity recommendations

**Google Geocoding API**:
- City disambiguation for hotel searches (resolves "Paris" → "Paris, France")
- Multi-result handling with user selection

**Google Generative AI (Gemini)**:
- Conversation handling
- Intent recognition (0.9+ confidence threshold)
- Natural language processing

**MailHog (dev) / SendGrid (prod)**:
- Email delivery
- Password reset
- Booking confirmations

**Stripe**:
- Payment intent creation with 5% platform fee
- Stripe Connect automatic transfers to suppliers
- Webhook-based payment status updates
- Transaction tracking and payout management
- See [PAYMENTS.md](PAYMENTS.md) for complete integration guide

### Database (MongoDB)

**Collections**:
- `users`: User accounts, profiles, authentication
- `trips`: Trip planning and itineraries
- `chats`: Chat sessions
- `chatHistory`: Message history with intent data
- `transactions`: Payment transactions with Stripe integration (payment intents, fees, payouts)
- `counters`: Auto-increment IDs
- `booking_sessions`: Temporary flight/hotel booking data with 3-hour TTL

**ODM**: Motor (async MongoDB driver)
**Authentication**: JWT tokens (no session storage)

## Integration Points

- Frontend build copies to `backend/build` for serving static files
- Backend serves React app for unmatched routes (SPA support)
- Chatbot uses Google Generative AI with sticky intent recognition
- Airport resolution integrates with FlightLogic for validated travel data
- Flight booking system provides complete search-to-reservation workflow via FlightLogic API
- Hotel booking system provides search → room rates → rate validation → booking workflow via FlightLogic API
- Google Geocoding API resolves ambiguous city names for hotel searches
- Trip planning integrates with FlightLogic for real travel data

## Security Architecture

### Authentication
- **JWT tokens**: 30-minute expiration
- **Google OAuth**: Social login integration
- **Password hashing**: bcrypt with work factor ≥ 12
- **Email verification**: Required for local accounts

### Security Measures
- **Input validation**: Pydantic models for all requests
- **MongoDB injection prevention**: Proper query structure
- **CORS configuration**: Production-ready settings
- **No secrets in code**: Environment variables only
- **Security scanning**: Bandit in CI/CD

## Performance Considerations

### Caching
- **Airport data**: Local cache (29,000+ airports)
- **API responses**: Smart caching for expensive operations
- **Database queries**: Optimized with proper indexing

### Async Patterns
- **Motor**: Async MongoDB operations
- **FastAPI**: Async endpoint handlers
- **asyncio.gather()**: Parallel I/O operations

### Optimization
- **Connection pooling**: Reuse database and HTTP connections
- **Bulk operations**: Group database operations
- **Streaming responses**: For large data transfers
