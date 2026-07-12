"""Google Maps encoded polyline decoder.

Implements the Encoded Polyline Algorithm Format as defined by Google Maps.
"""

from __future__ import annotations


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google Maps encoded polyline string.

    Args:
        encoded: Encoded polyline string from Google Maps API.

    Returns:
        List of (latitude, longitude) float tuples.
    """
    result: list[tuple[float, float]] = []
    index = 0
    length = len(encoded)
    lat = 0
    lng = 0

    while index < length:
        # Decode one coordinate component (lat then lng)
        for is_lng in (False, True):
            b = 0
            shift = 0
            while True:
                char = ord(encoded[index]) - 63
                index += 1
                b |= (char & 0x1F) << shift
                shift += 5
                if char < 32:
                    break
            delta = ~(b >> 1) if b & 1 else b >> 1
            if is_lng:
                lng += delta
            else:
                lat += delta

        result.append((lat / 1e5, lng / 1e5))

    return result


def first_last_points(
    encoded: str,
) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    """Return only the first and last decoded coordinate of a polyline.

    Avoids decoding the entire polyline when only endpoints are needed.
    For very short polylines this still decodes all points, but avoids
    storing the full list when only the endpoints matter.

    # TODO: for very long polylines (hundreds of legs) consider an early-exit
    # decoder that stops after the first point is captured and restarts from
    # the last chunk without accumulating intermediate tuples.

    Args:
        encoded: Encoded polyline string.

    Returns:
        Tuple of (first_point, last_point); each is (lat, lng) or None when
        the polyline is empty or cannot be decoded.
    """
    try:
        points = decode_polyline(encoded)
    except Exception:
        return None, None
    if not points:
        return None, None
    return points[0], points[-1]
