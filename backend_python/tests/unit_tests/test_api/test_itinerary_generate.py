"""Unit tests for POST /api/itinerary/generate endpoint."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.itinerary.generate import (
    GenerateItineraryRequest,
    generate_itinerary_direct,
)
from app.domains.user.schemas import UserPublic

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_ITINERARY: dict = {
    "itineraryItems": [
        {
            "day": 1,
            "title": "Arrival",
            "imageUrl": "",
            "expandedContent": {"activities": []},
        }
    ],
    "budgetSnapshot": {"description": "~$500 pp", "title": "Budget Snapshot"},
    "localExperiences": [],
    "footerSectionTitle": "Must-Try Local Experiences",
}
_SUCCESS_CONTENT = json.dumps(
    {
        "status": "success",
        "destination": "London",
        "validation": {"valid": True, "warnings": []},
    }
)
_SAVED_ID = "507f1f77bcf86cd799439011"  # pragma: allowlist secret

_ITINERARY_TOOL_PATH = "app.ai.graph.tools.itinerary.generate_itinerary"


def _mock_user() -> MagicMock:
    u = MagicMock(spec=UserPublic)
    u.id = "user123"
    return u


def _mock_saved() -> MagicMock:
    s = MagicMock()
    s.id = _SAVED_ID
    return s


def _mock_tool(
    content: str = _SUCCESS_CONTENT, itinerary: dict | None = None
) -> MagicMock:
    tool = MagicMock()
    tool.coroutine = AsyncMock(return_value=(content, itinerary or _MOCK_ITINERARY))
    return tool


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateItineraryEndpoint:
    @pytest.mark.asyncio
    async def test_success_returns_saved_id_and_itinerary(self) -> None:
        """Happy path: tool succeeds, geocoding runs, saved itinerary returned."""
        with (
            patch(_ITINERARY_TOOL_PATH, _mock_tool()),
            patch(
                "app.api.itinerary.generate.create_saved_itinerary",
                new=AsyncMock(return_value=_mock_saved()),
            ),
            patch("app.shared.geocoding.GeocodingService", autospec=True) as MockGeo,
        ):
            geo_instance = MockGeo.return_value
            geo_instance.geocode_city = AsyncMock(
                return_value=[MagicMock(lat=51.5, lng=-0.1)]
            )

            result = await generate_itinerary_direct(
                GenerateItineraryRequest(
                    destination="London",
                    origin="Paris",
                    departure_date="2026-06-01",
                    return_date="2026-06-07",
                    adults=2,
                ),
                _mock_user(),
            )

        assert result.saved_itinerary_id == _SAVED_ID
        assert result.structured_itinerary == _MOCK_ITINERARY
        assert result.trip_meta["destination"] == "London"
        assert result.trip_meta["origin"] == "Paris"
        assert "destination_location" in result.trip_meta

    @pytest.mark.asyncio
    async def test_skip_flights_requested_passed_to_tool(self) -> None:
        """skip_flights_requested=True is forwarded so origin is not required."""
        captured_config: list[RunnableConfig] = []

        async def _capture(**kwargs: object) -> tuple[str, dict]:
            captured_config.append(kwargs.get("config"))  # type: ignore[arg-type]
            return _SUCCESS_CONTENT, _MOCK_ITINERARY

        tool = MagicMock()
        tool.coroutine = _capture

        with (
            patch(_ITINERARY_TOOL_PATH, tool),
            patch(
                "app.api.itinerary.generate.create_saved_itinerary",
                new=AsyncMock(return_value=_mock_saved()),
            ),
            patch("app.shared.geocoding.GeocodingService", autospec=True) as MockGeo,
        ):
            MockGeo.return_value.geocode_city = AsyncMock(return_value=[])
            await generate_itinerary_direct(
                GenerateItineraryRequest(destination="Tokyo", adults=1),
                _mock_user(),
            )

        assert captured_config, "No config was captured"
        cfg = captured_config[0]
        assert cfg is not None
        assert cfg.get("configurable", {}).get("skip_flights_requested") is True

    @pytest.mark.asyncio
    async def test_tool_error_raises_422_with_actionable_detail(self) -> None:
        """Tool status=error is surfaced as 422 with the tool's own message."""
        from fastapi import HTTPException

        error_body = json.dumps(
            {"status": "error", "message": "Destination is required."}
        )
        with (
            patch(_ITINERARY_TOOL_PATH, _mock_tool(content=error_body, itinerary={})),
            pytest.raises(HTTPException) as exc_info,
        ):
            await generate_itinerary_direct(
                GenerateItineraryRequest(destination="London", adults=1),
                _mock_user(),
            )

        assert exc_info.value.status_code == 422
        assert "Destination is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_geocoding_failure_does_not_block_response(self) -> None:
        """Geocoding errors are swallowed — itinerary is still returned."""
        with (
            patch(_ITINERARY_TOOL_PATH, _mock_tool()),
            patch(
                "app.api.itinerary.generate.create_saved_itinerary",
                new=AsyncMock(return_value=_mock_saved()),
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
                side_effect=RuntimeError("geocoding down"),
            ),
        ):
            result = await generate_itinerary_direct(
                GenerateItineraryRequest(
                    destination="London", origin="Paris", adults=1
                ),
                _mock_user(),
            )

        assert result.saved_itinerary_id == _SAVED_ID
        assert "origin_location" not in result.trip_meta
        assert "destination_location" not in result.trip_meta
