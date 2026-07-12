"""User preferences schemas per PROFILE_BACKEND_SPEC."""

import re

from pydantic import Field, field_validator

from app.shared.schemas import StrictModel

# --- Travel Style (per spec §4) ---

TRAVEL_PACE_OPTIONS = frozenset({"relaxed", "balanced", "packed", "ultraEfficient"})
BUDGET_MINDSET_OPTIONS = frozenset({"comfort", "bestValue", "premium", "luxury"})
ACCOMMODATION_OPTIONS = frozenset({"4", "5", "4star", "5star", "unique", "noPref"})
ACTIVITY_DENSITY_OPTIONS = frozenset(
    {"structured", "guided", "freeTime", "selfExplore", "noPref"}
)
PRIMARY_GOALS_OPTIONS = frozenset(
    {
        "business",
        "culture",
        "food",
        "nature",
        "family",
        "luxury",
        "hidden",
        "nightlife",
        "photography",
    }
)
GETTING_AROUND_OPTIONS = frozenset(
    {"public", "rideshare", "walking", "rental", "private", "trains", "noPref"}
)


class TravelStylePreferences(StrictModel):
    """Travel style preferences."""

    travel_pace: str | None = Field(
        None, description="relaxed|balanced|packed|ultraEfficient"
    )
    budget_mindset: str | None = Field(
        None, description="comfort|bestValue|premium|luxury"
    )
    accommodation: str | None = Field(None, description="4star|5star|unique|noPref")
    activity_density: str | None = Field(
        None, description="structured|guided|freeTime|selfExplore|noPref"
    )
    primary_goals: list[str] = Field(default_factory=list)
    getting_around: list[str] = Field(default_factory=list)

    @field_validator(
        "travel_pace", "budget_mindset", "accommodation", "activity_density"
    )
    @classmethod
    def validate_str_option(cls, v: str | None) -> str | None:
        if v is None:
            return v
        all_opts = (
            TRAVEL_PACE_OPTIONS
            | BUDGET_MINDSET_OPTIONS
            | ACCOMMODATION_OPTIONS
            | ACTIVITY_DENSITY_OPTIONS
        )
        if v not in all_opts:
            raise ValueError(f"Invalid value {v!r}, must be one of the allowed options")
        return v

    @field_validator("primary_goals", "getting_around")
    @classmethod
    def validate_list_options(cls, v: list[str]) -> list[str]:
        if not v:
            return v
        all_opts = PRIMARY_GOALS_OPTIONS | GETTING_AROUND_OPTIONS
        invalid = [x for x in v if x not in all_opts]
        if invalid:
            raise ValueError(f"Invalid items {invalid}, must be in allowed options")
        return v


# --- Flights ---

SEAT_PREFERENCE_OPTIONS = frozenset({"window", "aisle", "noPreference"})
MAX_STOPS_OPTIONS = frozenset({"nonstop", "1stop", "2stops", "any"})


