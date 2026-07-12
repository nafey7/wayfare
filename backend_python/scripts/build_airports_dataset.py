#!/usr/bin/env python3
"""
Build curated airports dataset from multiple sources.

Data sources (in priority order):
1. Manual overrides - Curated fixes in airports_overrides.json (highest priority)
2. OpenFlights - English city names, 7.6k commercial airports
3. mwgg/Airports - Comprehensive coverage, 29k+ airports (base layer)

Filter layers:
- FlightLogic API - Commercial airports only (excludes private/military)
- Keyword filtering - Excludes heliports, seaplane bases, military bases, etc.

Usage:
    python scripts/build_airports_dataset.py [--use-flightlogic] [--include-all]

Options:
    --use-flightlogic    Filter using FlightLogic API (requires credentials in .env)
    --include-all        Include all airports (skip commercial-only filter)

Output:
    airports_cache.json - Merged and curated dataset

Environment variables (for --use-flightlogic):
    FLIGHTLOGIC_USER_ID      FlightLogic API user ID
    FLIGHTLOGIC_PASSWORD     FlightLogic API password
    FLIGHTLOGIC_IP_ADDRESS   Registered IP address
    FLIGHTLOGIC_FLIGHTS_API_BASE_URL  API base URL (default: https://travelnext.works/api/aeroVE5)
"""

import argparse
import csv
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

# Data source URLs
OPENFLIGHTS_URL = (
    "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
)
MWGG_URL = "https://raw.githubusercontent.com/mwgg/Airports/master/airports.json"

# FlightLogic API
FLIGHTLOGIC_DEFAULT_URL = "https://travelnext.works/api/aeroVE5"

# Output paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_FILE = PROJECT_ROOT / "airports_cache.json"
OVERRIDES_FILE = PROJECT_ROOT / "airports_overrides.json"


