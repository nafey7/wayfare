"""Verify that all generated PDFs are exactly 1 page."""

from pathlib import Path

from PyPDF2 import PdfReader


def count_pdf_pages(pdf_path: Path) -> int:
    """Count number of pages in a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        print(f"Error reading {pdf_path.name}: {e}")
        return -1


def main():
    pdf_dir = Path(__file__).parent / "logs" / "pdfs"

    if not pdf_dir.exists():
        print(f"PDF directory not found: {pdf_dir}")
        return

    # Get all PDFs
    pdf_files = sorted(
        pdf_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not pdf_files:
        print("No PDF files found")
        return

    # Check only the 3 most recent PDFs (latest generation)
    recent_pdfs = pdf_files[:3]

    print("Verifying PDF page counts...\n")
    print("=" * 70)

    all_single_page = True

    for pdf_file in recent_pdfs:
        page_count = count_pdf_pages(pdf_file)
        file_size_kb = pdf_file.stat().st_size / 1024

        status = "OK" if page_count == 1 else "MULTIPLE PAGES"

        print(f"{pdf_file.name}")
        print(f"  Pages: {page_count}")
        print(f"  Size: {file_size_kb:.1f} KB")
        print(f"  Status: {status}")
        print()

        if page_count != 1:
            all_single_page = False

    print("=" * 70)

    if all_single_page:
        print("\nSUCCESS: All PDFs are exactly 1 page!")
    else:
        print("\nISSUE: Some PDFs have multiple pages. More compression needed.")


if __name__ == "__main__":
    main()
