# Booking Architecture Proposal

This document defines the architecture for Phase 2 (flight booking) and Phase 3 (hotel booking) implementation.

## Overview

Both booking flows share common patterns:
- Multi-step wizard with Redux state management
- Stripe payment integration
- Session-based API interaction
- Shared UI components (stepper, payment, confirmation)

## State Management

### Redux Slice Architecture

```
store/slices/
├── authSlice.ts           # Auth + tokens (existing)
├── chatSlice.ts           # Chat messages (existing)
├── flightBookingSlice.ts  # Flight wizard state (scaffolded)
└── hotelBookingSlice.ts   # Hotel wizard state (NEW - Phase 3)
```

### Flight Booking Slice (Existing Scaffold)

**File**: `src/store/slices/flightBookingSlice.ts`

```typescript
export type BookingStep =
  | 'search'
  | 'results'
  | 'rules'       // Fare rules display
  | 'passengers'  // Passenger details
  | 'review'
  | 'payment'
  | 'confirmation';

interface FlightBookingState {
  currentStep: BookingStep;
  searchParams: FlightSearchParams | null;
  selectedFlight: MappedFlight | null;
  sessionId: string | null;
  passengers: PassengerDetails[];
  loading: boolean;
  error: string | null;
  bookingReference: string | null;
}

interface PassengerDetails {
  type: 'adult' | 'child' | 'infant';
  title: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  nationality: string;
  passportNumber?: string;
  passportExpiry?: string;
  passportCountry?: string;
}
```

### Hotel Booking Slice (Phase 3 - NEW)

**File**: `src/store/slices/hotelBookingSlice.ts`

```typescript
export type HotelBookingStep =
  | 'search'
  | 'results'
  | 'rooms'          // Room selection
  | 'cancellation'   // Rate rules/cancellation policy
  | 'guest'          // Guest details
  | 'review'
  | 'payment'
  | 'confirmation';

interface HotelBookingState {
  currentStep: HotelBookingStep;
  searchParams: HotelSearchRequest | null;
  sessionId: string | null;
  selectedHotel: Hotel | null;
  selectedRoom: RoomRate | null;
  tokenId: string | null;           // FlightLogic hotel token
  rateBasisId: string | null;       // Selected rate identifier
  productId: string | null;         // Room product identifier
  guests: GuestDetails[];
  specialRequests: string;
  cancellationPolicy: CancellationPolicy | null;
  loading: boolean;
  error: string | null;
  bookingReference: string | null;
}

interface GuestDetails {
  title: 'Mr' | 'Mrs' | 'Ms' | 'Miss' | 'Dr';
  firstName: string;
  lastName: string;
  email?: string;
  phone?: string;
}
```

## Booking Flows

### Flight Booking Flow (Phase 2)

```
┌──────────┐    ┌──────────┐    ┌───────┐    ┌────────────┐
│  Search  │───▶│ Results  │───▶│ Rules │───▶│ Passengers │
└──────────┘    └──────────┘    └───────┘    └────────────┘
                                                    │
                                                    ▼
┌──────────────┐    ┌─────────┐    ┌────────┐    ┌────────┐
│ Confirmation │◀───│ Payment │◀───│ Review │◀───│   ...  │
└──────────────┘    └─────────┘    └────────┘    └────────┘
```

**Steps**:
1. **Search**: Origin, destination, dates, passengers, cabin class
2. **Results**: Curated categories (cheapest, fastest, best value)
3. **Rules**: Fare rules, baggage allowance, refund policy
4. **Passengers**: Details for each traveler (passport for international)
5. **Review**: Booking summary, price breakdown
6. **Payment**: Stripe payment form
7. **Confirmation**: Booking reference, itinerary details

**API Endpoints** (from `flightsApi.ts`):
- `POST /flights/search` - Search flights
- `POST /flights/select` - Select flight, get session
- `POST /flights/fare-rules` - Get fare rules
- `POST /flights/revalidate` - Revalidate pricing
- `POST /flights/book` - Complete booking
- `POST /flights/payment-intent` - Create Stripe intent

### Hotel Booking Flow (Phase 3)

