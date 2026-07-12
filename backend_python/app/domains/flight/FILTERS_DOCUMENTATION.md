# Flight Search Filters Documentation

This document describes the available filters for flight search results, their payload structure, and how they are applied.

## Overview

Flight search filters are applied **post-API** (after receiving results from FlightLogic API). All filters are optional and can be combined. Filters are applied in the following order:

1. **Global filters** (price, refundability, stops, airlines, etc.)
2. **City-wise search filters** (origin/destination airport matching)
3. **Leg-specific filters** (time windows, duration, layover airports)

## Payload Structure

```json
{
  "filters": {
    // Global filters
    "min_price": 100.0,
    "max_price": 1000.0,
    "is_refundable": true,
    "carrier": "GDS",
    "max_stops": 1,
    "operating_airlines": ["Emirates", "Qatar Airways"],

    // Leg-specific filters
    "journey_filters": [
      {
        "leg_index": 0,
        "description": "Outbound leg preferences",
        "city_wise_search": true,
        "departure_window": {
          "min": "06:00",
          "max": "12:00"
        },
        "arrival_window": {
          "min": "14:00",
          "max": "20:00"
        },
        "max_duration_minutes": 600,
        "excluded_layover_airports": ["DXB"],
        "allowed_layover_airports": ["IST", "DOH"]
      },
      {
        "leg_index": 1,
        "city_wise_search": false,
        "departure_window": {
          "min": "10:00",
          "max": "18:00"
        }
      }
    ]
  }
}
```

## Global Filters

### `city_wise_search_origin` (bool | null) [DEPRECATED]
- **Description**: **[DEPRECATED]** Use `journey_filters[].city_wise_search` instead for per-leg control. If `true`, allows flights from any airport in the origin city. If `false` or `null`, only exact origin airport matches are kept.
- **Default**: `null` (exact match required)
- **Note**: This global filter is kept for backward compatibility. For multi-city support, use leg-specific `city_wise_search` in `journey_filters`.

### `city_wise_search_destination` (bool | null) [DEPRECATED]
- **Description**: **[DEPRECATED]** Use `journey_filters[].city_wise_search` instead for per-leg control. If `true`, allows flights to any airport in the destination city. If `false` or `null`, only exact destination airport matches are kept.
- **Default**: `null` (exact match required)
- **Note**: This global filter is kept for backward compatibility. For multi-city support, use leg-specific `city_wise_search` in `journey_filters`.

### `min_price` (float | null)
- **Description**: Minimum total fare price (in requested currency).
- **Default**: `null` (no minimum)

### `max_price` (float | null)
- **Description**: Maximum total fare price (in requested currency).
- **Default**: `null` (no maximum)

### `is_refundable` (bool | null)
- **Description**: Filter by refundability status.
- **Values**: `true` (only refundable), `false` (only non-refundable), `null` (no filter)
- **Default**: `null`

### `carrier` (string | null)
- **Description**: Filter by carrier type.
- **Values**: `"GDS"` (Global Distribution System - Private/Public fares), `"LCC"` (Low Cost Carrier - WebFare)
- **Default**: `null`

### `max_stops` (int | null)
- **Description**: Maximum number of stops allowed per leg. For multi-city flights, **each leg** must individually pass this filter.
- **Example**: `max_stops: 1` means each leg can have at most 1 stop.
- **Default**: `null` (no limit)

### `operating_airlines` (list[string] | null)
- **Description**: Filter flights where **any segment** is operated by one of the specified airlines. Matching is done by airline name (case-insensitive).
- **Example**: `["Emirates", "Qatar Airways"]` keeps flights with at least one segment operated by either airline.
- **Default**: `null` (no filter)

## Leg-Specific Filters

Leg-specific filters are defined in the `journey_filters` array. Each filter applies to a specific leg of the journey.

### `leg_index` (int, required)
- **Description**: Leg index in the journey.
- **Values**: `0` = outbound leg, `1` = inbound leg, `2+` = additional legs for multi-city
- **Required**: Yes

### `city_wise_search` (bool | null)
- **Description**: If `true`, allows flights from/to any airport in the origin/destination city for this leg. If `false` or `null`, only exact airport matches are kept. **Applies to both origin AND destination** of the leg.
- **Default**: `null` (falls back to global `city_wise_search_origin`/`city_wise_search_destination` if not set)
- **Example**: For a NYC → LON leg, `city_wise_search: true` allows any NYC airport (JFK, LGA, EWR) to any London airport (LHR, LGW, STN, etc.)
- **Multi-city benefit**: Different legs can have different city-wise settings (e.g., leg 0 allows any airports, leg 1 requires exact match)

