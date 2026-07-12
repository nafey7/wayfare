"""Unit tests for the airport dataset build script.

Tests the filtering, merging, and override logic used to build airports_cache.json.
"""

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# Import functions from build script
# We use importlib since the module name has underscores
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "build_airports_dataset",
    SCRIPT_DIR / "build_airports_dataset.py",
)
build_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_module)

# Extract functions to test
load_overrides = build_module.load_overrides
apply_exclusions = build_module.apply_exclusions
filter_by_flightlogic = build_module.filter_by_flightlogic
filter_commercial_only = build_module.filter_commercial_only
merge_datasets = build_module.merge_datasets
normalize_country_codes = build_module.normalize_country_codes


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_airports() -> dict[str, dict[str, Any]]:
    """Sample airport data for testing."""
    return {
        "EGLL": {
            "iata": "LHR",
            "icao": "EGLL",
            "name": "London Heathrow Airport",
            "city": "London",
            "country": "United Kingdom",
            "lat": 51.4706,
            "lon": -0.4619,
        },
        "EGLC": {
            "iata": "LCY",
            "icao": "EGLC",
            "name": "London City Airport",
            "city": "London",
            "country": "United Kingdom",
            "lat": 51.5053,
            "lon": 0.0553,
        },
        "EDDB": {
            "iata": "SXF",
            "icao": "EDDB",
            "name": "Berlin Schönefeld Airport",
            "city": "Berlin",
            "country": "Germany",
            "lat": 52.38,
            "lon": 13.5225,
        },
        "EDDT": {
            "iata": "TXL",
            "icao": "EDDT",
            "name": "Berlin-Tegel International Airport",
            "city": "Berlin",
            "country": "Germany",
            "lat": 52.5597,
            "lon": 13.2877,
        },
        "EDDI": {
            "iata": "THF",
            "icao": "EDDI",
            "name": "Berlin Tempelhof Airport",
            "city": "Berlin",
            "country": "Germany",
            "lat": 52.473,
            "lon": 13.4039,
        },
        "EDDF": {
            "iata": "FRA",
            "icao": "EDDF",
            "name": "Frankfurt Airport",
            "city": "Frankfurt",
            "country": "Germany",
            "lat": 50.0264,
            "lon": 8.5431,
        },
        "EHSB": {
            "iata": "UTC",
            "icao": "EHSB",
            "name": "Soesterberg Air Base",
            "city": "Soesterberg",
            "country": "Netherlands",
            "lat": 52.1273,
            "lon": 5.2761,
        },
        "LIRF": {
            "iata": "FCO",
            "icao": "LIRF",
            "name": "Leonardo Da Vinci International Airport",
            "city": "Roma",
            "country": "Italy",
            "lat": 41.8003,
            "lon": 12.2389,
        },
        "NO_IATA": {
            "icao": "XXXX",
            "name": "Small Regional Airport",
            "city": "Nowhere",
            "country": "XX",
        },
        "MILITARY": {
            "iata": "MIL",
            "icao": "MILL",
            "name": "Military Air Force Base",
            "city": "Somewhere",
            "country": "US",
        },
    }


@pytest.fixture
def sample_overrides() -> dict[str, dict[str, Any]]:
    """Sample override data for testing."""
    return {
        "_comment": "Test overrides",
        "SXF": {"_exclude": True, "_reason": "Closed airport"},
        "TXL": {"_exclude": True, "_reason": "Closed airport"},
        "THF": {"_exclude": True, "_reason": "Closed airport"},
        "UTC": {"_exclude": True, "_reason": "Military base"},
        "FCO": {"city": "Rome", "_note": "English city name"},
        "LHR": {"name": "London Heathrow Airport (Updated)"},
    }


# =============================================================================
# Test: apply_exclusions
# =============================================================================


class TestApplyExclusions:
    """Tests for apply_exclusions function."""

    def test_excludes_marked_airports(
        self, sample_airports: dict, sample_overrides: dict
    ):
        """Airports with _exclude: true should be removed."""
        result = apply_exclusions(sample_airports, sample_overrides)

        assert "EDDB" not in result  # SXF excluded
        assert "EDDT" not in result  # TXL excluded
        assert "EDDI" not in result  # THF excluded
        assert "EHSB" not in result  # UTC excluded

    def test_keeps_non_excluded_airports(
        self, sample_airports: dict, sample_overrides: dict
    ):
        """Airports without _exclude should be kept."""
        result = apply_exclusions(sample_airports, sample_overrides)

        assert "EGLL" in result  # LHR kept
        assert "EGLC" in result  # LCY kept
        assert "EDDF" in result  # FRA kept
        assert "LIRF" in result  # FCO kept (has override but not excluded)

    def test_no_exclusions_returns_original(self, sample_airports: dict):
        """If no exclusions in overrides, return all airports."""
        empty_overrides = {"_comment": "No exclusions"}
        result = apply_exclusions(sample_airports, empty_overrides)

        assert len(result) == len(sample_airports)

    def test_exclusion_by_iata_code(self, sample_airports: dict):
        """Exclusions can be specified by IATA code."""
        overrides = {"LHR": {"_exclude": True}}
        result = apply_exclusions(sample_airports, overrides)

        assert "EGLL" not in result  # LHR excluded by IATA


