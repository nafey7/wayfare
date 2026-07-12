# Frontend/Backend Collaboration Guide

**Purpose**: Define collaboration patterns between frontend and backend teams.

**Note**: This is NOT a complete API reference. Backend owns API contracts via Swagger.

## API Discovery Tools

### 1. Swagger UI (Primary Reference)
- **URL**: http://localhost:8000/api/docs
- **Purpose**: Auto-generated API documentation from FastAPI code
- **Contains**: All endpoints, request/response schemas, authentication
- **Single Source of Truth**: Backend maintains, frontend consumes

### 2. API Tester (Interactive Exploration)
- **URL**: http://localhost:8000/dev/api-tester.html
- **Purpose**: Interactive testing of all endpoints
- **Features**:
  - Google OAuth login integration
  - JWT token management
  - Built-in AI chat interface for testing conversation flows
  - Flight search testing with real API calls
  - Request/response inspection
  - Test all endpoints without external tools
- **Access**: Only available in dev mode (`DEBUG=True`, `ENVIRONMENT != "production"`)
- **Implementation**: Served from `backend_python/dev_ui/` via `/dev` mount in `app/main.py`
- **Companion Tool**: `/dev/agent-prompts-admin.html` for AI prompt management

### 3. OpenAPI JSON (Machine-Readable)
- **URL**: http://localhost:8000/openapi.json
- **Purpose**: Generate types, client code, documentation
- **Usage**: Can generate TypeScript types for frontend

## Collaboration Workflow

### Backend Team Responsibilities
1. **Define API contracts** in FastAPI route handlers
2. **Maintain Swagger docs** (auto-generated from code)
3. **Document breaking changes** in PRs
4. **Version endpoints** when needed (`/api/v2/...`)
5. **Test API contracts** with unit/integration tests
6. **Keep API Tester functional** for frontend exploration

### Frontend Team Responsibilities
1. **Discover APIs** via Swagger UI
2. **Test integrations** with API Tester tool
3. **Handle errors gracefully** with standard error format
4. **Transform data** between snake_case (backend) and camelCase (frontend)
5. **Manage authentication** tokens and refresh
6. **Report API issues** with reproducible test cases

### API Data Convention (frontend-v2): snake_case ↔ camelCase at the Boundary

- **Backend** uses **snake_case** in request/response bodies (OpenAPI, Pydantic).
- **Frontend** uses **camelCase** in components, Redux state, and TypeScript types.
- **Boundary**: Conversion is centralized in the **RTK Query API layer** (frontend-v2):
  - **Outgoing**: Request bodies are converted to snake_case via `toSnakeCase(body)` in each endpoint’s `query` (or equivalent) so the backend receives snake_case.
  - **Incoming**: Responses are normalized to camelCase via `transformResponse: (response) => toCamelCase(response)` so components and state only see camelCase.
- **Where**: `frontend-v2/src/api/flightsApi.ts`, `paymentsApi.ts`, `hotelsApi.ts` use `@/utils/transforms` (`toCamelCase` / `toSnakeCase`). Avoid ad-hoc `body: { session_id: ... }` in callers; pass camelCase and let the API layer convert.
- **Types**: Frontend types (e.g. `FlightBookingResponse`, `PaymentIntentCreateResponse`) are camelCase; the wire format remains snake_case.

### Profile photos contract

Backend persists a single `photo_key` (S3 key) on the user document and exposes pre-rendered signed imgproxy URLs in every user payload so the frontend never has to know imgproxy internals.

- **Backend**: `photo_key: str | null`, `photo_urls: { sm, md, lg } | null` on `UserPublic`/`UserResponse`/`ProfileUserResponse`.
- **Frontend**: `User.photoKey`, `User.photoUrls` (camelCase) — converted by `transformUser` for `/user/me*` payloads and via `toCamelCase` for the profile aggregate.
- **Endpoints**: `PUT /api/user/me/photo` (multipart `file`) returns `{ photo_key, photo_urls }`; `DELETE /api/user/me/photo` returns `204`.
- **Rendering**: The shared `<VoyaAvatar size="sm|md|lg">` (`frontend-v2/src/components/VoyaAvatar.tsx`) selects the right preset and falls back to initials when `photoUrls` is null or the image errors.

