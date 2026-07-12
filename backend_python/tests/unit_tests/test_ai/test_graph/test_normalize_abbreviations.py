"""Unit tests for _normalize_abbreviations in dates.py."""

from app.ai.graph.tools.dates import _normalize_abbreviations


class TestNormalizeAbbreviations:
    """Tests for the _normalize_abbreviations function."""

    def test_wknd_to_weekend(self) -> None:
        assert _normalize_abbreviations("next wknd") == "next weekend"

    def test_weeknd_to_weekend(self) -> None:
        assert _normalize_abbreviations("this weeknd") == "this weekend"

    def test_wk_to_week(self) -> None:
        assert _normalize_abbreviations("next wk") == "next week"

    def test_tmrw_to_tomorrow(self) -> None:
        assert _normalize_abbreviations("tmrw for 3 nights") == "tomorrow for 3 nights"

    def test_tmw_to_tomorrow(self) -> None:
        assert _normalize_abbreviations("tmw morning") == "tomorrow morning"

    def test_case_insensitive(self) -> None:
        assert _normalize_abbreviations("next WKND") == "next weekend"
        assert _normalize_abbreviations("TMRW") == "tomorrow"

    def test_word_boundary_wk_not_in_week(self) -> None:
        """'wk' should not affect 'week' or 'awkward'."""
        assert _normalize_abbreviations("next week") == "next week"
        assert _normalize_abbreviations("awkward timing") == "awkward timing"

    def test_word_boundary_wknd_not_in_weekend(self) -> None:
        """'wknd' should not affect 'weekend'."""
        assert _normalize_abbreviations("next weekend") == "next weekend"

    def test_no_abbreviations_unchanged(self) -> None:
        assert _normalize_abbreviations("april 15 to 20") == "april 15 to 20"

    def test_multiple_abbreviations(self) -> None:
        assert (
            _normalize_abbreviations("tmrw or next wknd") == "tomorrow or next weekend"
        )