```
┌──────────┐    ┌──────────┐    ┌───────┐    ┌──────────────┐
│  Search  │───▶│ Results  │───▶│ Rooms │───▶│ Cancellation │
└──────────┘    └──────────┘    └───────┘    └──────────────┘
                                                    │
                                                    ▼
┌──────────────┐    ┌─────────┐    ┌────────┐    ┌───────┐
│ Confirmation │◀───│ Payment │◀───│ Review │◀───│ Guest │
└──────────────┘    └─────────┘    └────────┘    └───────┘
```

**Steps**:
1. **Search**: City/location, check-in/out, rooms, occupancy
2. **Results**: Hotel list with curated picks (best value, cheapest, highest rated)
3. **Rooms**: Room type selection with rates
4. **Cancellation**: Rate rules, cancellation policy display
5. **Guest**: Guest details for each room
6. **Review**: Booking summary, price breakdown
7. **Payment**: Stripe payment form
8. **Confirmation**: Booking reference, hotel details

**API Endpoints** (from `hotelsApi.ts`):
- `POST /hotels/search` - Search hotels
- `POST /hotels/more-results` - Pagination
- `POST /hotels/room-rates` - Get room rates for hotel
- `POST /hotels/rate-rules` - Get cancellation policy
- `POST /hotels/book` - Complete booking
- `GET /hotels/session/:id` - Get session data

## Component Architecture

### Directory Structure

```
src/features/
├── booking/                    # Shared booking components
│   ├── components/
│   │   ├── BookingStepper.tsx     # Step indicator
│   │   ├── PaymentForm.tsx        # Stripe integration
│   │   ├── ReviewSummary.tsx      # Price breakdown
│   │   └── ConfirmationDisplay.tsx
│   ├── hooks/
│   │   ├── useBookingFlow.ts      # Step navigation
│   │   └── usePayment.ts          # Stripe hooks
│   └── types.ts
│
├── flights/                    # Flight-specific
│   ├── pages/
│   │   ├── FlightSearchPage.tsx
│   │   ├── FlightResultsPage.tsx
│   │   ├── PassengerDetailsPage.tsx
│   │   └── FlightConfirmationPage.tsx
│   ├── components/
│   │   ├── FlightSearchForm.tsx
│   │   ├── AirportAutocomplete.tsx # With 29K+ airports
│   │   ├── FlightCard.tsx
│   │   ├── FlightFilters.tsx
│   │   ├── PassengerForm.tsx
│   │   └── FareRulesDisplay.tsx
│   ├── hooks/
│   │   └── useFlightBooking.ts
│   └── index.ts
│
└── hotels/                     # Hotel-specific
    ├── pages/
    │   ├── HotelSearchPage.tsx
    │   ├── HotelResultsPage.tsx
    │   ├── RoomSelectionPage.tsx
    │   ├── GuestDetailsPage.tsx
    │   └── HotelConfirmationPage.tsx
    ├── components/
    │   ├── HotelSearchForm.tsx
    │   ├── CityAutocomplete.tsx    # Google Geocoding
    │   ├── HotelCard.tsx
    │   ├── HotelMap.tsx            # Google Maps
    │   ├── RoomSelector.tsx
    │   ├── GuestForm.tsx
    │   └── CancellationPolicyDisplay.tsx
    ├── hooks/
    │   └── useHotelBooking.ts
    └── index.ts
```

### Shared Components (features/booking/)

#### BookingStepper

```typescript
interface BookingStepperProps {
  steps: { key: string; label: string }[];
  currentStep: string;
  onStepClick?: (step: string) => void;
}
```

#### PaymentForm (Stripe)

```typescript
interface PaymentFormProps {
  amount: number;
  currency: string;
  onPaymentSuccess: (paymentIntentId: string) => void;
  onPaymentError: (error: string) => void;
}
```

Requires: `@stripe/react-stripe-js`, `@stripe/stripe-js`

#### useBookingFlow Hook

