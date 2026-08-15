"""Unit tests for the uniform response envelope and error mapping."""

from __future__ import annotations

import json

import pytest

from app.core.envelope import fail, fail_from, ok, paginated
from app.core.errors import ConflictError, ErrorCode, NotFoundError


@pytest.mark.unit
def test_ok_wraps_payload_with_no_error() -> None:
    response = ok({"id": 1})
    assert response.success is True
    assert response.data == {"id": 1}
    assert response.error is None


@pytest.mark.unit
def test_paginated_exposes_items_and_total() -> None:
    response = paginated(["a", "b"], total=7, page=2, page_size=2)
    assert response.data is not None
    assert response.data.items == ["a", "b"]
    assert response.data.total == 7
    assert response.data.page == 2


@pytest.mark.unit
def test_fail_produces_error_envelope_with_null_data() -> None:
    response = fail(ErrorCode.VALIDATION_ERROR, "bad input", status_code=422)
    body = json.loads(bytes(response.body))
    assert response.status_code == 422
    assert body == {
        "success": False,
        "data": None,
        "error": {"code": "VALIDATION_ERROR", "message": "bad input"},
    }


@pytest.mark.unit
def test_fail_from_uses_exception_code_and_status() -> None:
    response = fail_from(NotFoundError())
    body = json.loads(bytes(response.body))
    assert response.status_code == 404
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.unit
def test_domain_error_accepts_custom_message_and_private_context() -> None:
    error = ConflictError("Email already registered.", context={"email_hash": "abc123"})
    assert error.status_code == 409
    assert error.code is ErrorCode.CONFLICT
    assert error.message == "Email already registered."
    # Context is for logs only and must never reach the client payload.
    assert "email_hash" not in json.loads(bytes(fail_from(error).body))["error"]
