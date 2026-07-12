"""Email attachments package."""

from .pdf_generator import FlightPDFGenerator
from .schemas import EmailAttachment, PDFMetadata

__all__ = [
    "EmailAttachment",
    "FlightPDFGenerator",
    "PDFMetadata",
]