```typescript
function useBookingFlow<T extends string>(
  steps: T[],
  currentStep: T,
  setStep: (step: T) => void
) {
  return {
    goToNext: () => void,
    goToPrevious: () => void,
    goToStep: (step: T) => void,
    canGoNext: boolean,
    canGoPrevious: boolean,
    stepIndex: number,
    totalSteps: number,
  };
}
```

## Data Flow

### Flight Booking Data Flow

```
User Action           Redux Action              API Call
────────────────────────────────────────────────────────────
Search submit    →    setSearchParams      →    searchFlights
                      setStep('results')

Select flight    →    selectFlight         →    selectFlight API
                      setStep('rules')          (returns sessionId)

View rules       →    (display only)       →    getFareRules
                      setStep('passengers')

Enter passengers →    setPassengers        →    (local only)
                      setStep('review')

Review booking   →    (display only)       →    revalidateFlight
                      setStep('payment')

Payment          →    setLoading(true)     →    createPaymentIntent
                                           →    bookFlight
                      setBookingConfirmation
                      setStep('confirmation')
```

### Hotel Booking Data Flow

```
User Action           Redux Action              API Call
────────────────────────────────────────────────────────────
Search submit    →    setSearchParams      →    searchHotels
                      setStep('results')        (returns sessionId)

Select hotel     →    selectHotel          →    getRoomRates
                      setStep('rooms')          (returns tokenId)

Select room      →    selectRoom           →    getRateRules
                      setStep('cancellation')   (validates rate)

View policy      →    setCancellationPolicy →   (from rate rules)
                      setStep('guest')

Enter guests     →    setGuests            →    (local only)
                      setStep('review')

Review booking   →    (display only)       →    (validate session)
                      setStep('payment')

Payment          →    setLoading(true)     →    createPaymentIntent
                                           →    bookHotel
                      setBookingConfirmation
                      setStep('confirmation')
```

## Form Validation (Zod Schemas)

### Flight Passenger Schema

```typescript
const passengerSchema = z.object({
  type: z.enum(['adult', 'child', 'infant']),
  title: z.string().min(1, 'Required'),
  firstName: z.string().min(2, 'Min 2 characters'),
  lastName: z.string().min(2, 'Min 2 characters'),
  dateOfBirth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Invalid date'),
  nationality: z.string().length(2, 'Use 2-letter code'),
  passportNumber: z.string().optional(),
  passportExpiry: z.string().optional(),
  passportCountry: z.string().optional(),
});
```

### Hotel Guest Schema

```typescript
const guestSchema = z.object({
  title: z.enum(['Mr', 'Mrs', 'Ms', 'Miss', 'Dr']),
  firstName: z.string().min(2, 'Min 2 characters'),
  lastName: z.string().min(2, 'Min 2 characters'),
  email: z.string().email().optional(),
  phone: z.string().optional(),
});
```

## Dependencies to Add

```bash
# Phase 2: Stripe integration
npm install @stripe/react-stripe-js @stripe/stripe-js

# Already included: date-fns, @mui/x-date-pickers, @react-google-maps/api
```

## Implementation Timeline

### Phase 2: Flight Booking (8-11 days)

1. **Day 1-2**: Search form + AirportAutocomplete
2. **Day 3-4**: Results page + FlightCard + filters
3. **Day 5**: Fare rules display
4. **Day 6-7**: Passenger forms (multi-passenger)
5. **Day 8-9**: Review + Stripe payment
6. **Day 10-11**: Confirmation + testing

### Phase 3: Hotel Booking (3-5 days)

1. **Day 1**: Search form + CityAutocomplete
2. **Day 2**: Results + HotelCard + map integration
3. **Day 3**: Room selection + cancellation policy
4. **Day 4**: Guest forms (reuse patterns from flights)
5. **Day 5**: Payment + confirmation (reuse from flights)

## Reference: Vanilla JS Bookers

For complete flow details and edge cases:

- **Flight booker**: `backend_python/dev_ui/flight-booker/index.html` (14,858 lines)
- **Hotel booker**: `backend_python/dev_ui/hotel-booker/index.html` (7,847 lines)

These vanilla JS implementations contain the complete business logic including:
- Multi-step form validation
- API error handling
- Session management
- Payment flow integration