## Authentication Flow

### JWT Token Lifecycle
```
1. User logs in → Backend issues JWT token (30 min expiry)
2. Frontend stores token in memory (NOT localStorage for security)
3. Frontend includes token in all requests:
   Authorization: Bearer <token>
4. Token expires → Frontend shows login prompt
5. User re-authenticates → New token issued
```

### Google OAuth Flow
```
1. Frontend initiates OAuth with Google Sign-In button
2. Google returns authorization code
3. Frontend sends code to /api/auth/google
4. Backend validates with Google, creates/updates user, returns JWT
5. Frontend uses JWT for subsequent requests
6. Frontend stores JWT in memory (secure, not persisted)
```

**Security Notes**:
- JWT tokens stored in memory only (cleared on page refresh/close)
- No localStorage/sessionStorage for tokens (XSS vulnerability)
- Tokens expire after 30 minutes
- Backend validates signature and expiry on every request

## Public (guest) chat

Anonymous users on the marketing landing route (`/`) can chat **before** signing in. This path is separate from authenticated chat: it does not use `/api/chat/*` (those endpoints remain JWT-only).

### Rollout

- **Backend flag**: `VOYA_FEATURE_FLAG_PUBLIC_CHAT` (default **true** in settings and ECS) enables the public route and exposes `public_chat_enabled` on `GET /api/config`.
- **Frontend**: `frontend-v2` should treat `GET /api/config` as the source of truth: when `public_chat_enabled` is false, do not render the embedded landing chat widget and do not call the public send endpoint.

### Guest send endpoint

| | |
|--|--|
| **Method / path** | `POST /api/public/chat/message` |
| **Auth** | None |
| **Header** | `X-Public-Chat-Session: <uuid>` (required; browser-scoped guest session id) |
| **Body** | Same shape as authenticated chat: `{ "message": string, "chat_id"?: string }` (snake_case) |
| **Success** | Same `ChatResponse` shape as `POST /api/chat/message` |

### Error responses (JSON `detail` + `code` where applicable)

| HTTP | `code` | When |
|------|--------|------|
| `403` | `public_chat_disabled` | `VOYA_FEATURE_FLAG_PUBLIC_CHAT` is off — public chat is not available |
| `429` | `public_rate_limit` | Guest exceeded the per-IP sliding window (default 7 messages / 60s when rate limiting is enabled) — **frontend should prompt sign-up** (e.g. open the auth modal) with the returned `detail` message |
| `429` | `chat_request_in_progress` | Same conversation lock as authenticated chat — another request is still processing for this `chat_id` |

Guest chat traffic and rate-limit events are logged with **anonymized buckets** (hashed identifiers), not raw client IPs or full session UUIDs in log lines.

### Full-page public chat (`/public/chat`)

When `public_chat_enabled` is true, the SPA registers **`/public/chat`**: a full-viewport guest chat using the same **`ChatPanel`** (standalone) as authenticated **`/chat`**, not a second chat implementation. The landing flow can navigate here with **`?prompt=`** for the first message.

**After sign-in**, `PublicRoute` sends the user to **`/chat`** with **`replace`**, preserving **`?prompt=`** when it came from the URL or from the landing “redirect to chat after auth” localStorage keys. Rich-result CTAs (**View itinerary**, **View flights**, **View hotels**) use `usePublicChatConversionGate` for guests (auth modal) vs direct navigation when signed in.

**Guest `sessionStorage`** (`X-Public-Chat-Session` id and guest `chat_id`) is **not** cleared automatically on login; it is cleared when the guest explicitly clears the chat in guest mode, or when a future **claim** flow succeeds (see below). That avoids wiping tab-local state before a claim API exists.

### Guest chat ownership after login (not implemented)

