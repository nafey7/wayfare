"""Script to make all PDF templates more compact to fit on 1 page."""

from pathlib import Path

# Compact CSS replacements
# Note: Removed duplicate keys - last occurrence wins in dict
css_replacements = {
    "margin: 1.5cm": "margin: 1cm",
    "font-size: 10pt": "font-size: 9pt",
    "line-height: 1.3": "line-height: 1.2",
    "padding-bottom: 8px": "padding-bottom: 5px",
    "margin-bottom: 12px": "margin-bottom: 8px",
    "margin-bottom: 8px": "margin-bottom: 4px",  # Last value wins (was 5px, then 4px)
    "padding-bottom: 3px": "padding-bottom: 2px",
    "margin-bottom: 6px": "margin-bottom: 3px",  # Last value wins (was 4px, then 3px)
    "padding: 4px": "padding: 2px",
    "font-size: 9pt": "font-size: 8pt",
    "padding: 6px": "padding: 3px",
    "border-left: 3px solid": "border-left: 2px solid",
    "padding: 8px": "padding: 4px",
    "font-size: 11pt": "font-size: 9pt",
    "margin-bottom: 4px": "margin-bottom: 2px",
    "margin-top: 12px": "margin-top: 6px",
    "padding-top: 8px": "padding-top: 4px",
    "font-size: 8pt": "font-size: 7pt",
    "margin: 6px 0": "margin: 3px 0",
    "padding-left: 20px": "padding-left: 15px",
    "margin: 2px 0": "margin: 1px 0",
    "margin: 10px 0": "margin: 6px 0",
    "padding: 15px": "padding: 8px",
    "padding-bottom: 15px": "padding-bottom: 8px",
}


def compress_template(file_path: Path):
    """Apply compact CSS to a template file."""
    print(f"Compressing {file_path.name}...")

    content = file_path.read_text(encoding="utf-8")

    # Apply all replacements
    for old, new in css_replacements.items():
        content = content.replace(old, new)

    # Write back
    file_path.write_text(content, encoding="utf-8")
    print("  ✓ Done")


def main():
    template_dir = (
        Path(__file__).parent
        / "app"
        / "domains"
        / "email"
        / "attachments"
        / "templates"
    )

    templates = ["booking_gds.html", "ticket.html"]

    for template in templates:
        file_path = template_dir / template
        if file_path.exists():
            compress_template(file_path)
        else:
            print(f"  ✗ {template} not found")

    print("\nAll templates compressed!")


if __name__ == "__main__":
    main()