# Try to load .env file for FlightLogic credentials
def load_dotenv() -> None:
    """Load environment variables from .env files if they exist.

    Checks multiple locations:
    1. backend_python/.env (PROJECT_ROOT)
    2. voya/.env (parent directory, for Docker compose setup)
    """
    env_files = [
        PROJECT_ROOT / ".env",  # backend_python/.env
        PROJECT_ROOT.parent / ".env",  # voya/.env (root)
    ]

    for env_file in env_files:
        if env_file.exists():
            print(f"  Loading env from: {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        # Remove quotes and inline comments
                        value = value.split("#")[0].strip().strip('"').strip("'")
                        if key not in os.environ and value:
                            os.environ[key] = value


def download_flightlogic() -> set[str] | None:
    """
    Download FlightLogic airport list (commercial airports only).

    Returns a set of IATA codes that FlightLogic considers valid commercial airports.
    Returns None if credentials are not configured or API fails.
    """
    # Load credentials from environment
    user_id = os.environ.get("FLIGHTLOGIC_USER_ID")
    password = os.environ.get("FLIGHTLOGIC_PASSWORD")
    ip_address = os.environ.get("FLIGHTLOGIC_IP_ADDRESS")
    base_url = os.environ.get(
        "FLIGHTLOGIC_FLIGHTS_API_BASE_URL", FLIGHTLOGIC_DEFAULT_URL
    )

    if not all([user_id, password, ip_address]):
        print("⚠️  FlightLogic credentials not configured")
        print(
            "   Set FLIGHTLOGIC_USER_ID, FLIGHTLOGIC_PASSWORD, FLIGHTLOGIC_IP_ADDRESS"
        )
        return None

    print("📥 Downloading FlightLogic airport list...")

    # Build request payload
    payload = {
        "user_id": user_id,
        "user_password": password,
        "access": "Test",  # Use Test access for build script
        "ip_address": ip_address,
    }

    url = f"{base_url}/airport_list"
    data = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            # Handle gzip if present
            if response.info().get("Content-Encoding") == "gzip":
                import gzip

                response_data = gzip.decompress(response.read()).decode("utf-8")
            else:
                response_data = response.read().decode("utf-8")

            airports = json.loads(response_data)

            # Check for error response
            if isinstance(airports, dict) and "Errors" in airports:
                error_msg = airports["Errors"].get("ErrorMessage", "Unknown error")
                print(f"❌ FlightLogic API error: {error_msg}")
                return None

            # Extract IATA codes
            iata_codes = set()
            for airport in airports:
                if isinstance(airport, dict) and airport.get("AirportCode"):
                    iata_codes.add(airport["AirportCode"])

            print(f"✅ Loaded {len(iata_codes)} commercial airports from FlightLogic")
            return iata_codes

    except Exception as e:
        print(f"❌ Failed to fetch FlightLogic airports: {e}")
        return None


def download_openflights() -> dict[str, dict[str, Any]]:
    """
    Download OpenFlights dataset and convert to our format.

    OpenFlights CSV format:
    0: Airport ID, 1: Name, 2: City, 3: Country, 4: IATA, 5: ICAO,
    6: Latitude, 7: Longitude, 8: Altitude, 9: Timezone offset,
    10: DST, 11: Tz database timezone, 12: Type, 13: Source
    """
    print("📥 Downloading OpenFlights dataset...")

    with urllib.request.urlopen(OPENFLIGHTS_URL) as response:
        data = response.read().decode("utf-8")

    airports = {}
    for line in csv.reader(data.strip().split("\n")):
        if len(line) < 14:
            continue

        iata = line[4].strip('"')
        icao = line[5].strip('"')

        # Skip if no IATA and no ICAO
        if not iata and not icao:
            continue

        # Use IATA as key, fallback to ICAO
        key = iata if iata else icao

        airports[key] = {
            "icao": icao if icao else "",
            "iata": iata if iata else "",
            "name": line[1].strip('"'),
            "city": line[2].strip('"'),  # English city name!
            "state": "",  # OpenFlights doesn't have state
            "country": line[3].strip('"'),  # Full country name
            "elevation": int(line[8]) if line[8] else 0,
            "lat": float(line[6]) if line[6] else 0.0,
            "lon": float(line[7]) if line[7] else 0.0,
            "tz": line[11].strip('"'),
            "_source": "openflights",
        }

    print(f"✅ Loaded {len(airports)} airports from OpenFlights (English city names)")
    return airports


def download_mwgg() -> dict[str, dict[str, Any]]:
    """Download mwgg/Airports dataset (comprehensive coverage)."""
    print("📥 Downloading mwgg/Airports dataset...")

    with urllib.request.urlopen(MWGG_URL) as response:
        data = json.loads(response.read().decode("utf-8"))

    # Add source marker
    for _key, airport in data.items():
        airport["_source"] = "mwgg"

    print(f"✅ Loaded {len(data)} airports from mwgg/Airports (comprehensive)")
    return data


def load_overrides() -> dict[str, dict[str, Any]]:
    """Load manual overrides from airports_overrides.json."""
    if not OVERRIDES_FILE.exists():
        print("i  No overrides file found (airports_overrides.json)")
        return {}

    with open(OVERRIDES_FILE) as f:
        data = json.load(f)

    # Filter out metadata keys (starting with _)
    overrides = {k: v for k, v in data.items() if not k.startswith("_")}

    print(f"✅ Loaded {len(overrides)} manual overrides")
    return overrides


def merge_datasets(
    openflights: dict[str, dict[str, Any]],
    mwgg: dict[str, dict[str, Any]],
    overrides: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Merge datasets with priority:
    1. Manual overrides (highest priority)
    2. OpenFlights (English city names)
    3. mwgg (fallback for missing airports)

    Note: mwgg uses ICAO codes as keys, OpenFlights uses IATA codes.
    We need to match them by IATA/ICAO codes to overlay properly.
    """
    print("\n🔄 Merging datasets...")

    merged = {}

    # Start with mwgg (base layer - comprehensive coverage)
    # Keep original keys (ICAO codes)
    merged.update(mwgg)
    print(f"  Base layer: {len(merged)} airports from mwgg")

    # Build lookup index: IATA -> ICAO key for mwgg data
    iata_to_key = {}
    icao_to_key = {}
    for key, airport in merged.items():
        if airport.get("iata"):
            iata_to_key[airport["iata"]] = key
        if airport.get("icao"):
            icao_to_key[airport["icao"]] = key

    # Overlay OpenFlights (priority layer - English city names)
    openflights_overlays = 0
    openflights_additions = 0

    for of_key, of_airport in openflights.items():
        # Try to find matching airport in mwgg by IATA or ICAO
        mwgg_key = None
        if of_airport.get("iata"):
            mwgg_key = iata_to_key.get(of_airport["iata"])
        if not mwgg_key and of_airport.get("icao"):
            mwgg_key = icao_to_key.get(of_airport["icao"])

        if mwgg_key:
            # Airport exists in mwgg - overlay English city name
            merged[mwgg_key]["city"] = of_airport["city"]  # English name!
            merged[mwgg_key]["_source"] = "openflights+mwgg"
            openflights_overlays += 1
        else:
            # New airport not in mwgg - add it with OpenFlights key
            merged[of_key] = of_airport
            openflights_additions += 1

    print(
        f"  OpenFlights: {openflights_overlays} overlays (English names), "
        f"{openflights_additions} additions"
    )

    # Apply manual overrides (top layer - curated fixes)
    overrides_applied = 0
    for override_key, override_data in overrides.items():
        # Skip non-dict overrides (metadata keys like "_comment")
        if not isinstance(override_data, dict):
            continue

        # Find the actual key in merged (might be ICAO if override uses IATA)
        actual_key = override_key
        if override_key not in merged:
            # Try to find by IATA or ICAO
            if override_key in iata_to_key:
                actual_key = iata_to_key[override_key]
            elif override_key in icao_to_key:
                actual_key = icao_to_key[override_key]

        if actual_key in merged:
            merged[actual_key].update(override_data)
            merged[actual_key]["_source"] = "override+" + merged[actual_key].get(
                "_source", ""
            )
            overrides_applied += 1
        # New airport from override (only if it has airport data)
        elif override_data.get("iata") or override_data.get("icao"):
            merged[override_key] = override_data.copy()
            merged[override_key]["_source"] = "override"
            overrides_applied += 1

    if overrides_applied > 0:
        print(f"  Overrides: {overrides_applied} manual edits applied")

    return merged


def normalize_country_codes(airports: dict[str, dict[str, Any]]) -> None:
    """
    Convert OpenFlights full country names to ISO 2-letter codes.

    Common mappings for major countries:
    """
    country_mapping = {
        "Italy": "IT",
        "France": "FR",
        "Germany": "DE",
        "Spain": "ES",
        "United Kingdom": "GB",
        "United States": "US",
        "Canada": "CA",
        "Japan": "JP",
        "China": "CN",
        "India": "IN",
        "Australia": "AU",
        "Brazil": "BR",
        "Mexico": "MX",
        "Netherlands": "NL",
        "Belgium": "BE",
        "Switzerland": "CH",
        "Austria": "AT",
        "Sweden": "SE",
        "Norway": "NO",
        "Denmark": "DK",
        "Finland": "FI",
        "Poland": "PL",
        "Greece": "GR",
        "Portugal": "PT",
        "Czech Republic": "CZ",
        "Ireland": "IE",
        "New Zealand": "NZ",
        "Singapore": "SG",
        "South Korea": "KR",
        "Thailand": "TH",
        "Malaysia": "MY",
        "Indonesia": "ID",
        "Philippines": "PH",
        "Vietnam": "VN",
        "Turkey": "TR",
        "South Africa": "ZA",
        "Egypt": "EG",
        "United Arab Emirates": "AE",
        "Saudi Arabia": "SA",
        "Argentina": "AR",
        "Chile": "CL",
        "Colombia": "CO",
        "Peru": "PE",
        "Russia": "RU",
        "Ukraine": "UA",
    }

    for airport in airports.values():
        country = airport.get("country", "")
        if country in country_mapping:
            airport["country"] = country_mapping[country]


def filter_commercial_only(
    airports: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Filter to keep only commercial airports.

    Criteria for commercial airports:
    1. Must have IATA code (3-letter code used for booking)
    2. Excludes: heliports, seaplane bases, closed airports
    3. Keeps: large/medium/small airports with scheduled service
    """
    print("\n🔍 Filtering for commercial airports only...")

    filtered = {}
    excluded_types = {
        "heliport",
        "seaplane_base",
        "closed",
        "balloonport",
        "ultralight",
        "glider",
        "helicopter",
        "military",
        "air base",
        "airbase",
        "air force",
        "naval air",
        "afb",
    }

    for key, airport in airports.items():
        # Must have IATA code
        if not airport.get("iata"):
            continue

        # Check airport type/name for excluded types
        name_lower = airport.get("name", "").lower()
        excluded = any(ex_type in name_lower for ex_type in excluded_types)
        if excluded:
            continue

        # Keep it
        filtered[key] = airport

    print(f"  Kept {len(filtered)} commercial airports (with IATA codes)")
    print(f"  Removed {len(airports) - len(filtered)} non-commercial airports")

    return filtered


def filter_by_flightlogic(
    airports: dict[str, dict[str, Any]],
    flightlogic_codes: set[str],
) -> dict[str, dict[str, Any]]:
    """
    Filter airports to keep only those in FlightLogic's commercial list.

    This is the authoritative source for bookable airports.
    """
    print("\n🔍 Filtering by FlightLogic commercial airport list...")

    filtered = {}
    for key, airport in airports.items():
        iata = airport.get("iata", "")
        if iata in flightlogic_codes:
            filtered[key] = airport

    print(f"  Kept {len(filtered)} airports (in FlightLogic list)")
    print(f"  Removed {len(airports) - len(filtered)} airports (not in FlightLogic)")

    return filtered


def apply_exclusions(
    airports: dict[str, dict[str, Any]],
    overrides: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Remove airports marked for exclusion in overrides.

    Airports with "_exclude": true in overrides are removed from the dataset.
    """
    exclusions = {
        k
        for k, v in overrides.items()
        if isinstance(v, dict) and v.get("_exclude") is True
    }

    if not exclusions:
        return airports

    print(f"\n🚫 Applying exclusions ({len(exclusions)} airports)...")

    # Build lookup for finding airports by IATA code
    iata_to_key = {}
    for key, airport in airports.items():
        if airport.get("iata"):
            iata_to_key[airport["iata"]] = key

    filtered = {}
    excluded_count = 0
    for key, airport in airports.items():
        # Check if this airport should be excluded (by key or IATA)
        iata = airport.get("iata", "")
        if key in exclusions or iata in exclusions:
            excluded_count += 1
            excluded_name = airport.get("name", key)
            print(f"  Excluded: {iata or key} - {excluded_name}")
            continue
        filtered[key] = airport

    print(f"  Removed {excluded_count} excluded airports")
    return filtered


def save_dataset(airports: dict[str, dict[str, Any]]) -> None:
    """Save merged dataset to airports_cache.json."""
    print(f"\n💾 Saving dataset to {OUTPUT_FILE}...")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(airports, f, separators=(",", ":"))

    file_size = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"✅ Saved {len(airports)} airports ({file_size:.1f} MB)")


def generate_stats(airports: dict[str, dict[str, Any]]) -> None:
    """Print dataset statistics."""
    print("\n📊 Dataset Statistics:")
    print(f"  Total airports: {len(airports)}")

    with_iata = sum(1 for a in airports.values() if a.get("iata"))
    print(f"  With IATA codes: {with_iata}")

    # Count by source
    sources = {}
    for airport in airports.values():
        source = airport.get("_source", "unknown")
        sources[source] = sources.get(source, 0) + 1

    print("  By source:")
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {source}: {count}")

    # Build IATA lookup (keys are ICAO from mwgg, but we want to lookup by IATA)
    iata_lookup = {}
    for _key, airport in airports.items():
        iata = airport.get("iata")
        if iata:
            iata_lookup[iata] = airport

    # Sample English city names
    print("\n  Sample English city names (verification):")
    samples = ["VCE", "FCO", "CDG", "NRT", "HND", "LHR", "AMS", "LCY", "GOA", "GOI"]
    for code in samples:
        if code in iata_lookup:
            city = iata_lookup[code].get("city", "N/A")
            name = iata_lookup[code].get("name", "N/A")
            print(f"    {code}: {city} - {name}")
        else:
            print(f"    {code}: (not in dataset)")


def main():
    """Build curated airports dataset."""
    # Load .env file for credentials
    load_dotenv()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Build curated airports dataset from multiple sources"
    )
    parser.add_argument(
        "--use-flightlogic",
        action="store_true",
        help="Filter using FlightLogic API (requires credentials in .env)",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include all airports (skip commercial-only filter)",
    )
    args = parser.parse_args()

    use_flightlogic = args.use_flightlogic
    include_all = args.include_all

    print("🛫 Building Curated Airports Dataset\n")
    print("=" * 60)
    if use_flightlogic:
        print("Mode: FlightLogic filter (commercial airports only)")
    elif not include_all:
        print("Mode: Keyword filter (commercial airports only)")
    else:
        print("Mode: All airports (includes small regional)")
    print("=" * 60)

    # Download FlightLogic airport list if requested
    flightlogic_codes: set[str] | None = None
    if use_flightlogic:
        flightlogic_codes = download_flightlogic()
        if flightlogic_codes is None:
            print("\n⚠️  Falling back to keyword-based filtering")

    # Download datasets
    openflights = download_openflights()
    mwgg = download_mwgg()
    overrides = load_overrides()

    # Merge datasets
    merged = merge_datasets(openflights, mwgg, overrides)

    # Normalize country codes
    normalize_country_codes(merged)

    # Apply exclusions from overrides (closed airports, etc.)
    merged = apply_exclusions(merged, overrides)

    # Apply filters
    if flightlogic_codes:
        # Use FlightLogic as primary filter
        merged = filter_by_flightlogic(merged, flightlogic_codes)
        # Also apply keyword filter - FlightLogic includes some military bases
        merged = filter_commercial_only(merged)
        print(
            "  [i] Applied keyword filter to remove military bases from FlightLogic list"
        )
    elif not include_all:
        # Fallback to keyword-based filtering only
        merged = filter_commercial_only(merged)

    # Save output
    save_dataset(merged)

    # Print statistics
    generate_stats(merged)

    print("\n" + "=" * 60)
    print("✅ Dataset build complete!")
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"Manual overrides: {OVERRIDES_FILE} (edit to fix specific airports)")
    if use_flightlogic:
        print("\ni  Dataset filtered by FlightLogic commercial airport list")
    elif not include_all:
        print("\ni  To include all airports, run with: --include-all")
        print("   To use FlightLogic filter, run with: --use-flightlogic")


if __name__ == "__main__":
    main()