### `departure_window` (TimeWindow | null)
- **Description**: Time window for departure time of the **first segment** of the leg.
- **Format**: `{"min": "HH:mm", "max": "HH:mm"}` (24-hour format)
- **Example**: `{"min": "06:00", "max": "12:00"}` keeps flights departing between 6 AM and 12 PM
- **Default**: `null`

### `arrival_window` (TimeWindow | null)
- **Description**: Time window for arrival time of the **last segment** of the leg.
- **Format**: `{"min": "HH:mm", "max": "HH:mm"}` (24-hour format)
- **Example**: `{"min": "14:00", "max": "20:00"}` keeps flights arriving between 2 PM and 8 PM
- **Default**: `null`

### `max_duration_minutes` (int | null)
- **Description**: Maximum total travel time for the leg (includes flight time + layover time).
- **Calculation**: Flight Duration + Layover Time = Total Travel Time
- **Example**: `600` means the leg must complete within 10 hours total
- **Default**: `null`

### `excluded_layover_airports` (list[string] | null)
- **Description**: List of airport codes to exclude as layover airports.
- **Example**: `["DXB", "IST"]` excludes flights with layovers in Dubai or Istanbul
- **Note**: Direct flights (no layovers) always pass this filter
- **Default**: `null`

### `allowed_layover_airports` (list[string] | null)
- **Description**: List of airport codes that are allowed as layover airports. If provided, **at least one** layover must be in this list.
- **Example**: `["IST", "DOH"]` only allows flights with layovers in Istanbul or Doha
- **Note**: Direct flights (no layovers) fail this filter if provided
- **Default**: `null`

## Filter Application Logic

### Multi-City Support
- For multi-city flights, a `FareItinerary` can contain multiple legs (0, 1, 2, 3, etc.)
- The `max_stops` filter checks **all legs individually** - each leg must pass
- Leg-specific filters apply to the leg matching the `leg_index` in the filter

### Round-Trip Flights
- Outbound leg: `leg_index: 0` in `journey_filters`
- Inbound leg: `leg_index: 1` in `journey_filters`
- City-wise filters are automatically swapped for inbound legs (origin/destination reversed)

### City-Wise Search Precedence
1. **Leg-specific `city_wise_search`** (in `journey_filters`) takes precedence if set
2. **Global filters** (`city_wise_search_origin`/`city_wise_search_destination`) are used as fallback for backward compatibility
3. If neither is set, exact airport match is required (default behavior)

### Filter Precedence
1. If a flight fails any global filter, it is excluded
2. If a flight fails city-wise filters, it is excluded
3. If a leg fails its leg-specific filters, the entire itinerary is excluded

## Examples

### Example 1: Price and Refundability
```json
{
  "filters": {
    "min_price": 200.0,
    "max_price": 800.0,
    "is_refundable": true
  }
}
```
Keeps only refundable flights priced between $200 and $800.

### Example 2: Direct Flights Only
```json
{
  "filters": {
    "max_stops": 0
  }
}
```
Keeps only direct flights (no stops).

### Example 3: Morning Departures
```json
{
  "filters": {
    "journey_filters": [
      {
        "leg_index": 0,
        "departure_window": {
          "min": "06:00",
          "max": "10:00"
        }
      }
    ]
  }
}
```
Keeps outbound flights departing between 6 AM and 10 AM.

### Example 4: Avoid Specific Layover
```json
{
  "filters": {
    "journey_filters": [
      {
        "leg_index": 0,
        "excluded_layover_airports": ["DXB"]
      }
    ]
  }
}
```
Excludes outbound flights with layovers in Dubai.

### Example 5: Multi-City with Per-Leg City-Wise Search
```json
{
  "filters": {
    "journey_filters": [
      {
        "leg_index": 0,
        "city_wise_search": true,
        "description": "NYC → LON: any airports"
      },
      {
        "leg_index": 1,
        "city_wise_search": false,
        "description": "LON → PAR: exact airports only"
      },
      {
        "leg_index": 2,
        "city_wise_search": true,
        "description": "PAR → NYC: any airports"
      }
    ]
  }
}
```
For a multi-city trip (NYC → LON → PAR → NYC):
- Leg 0: Allows any NYC airport to any London airport
- Leg 1: Requires exact airport match (e.g., LHR → CDG only)
- Leg 2: Allows any Paris airport to any NYC airport

## Implementation Notes

- All filters are applied **post-API** (after receiving results from FlightLogic)
- Filters are case-insensitive where applicable (airline names, airport codes)
- Empty filter lists (e.g., `operating_airlines: []`) are treated as no filter
- Time windows use string comparison in "HH:mm" format
- Duration calculation includes both flight time and layover time between segments
