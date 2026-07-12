"""Parse finite floats from hotel JSON (session / API payloads) — not range-validated."""

from __future__ import annotations

import math
from typing import Any


def finite_float_from_hotel_json(value: object) -> float | None:
    """Parse a finite float from session / request JSON (not range-validated)."""
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            x = float(value)
        else:
            s = str(value).strip()
            if not s:
                return None
            x = float(s)
    except (TypeError, ValueError, OverflowError):
        return None
    return x if math.isfinite(x) else None


def first_dict_coord_value(d: dict[str, Any], *keys: str) -> Any:
    """First key present with a non-None value (treats 0.0 as present)."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None
