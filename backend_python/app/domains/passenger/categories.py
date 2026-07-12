"""Passenger categorization and hotel title derivation.

Shared between flights and hotels. Age brackets:
- Flights: Adult 12+, Child 2–11, Infant <2
- Hotels: Adult 18+, Child 0–17
"""

from typing import Literal

from app.domains.flight.validators import calculate_age


def derive_hotel_title(title: str, date_of_birth: str | None) -> str:
    """Derive hotel-appropriate title from flight title and DOB.

    Hotel category: 18+ = adult (Mr/Mrs/Miss), 0–17 = child (Master/Miss).
    Gender from title: Mr, Master → male; Mrs, Miss, Ms → female.
    Unknown title → treat as female (Miss).

    Args:
        title: User-provided title (Mr, Mrs, Miss, Ms, Master)
        date_of_birth: DOB in YYYY-MM-DD. If invalid/missing, assume adult.

    Returns:
        Mr (male adult), Mrs/Miss/Ms (female adult), Master (male child), Miss (female child)
    """
    age = calculate_age(date_of_birth)
    if age is None:
        age = 18  # Invalid/missing DOB: assume adult

    t = title.strip().lower()
    is_male = t in ("mr", "master")

    if age >= 18:
        if is_male:
            return "Mr"
        if t in ("mrs", "miss", "ms"):
            return "Mrs" if t == "mrs" else ("Ms" if t == "ms" else "Miss")
        return "Miss"
    return "Master" if is_male else "Miss"


def get_passenger_category(
    dob: str | None,
    context: Literal["flight", "hotel"],
) -> str | None:
    """Get passenger category from DOB for the given context.

    Args:
        dob: Date of birth in YYYY-MM-DD format
        context: 'flight' or 'hotel'

    Returns:
        'adult' | 'child' | 'infant' (flight) or 'adult' | 'child' (hotel).
        None if DOB invalid or missing.
    """
    age = calculate_age(dob)
    if age is None:
        return None

    if context == "flight":
        if age >= 12:
            return "adult"
        if age >= 2:
            return "child"
        return "infant"

    if context == "hotel":
        return "adult" if age >= 18 else "child"

    return None


def derive_type_hotel(date_of_birth: str | None) -> str:
    """Derive hotel passenger type from DOB. 18+ = adult, 0–17 = child.

    Invalid/missing DOB assumes adult (same fallback as hotel_title).
    """
    cat = get_passenger_category(date_of_birth, "hotel")
    return cat if cat else "adult"