**Goal (optional follow-up):** attach the guest thread to the user so conversation history continues after JWT (e.g. `POST /api/chat/claim-guest` with `{ guest_session_id, chat_id }`, plus server-side ownership checks). Until then, the product behavior is: sign-in → **`/chat`** with the authenticated messaging API; the guest thread remains only in `sessionStorage` for same-tab pre-auth use.

### Authenticated chat (unchanged)

`POST /api/chat/message` and other `/api/chat/*` routes still require a valid JWT. There are no public equivalents for `/chat/latest`, conversation list, feedback, or clear-history APIs.

## Error Handling Conventions

### Standard Error Response Format
```json
{
  "detail": "Human-readable error message",
  "status_code": 400
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created (new resource)
- `400` - Bad Request (client error, invalid input)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (valid token, insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `409` - Conflict (e.g. `POST /api/flights/book`: `client_reference` is `VOYA-*` but the booking row is not `PENDING` with a placeholder supplier ref, or the supplier accepted the booking but Voya could not update the stored row — **do not** auto-retry payment; show `detail` and have the user refresh or contact support)
- `422` - Validation Error (Pydantic validation failed)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error (backend issue)
- `502` - Bad Gateway (external API error)
- `504` - Gateway Timeout (external API timeout)

**Places API**: `/api/places/*` may return `500` (unexpected server error) or `502` (Google Places API error). Frontend should treat both as server errors and display a generic retry message.
`GET /api/places/photos/{resource_name}/media` requires JWT auth. Because plain `<img src>` requests cannot attach `Authorization` headers, frontend code should fetch protected image URLs with the bearer token, convert the response to a blob URL, and render that blob URL in the image component.

### Frontend Error Handling Pattern
```javascript
try {
  const response = await api.post('/api/flights/search', params);
  return response.data;
} catch (error) {
  if (error.response) {
    // Backend returned error response
    const { status_code, detail } = error.response.data;
    if (status_code === 401) {
      // Token expired or invalid - redirect to login
      redirectToLogin();
    } else if (status_code === 422) {
      // Validation error - show field-specific errors
      displayValidationErrors(detail);
    } else {
      // Other error - show error message to user
      showErrorNotification(detail);
    }
  } else if (error.request) {
    // Network error - backend didn't respond
    showErrorNotification('Service unavailable. Please check your connection.');
  } else {
    // Request setup error
    showErrorNotification('Request failed. Please try again.');
  }
}
```

### Backend Error Response Examples

**Validation Error (422)**:
```json
{
  "detail": [
    {
      "loc": ["body", "origin_iata"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Business Logic Error (400)**:
```json
{
  "detail": "No flights available for selected dates",
  "status_code": 400
}
```

**Authentication Error (401)**:
```json
{
  "detail": "Invalid or expired token",
  "status_code": 401
}
```

## Data Transformation Patterns

### Backend → Frontend (snake_case → camelCase)
```javascript
// ✅ Transform in API layer
function transformBooking(backendData) {
  return {
    bookingId: backendData.booking_id,
    flightNumber: backendData.flight_number,
    passengerName: backendData.passenger_name,
    departureTime: backendData.departure_time,
    arrivalTime: backendData.arrival_time,
    totalPrice: backendData.total_price,
    status: backendData.status,
    createdAt: new Date(backendData.created_at),
  };
}

// Use in API client
async function getBooking(bookingId) {
  const response = await api.get(`/api/bookings/${bookingId}`);
  return transformBooking(response.data);
}
```

### Frontend → Backend (camelCase → snake_case)
```javascript
// ✅ Transform before sending
function transformSearchParams(frontendParams) {
  return {
    origin_iata: frontendParams.originIata,
    destination_iata: frontendParams.destinationIata,
    departure_date: frontendParams.departureDate,
    return_date: frontendParams.returnDate,
    adults: frontendParams.adults,
    children: frontendParams.children,
    infants: frontendParams.infants,
    cabin_class: frontendParams.cabinClass,
  };
}

// Use in API client
async function searchFlights(params) {
  const transformedParams = transformSearchParams(params);
  const response = await api.post('/api/flights/search', transformedParams);
  return response.data.map(transformFlight);
}
```

### Generic Transformation Utilities
```javascript
// ✅ Reusable transformation functions
function toSnakeCase(obj) {
  return Object.keys(obj).reduce((acc, key) => {
    const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
    acc[snakeKey] = obj[key];
    return acc;
  }, {});
}

function toCamelCase(obj) {
  return Object.keys(obj).reduce((acc, key) => {
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
    acc[camelKey] = obj[key];
    return acc;
  }, {});
}
```

## Common Integration Patterns

### Loading States
```javascript
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);

async function searchFlights() {
  setLoading(true);
  setError(null);
  try {
    const results = await api.post('/api/flights/search', params);
    setFlights(results.data);
  } catch (error) {
    setError(error.response?.data?.detail || 'Search failed');
  } finally {
    setLoading(false);
  }
}
```

### Async Operations with Redux
```javascript
// ✅ Use Redux Thunk for async actions
export const searchFlights = createAsyncThunk(
  'flights/search',
  async (params, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/flights/search', params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response.data);
    }
  }
);

// Use in slice
const flightSlice = createSlice({
  name: 'flights',
  initialState: {
    results: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(searchFlights.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(searchFlights.fulfilled, (state, action) => {
        state.loading = false;
        state.results = action.payload;
      })
      .addCase(searchFlights.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});
```

### Polling for Updates
```javascript
// ✅ Poll for booking status updates
useEffect(() => {
  if (!bookingId) return;

  const interval = setInterval(async () => {
    try {
      const status = await api.get(`/api/bookings/${bookingId}/status`);
      setBookingStatus(status.data);

      if (status.data.confirmed || status.data.failed) {
        clearInterval(interval);
        if (status.data.confirmed) {
          showConfirmation();
        } else {
          showError(status.data.error_message);
        }
      }
    } catch (error) {
      console.error('Status check failed:', error);
      clearInterval(interval);
    }
  }, 5000); // Poll every 5 seconds

  return () => clearInterval(interval);
}, [bookingId]);
```

### Debouncing API Calls
```javascript
// ✅ Debounce search input to reduce API calls
import { debounce } from 'lodash';

const debouncedSearch = useCallback(
  debounce(async (query) => {
    if (query.length < 3) return;

    try {
      const results = await api.get(`/api/airports/search?q=${query}`);
      setSuggestions(results.data);
    } catch (error) {
      console.error('Search failed:', error);
    }
  }, 300),
  []
);

useEffect(() => {
  debouncedSearch(searchQuery);
}, [searchQuery, debouncedSearch]);
```

### Request Cancellation
```javascript
// ✅ Cancel in-flight requests when component unmounts
useEffect(() => {
  const controller = new AbortController();

  async function fetchData() {
    try {
      const response = await api.get('/api/flights/search', {
        params: searchParams,
        signal: controller.signal,
      });
      setResults(response.data);
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Request cancelled');
      } else {
        handleError(error);
      }
    }
  }

  fetchData();

  return () => controller.abort();
}, [searchParams]);
```

## Payment Integration

### Payment Flow Overview

Voya uses **Stripe** for payment processing with automatic platform fee collection (5%).

```
Frontend                    Backend                      Stripe
   |                           |                            |
   |-- POST /api/payments/create-intent ------------------>|
   |                           |                            |
   |                           |-- Create PaymentIntent -->|
   |                           |<-- client_secret ---------|
   |<-- client_secret, publishable_key -------------------|
   |                           |                            |
   |-- Initialize Stripe.js --|                            |
   |-- Present Card Element --|                            |
   |                           |                            |
   |-- User enters card ----->|                            |
   |-- confirmCardPayment(client_secret) ----------------->|
   |                           |                            |
   |                           |<-- payment_intent.succeeded (webhook)
   |                           |-- Update transaction DB --|
   |<-- paymentIntent {id, status} ------------------------|
   |                           |                            |
   |-- POST /api/flights/create-booking-from-session ---->|
   |    (with payment_intent_id)                           |
   |                           |                            |
   |                           |-- Validate payment ------>|
   |                           |<-- status: succeeded -----|
   |                           |                            |
   |                           |-- Create booking with FlightLogic
   |<-- Booking confirmation -|
```

### Payment API Endpoints

#### 1. Create Payment Intent

**Endpoint**: `POST /api/payments/create-intent`

**Request**:
```javascript
const response = await fetch('/api/payments/create-intent', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    booking_amount: 10000,  // $100.00 in cents
    currency: 'usd',
    voya_booking_reference: 'VOYA-TEST-12345'
  })
});

const data = await response.json();
// {
//   payment_intent_id: "pi_3ABC123...",
//   client_secret: "pi_3ABC123..._secret_xyz",
//   amount: 10000,
//   currency: "usd",
//   platform_fee: 500,        // 5% = $5.00
//   supplier_amount: 9500,    // 95% = $95.00
//   publishable_key: "pk_test_..."
// }
```

#### 2. Get Transaction

**Endpoint**: `GET /api/payments/transaction/{payment_intent_id}`

**Request**:
```javascript
const response = await fetch(`/api/payments/transaction/${paymentIntentId}`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const transaction = await response.json();
// {
//   id: "transaction_123",
//   stripe_payment_intent_id: "pi_3ABC123...",
//   voya_booking_reference: "VOYA-TEST-12345",
//   amount: 10000,
//   platform_fee: 500,
//   supplier_amount: 9500,
//   status: "succeeded",
//   created_at: "2025-10-20T12:00:00Z",
//   paid_at: "2025-10-20T12:05:00Z"
// }
```

#### 3. Release Payout (Admin Only)

**Endpoint**: `POST /api/payments/payouts/release`

**Request**:
```javascript
const response = await fetch('/api/payments/payouts/release', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    voya_booking_reference: 'VOYA-TEST-12345',
    notes: 'Released after flight completion'
  })
});

const payout = await response.json();
// {
//   transfer_id: "tr_3XYZ789...",
//   amount: 9500,
//   destination_account: "acct_xxx",
//   status: "paid"
// }
```

### Stripe.js Client-Side Integration

#### Setup

**1. Load Stripe.js**:
```html
<script src="https://js.stripe.com/v3/"></script>
```

**2. Create Payment Intent on Backend**:
```javascript
async function createPaymentIntent(bookingAmount, bookingReference) {
  const response = await fetch('/api/payments/create-intent', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      booking_amount: bookingAmount,
      currency: 'usd',
      voya_booking_reference: bookingReference
    })
  });

  if (!response.ok) {
    throw new Error('Failed to create payment intent');
  }

  return await response.json();
}
```

**3. Initialize Stripe and Card Element**:
```javascript
let stripe;
let cardElement;

async function initializeStripePayment(bookingAmount, bookingReference) {
  try {
    // Create payment intent
    const paymentIntent = await createPaymentIntent(bookingAmount, bookingReference);

    // Initialize Stripe.js
    stripe = Stripe(paymentIntent.publishable_key);

    // Create card element
    const elements = stripe.elements();
    cardElement = elements.create('card', {
      style: {
        base: {
          fontSize: '16px',
          color: '#32325d',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          '::placeholder': {
            color: '#aab7c4'
          }
        },
        invalid: {
          color: '#fa755a',
          iconColor: '#fa755a'
        }
      }
    });

    // Mount to DOM
    cardElement.mount('#card-element');

    // Handle real-time validation errors
    cardElement.on('change', (event) => {
      const displayError = document.getElementById('card-errors');
      if (event.error) {
        displayError.textContent = event.error.message;
      } else {
        displayError.textContent = '';
      }
    });

    return paymentIntent.client_secret;

  } catch (error) {
    console.error('Payment initialization failed:', error);
    showError('Failed to initialize payment');
  }
}
```

**4. Confirm Payment**:
```javascript
async function confirmPayment(clientSecret) {
  const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
    payment_method: {
      card: cardElement,
      billing_details: {
        name: document.getElementById('cardholder-name').value,
        email: document.getElementById('email').value
      }
    }
  });

  if (error) {
    // Payment failed
    console.error('Payment failed:', error);
    showError(error.message);
    return null;
  }

  if (paymentIntent.status === 'succeeded') {
    // Payment succeeded
    console.log('Payment succeeded:', paymentIntent.id);
    return paymentIntent.id;
  }

  return null;
}
```

**5. Complete Booking with Payment**:
```javascript
async function completeBooking(sessionId, passengerData, paymentIntentId) {
  const response = await fetch('/api/flights/create-booking-from-session', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      session_id: sessionId,
      passenger_data: {
        ...passengerData,
        payment_intent_id: paymentIntentId  // Link payment to booking
      }
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Booking failed');
  }

  return await response.json();
}
```

### Full Payment Flow Example

```javascript
async function handleFlightBooking() {
  try {
    // 1. Initialize payment
    const clientSecret = await initializeStripePayment(
      bookingAmount,
      voyaBookingReference
    );

    // 2. Show payment form to user
    showPaymentForm();

    // 3. User clicks "Pay Now"
    document.getElementById('pay-button').addEventListener('click', async () => {
      // Confirm payment with Stripe
      const paymentIntentId = await confirmPayment(clientSecret);

      if (!paymentIntentId) {
        return; // Payment failed
      }

      // 4. Create booking with payment validation
      try {
        const booking = await completeBooking(
          sessionId,
          passengerData,
          paymentIntentId
        );

        showBookingConfirmation(booking);

      } catch (error) {
        if (error.message.includes('Payment validation failed')) {
          showError('Payment validation failed. Please contact support.');
        } else {
          showError(error.message);
        }
      }
    });

  } catch (error) {
    console.error('Booking flow failed:', error);
    showError('Something went wrong. Please try again.');
  }
}
```

### Error Handling

#### Payment Required Error (402)

```javascript
async function createBookingWithPayment(sessionId, passengerData, paymentIntentId) {
  try {
    const response = await fetch('/api/flights/create-booking-from-session', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: sessionId,
        passenger_data: {
          ...passengerData,
          payment_intent_id: paymentIntentId
        }
      })
    });

    if (response.status === 402) {
      // Payment Required
      const error = await response.json();
      showError(`Payment required: ${error.detail}`);
      // Redirect back to payment page
      redirectToPayment();
      return;
    }

    if (!response.ok) {
      throw new Error('Booking failed');
    }

    return await response.json();

  } catch (error) {
    console.error('Booking error:', error);
    showError('Failed to create booking');
  }
}
```

#### Stripe Error Codes

```javascript
// Handle Stripe-specific errors
cardElement.on('change', (event) => {
  if (event.error) {
    switch (event.error.code) {
      case 'incomplete_number':
        showError('Card number is incomplete');
        break;
      case 'incomplete_expiry':
        showError('Expiration date is incomplete');
        break;
      case 'incomplete_cvc':
        showError('CVC is incomplete');
        break;
      case 'invalid_number':
        showError('Card number is invalid');
        break;
      case 'card_declined':
        showError('Your card was declined');
        break;
      default:
        showError(event.error.message);
    }
  }
});
```

### Demo Mode vs Production Mode

#### Demo Mode (Testing Without Payment)

```javascript
// Skip Stripe integration for testing
async function createDemoBooking(sessionId, passengerData) {
  return await completeBooking(
    sessionId,
    passengerData,
    'demo_payment_intent'  // Backend skips validation for demo
  );
}
```

#### Production Mode (Real Stripe Payment)

```javascript
// Full Stripe.js integration
async function createProductionBooking(sessionId, passengerData) {
  // 1. Create payment intent
  const clientSecret = await initializeStripePayment(...);

  // 2. Collect payment
  const paymentIntentId = await confirmPayment(clientSecret);

  // 3. Create booking with real payment ID
  return await completeBooking(sessionId, passengerData, paymentIntentId);
}
```

### Payment State Management (Redux Example)

```javascript
// Payment slice
const paymentSlice = createSlice({
  name: 'payment',
  initialState: {
    clientSecret: null,
    paymentIntentId: null,
    status: 'idle', // 'idle' | 'processing' | 'succeeded' | 'failed'
    error: null,
  },
  reducers: {
    paymentProcessing: (state) => {
      state.status = 'processing';
      state.error = null;
    },
    paymentSucceeded: (state, action) => {
      state.status = 'succeeded';
      state.paymentIntentId = action.payload.paymentIntentId;
    },
    paymentFailed: (state, action) => {
      state.status = 'failed';
      state.error = action.payload.error;
    },
    resetPayment: (state) => {
      state.clientSecret = null;
      state.paymentIntentId = null;
      state.status = 'idle';
      state.error = null;
    }
  }
});

// Async thunk for payment processing
export const processPayment = createAsyncThunk(
  'payment/process',
  async ({ clientSecret, stripe, cardElement, billingDetails }, { rejectWithValue }) => {
    try {
      const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: cardElement,
          billing_details: billingDetails
        }
      });

      if (error) {
        return rejectWithValue(error.message);
      }

      return { paymentIntentId: paymentIntent.id };

    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);
```

### Security Best Practices

**✅ DO**:
- Load Stripe.js from CDN (PCI compliant)
- Use `client_secret` for payment confirmation
- Never send card details to your backend
- Validate payment on backend before booking
- Use HTTPS in production

**❌ DON'T**:
- Store card details in your database
- Send card details to your backend
- Skip payment validation on backend
- Hardcode Stripe API keys in frontend code
- Use test keys in production

### Testing Payments

#### Stripe Test Cards

**Successful Payment**:
```
Card: 4242 4242 4242 4242
Expiry: Any future date (e.g., 12/25)
CVC: Any 3 digits
ZIP: Any valid ZIP
```

**Payment Declined**:
```
Card: 4000 0000 0000 0002
```

**Insufficient Funds**:
```
Card: 4000 0000 0000 9995
```

**Requires Authentication (3D Secure)**:
```
Card: 4000 0025 0000 3155
```

Full list: https://stripe.com/docs/testing#cards

## Passenger Storage API (Issue #418)

Stored passenger/guest details per authenticated user with field-level encryption for sensitive PII. Shared by flight `PassengerInfoPage` and hotel `GuestInfoPage`.

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/user/me/passengers` | POST | Create saved passenger |
| `/api/user/me/passengers` | GET | List saved passengers (sensitive fields masked) |
| `/api/user/me/passengers/{id}` | GET | Get single passenger (`?include_sensitive=true` plus `X-PII-View-Token` for passport view) |
| `/api/user/me/passengers/{id}` | PUT | Update passenger |
| `/api/user/me/passengers/{id}` | DELETE | Delete passenger (GDPR right to deletion) |

### Response Masking

Sensitive fields are masked in list/GET responses (full passport values require `include_sensitive=true` plus `X-PII-View-Token`):

- `passport_number`: `****4589`
- `passport_expiry`: `2028-**-**`
- `frequent_flyer_number`: `****7890`

### Frontend Integration (frontend-v2)

- **RTK Query**: `usersApi` in `frontend-v2/src/api/usersApi.ts` with `useGetPassengersQuery`, `useCreatePassengerMutation`, etc.
- **Types**: `frontend-v2/src/types/passengers.ts` (`StoredPassenger`, `PassengerCreateRequest`)
- **Flight**: `PassengerInfoPage` — "Use saved passenger" dropdown, "Save for future bookings" checkbox
- **Hotel**: `GuestInfoPage` — same pattern via `GuestForm` component
- **Utils**: `passengerStorageUtils.ts` for `storedPassengerToFormData`, `formatSavedPassengerLabel`
- **Data**: Backend uses snake_case; frontend uses camelCase. Transform at API boundary via `toSnakeCase` / `toCamelCase`.

## Debugging Integration Issues

### Backend Logs
```bash
# View backend logs
docker compose logs backend -f

# Search for specific request
docker compose logs backend | grep "POST /api/flights/search"

# View last 100 lines
docker compose logs backend --tail 100

# Filter by log level
docker compose logs backend | grep ERROR
```

### Frontend Network Tab
1. Open browser DevTools (F12)
2. Navigate to Network tab
3. Filter by "XHR" or "Fetch"
4. Click request to see:
   - Request headers (Authorization, Content-Type)
   - Request payload (sent data)
   - Response headers (Content-Type, status)
   - Response body (returned data)
5. Check timing (slow requests)

### API Tester Tool
- **URL**: http://localhost:8000/dev/api-tester.html
- **Use case**: Isolate backend vs frontend issues
- **Process**:
  1. Try the same request in API Tester
  2. If API Tester works but frontend doesn't → Frontend issue (transformation, error handling, state management)
  3. If API Tester fails → Backend issue (API logic, database, external API)
  4. Compare request/response between frontend and API Tester

### Common Issues

**Issue 1: "undefined undefined" in User Profile**
- **Cause**: Backend returns `first_name`/`last_name` but frontend expects `firstName`/`lastName`
- **Solution**: Add transformation in API layer

**Issue 2: Token Expired Errors**
- **Cause**: JWT token expires after 30 minutes
- **Solution**: Implement token refresh or redirect to login on 401

**Issue 3: CORS Errors**
- **Cause**: Frontend and backend on different origins
- **Solution**: Backend CORS configured for http://localhost:3000 (dev) and production domain

**Issue 4: "Network Error" with No Response**
- **Cause**: Backend not running or wrong URL
- **Solution**: Check backend is running, verify `VITE_API_URL` in `.env`

## When to Communicate

### Backend → Frontend Communication Required
- ✅ Adding new endpoint (announce before implementing)
- ✅ Changing request/response schema (breaking change)
- ✅ Deprecating endpoint (give 2-week notice)
- ✅ Changing error codes or formats
- ✅ Performance issues (slow responses >2 seconds)
- ✅ Planned downtime or maintenance
- ✅ New authentication requirements

### Frontend → Backend Communication Required
- ✅ Need new endpoint functionality
- ✅ Request schema doesn't meet UI needs
- ✅ Error messages not user-friendly
- ✅ Need additional data in response (new fields)
- ✅ Performance issues (large payloads, slow responses)
- ✅ Need pagination support
- ✅ Need filtering/sorting capabilities

### Communication Channels
- **GitHub Issues**: Feature requests, bug reports
- **Pull Request Comments**: Code review feedback
- **Slack/Teams**: Quick questions, urgent issues
- **Weekly Sync**: Upcoming changes, roadmap alignment

## Best Practices

### Backend Best Practices
1. **Versioning**: Use `/api/v1/` prefix for breaking changes
2. **Backward Compatibility**: Don't remove fields, add new ones
3. **Descriptive Errors**: Return user-friendly error messages
4. **Consistent Naming**: Use snake_case for all fields
5. **Documentation**: Keep Swagger docs up to date
6. **Validation**: Validate all inputs with Pydantic
7. **Rate Limiting**: Implement for expensive operations

### Frontend Best Practices
1. **Error Boundaries**: Catch and display errors gracefully
2. **Loading States**: Always show loading indicators
3. **Optimistic Updates**: Update UI before API response
4. **Retry Logic**: Retry failed requests with exponential backoff
5. **Caching**: Cache expensive API calls
6. **Transformation Layer**: Centralize snake_case ↔ camelCase conversion
7. **Type Safety**: Use TypeScript types generated from OpenAPI

## Related Documentation

- **API Reference**: http://localhost:8000/api/docs (Swagger UI)
- **Interactive Testing**: http://localhost:8000/dev/api-tester.html
- **Backend Patterns**: `backend_python/CLAUDE.md`
- **Frontend Patterns**: `frontend-v2/` and this document
- **Architecture**: `docs/ARCHITECTURE.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

---

**Last Updated**: October 2025
**Maintainer**: Full-stack team
**Questions**: Create GitHub issue with label `frontend-backend-integration`
