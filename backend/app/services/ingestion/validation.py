"""Upload validation (design §9.5, FR-C1).

Extension and MIME are both checked against the allow-list before any bytes
are processed (design §8.1). Filenames are sanitised to prevent path traversal
(design §9.5).
"""

from __future__ import annotations

import os

from app.core.errors import FileTooLargeError, UnsupportedFileTypeError

#: Extension → canonical MIME type, restricted to the Phase 3 allow-list
#: (design FR-C1: "accepts PDF and DOCX. Other types are rejected").
_EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def sanitise_filename(filename: str) -> str:
    """Strip any directory component, preventing path traversal (design §9.5).

    Only the base name is ever stored or used on disk; a value like
    ``"../../etc/passwd"`` becomes ``"passwd"``.
    """
    return os.path.basename(filename).strip() or "upload"


def validate_upload(
    *,
    filename: str,
    content_type: str | None,
    size_bytes: int,
    allowed_mime_types: list[str],
    max_size_bytes: int,
) -> str:
    """Validate an upload against the allow-list and size limit.

    Returns the canonical MIME type to store. Raises before any parsing is
    attempted (design §8.1: "Reject anything else with a clear error before
    any bytes are processed").

    Raises
    ------
    UnsupportedFileTypeError
        If the extension is not recognised or the MIME type is not allowed.
    FileTooLargeError
        If the upload exceeds ``max_size_bytes``.
    """
    _, extension = os.path.splitext(filename.lower())
    canonical_mime = _EXTENSION_TO_MIME.get(extension)

    if canonical_mime is None or canonical_mime not in allowed_mime_types:
        raise UnsupportedFileTypeError("Only PDF and DOCX files are supported.")

    # A browser-supplied Content-Type is advisory; only reject when it is
    # present and unambiguously wrong, rather than trusting it as the sole
    # gate (design §9.5: "extension AND MIME allow-list").
    if content_type and content_type not in (canonical_mime, "application/octet-stream"):
        raise UnsupportedFileTypeError("Only PDF and DOCX files are supported.")

    if size_bytes > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise FileTooLargeError(f"Files must be {max_mb} MB or smaller.")

    if size_bytes == 0:
        raise UnsupportedFileTypeError("The uploaded file is empty.")

    return canonical_mime
