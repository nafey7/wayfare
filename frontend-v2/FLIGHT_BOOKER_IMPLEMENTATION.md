# [FEATURE] Implement Flight Booker Flow in Frontend-v2

**GitHub Issue:** [#293](https://github.com/myvoya/voya/issues/293)
**Status:** In Progress
**Priority:** High (P1)
**Effort Estimate:** L (2-4 weeks)

## 📊 Business Context

- **Current state:** Flight booking functionality exists in backend dev UI (`backend_python/dev_ui/flight-booker/index.html`) but not in the modern frontend-v2 React application
- **Problem:** Users cannot complete flight bookings through the main frontend application, limiting the platform's core functionality
- **Opportunity:** Provide a seamless, modern flight booking experience integrated into the main frontend-v2 application

## 💰 Business Value

- Enable end-to-end flight booking through the main application
- Improved user experience with modern React components and state management
- Foundation for future multi-city flight booking support
- Better integration with existing chat-based flight search results
- Estimated impact: Core feature enabling primary revenue stream

## 👤 User Story

As a traveler
I want to search, select, and book flights through the frontend-v2 application
So that I can complete my travel booking in a seamless, modern interface

## 🔧 Technical Implementation

### Proposed Solution

- Implement complete flight booking wizard flow in `frontend-v2/src/features/flights/`
- Reference implementation: `backend_python/dev_ui/flight-booker/index.html`
- Use existing Redux slice (`flightBookingSlice.ts`) for state management
- Leverage existing API endpoints in `flightsApi.ts`
- Support multi-city flight variable naming from the start (future-proofing)

### Key Components to Implement

#### 1. Flight Search Form (`FlightSearchForm.tsx`)
- Airport autocomplete with search functionality
- Date pickers for departure/return dates
- Journey type selector (OneWay, Return, Circle - for future multi-city)
- Passenger selection (adults, children, infants)
- Cabin class selection

#### 2. Flight Results Display (`FlightResults.tsx`)
- Display flight results in categories (cheapest, fastest, best value)
- Filtering capabilities (price, duration, stops, airlines, departure/arrival times)
- Sorting options
- Flight selection functionality

#### 3. Fare Rules Display (`FareRules.tsx`)
- Show fare rules after flight selection
- Terms and conditions display

#### 4. Passenger Details Form (`PassengerDetailsForm.tsx`)
- Collect passenger information for all travelers
- Form validation
- Support for adults, children, and infants

#### 5. Booking Review (`BookingReview.tsx`)
- Review selected flight details
- Review passenger information
- Price breakdown (including platform fees)

#### 6. Payment Integration (`PaymentStep.tsx`)
- Revolut payment integration (@revolut/checkout)
- Revolut order creation and card field confirmation

#### 7. Booking Confirmation (`BookingConfirmation.tsx`)
- Display booking reference
- Show booking details
- Success messaging

### Technical Considerations

#### Multi-city Support
**CRITICAL:** Use array-based variable names (e.g., `flightLegs[]`, `segments[]`) instead of hardcoded `outbound`/`return` to support future multi-city implementation.

**Examples:**
- ✅ Use `flightLegs: FlightLeg[]` instead of separate `outbound`/`return` properties
- ✅ Use `segments: FlightSegment[]` arrays instead of hardcoded single segments
- ✅ Journey type should support `Circle` type (already in types)
- ✅ Variable names should be plural/array-based where applicable
- ❌ Avoid hardcoded assumptions about number of legs

#### State Management
- Extend existing `flightBookingSlice.ts` if needed, but maintain compatibility
- Current steps: `'search' | 'results' | 'rules' | 'passengers' | 'review' | 'payment' | 'confirmation'`

#### API Integration
Use existing `flightsApi.ts` endpoints:
- `searchFlights` - Flight search
- `selectFlight` - Flight selection and session creation
- `getFareRules` - Fare rules retrieval
- `revalidateFlight` - Fare revalidation
- `bookFlightFromSession` - Complete booking

#### Routing
- Integrate with React Router for navigation between steps
- Support URL parameters for deep linking (e.g., from chat results)
- Handle booking session persistence across page refreshes

#### Session ID (localStorage)
- `sessionId` is stored in localStorage as a fallback for navigation (e.g. when reopening payment tab). The new response’s `session_id` is the single source of truth for the current flow.
- **Cleared on logout** so it is not reused across users or after sign-out.
- **Cleared on new search** (when the user clicks Search on FlightSearchPage) so each search uses only its own session.
- Do not rely on localStorage `sessionId` after logout or after starting a new flight search.

#### Currency amount conventions (cents vs base currency)
- **Major units (base currency):** Display amounts, e.g. `199.50` for $199.50. Used by API `fare_totals.total_fare.amount`, `FlightPrice`, and `FilterableFlight.price`.
- **Cents (minor units):** Integer amounts for Revolut and booking totals, e.g. `19950` for $199.50. Used by `FlightBookingResponse.totalAmount`, `UserBooking.totalAmount`, Redux `bookingResult.totalAmount`, and all payment API amount fields (`booking_amount`, `amount`, etc.).
- **Helpers:** `formatCurrencyFromCents(cents, currency)` in `flightUtils.ts` for displaying booking/payment amounts (cents → locale-aware string); `formatCurrency(amount, currency)` for API amounts in major units. When the API returns major units (e.g. fare total), convert to cents with `* 100` before storing in `bookingResult.totalAmount` or sending to payment APIs.
- Full convention and type-level docs: `src/types/flights.ts` (file-level comment).

### Dependencies

- ✅ Existing flight API endpoints (already implemented)
- ✅ Redux store setup (already configured)
- ✅ Material-UI components (already in use)
- ✅ Revolut integration (@revolut/checkout, revolutPaymentsApi)

### Differences from Reference Implementation

- Reference HTML supports only one-way and round-trip
- Frontend-v2 implementation should use variable names that support multi-city (e.g., `flightLegs: FlightLeg[]` instead of `outbound`/`return` properties)
- Use TypeScript for type safety
- Use React hooks and modern patterns
- Integrate with existing Redux state management

## ✅ Acceptance Criteria

- [ ] Flight search form with airport autocomplete, date pickers, and passenger selection
- [ ] Flight results display with filtering and sorting capabilities
- [ ] Flight selection creates booking session
- [ ] Fare rules display after flight selection
- [ ] Passenger details form collects all required information
- [ ] Booking review shows complete booking summary
- [ ] Payment integration with Revolut works correctly
- [ ] Booking confirmation displays booking reference
- [ ] All steps are navigable (forward and backward)
- [ ] URL parameters support deep linking from chat results
- [ ] Session persistence works across page refreshes
- [ ] Variable names support multi-city flights (future-proofing)
- [ ] Responsive design works on mobile and desktop
- [ ] Error handling for API failures
- [ ] Loading states during API calls
- [ ] Unit tests for all new components
- [ ] Integration tests for booking flow
- [ ] Existing unit tests verified and updated as needed
- [ ] Documentation updated (CHANGELOG.md, relevant docs/)

## 🎯 Success Criteria

### Metrics
- Booking completion rate: >80%
- Average booking time: <10 minutes
- Error rate: <2%
- Mobile usability score: >90

### Qualitative measures
- User feedback on booking flow ease-of-use
- Code maintainability (multi-city ready)
- Performance benchmarks (page load, API response times)
- Developer satisfaction with implementation

## 📎 Reference Files

### Implementation Reference
- **Primary reference:** `backend_python/dev_ui/flight-booker/index.html`
  - Step-based wizard flow (search → select → rules → passengers → review → payment → confirmation)
  - Airport autocomplete with search
  - Advanced filtering (price, duration, stops, airlines, times)
  - Flight result categorization (cheapest, fastest, best value)
  - Fare rules display
  - Passenger information collection
  - Payment integration
  - Booking confirmation

### Existing Frontend-v2 Files
- **Redux slice:** `frontend-v2/src/store/slices/flightBookingSlice.ts`
- **API:** `frontend-v2/src/api/flightsApi.ts`
- **Flight types:**
  - `frontend-v2/src/types/flight.ts`
  - `src/types/flights.ts`
- **Existing components:** `frontend-v2/src/features/chat/components/flights/` (can be reused/adapted)

### Related Components
- Existing flight display components in `frontend-v2/src/features/chat/components/flights/` can be reused/adapted
- Chat integration: Flight results from chat should be able to link to booking flow

## 🧪 Testing & Documentation Requirements

**All features must include:**
- Comprehensive unit tests for new functionality
- Integration tests where applicable
- Verify existing unit tests still pass
- Update CLAUDE.md only for AI context changes (brief behavioral notes, not implementation details)
- Document features in appropriate files:
  - CHANGELOG.md (user summary)
  - docs/ (technical details)
  - README.md (major features)
  - API docs (endpoints)

## 📝 Implementation Steps

### Phase 1: Setup & Foundation
1. [ ] Create feature directory structure: `frontend-v2/src/features/flights/`
2. [ ] Review and extend `flightBookingSlice.ts` if needed for multi-city support
3. [ ] Set up routing for booking flow
4. [ ] Create base wizard component with step navigation

### Phase 2: Search & Results
5. [ ] Implement `FlightSearchForm.tsx` with airport autocomplete
6. [ ] Implement `FlightResults.tsx` with filtering and sorting
7. [ ] Integrate with `searchFlights` API endpoint
8. [ ] Add URL parameter support for deep linking

### Phase 3: Selection & Rules
9. [ ] Implement flight selection functionality
10. [ ] Integrate with `selectFlight` API endpoint
11. [ ] Implement `FareRules.tsx` component
12. [ ] Integrate with `getFareRules` API endpoint

### Phase 4: Passenger Details
13. [ ] Implement `PassengerDetailsForm.tsx`
14. [ ] Add form validation
15. [ ] Support for adults, children, and infants

### Phase 5: Review & Payment
16. [ ] Implement `BookingReview.tsx`
17. [ ] Implement `PaymentStep.tsx` with Revolut integration
18. [ ] Integrate with `bookFlightFromSession` API endpoint

### Phase 6: Confirmation & Polish
19. [ ] Implement `BookingConfirmation.tsx`
20. [ ] Add session persistence
21. [ ] Add error handling and loading states
22. [ ] Responsive design implementation
23. [ ] Write unit tests
24. [ ] Write integration tests
25. [ ] Update documentation

## 🔑 Key Implementation Notes

### Multi-city Future-proofing Checklist

When implementing, ensure:
- [ ] Use `flightLegs: FlightLeg[]` instead of separate `outbound`/`return` properties
- [ ] Use `segments: FlightSegment[]` arrays instead of hardcoded single segments
- [ ] Journey type supports `Circle` type (already in types)
- [ ] Variable names are plural/array-based where applicable
- [ ] No hardcoded assumptions about number of legs
- [ ] Components can handle variable number of flight legs
- [ ] UI adapts dynamically to number of segments

### Code Quality Standards

- Follow existing frontend-v2 patterns and conventions
- Use TypeScript with proper type definitions
- Follow Material-UI design system
- Implement proper error boundaries
- Add loading states for all async operations
- Ensure accessibility (a11y) compliance
- Optimize for performance (lazy loading, memoization where appropriate)

---

**Last Updated:** January 27, 2026
**Next Review:** After Phase 1 completion
