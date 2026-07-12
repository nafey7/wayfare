"""Schemas for PDF attachments."""

from datetime import datetime

from pydantic import BaseModel, Field


class PDFMetadata(BaseModel):
    """Metadata for generated PDF."""

    voya_booking_reference: str = Field(..., description="VOYA booking reference")
    external_reference: str | None = Field(
        None, description="FlightLogic booking reference (if available)"
    )
    pdf_type: str = Field(..., description="booking or ticket")
    generated_at: datetime = Field(default_factory=datetime.now)
    file_size_bytes: int = Field(..., description="PDF file size in bytes")
    file_path: str | None = Field(None, description="Path to saved PDF file")


class EmailAttachment(BaseModel):
    """Email attachment data."""

    filename: str = Field(..., description="Attachment filename")
    content: bytes = Field(..., description="File content as bytes")
    content_type: str = Field(default="application/pdf", description="MIME type")