# =============================================================================
# Test: filter_by_flightlogic
# =============================================================================


class TestFilterByFlightlogic:
    """Tests for FlightLogic filtering."""

    def test_keeps_only_flightlogic_airports(self, sample_airports: dict):
        """Only airports in FlightLogic set should be kept."""
        flightlogic_codes = {"LHR", "LCY", "FRA", "FCO"}
        result = filter_by_flightlogic(sample_airports, flightlogic_codes)

        assert len(result) == 4
        assert "EGLL" in result  # LHR
        assert "EGLC" in result  # LCY
        assert "EDDF" in result  # FRA
        assert "LIRF" in result  # FCO

    def test_excludes_non_flightlogic_airports(self, sample_airports: dict):
        """Airports not in FlightLogic set should be excluded."""
        flightlogic_codes = {"LHR", "LCY"}
        result = filter_by_flightlogic(sample_airports, flightlogic_codes)

        assert "EDDB" not in result  # SXF not in set
        assert "EDDF" not in result  # FRA not in set

    def test_handles_airports_without_iata(self, sample_airports: dict):
        """Airports without IATA codes should be excluded."""
        flightlogic_codes = {"LHR", "LCY", "XXX"}  # XXX doesn't exist
        result = filter_by_flightlogic(sample_airports, flightlogic_codes)

        assert "NO_IATA" not in result

    def test_empty_flightlogic_set(self, sample_airports: dict):
        """Empty FlightLogic set should return empty dict."""
        result = filter_by_flightlogic(sample_airports, set())
        assert len(result) == 0


# =============================================================================
# Test: filter_commercial_only
# =============================================================================


class TestFilterCommercialOnly:
    """Tests for keyword-based commercial filtering."""

    def test_excludes_military(self, sample_airports: dict):
        """Military airports should be excluded by keyword."""
        result = filter_commercial_only(sample_airports)

        assert "MILITARY" not in result
        assert "EHSB" not in result  # "Air Base" in name

    def test_keeps_commercial_airports(self, sample_airports: dict):
        """Commercial airports with IATA codes should be kept."""
        result = filter_commercial_only(sample_airports)

        assert "EGLL" in result  # LHR
        assert "EGLC" in result  # LCY
        assert "EDDF" in result  # FRA
        assert "LIRF" in result  # FCO

    def test_excludes_no_iata(self, sample_airports: dict):
        """Airports without IATA codes should be excluded."""
        result = filter_commercial_only(sample_airports)

        assert "NO_IATA" not in result

    def test_heliport_excluded(self):
        """Heliports should be excluded by keyword."""
        airports = {
            "HELI": {
                "iata": "HEL",
                "name": "City Heliport",
                "city": "Test",
                "country": "XX",
            }
        }
        result = filter_commercial_only(airports)
        assert "HELI" not in result


# =============================================================================
# Test: normalize_country_codes
# =============================================================================


class TestNormalizeCountryCodes:
    """Tests for country code normalization."""

    def test_normalizes_full_names(self, sample_airports: dict):
        """Full country names should be converted to ISO codes."""
        airports = sample_airports.copy()
        normalize_country_codes(airports)

        assert airports["EGLL"]["country"] == "GB"  # United Kingdom
        assert airports["EDDF"]["country"] == "DE"  # Germany
        assert airports["LIRF"]["country"] == "IT"  # Italy

    def test_preserves_iso_codes(self):
        """Already-ISO codes should not be changed."""
        airports = {
            "TEST": {"country": "US"},
        }
        normalize_country_codes(airports)
        assert airports["TEST"]["country"] == "US"

    def test_handles_unknown_country(self):
        """Unknown countries should not cause errors."""
        airports = {
            "TEST": {"country": "Unknown Country Name"},
        }
        normalize_country_codes(airports)
        # Should remain unchanged
        assert airports["TEST"]["country"] == "Unknown Country Name"


# =============================================================================
# Test: merge_datasets
# =============================================================================


