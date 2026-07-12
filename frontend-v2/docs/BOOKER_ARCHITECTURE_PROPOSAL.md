# Frontend Booker Architecture Proposal

**Date**: January 2026
**Participants**: Roel Sadza, Moiz Nafey (@nafey7)
**Status**: Draft - For Review

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Redux usage | Minimize - use RTK Query first, add slices only where truly needed |
| Booking slices | Separate slices for flights vs hotels (avoid conflicts) |
| Shared logic | `useBookingFlow` hook (not a slice) for common step orchestration |
| Auth slice | Shared across all bookers |
| Implementation order | Flight booker first, then hotel (reuse patterns) |
| Search results | Frontend pagination (backend changes out of scope) |
| Database tables | Defer refactoring - keep shared `booking_events` for now |

---

## Architecture Principles

### 1. Redux Minimalism

**Approach**: Try implementing features without Redux first. Add slices only where state truly needs to be global.

**Why**: RTK Query already handles:
- API response caching
- Loading states (no boilerplate)
- Cache invalidation

**What still needs Redux slices**:
- Authentication state (shared across app)
- Multi-step wizard state (survives navigation between steps)
- User selections that must persist across components

### 2. Separate Booking Slices

```
store/slices/
├── authSlice.ts           # Shared - auth state
├── flightBookingSlice.ts  # Flight wizard state only
└── hotelBookingSlice.ts   # Hotel wizard state only (Phase 3)
```

**Why separate?** Prevents conflicts when user has both a flight and hotel booking in progress.

**Slice contains** (minimal):
- Current step
- Selected flight/hotel
- Session ID
- Passenger/guest details (for form persistence)
- Booking reference (after completion)

**Slice does NOT contain**:
- Search results (RTK Query cache)
- Fare rules/rate rules (RTK Query cache)
- Loading states (RTK Query handles)

### 3. Shared `useBookingFlow` Hook

Common booking logic orchestrated via a hook, not a slice:

```typescript
// features/booking/hooks/useBookingFlow.ts

function useBookingFlow<TStep extends string>(config: {
  steps: TStep[];
  currentStep: TStep;
  setStep: (step: TStep) => void;
  canProceed: () => boolean;  // validation check
}) {
  return {
    // Navigation
    goToNext: () => void;
    goToPrevious: () => void;
    goToStep: (step: TStep) => void;

    // State
    stepIndex: number;
    totalSteps: number;
    canGoNext: boolean;
    canGoPrevious: boolean;
    isFirstStep: boolean;
    isLastStep: boolean;

    // Progress
    progressPercent: number;
  };
}
```

**Usage**:
```typescript
// In FlightBookingPage.tsx
const { goToNext, canGoNext } = useBookingFlow({
  steps: ['search', 'results', 'rules', 'passengers', 'review', 'payment', 'confirmation'],
  currentStep: currentStep,  // from flightBookingSlice
  setStep: (step) => dispatch(setStep(step)),
  canProceed: () => validateCurrentStep(),
});
```

**Benefits**:
- Reusable across flight, hotel, car rental, etc.
- Each booker maintains its own state (via its own slice)
- No global state conflicts
- Easy to test in isolation

---

## Implementation Plan

### Phase 2: Flight Booker

**Priority**: First

**Goal**: Set up flight booker with shared patterns so hotel booker implementation is faster.

**Components to build**:
1. `useBookingFlow` hook (shared)
2. `BookingStepper` component (shared)
3. `PaymentForm` component (shared, Stripe)
4. Flight-specific pages and components

**Ticket**: Moiz to create flight booking setup ticket

### Phase 3: Hotel Booker

**Reuse from Phase 2**:
- `useBookingFlow` hook
- `BookingStepper` component
- `PaymentForm` component
- Review/confirmation patterns

**New for hotels**:
- `hotelBookingSlice`
- Hotel-specific components (map, room selector)

---

## Search Results & Pagination

**Problem**: Loading hundreds/thousands of flights into DOM is slow.

**Solution**: Frontend pagination

```typescript
// Example: Paginate locally cached results
const RESULTS_PER_PAGE = 20;
const [page, setPage] = useState(1);

const displayedFlights = useMemo(() => {
  const start = (page - 1) * RESULTS_PER_PAGE;
  return allFlights.slice(start, start + RESULTS_PER_PAGE);
}, [allFlights, page]);
```

**Out of scope**: Backend API changes for server-side pagination.

---

## Database Strategy (Deferred)

**Current state**: Shared `booking_events` table for all booking types.

**Future consideration**: Separate tables for flights vs hotels to reduce conflict risk.

**Decision**: Defer database refactoring. Focus on frontend architecture first.

---

## Existing RTK Query Setup

Already in place (`frontend-v2/src/api/`):

| API File | Endpoints |
|----------|-----------|
| `flightsApi.ts` | search, select, fare-rules, revalidate, book, payment-intent |
| `hotelsApi.ts` | search, more-results, room-rates, rate-rules, book, session |
| `authApi.ts` | login, register, refresh, OAuth |

No changes needed to API layer - focus is on UI components and state orchestration.

---

## Open Questions

1. **Form persistence**: Should form data persist to localStorage for recovery after browser refresh?

2. **Analytics**: Where to track booking funnel events? (In hook? In components?)

3. **Error boundaries**: How to handle mid-booking failures gracefully?

---

## Next Steps

- [ ] Moiz: Create ticket for flight booking setup in frontend-v2
- [ ] Roel: Follow-up meeting with Anique and Christian on architecture changes
- [ ] Implementation: Start with `useBookingFlow` hook + `flightBookingSlice` refinement

---

## References

- [BOOKING_ARCHITECTURE.md](./BOOKING_ARCHITECTURE.md) - Detailed component structure and data flows
- [../CLAUDE.md](../CLAUDE.md) - Frontend-v2 development guide
- Vanilla JS bookers: `backend_python/dev_ui/flight-booker/` and `hotel-booker/`
