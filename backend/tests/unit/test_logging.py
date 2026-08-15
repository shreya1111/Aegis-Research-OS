"""Unit tests for the JSON log formatter and correlation context."""

from __future__ import annotations

import json
import logging

import pytest

from app.core.logging import JsonFormatter, request_id_var, run_id_var


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event occurred",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


@pytest.mark.unit
def test_formatter_emits_single_line_json() -> None:
    output = JsonFormatter().format(_record())
    assert "\n" not in output
    payload = json.loads(output)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "event occurred"
    assert "timestamp" in payload


@pytest.mark.unit
def test_formatter_includes_extra_fields() -> None:
    record = _record(event="http.request.completed", status_code=200)
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "http.request.completed"
    assert payload["status_code"] == 200


@pytest.mark.unit
def test_formatter_includes_correlation_ids_when_set() -> None:
    request_token = request_id_var.set("req-1")
    run_token = run_id_var.set("run-1")
    try:
        payload = json.loads(JsonFormatter().format(_record()))
    finally:
        request_id_var.reset(request_token)
        run_id_var.reset(run_token)
    assert payload["request_id"] == "req-1"
    assert payload["run_id"] == "run-1"


@pytest.mark.unit
def test_formatter_omits_correlation_ids_when_unset() -> None:
    payload = json.loads(JsonFormatter().format(_record()))
    assert "request_id" not in payload
    assert "run_id" not in payload
