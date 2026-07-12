"""Unit tests for cabin class selection feature in flight booker UI.

Tests that the cabin class dropdown is properly implemented and integrated
into the search request flow.
"""

import os
import re

import pytest


class TestCabinClassSelection:
    """Test cabin class dropdown and integration."""

    @pytest.fixture
    def html_file(self):
        """Return path to flight-booker HTML file."""
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        return os.path.join(base_dir, "dev_ui", "flight-booker", "index.html")

    @pytest.fixture
    def html_content(self, html_file):
        """Load and return HTML file content."""
        assert os.path.exists(html_file), f"File not found: {html_file}"
        with open(html_file, encoding="utf-8") as f:
            return f.read()

    def test_cabin_class_dropdown_exists(self, html_content):
        """Test that cabin class dropdown field exists in the form."""
        # Check for the select element with id="cabin_class"
        assert 'id="cabin_class"' in html_content, (
            "Cabin class dropdown field not found (id='cabin_class')"
        )
        assert 'name="cabin_class"' in html_content, (
            "Cabin class field missing name attribute"
        )

    def test_cabin_class_label_exists(self, html_content):
        """Test that cabin class field has proper label."""
        # Check for label with "Cabin Class"
        label_pattern = r'<label[^>]*for=["\']cabin_class["\'][^>]*>.*?Cabin Class'
        assert re.search(label_pattern, html_content, re.IGNORECASE | re.DOTALL), (
            "Cabin class label not found or not properly associated"
        )

    def test_all_cabin_class_options_exist(self, html_content):
        """Test that all required cabin class options are present."""
        required_options = ["Economy", "PremiumEconomy", "Business", "First"]

        for option in required_options:
            # Check for option value in the select element
            pattern = rf'<option[^>]*value=["\']{re.escape(option)}["\']'
            assert re.search(pattern, html_content), (
                f"Cabin class option '{option}' not found in dropdown"
            )

    def test_economy_is_default(self, html_content):
        """Test that Economy is selected by default."""
        # Find the Economy option and check if it has 'selected' attribute
        economy_pattern = r'<option[^>]*value=["\']Economy["\'][^>]*selected'
        assert re.search(economy_pattern, html_content), (
            "Economy option should be selected by default"
        )

    def test_cabin_class_read_from_form(self, html_content):
        """Test that cabin_class is read from form data in handleSearch function."""
        # Check that formData.get("cabin_class") is called
        assert (
            'formData.get("cabin_class")' in html_content
            or "formData.get('cabin_class')" in html_content
        ), "cabin_class not being read from form data"

    def test_cabin_class_in_search_request(self, html_content):
        """Test that cabin_class is included in the search request payload."""
        # Check that cabin_class is included in searchRequest object
        # Look for pattern like: cabin_class: cabinClass or cabin_class: formData.get...
        cabin_class_patterns = [
            r"cabin_class\s*:\s*cabinClass",
            r'cabin_class\s*:\s*formData\.get\(["\']cabin_class["\']\)',
        ]

        found = any(
            re.search(pattern, html_content) for pattern in cabin_class_patterns
        )
        assert found, (
            "cabin_class not found in search request object. "
            "Should be: cabin_class: cabinClass"
        )

    def test_cabin_class_in_cache_params(self, html_content):
        """Test that cabin_class is included in cache validation parameters."""
        # Check that cabin_class is included in currentSearchParams
        # This ensures different cabin classes don't share cache
        cache_pattern = r"currentSearchParams\s*=\s*\{[^}]*cabin_class"
        assert re.search(cache_pattern, html_content, re.DOTALL), (
            "cabin_class not found in currentSearchParams for cache validation"
        )

    def test_cabin_class_in_get_current_search_params(self, html_content):
        """Test that getCurrentSearchParams includes cabin_class."""
        # Check that getCurrentSearchParams function includes cabin_class
        get_params_pattern = r"getCurrentSearchParams[^}]*cabin_class"
        assert re.search(get_params_pattern, html_content, re.DOTALL), (
            "cabin_class not found in getCurrentSearchParams function"
        )

    def test_cabin_class_in_populate_search_form(self, html_content):
        """Test that populateSearchForm handles cabin_class."""
        # Check that populateSearchForm sets cabin_class field
        populate_pattern = r'setFieldValue\(["\']cabin_class["\']'
        assert re.search(populate_pattern, html_content), (
            "cabin_class not being set in populateSearchForm function"
        )

    def test_cabin_class_default_value(self, html_content):
        """Test that default value 'Economy' is used when cabin_class is not provided."""
        # Check for fallback to "Economy" when formData.get returns null/undefined
        default_patterns = [
            r'formData\.get\(["\']cabin_class["\']\)\s*\|\|\s*["\']Economy["\']',
            (
                r'cabin_class\s*=\s*formData\.get\(["\']cabin_class["\']\)'
                r'\s*\|\|\s*["\']Economy["\']'
            ),
        ]

        found = any(re.search(pattern, html_content) for pattern in default_patterns)
        assert found, (
            "Default value 'Economy' not set when cabin_class is missing from form"
        )

    def test_cabin_class_field_position(self, html_content):
        """Test that cabin class field is in the correct location (after passenger fields)."""
        # Find the form structure - cabin_class should be after infants field
        # This is a structural test to ensure proper form layout
        infants_pos = html_content.find('id="infants"')
        cabin_class_pos = html_content.find('id="cabin_class"')

        assert infants_pos != -1, "Infants field not found"
        assert cabin_class_pos != -1, "Cabin class field not found"
        assert cabin_class_pos > infants_pos, (
            "Cabin class field should be positioned after passenger fields (infants)"
        )

    def test_cabin_class_options_order(self, html_content):
        """Test that cabin class options are in logical order."""
        # Extract the select element for cabin_class
        select_pattern = r'<select[^>]*id=["\']cabin_class["\'][^>]*>(.*?)</select>'
        match = re.search(select_pattern, html_content, re.DOTALL | re.IGNORECASE)

        if match:
            select_content = match.group(1)
            # Check order: Economy (default), PremiumEconomy, Business, First
            economy_pos = select_content.find('value="Economy"')
            premium_pos = select_content.find('value="PremiumEconomy"')
            business_pos = select_content.find('value="Business"')
            first_pos = select_content.find('value="First"')

            assert economy_pos != -1, "Economy option not found"
            assert premium_pos != -1, "PremiumEconomy option not found"
            assert business_pos != -1, "Business option not found"
            assert first_pos != -1, "First option not found"

            # Verify order: Economy < PremiumEconomy < Business < First
            assert economy_pos < premium_pos < business_pos < first_pos, (
                "Cabin class options should be in order: "
                "Economy, PremiumEconomy, Business, First"
            )


if __name__ == "__main__":
    """Run tests directly."""
    pytest.main([__file__, "-v"])
