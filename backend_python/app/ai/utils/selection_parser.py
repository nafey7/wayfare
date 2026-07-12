"""Selection parsing utility for booking handlers.

Consolidates selection parsing logic used by booking handlers.

Handles patterns like:
- "book option 1", "select option 2"
- "book the first one", "take the second"
- "book 1", "select 2"
- "book best value", "select cheapest" (domain-specific labels)
- Just a number "1", "2"
"""

import re
from enum import Enum


class SelectionDomain(Enum):
    """Domain for label-based selection patterns."""

    FLIGHT = "flight"
    HOTEL = "hotel"
    GENERIC = "generic"


# Label patterns by domain and option number
LABEL_PATTERNS: dict[SelectionDomain, dict[int, list[str]]] = {
    SelectionDomain.FLIGHT: {
        # Option 1 is typically "BEST VALUE"
        1: ["best value", "best", "value", "recommended", "balance"],
        # Option 2 is typically "CHEAPEST"
        2: ["cheapest", "cheap", "lowest price", "budget", "economy"],
        # Option 3 is typically "MOST CONVENIENT"
        3: ["convenient", "direct", "fastest", "quick", "nonstop", "non-stop"],
    },
    SelectionDomain.HOTEL: {
        # Option 1 is typically "BEST VALUE"
        1: ["best value", "best", "value", "recommended", "balance"],
        # Option 2 is typically "LOWEST PRICE"
        2: ["cheapest", "cheap", "lowest price", "budget", "economy"],
        # Option 3 is typically "HIGHEST RATED"
        3: ["highest rated", "best rated", "top rated", "best reviews", "rating"],
    },
    SelectionDomain.GENERIC: {
        1: ["best value", "best", "value", "recommended"],
        2: ["cheapest", "cheap", "lowest price", "budget"],
        3: ["third", "option 3"],
    },
}

# Ordinal word to number mapping
ORDINAL_WORDS: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "1st": 1,
    "2nd": 2,
    "3rd": 3,
    "4th": 4,
    "5th": 5,
    "6th": 6,
    "7th": 7,
    "8th": 8,
    "9th": 9,
    "10th": 10,
}

# Action words that indicate selection intent
ACTION_WORDS = ["book", "select", "choose", "take", "want", "pick"]


class SelectionParser:
    """Parses user messages to extract option selections."""

    @staticmethod
    def parse(
        message: str,
        domain: SelectionDomain = SelectionDomain.GENERIC,
        include_labels: bool = True,
    ) -> int | None:
        """Parse selection from user message.

        Recognizes patterns in this order:
        1. "book option 1", "select option 2", "choose option 3"
        2. "book the first one", "take the second", "choose third"
        3. "book 1", "select 2", "take 3"
        4. "book best value", "select cheapest" (if include_labels=True)
        5. Just a number "1", "2", "3"

        Args:
            message: User message to parse
            domain: Domain for label-based patterns (FLIGHT, HOTEL, GENERIC)
            include_labels: Whether to check for label patterns (best value, cheapest, etc.)

        Returns:
            Option number (1-based) if found, None otherwise
        """
        message_lower = message.lower().strip()

        # Pattern 1: "book option 1", "select option 2", "choose option 3"
        result = SelectionParser._parse_option_pattern(message_lower)
        if result is not None:
            return result

        # Pattern 2: "book the first one", "take the second"
        result = SelectionParser._parse_ordinal_pattern(message_lower)
        if result is not None:
            return result

        # Pattern 3: "book 1", "select 2"
        result = SelectionParser._parse_action_number_pattern(message_lower)
        if result is not None:
            return result

        # Pattern 4: Label-based selection (domain-specific)
        if include_labels:
            result = SelectionParser._parse_label_pattern(message_lower, domain)
            if result is not None:
                return result

        # Pattern 5: Just a number by itself
        result = SelectionParser._parse_bare_number(message_lower)
        if result is not None:
            return result

        return None

    @staticmethod
    def _parse_option_pattern(message: str) -> int | None:
        """Parse 'book option 1' pattern."""
        match = re.search(r"(?:book|select|choose|pick|take)\s+option\s+(\d+)", message)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _parse_ordinal_pattern(message: str) -> int | None:
        """Parse 'book the first one' pattern."""
        for word, num in ORDINAL_WORDS.items():
            if word in message and any(action in message for action in ACTION_WORDS):
                return num
        return None

    @staticmethod
    def _parse_action_number_pattern(message: str) -> int | None:
        """Parse 'book 1' pattern."""
        match = re.search(r"(?:book|select|choose|take|want)\s+(\d+)", message)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _parse_label_pattern(message: str, domain: SelectionDomain) -> int | None:
        """Parse 'book best value' pattern based on domain."""
        patterns = LABEL_PATTERNS.get(domain, LABEL_PATTERNS[SelectionDomain.GENERIC])

        for option_num, labels in patterns.items():
            for label in labels:
                if label in message and any(
                    action in message for action in ACTION_WORDS
                ):
                    return option_num
        return None

    @staticmethod
    def _parse_bare_number(message: str) -> int | None:
        """Parse just a number '1', '2', '3'."""
        stripped = message.strip()
        # Handle trailing punctuation like "4."
        stripped = stripped.rstrip(".,!?")
        if stripped.isdigit():
            return int(stripped)
        return None

    @staticmethod
    def has_selection_intent(message: str) -> bool:
        """Check if message contains selection intent words.

        Useful for determining if a message might be a selection attempt
        before parsing.

        Args:
            message: User message to check

        Returns:
            True if message contains selection intent words
        """
        message_lower = message.lower()
        return any(action in message_lower for action in ACTION_WORDS)

    @staticmethod
    def extract_all_numbers(message: str) -> list[int]:
        """Extract all numbers from message.

        Useful for handling multi-selection scenarios.

        Args:
            message: User message

        Returns:
            List of numbers found in message
        """
        return [int(n) for n in re.findall(r"\d+", message)]

    @staticmethod
    def validate_selection(
        selection: int | None,
        max_options: int,
        min_options: int = 1,
    ) -> tuple[bool, str | None]:
        """Validate that a selection is within valid range.

        Args:
            selection: Parsed selection number (can be None)
            max_options: Maximum valid option number
            min_options: Minimum valid option number (default 1)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if selection is None:
            return False, "Could not parse selection from message"

        if selection < min_options:
            return False, f"Selection must be at least {min_options}"

        if selection > max_options:
            return (
                False,
                f"Selection {selection} is out of range. "
                f"Please choose between {min_options} and {max_options}.",
            )

        return True, None


def parse_selection(
    message: str,
    domain: str | SelectionDomain = "generic",
    include_labels: bool = True,
) -> int | None:
    """Convenience function to parse selection.

    Args:
        message: User message to parse
        domain: Domain string ("flight", "hotel", "generic") or SelectionDomain enum
        include_labels: Whether to check label patterns

    Returns:
        Option number (1-based) if found, None otherwise
    """
    if isinstance(domain, str):
        domain = SelectionDomain(domain.lower())

    return SelectionParser.parse(message, domain, include_labels)
