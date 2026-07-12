# Airport Dataset Build Scripts

## Overview

The airport dataset (`airports_cache.json`) is built from multiple sources to ensure:
- **English city names** for geocoding compatibility (from OpenFlights)
- **Comprehensive coverage** of 29k+ airports (from mwgg/Airports)
- **Commercial filtering** using FlightLogic API (bookable airports only)
- **Manual curation** for fixes and overrides (from `airports_overrides.json`)

## Building the Dataset

### Quick Start

```bash
cd backend_python

# Build with FlightLogic filter (recommended - only bookable airports)
python3 scripts/build_airports_dataset.py --use-flightlogic

# Build with keyword filter (fallback - no API needed)
python3 scripts/build_airports_dataset.py

# Build with all airports (includes non-commercial)
python3 scripts/build_airports_dataset.py --include-all
```

### FlightLogic Mode (Recommended)

Uses FlightLogic's `airport_list` API as the authoritative source for commercial airports.

**Requirements**: Set these environment variables in `.env`:
```bash
FLIGHTLOGIC_USER_ID=your_user_id
FLIGHTLOGIC_PASSWORD=your_password
FLIGHTLOGIC_IP_ADDRESS=your_registered_ip
```

**Result**: ~6,000 airports (FlightLogic's commercial list)

### Keyword Filter Mode (Fallback)

If FlightLogic credentials aren't configured, the script falls back to keyword-based filtering:
- Requires IATA code
- Excludes: heliports, seaplane bases, military bases, closed airports

**Result**: ~8,000 airports

### Data Sources

1. **OpenFlights** (Primary for city names)
   - Source: https://github.com/jpatokal/openflights
   - Coverage: 7,698 commercial airports
   - **English city names**: Venice, Rome, Paris, Tokyo, etc.
   - License: Open Database License (ODbL)

2. **mwgg/Airports** (Base layer for coverage)
   - Source: https://github.com/mwgg/Airports
   - Coverage: 29,293 airports (includes small regional)
   - Native city names: Venezia, Roma, etc.
   - License: Public domain

3. **FlightLogic API** (Filter layer)
   - Commercial airports only
   - Excludes: private, military, closed airports
   - Authoritative source for bookable airports

4. **Manual Overrides** (Highest priority)
   - File: `airports_overrides.json`
   - City name fixes for non-English names
   - Exclusions for closed/deprecated airports
   - Special handling for edge cases

### Merge Strategy

```
Priority (highest to lowest):
1. airports_overrides.json  (manual fixes & exclusions)
2. OpenFlights              (English city names)
3. mwgg/Airports            (comprehensive coverage)

Filter:
- FlightLogic API           (commercial airports only)
```

**Example**: Venice VCE airport
- mwgg provides: `"city": "Venezia"` (native language)
- OpenFlights overlays: `"city": "Venice"` (English)
- Final result: `"city": "Venice"` ✅

## Manual Overrides

Edit `airports_overrides.json` to fix incorrect data or exclude airports:

### City Name Fixes
```json
{
  "CGN": {
    "city": "Cologne",
    "_note": "German: Köln"
  }
}
```

### Exclude Closed Airports
```json
{
  "SXF": {
    "_exclude": true,
    "_reason": "Berlin Schönefeld - closed October 2020, replaced by BER"
  }
}
```

### Fields You Can Override
- `city` - City name (most common override)
- `name` - Airport name
- `country` - 2-letter ISO code
- `state` - State/region
- `lat`, `lon` - Coordinates
- `elevation` - Elevation in feet
- `tz` - Timezone identifier
- `_exclude` - Set to `true` to remove airport
- `_region` - Tag for regional grouping (e.g., "Crete")

## Edge Cases Handled

### Goa vs GOA
- **GOI** = Goa International Airport (India)
- **GOA** = Genoa Airport (Italy)

The overrides ensure correct disambiguation.

### Cities Without Airports
Cities like Utrecht don't have their own airport. The geocoding service will find nearby airports (AMS, RTM, EIN) based on coordinates.

### Multi-Airport Cities
London, Paris, Tokyo, etc. have multiple airports. All are included with correct city names for proper matching.

### Non-English City Names
- "Köln" → CGN (Cologne)
- "Den Haag" → RTM (Rotterdam The Hague)
- "Venezia" → VCE (Venice)

OpenFlights provides English names, overrides fix any gaps.

## Rebuilding the Dataset

Rebuild after:
- FlightLogic updates their airport list
- Upstream datasets are updated (quarterly recommended)
- Adding manual overrides to `airports_overrides.json`
- Discovering incorrect data

```bash
# Backup current dataset
cp airports_cache.json airports_cache.json.bak

# Rebuild from sources (with FlightLogic)
python3 scripts/build_airports_dataset.py --use-flightlogic

# Restart backend to reload data
docker compose restart backend
```

## Dataset Statistics

After running the build script, you'll see:

```
📊 Dataset Statistics:
  Total airports: 6,247
  With IATA codes: 6,247
  By source:
    openflights+mwgg: 5,899  (English city names)
    mwgg: 348                 (comprehensive coverage)

  Sample English city names (verification):
    VCE: Venice - Venice Marco Polo Airport
    FCO: Rome - Leonardo da Vinci International Airport
    CDG: Paris - Charles de Gaulle Airport
    NRT: Tokyo - Narita International Airport
```

## Troubleshooting

### Issue: FlightLogic credentials not working
```
⚠️  FlightLogic credentials not configured
```
**Solution**: Check your `.env` file has all three values:
- `FLIGHTLOGIC_USER_ID`
- `FLIGHTLOGIC_PASSWORD`
- `FLIGHTLOGIC_IP_ADDRESS`

### Issue: City name still wrong after rebuild
**Check**:
1. Is your override in `airports_overrides.json`?
2. Did you restart the backend?
3. Check `_source` field in `airports_cache.json` - should show "override"

### Issue: Airport missing after FlightLogic filter
FlightLogic only includes airports they can book. If an airport is missing:
1. Verify it's a commercial airport
2. Check if it's in FlightLogic's list
3. Use `--include-all` for non-commercial airports

## Related Files

- `airports_cache.json` - Generated dataset (DO NOT edit directly)
- `airports_overrides.json` - Manual fixes (edit this)
- `app/domains/airport/service.py` - AirportService that uses the dataset
- `app/domains/airport/repository.py` - Repository that loads airports_cache.json
- `scripts/build_airports_dataset.py` - This build script

## Maintenance Schedule

**Recommended**: Rebuild monthly or when issues are reported

```bash
# Add to crontab or CI/CD pipeline
0 0 1 * * cd /path/to/voya/backend_python && python3 scripts/build_airports_dataset.py --use-flightlogic
```
