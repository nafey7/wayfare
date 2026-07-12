"""Tests for suggestion chip parsing from agent responses."""

from app.ai.graph.suggestion_chips import MAX_SUGGESTIONS, parse_suggestions


class TestParseSuggestions:
    """Tests for parse_suggestions()."""

    def test_no_tag_returns_original(self):
        msg = "Here are some great options for your trip!"
        cleaned, suggestions = parse_suggestions(msg)
        assert cleaned == msg
        assert suggestions == []

    def test_empty_message(self):
        cleaned, suggestions = parse_suggestions("")
        assert cleaned == ""
        assert suggestions == []

    def test_valid_tag_parsed(self):
        msg = (
            "Dubai is amazing!\n\n"
            "[SUGGESTIONS]Find flights to Dubai|"
            "What hotels are in Dubai?|"
            "Plan a Dubai itinerary[/SUGGESTIONS]"
        )
        cleaned, suggestions = parse_suggestions(msg)
        assert cleaned == "Dubai is amazing!"
        assert len(suggestions) == 3
        assert suggestions[0] == {
            "title": "Find flights to Dubai",
            "command": "Find flights to Dubai",
        }
        assert suggestions[1] == {
            "title": "What hotels are in Dubai?",
            "command": "What hotels are in Dubai?",
        }
        assert suggestions[2] == {
            "title": "Plan a Dubai itinerary",
            "command": "Plan a Dubai itinerary",
        }

    def test_title_equals_command(self):
        msg = "Hello! [SUGGESTIONS]Search flights[/SUGGESTIONS]"
        _, suggestions = parse_suggestions(msg)
        assert suggestions[0]["title"] == suggestions[0]["command"]

    def test_max_three_suggestions(self):
        parts = "|".join(f"option {i}" for i in range(5))
        msg = f"Response [SUGGESTIONS]{parts}[/SUGGESTIONS]"
        _, suggestions = parse_suggestions(msg)
        assert len(suggestions) == MAX_SUGGESTIONS

    def test_empty_suggestions_filtered(self):
        msg = "Response [SUGGESTIONS]  | |valid one|  [/SUGGESTIONS]"
        _, suggestions = parse_suggestions(msg)
        assert len(suggestions) == 1
        assert suggestions[0]["title"] == "valid one"

    def test_whitespace_trimmed(self):
        msg = "Response [SUGGESTIONS]  option A  |  option B  [/SUGGESTIONS]"
        _, suggestions = parse_suggestions(msg)
        assert suggestions[0]["title"] == "option A"
        assert suggestions[1]["title"] == "option B"

    def test_tag_must_be_at_end(self):
        msg = "[SUGGESTIONS]early|tag[/SUGGESTIONS] some text after"
        cleaned, suggestions = parse_suggestions(msg)
        assert cleaned == msg
        assert suggestions == []

    def test_trailing_whitespace_after_tag(self):
        msg = "Response [SUGGESTIONS]opt1|opt2[/SUGGESTIONS]  \n  "
        cleaned, suggestions = parse_suggestions(msg)
        assert cleaned == "Response"
        assert len(suggestions) == 2

    def test_multiline_message(self):
        msg = (
            "Here are the results:\n\n"
            "1. Flight A - $500\n"
            "2. Flight B - $600\n\n"
            "[SUGGESTIONS]Show cheaper options|"
            "What about direct flights?[/SUGGESTIONS]"
        )
        cleaned, suggestions = parse_suggestions(msg)
        assert "Flight A" in cleaned
        assert "[SUGGESTIONS]" not in cleaned
        assert len(suggestions) == 2

    def test_single_suggestion(self):
        msg = "Done! [SUGGESTIONS]View your booking[/SUGGESTIONS]"
        cleaned, suggestions = parse_suggestions(msg)
        assert cleaned == "Done!"
        assert len(suggestions) == 1
        assert suggestions[0]["title"] == "View your booking"

    def test_tag_with_newlines_inside(self):
        msg = "Response [SUGGESTIONS]opt 1\n|opt 2[/SUGGESTIONS]"
        _, suggestions = parse_suggestions(msg)
        assert len(suggestions) == 2
        assert suggestions[0]["title"] == "opt 1"
