# FlightLogic data quality issue — Accesrail "rail-fly" combos returned as flights

**Status**: Open — needs discussion with FlightLogic vendor
**Discovered**: 2026-05-04 weekly trace review
**Source session**: `e5cb8c14-81da-4f21-afad-d158a2a00038` (production)
**Severity**: HIGH — direct user-money impact ($3,000+ accidental bookings possible)

---

## TL;DR

When FlightLogic does an airport-specific search for routes that have no direct
flights from that airport, it returns **multi-modal "Accesrail" rail+flight
combinations** as if they were ordinary flights. These combos are priced 6–7×
higher than the cheapest real flight from a nearby airport — and the user has no
visible signal that they're booking a train ticket combined with a flight. A
user could reasonably select what looks like a $3,485 "flight" when a $515
real flight exists from another airport in the same metro area.

This is a **FlightLogic data-quality issue**, not a Voya bug. We pass the
search request correctly; FlightLogic mixes airline flights and rail-fly combos
in the same result set with the same shape. We need FlightLogic to either
exclude these results or tag them so we can filter / warn the user.

---

## The data — same route, three London airports

User session: round-trip **London → Funchal (Madeira)**, 14 May → 23 May 2026,
1 adult, economy.

| Origin airport | Cheapest result | Carrier | Stops | Duration |
|----------------|-----------------|---------|-------|----------|
| **LGW** Gatwick | **$515.03** | Tap Air Portugal | 2 | 21h 10m |
| **STN** Stansted | **$3,485.39** ❌ | **Accesrail** | 4 | 37h 30m |
| **LTN** Luton | **$3,371.02** ❌ | **Accesrail** | 4 | 29h 30m |

The Stansted/Luton results are **6.7× more expensive**, **2× longer in flight
time**, and travel via Accesrail — which is a rail-air interline carrier (think
"train + connecting flight" sold as one ticket), not an airline.

A user comparing London airports would see:
- "Funchal from Gatwick: $515" (real)
- "Funchal from Stansted: $3,485" (rail+flight)
- "Funchal from Luton: $3,371" (rail+flight)

…and if they're brand-loyal to Stansted (Ryanair hub) or live near Luton, they
might book the Accesrail combo without realising it.

---

## Why we can't fix this in Voya's chat layer

We send a clean, well-formed request to FlightLogic:

```jsonc
{
  "origin": "STN",
  "destination": "FNC",
  "departure_date": "2026-05-14",
  "return_date": "2026-05-23",
  "adults": 1,
  "city_wise_search_origin": false   // explicitly STN-only
}
```

FlightLogic's response includes a mix of:
1. Real airline flights from STN (when they exist)
2. Accesrail rail+flight combos (always included, regardless of #1)

We don't have a reliable signal in the response payload to distinguish the two.
The fields we get back (`OperatingAirline.Code`, `Stops`, `Duration`,
`FareSourceCode`) are present for both — Accesrail just appears as a normal
carrier. The only practical heuristic on our side would be:
- "If the carrier code is `9B` or the airline name contains 'Accesrail' →
  treat as rail+flight"
- This is brittle (carrier codes can change) and silently filters real data
  the user might want.

The right fix is at the source.

---

## What we'd like from FlightLogic

Listed in order of preference:

### Option A — preferred: server-side filter flag

Add a request-level flag `include_rail_fly_combos: false` (default `false` for
new integrations, `true` for backward-compat). When `false`, results contain
only carrier-operated flights — no Accesrail or other rail-air interlines.

This matches the IATA spec convention of treating rail+flight as a separate
"intermodal" product, not a flight product.

### Option B — acceptable: tag results

Add a field to each itinerary describing the segment-mode mix, e.g.:

```jsonc
{
  "Stops": 4,
  "TotalDuration": "PT37H30M",
  "Modes": ["RAIL", "FLIGHT", "FLIGHT", "RAIL"],   // ← new field
  "IsIntermodal": true                              // ← new field
}
```

Voya then filters or warns based on `IsIntermodal=true`.

### Option C — minimum viable: documented carrier list

Provide the list of carrier codes that operate rail-air interlines in the
FlightLogic content (Accesrail = `9B`, Deutsche Bahn-related codes, SNCF =
`2C`, etc.). We hardcode-filter on our side. Brittle, but workable.

---

## Concrete examples for the FlightLogic discussion

Pull these directly from FlightLogic search response logs for session
`e5cb8c14-81da-4f21-afad-d158a2a00038`:

**Stansted → Funchal cheapest result:**
```
SEARCH | Success | route=STN→FNC | departure_date=2026-05-14
TotalAmount: 3485.39 USD
OperatingAirline: Accesrail (9B)
Stops: 4
Duration: 37h 30m
```

**Gatwick → Funchal cheapest result (same route, different airport):**
```
SEARCH | Success | route=LGW→FNC | departure_date=2026-05-14
TotalAmount: 515.03 USD
OperatingAirline: Tap Air Portugal (TP)
Stops: 2
Duration: 21h 10m
```

The price gap and stop count in isolation aren't conclusive, but the
combination of `OperatingAirline=Accesrail` plus an extreme duration plus a
6.7× price multiplier is the signature of a rail-fly combo.

---

## Impact on Voya users

1. **Direct financial harm**: a confused user could book a $3,485 ticket when
   a $515 ticket exists at a different airport in the same city.
2. **Reputational risk**: post-booking, users discover they're on a 4-leg
   rail+air journey and blame Voya, not FlightLogic.
3. **Trust in the chat assistant**: when our bot lists "Stansted → Funchal:
   $3,485" without context, it looks like the bot is wrong, even though we're
   accurately rendering FlightLogic's data.

---

## Recommended next steps

1. **Send this document to FlightLogic** (account manager / technical contact)
   asking for one of Options A/B/C above. Lead with Option A.
2. **Until FlightLogic responds**: consider an interim mitigation in our chat
   layer — when a carrier code is in a known rail-fly list, append a one-line
   warning to the result card: *"This option includes a train segment. Total
   journey time and price reflect the combined ticket."* This isn't perfect
   but flags the user.
3. **Track in our own deferred doc** ([DEFERRED_CHAT_IMPROVEMENTS.md](DEFERRED_CHAT_IMPROVEMENTS.md))
   under a new "vendor data quality" section.

---

## Reference

- Source session: `e5cb8c14-81da-4f21-afad-d158a2a00038` (Langfuse, prod)
- Trace IDs:
  - `592a97890af2c39e9ffdcde38a92a9b0` — Stansted query, returned $3,485 Accesrail
  - `c2b2aa7c0ad73acb362c0a591258dc6d` — Luton query, returned $3,371 Accesrail
  - `d7a0cc1ccb70592d36c38f79969165a4` — Gatwick query, returned $515 TAP (real)
- Related Voya code path: `backend_python/integrations/flightlogic/adapter.py`,
  `backend_python/app/ai/graph/tools/flights.py:search_flights`
- Accesrail background: rail-air codeshare consortium operating ~2,000+ rail
  segments under airline-style IATA codes (9B etc.). Designed for missed-flight
  protection, not as a primary booking option.
