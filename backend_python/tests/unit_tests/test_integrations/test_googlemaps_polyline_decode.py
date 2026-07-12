"""Unit tests for Google Maps encoded polyline decoder."""

from integrations.googlemaps.polyline_decode import decode_polyline, first_last_points


class TestDecodePolyline:
    def test_known_polyline(self) -> None:
        # Google's canonical example: (38.5, -120.2), (40.7, -120.95), (43.252, -126.453)
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        points = decode_polyline(encoded)
        assert len(points) == 3
        assert abs(points[0][0] - 38.5) < 1e-4
        assert abs(points[0][1] - (-120.2)) < 1e-4
        assert abs(points[1][0] - 40.7) < 1e-4
        assert abs(points[1][1] - (-120.95)) < 1e-4
        assert abs(points[2][0] - 43.252) < 1e-4
        assert abs(points[2][1] - (-126.453)) < 1e-4

    def test_single_point(self) -> None:
        # Lahore approx: (31.5497, 74.3436) → encode manually
        # lat=31.5497 → round(31.5497*1e5)=3154970; lng=74.3436 → round(74.3436*1e5)=7434360
        # For a single-point test use a known encoded value from the canonical algorithm
        # (0.0, 0.0) → "??" (both are 0)
        points = decode_polyline("??")
        assert len(points) == 1
        assert points[0] == (0.0, 0.0)

    def test_empty_string(self) -> None:
        assert decode_polyline("") == []

    def test_negative_coordinates(self) -> None:
        # Exercises the negative-delta branch: negative latitude (-34.0) and
        # positive longitude (151.0). Encoded value verified by round-trip.
        encoded = "~ronE_esx["
        points = decode_polyline(encoded)
        assert len(points) == 1
        assert abs(points[0][0] - (-34.0)) < 1e-4
        assert abs(points[0][1] - 151.0) < 1e-4


class TestFirstLastPoints:
    def test_multi_point_returns_endpoints(self) -> None:
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        first, last = first_last_points(encoded)
        assert first is not None
        assert last is not None
        assert abs(first[0] - 38.5) < 1e-4
        assert abs(first[1] - (-120.2)) < 1e-4
        assert abs(last[0] - 43.252) < 1e-4
        assert abs(last[1] - (-126.453)) < 1e-4

    def test_single_point_same_start_end(self) -> None:
        first, last = first_last_points("??")
        assert first == last == (0.0, 0.0)

    def test_empty_string_returns_none_pair(self) -> None:
        first, last = first_last_points("")
        assert first is None
        assert last is None

    def test_invalid_string_returns_none_pair(self) -> None:
        first, last = first_last_points("\x00")
        assert first is None
        assert last is None