class TestMergeDatasets:
    """Tests for dataset merging logic."""

    def test_mwgg_base_layer(self):
        """mwgg data should form the base layer."""
        mwgg = {
            "EGLL": {
                "iata": "LHR",
                "city": "London",
                "name": "Heathrow",
                "_source": "mwgg",
            }
        }
        openflights: dict = {}
        overrides: dict = {}

        result = merge_datasets(openflights, mwgg, overrides)

        assert "EGLL" in result
        assert result["EGLL"]["city"] == "London"

    def test_openflights_overlays_city_name(self):
        """OpenFlights should overlay English city names."""
        mwgg = {
            "LIRF": {
                "iata": "FCO",
                "icao": "LIRF",
                "city": "Roma",
                "name": "Fiumicino",
            }
        }
        openflights = {
            "FCO": {
                "iata": "FCO",
                "icao": "LIRF",
                "city": "Rome",  # English name
                "name": "Leonardo da Vinci",
            }
        }
        overrides: dict = {}

        result = merge_datasets(openflights, mwgg, overrides)

        assert result["LIRF"]["city"] == "Rome"  # OpenFlights overlaid

    def test_overrides_highest_priority(self):
        """Manual overrides should have highest priority."""
        mwgg = {
            "LIRF": {
                "iata": "FCO",
                "city": "Roma",
                "name": "Fiumicino",
            }
        }
        openflights = {
            "FCO": {
                "iata": "FCO",
                "city": "Rome",
                "name": "Leonardo da Vinci",
            }
        }
        overrides = {
            "FCO": {
                "city": "Rome, Italy",  # Override
                "name": "Rome Fiumicino Airport",
            }
        }

        result = merge_datasets(openflights, mwgg, overrides)

        assert result["LIRF"]["city"] == "Rome, Italy"
        assert result["LIRF"]["name"] == "Rome Fiumicino Airport"


# =============================================================================
# Test: load_overrides
# =============================================================================


class TestLoadOverrides:
    """Tests for override file loading."""

    def test_loads_valid_json(self, tmp_path: Path):
        """Should load valid JSON overrides file."""
        overrides_file = tmp_path / "overrides.json"
        overrides_file.write_text(
            json.dumps(
                {
                    "_comment": "Test",
                    "LHR": {"city": "London"},
                }
            )
        )

        with patch.object(build_module, "OVERRIDES_FILE", overrides_file):
            result = load_overrides()

        assert "LHR" in result
        assert result["LHR"]["city"] == "London"

    def test_excludes_metadata_keys(self, tmp_path: Path):
        """Keys starting with _ should be excluded."""
        overrides_file = tmp_path / "overrides.json"
        overrides_file.write_text(
            json.dumps(
                {
                    "_comment": "Should be excluded",
                    "_section": "Should be excluded",
                    "LHR": {"city": "London"},
                }
            )
        )

        with patch.object(build_module, "OVERRIDES_FILE", overrides_file):
            result = load_overrides()

        assert "_comment" not in result
        assert "_section" not in result
        assert "LHR" in result

    def test_handles_missing_file(self, tmp_path: Path):
        """Should return empty dict if file doesn't exist."""
        missing_file = tmp_path / "nonexistent.json"

        with patch.object(build_module, "OVERRIDES_FILE", missing_file):
            result = load_overrides()

        assert result == {}


# =============================================================================
# Integration Test: Full Pipeline
# =============================================================================


class TestFullPipeline:
    """Integration tests for the full build pipeline."""

    def test_berlin_airports_excluded(
        self, sample_airports: dict, sample_overrides: dict
    ):
        """Berlin closed airports should be excluded in full pipeline."""
        # Apply exclusions
        result = apply_exclusions(sample_airports, sample_overrides)

        # Verify Berlin closed airports are gone
        berlin_codes = {
            a.get("iata") for a in result.values() if a.get("city") == "Berlin"
        }
        assert "SXF" not in berlin_codes
        assert "TXL" not in berlin_codes
        assert "THF" not in berlin_codes

    def test_city_names_updated(self, sample_airports: dict, sample_overrides: dict):
        """City names should be updated from overrides."""
        # Merge with overrides
        mwgg = sample_airports
        openflights: dict = {}

        result = merge_datasets(openflights, mwgg, sample_overrides)

        # FCO should have Rome from override
        fco_airport = next((a for a in result.values() if a.get("iata") == "FCO"), None)
        assert fco_airport is not None
        assert fco_airport["city"] == "Rome"

    def test_combined_filtering(self, sample_airports: dict, sample_overrides: dict):
        """Combined exclusions and FlightLogic filtering."""
        # Step 1: Apply exclusions
        after_exclusions = apply_exclusions(sample_airports, sample_overrides)

        # Step 2: Apply FlightLogic filter
        flightlogic_codes = {"LHR", "LCY", "FRA", "FCO"}
        final = filter_by_flightlogic(after_exclusions, flightlogic_codes)

        # Should have exactly 4 airports
        assert len(final) == 4

        # All should be commercial, no military or closed
        for airport in final.values():
            assert "military" not in airport.get("name", "").lower()
            assert "air base" not in airport.get("name", "").lower()
