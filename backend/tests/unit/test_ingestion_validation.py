"""Unit tests for upload validation (design §9.5, FR-C1)."""

from __future__ import annotations

import pytest

from app.core.errors import FileTooLargeError, UnsupportedFileTypeError
from app.services.ingestion.validation import sanitise_filename, validate_upload

ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]


@pytest.mark.unit
class TestSanitiseFilename:
    def test_strips_directory_components(self) -> None:
        assert sanitise_filename("../../etc/passwd") == "passwd"

    def test_strips_windows_style_paths(self) -> None:
        assert sanitise_filename("C:\\Users\\a\\..\\..\\evil.pdf") == "evil.pdf"

    def test_preserves_a_plain_filename(self) -> None:
        assert sanitise_filename("thesis.pdf") == "thesis.pdf"

    def test_falls_back_when_the_result_is_empty(self) -> None:
        assert sanitise_filename("   ") == "upload"


@pytest.mark.unit
class TestValidateUpload:
    def test_accepts_a_valid_pdf(self) -> None:
        mime = validate_upload(
            filename="paper.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            allowed_mime_types=ALLOWED_MIME_TYPES,
            max_size_bytes=10_000,
        )
        assert mime == "application/pdf"

    def test_accepts_a_valid_docx(self) -> None:
        mime = validate_upload(
            filename="paper.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=1024,
            allowed_mime_types=ALLOWED_MIME_TYPES,
            max_size_bytes=10_000,
        )
        assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_accepts_a_generic_octet_stream_content_type(self) -> None:
        """Some clients send a generic content type; the extension is
        authoritative when the browser's hint is not conclusive."""
        mime = validate_upload(
            filename="paper.pdf",
            content_type="application/octet-stream",
            size_bytes=1024,
            allowed_mime_types=ALLOWED_MIME_TYPES,
            max_size_bytes=10_000,
        )
        assert mime == "application/pdf"

    def test_accepts_a_missing_content_type(self) -> None:
        mime = validate_upload(
            filename="paper.pdf",
            content_type=None,
            size_bytes=1024,
            allowed_mime_types=ALLOWED_MIME_TYPES,
            max_size_bytes=10_000,
        )
        assert mime == "application/pdf"

    def test_rejects_an_unsupported_extension(self) -> None:
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload(
                filename="paper.txt",
                content_type="text/plain",
                size_bytes=1024,
                allowed_mime_types=ALLOWED_MIME_TYPES,
                max_size_bytes=10_000,
            )

    def test_rejects_an_extension_not_on_the_allow_list_even_if_recognised(self) -> None:
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload(
                filename="paper.pdf",
                content_type="application/pdf",
                size_bytes=1024,
                allowed_mime_types=[
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ],
                max_size_bytes=10_000,
            )

    def test_rejects_a_mismatched_content_type(self) -> None:
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload(
                filename="paper.pdf",
                content_type="image/png",
                size_bytes=1024,
                allowed_mime_types=ALLOWED_MIME_TYPES,
                max_size_bytes=10_000,
            )

    def test_rejects_a_file_exceeding_the_size_limit(self) -> None:
        with pytest.raises(FileTooLargeError):
            validate_upload(
                filename="paper.pdf",
                content_type="application/pdf",
                size_bytes=20_000,
                allowed_mime_types=ALLOWED_MIME_TYPES,
                max_size_bytes=10_000,
            )

    def test_rejects_an_empty_file(self) -> None:
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload(
                filename="paper.pdf",
                content_type="application/pdf",
                size_bytes=0,
                allowed_mime_types=ALLOWED_MIME_TYPES,
                max_size_bytes=10_000,
            )

    def test_rejects_before_processing_bytes_are_ever_touched(self) -> None:
        """The function never reads file content, only the reported size —
        matching design §8.1: "Reject anything else ... before any bytes are
        processed"."""
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload(
                filename="malicious.exe",
                content_type="application/octet-stream",
                size_bytes=1,
                allowed_mime_types=ALLOWED_MIME_TYPES,
                max_size_bytes=10_000,
            )