class FlightsPreferences(StrictModel):
    """Flight preferences."""

    seat_preference: str | None = Field(None, description="window|aisle|noPreference")
    max_stops: str | None = Field(None, description="nonstop|1stop|2stops|any")
    preferred_airlines: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="IATA codes or airline names, max 50 items, each up to 80 chars",
    )
    departure_window: list[str] = Field(
        default_factory=lambda: ["00:00", "23:59"],
        description="Time window as [min, max] in HH:mm format",
    )

    @field_validator("seat_preference")
    @classmethod
    def validate_seat(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in SEAT_PREFERENCE_OPTIONS:
            raise ValueError(
                f"seat_preference must be in {sorted(SEAT_PREFERENCE_OPTIONS)}"
            )
        return v

    @field_validator("max_stops")
    @classmethod
    def validate_max_stops(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in MAX_STOPS_OPTIONS:
            raise ValueError(f"max_stops must be in {sorted(MAX_STOPS_OPTIONS)}")
        return v

    @field_validator("preferred_airlines")
    @classmethod
    def validate_preferred_airlines(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ValueError("preferred_airlines must have at most 50 items")
        for i, item in enumerate(v):
            if not isinstance(item, str) or len(item) > 80:
                raise ValueError(
                    f"preferred_airlines[{i}] must be a string up to 80 characters"
                )
        return v

    @field_validator("departure_window", mode="before")
    @classmethod
    def normalize_departure_window(cls, v: object) -> list[str]:
        """Normalize and validate. Accepts legacy numeric [min_h, max_h] or HH:mm strings."""
        if not isinstance(v, list) or len(v) != 2:
            raise ValueError("departure_window must have exactly 2 elements [min, max]")
        pattern = r"^([01]\d|2[0-3]):[0-5]\d$"
        result: list[str] = []
        for i, t in enumerate(v):
            if isinstance(t, (int, float)):
                if t < 0:
                    raise ValueError(
                        f"departure_window[{i}] must be non-negative, got {t!r}"
                    )
                h = int(t) % 24
                m = round((t % 1) * 60) % 60
                result.append(f"{h:02d}:{m:02d}")
            elif isinstance(t, str) and re.match(pattern, t):
                result.append(t)
            else:
                raise ValueError(
                    f"departure_window[{i}] must be HH:mm (00:00-23:59) or numeric hour, got {t!r}"
                )
        return result


# --- Hotels ---

BED_TYPE_OPTIONS = frozenset({"king", "twin", "queen", "noPreference"})
ROOM_TYPE_OPTIONS = frozenset(
    {"standard", "suite", "apartmentStyle", "noPreference", "hotel", "apartment"}
)
AMENITIES_OPTIONS = frozenset(
    {
        "breakfast",
        "gym",
        "spa",
        "pool",
        "workspace",
        "familyFriendly",
        "petFriendly",
        "airportShuttle",
    }
)
HOTEL_STYLE_OPTIONS = frozenset(
    {
        "modern",
        "classic",
        "designForward",
        "traditional",
        "ecoConscious",
        "minimalist",
        "industrial",
        "artisanal",
    }
)
LOCATION_PREFERENCE_OPTIONS = frozenset(
    {
        "cityCenter",
        "nearTransport",
        "quietNeighborhood",
        "closeToAttractions",
        "waterfront",
    }
)
CANCELLATION_OPTIONS = frozenset(
    {"freeOnly", "flexiblePreferred", "nonRefundableOk", "refundable", "nonrefundable"}
)


class HotelsPreferences(StrictModel):
    """Hotel preferences."""

    bed_type: str | None = Field(None, description="king|twin|queen|noPreference")
    room_type: str | None = Field(
        None, description="standard|suite|apartmentStyle|noPreference"
    )
    amenities: list[str] = Field(default_factory=list)
    hotel_style: list[str] = Field(default_factory=list)
    location_preference: list[str] = Field(default_factory=list)
    cancellation: list[str] = Field(default_factory=list)

    @field_validator("bed_type")
    @classmethod
    def validate_bed_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in BED_TYPE_OPTIONS:
            raise ValueError(f"bed_type must be in {sorted(BED_TYPE_OPTIONS)}")
        return v

    @field_validator("room_type")
    @classmethod
    def validate_room_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ROOM_TYPE_OPTIONS:
            raise ValueError(f"room_type must be in {sorted(ROOM_TYPE_OPTIONS)}")
        return v

    @field_validator("amenities")
    @classmethod
    def validate_amenities(cls, v: list[str]) -> list[str]:
        if not v:
            return v
        invalid = [x for x in v if x not in AMENITIES_OPTIONS]
        if invalid:
            raise ValueError(f"amenities: invalid items {invalid}")
        return v

    @field_validator("hotel_style")
    @classmethod
    def validate_hotel_style(cls, v: list[str]) -> list[str]:
        if not v:
            return v
        invalid = [x for x in v if x not in HOTEL_STYLE_OPTIONS]
        if invalid:
            raise ValueError(f"hotel_style: invalid items {invalid}")
        return v

    @field_validator("location_preference")
    @classmethod
    def validate_location_preference(cls, v: list[str]) -> list[str]:
        if not v:
            return v
        invalid = [x for x in v if x not in LOCATION_PREFERENCE_OPTIONS]
        if invalid:
            raise ValueError(f"location_preference: invalid items {invalid}")
        return v

    @field_validator("cancellation")
    @classmethod
    def validate_cancellation(cls, v: list[str]) -> list[str]:
        if not v:
            return v
        invalid = [x for x in v if x not in CANCELLATION_OPTIONS]
        if invalid:
            raise ValueError(f"cancellation: invalid items {invalid}")
        return v


# --- Full preferences response ---


class UserPreferencesResponse(StrictModel):
    """Full preferences for profile aggregate response."""

    document_exists: bool = Field(
        True,
        description="False when no MongoDB document exists; frontend treats all fields as empty.",
    )
    preference_chips: list[str] = Field(
        default_factory=list,
        description="Display labels for preferences, max 20 items",
    )

    @field_validator("preference_chips")
    @classmethod
    def validate_preference_chips(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ValueError("preference_chips must have at most 20 items")
        for i, item in enumerate(v):
            if not isinstance(item, str) or len(item) > 100:
                raise ValueError(
                    f"preference_chips[{i}] must be a string up to 100 characters"
                )
        return v

    travel_style: TravelStylePreferences = Field(
        default_factory=lambda: TravelStylePreferences(
            travel_pace=None,
            budget_mindset=None,
            accommodation=None,
            activity_density=None,
            primary_goals=[],
            getting_around=[],
        )
    )
    flights: FlightsPreferences = Field(
        default_factory=lambda: FlightsPreferences(
            seat_preference=None,
            max_stops=None,
            preferred_airlines=[],
            departure_window=["00:00", "23:59"],
        )
    )
    hotels: HotelsPreferences = Field(
        default_factory=lambda: HotelsPreferences(
            bed_type=None,
            room_type=None,
            amenities=[],
            hotel_style=[],
            location_preference=[],
            cancellation=[],
        )
    )


# --- Update request (partial update supported) ---
#
# Uses all-optional nested schemas so model_dump(exclude_unset=True) returns only
# fields the client actually sent. Fixes partial update overwriting (e.g. sending
# {"flights": {"seat_preference": "aisle"}} no longer erases preferred_airlines).
#


class TravelStylePreferencesUpdate(StrictModel):
    """All fields optional for partial updates."""

    travel_pace: str | None = None
    budget_mindset: str | None = None
    accommodation: str | None = None
    activity_density: str | None = None
    primary_goals: list[str] | None = None
    getting_around: list[str] | None = None

    @field_validator(
        "travel_pace", "budget_mindset", "accommodation", "activity_density"
    )
    @classmethod
    def _validate_str_option(cls, v: str | None) -> str | None:
        if v is None:
            return v
        all_opts = (
            TRAVEL_PACE_OPTIONS
            | BUDGET_MINDSET_OPTIONS
            | ACCOMMODATION_OPTIONS
            | ACTIVITY_DENSITY_OPTIONS
        )
        if v not in all_opts:
            raise ValueError(f"Invalid value {v!r}, must be one of the allowed options")
        return v

    @field_validator("primary_goals", "getting_around")
    @classmethod
    def _validate_list_options(cls, v: list[str] | None) -> list[str] | None:
        if v is None or not v:
            return v
        all_opts = PRIMARY_GOALS_OPTIONS | GETTING_AROUND_OPTIONS
        invalid = [x for x in v if x not in all_opts]
        if invalid:
            raise ValueError(f"Invalid items {invalid}, must be in allowed options")
        return v


class FlightsPreferencesUpdate(StrictModel):
    """All fields optional for partial updates."""

    seat_preference: str | None = None
    max_stops: str | None = None
    preferred_airlines: list[str] | None = None
    departure_window: list[str] | None = None

    @field_validator("preferred_airlines")
    @classmethod
    def _validate_preferred_airlines(cls, v: list[str] | None) -> list[str] | None:
        if v is None or not v:
            return v
        if len(v) > 50:
            raise ValueError("preferred_airlines must have at most 50 items")
        for i, item in enumerate(v):
            if not isinstance(item, str) or len(item) > 80:
                raise ValueError(
                    f"preferred_airlines[{i}] must be a string up to 80 characters"
                )
        return v

    @field_validator("seat_preference")
    @classmethod
    def _validate_seat(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in SEAT_PREFERENCE_OPTIONS:
            raise ValueError(
                f"seat_preference must be in {sorted(SEAT_PREFERENCE_OPTIONS)}"
            )
        return v

    @field_validator("max_stops")
    @classmethod
    def _validate_max_stops(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in MAX_STOPS_OPTIONS:
            raise ValueError(f"max_stops must be in {sorted(MAX_STOPS_OPTIONS)}")
        return v

    @field_validator("departure_window", mode="before")
    @classmethod
    def _normalize_departure_window(cls, v: object) -> list[str] | None:
        if v is None:
            return v
        if not isinstance(v, list) or len(v) != 2:
            raise ValueError("departure_window must have exactly 2 elements [min, max]")
        pattern = r"^([01]\d|2[0-3]):[0-5]\d$"
        result: list[str] = []
        for i, t in enumerate(v):
            if isinstance(t, (int, float)):
                if t < 0:
                    raise ValueError(
                        f"departure_window[{i}] must be non-negative, got {t!r}"
                    )
                h = int(t) % 24
                m = round((t % 1) * 60) % 60
                result.append(f"{h:02d}:{m:02d}")
            elif isinstance(t, str) and re.match(pattern, t):
                result.append(t)
            else:
                raise ValueError(
                    f"departure_window[{i}] must be HH:mm (00:00-23:59) or numeric hour, got {t!r}"
                )
        return result


class HotelsPreferencesUpdate(StrictModel):
    """All fields optional for partial updates."""

    bed_type: str | None = None
    room_type: str | None = None
    amenities: list[str] | None = None
    hotel_style: list[str] | None = None
    location_preference: list[str] | None = None
    cancellation: list[str] | None = None

    @field_validator("bed_type")
    @classmethod
    def _validate_bed_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in BED_TYPE_OPTIONS:
            raise ValueError(f"bed_type must be in {sorted(BED_TYPE_OPTIONS)}")
        return v

    @field_validator("room_type")
    @classmethod
    def _validate_room_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ROOM_TYPE_OPTIONS:
            raise ValueError(f"room_type must be in {sorted(ROOM_TYPE_OPTIONS)}")
        return v

    @field_validator("amenities")
    @classmethod
    def _validate_amenities(cls, v: list[str] | None) -> list[str] | None:
        if v is None or not v:
            return v
        invalid = [x for x in v if x not in AMENITIES_OPTIONS]
        if invalid:
            raise ValueError(f"amenities: invalid items {invalid}")
        return v

    @field_validator("hotel_style")
    @classmethod
    def _validate_hotel_style(cls, v: list[str] | None) -> list[str] | None:
        if v is None or not v:
            return v
        invalid = [x for x in v if x not in HOTEL_STYLE_OPTIONS]
        if invalid:
            raise ValueError(f"hotel_style: invalid items {invalid}")
        return v

    @field_validator("location_preference")
    @classmethod
    def _validate_location_preference(cls, v: list[str] | None) -> list[str] | None:
        if v is None or not v:
            return v
        invalid = [x for x in v if x not in LOCATION_PREFERENCE_OPTIONS]
        if invalid:
            raise ValueError(f"location_preference: invalid items {invalid}")
        return v

    @field_validator("cancellation")
    @classmethod
    def _validate_cancellation(cls, v: list[str] | None) -> list[str] | None:
        if v is None or not v:
            return v
        invalid = [x for x in v if x not in CANCELLATION_OPTIONS]
        if invalid:
            raise ValueError(f"cancellation: invalid items {invalid}")
        return v


class PreferencesUpdateRequest(StrictModel):
    """Partial update request for preferences. All fields optional."""

    preference_chips: list[str] | None = None

    @field_validator("preference_chips")
    @classmethod
    def _validate_preference_chips(cls, v: list[str] | None) -> list[str] | None:
        if v is None or not v:
            return v
        if len(v) > 20:
            raise ValueError("preference_chips must have at most 20 items")
        for i, item in enumerate(v):
            if not isinstance(item, str) or len(item) > 100:
                raise ValueError(
                    f"preference_chips[{i}] must be a string up to 100 characters"
                )
        return v

    travel_style: TravelStylePreferencesUpdate | None = None
    flights: FlightsPreferencesUpdate | None = None
    hotels: HotelsPreferencesUpdate | None = None
