# 2-Column App Layout (30–70 Split) with Global Chat

## Overview

The app uses a consistent 2-column layout for authenticated pages that include chat:
- **Left column (30%)**: Persistent chat panel (`ChatPanel`) — stays mounted across navigation
- **Right column (70%)**: Page content via `<Outlet />` — varies by route

---

## Current Implementation

### Layout Hierarchy

```
App
├── Public routes (/, /forgot-password, etc.)
│   └── No 2-column layout; no persistent chat
│
└── Protected routes (ProtectedRoute layout)
    ├── LayoutWithChat routes (home, itinerary, flights/*, hotels/*)
    │   └── MainLayout + 2-column body
    │       ├── Left (30%): ChatPanel (persistent, no remount on navigation)
    │       └── Right (70%): <Outlet /> (page content)
    │
    └── LayoutNoChat routes (profile, admin/*)
        └── MainLayout + full-width content via <Outlet />
```

### Component Placement

| Component | Location | Purpose |
|-----------|----------|---------|
| `ChatPanel` | `features/chat/components/ChatPanel.tsx` | Persistent chat UI for the left column |
| `LayoutWithChat` | `components/layout/LayoutWithChat.tsx` | Layout route: MainLayout + 2-column body (ChatPanel \| Outlet) |
| `LayoutNoChat` | `components/layout/LayoutNoChat.tsx` | Layout route: MainLayout + full-width Outlet (no ChatPanel) |
| `MainLayout` | `components/layout/MainLayout.tsx` | Header + children; used inside LayoutWithChat and by profile/admin pages |
| `layoutConstants` | `components/layout/layoutConstants.ts` | `CHAT_COLUMN_WIDTH: '30%'`, `CONTENT_FLEX: 1` |

### Route Structure (App.tsx)

```tsx
<Route element={<ProtectedRoute />}>
  <Route element={<LayoutWithChat />}>
    <Route path="home" element={<HomePage />} />
    <Route path="itinerary" element={<ItineraryPage />} />
    <Route path="flights/search" element={<FlightSearchPage />} />
    <Route path="flights/details/:fareSourceCode" element={<FlightDetailsPage />} />
    <!-- ... all flight and hotel routes ... -->
  </Route>
  <Route element={<LayoutNoChat />}>
    <Route path="profile" element={<ProfilePage />} />
    <Route path="admin/bookings" element={<AdminBookingsPage />} />
    <!-- ... admin detail routes ... -->
  </Route>
</Route>
```

- **ProtectedRoute**: Layout route; checks auth, renders `<Outlet />` when authenticated.
- **LayoutWithChat**: Layout route; wraps MainLayout + ChatPanel + Outlet. ChatPanel stays mounted when navigating between child routes.

---

## Page Content (Right Column)

| Route | Content |
|-------|---------|
| `/home` | HomePage: title, cards grid (Flights, Hotels, Itinerary, Admin) |
| `/itinerary` | 2 sub-columns: ItineraryDetails \| Map |
| `/flights/*` | Flight search, details, passenger info, review, payment, confirmation |
| `/hotels/*` | Hotel search, rooms, guest info, review, payment, confirmation |
| `/profile` | Profile form (no chat; uses MainLayout directly) |
| `/admin/*` | Admin bookings (no chat; uses MainLayout directly) |

---

## File Structure

```
components/layout/
├── Header.tsx
├── MainLayout.tsx
├── LayoutWithChat.tsx       # 30/70 layout with persistent ChatPanel
├── layoutConstants.ts       # CHAT_COLUMN_WIDTH, CONTENT_FLEX
├── HomePage.tsx             # Content only (no MainLayout)
└── index.ts

features/chat/
├── components/
│   ├── ChatBot.tsx          # Floating widget (rendered in App.tsx)
│   ├── ChatPanel.tsx        # Persistent chat for left column
│   └── ...
├── context/
└── index.ts

features/itinerary/
├── components/
│   ├── ItineraryDetailsComponent.tsx
│   ├── MapComponent.tsx
│   └── index.ts
└── pages/
    └── ItineraryPage.tsx    # 2 columns: Details | Map (in right 70%)
```

---

## Architecture Notes

### Persistent Chat (No Remount)

ChatPanel is rendered once inside `LayoutWithChat`. Because `LayoutWithChat` is a parent route of home, itinerary, flights, and hotels, it stays mounted when navigating between those routes. Only the `<Outlet />` content changes.

### Floating ChatBot

The floating `ChatBot` widget is currently **disabled** (not rendered in `App.tsx`) to avoid duplicating chat UI with the persistent `ChatPanel` layout.

### Layout Constants

```ts
// layoutConstants.ts
export const LAYOUT = {
  CHAT_COLUMN_WIDTH: '30%',
  CONTENT_FLEX: 1,
} as const;
```

---

**Document status:** Implementation complete (Phase 1–2).
**Future:** Consider re-enabling ChatBot only on public routes (or replacing it entirely with ChatPanel); responsive behavior (tablet/mobile).
