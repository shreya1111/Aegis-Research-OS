"""Unit tests for password hashing and JWT issuance/verification."""

from __future__ import annotations

import uuid
from datetime import timedelta

import jwt as pyjwt
import pytest

from app.core.errors import AuthenticationError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

SECRET = "unit-test-secret-value-of-sufficient-length-32b"


@pytest.mark.unit
def test_hash_password_produces_a_different_string_than_the_input() -> None:
    hashed = hash_password("correct-horse-battery")
    assert hashed != "correct-horse-battery"
    assert hashed.startswith("$2b$")


@pytest.mark.unit
def test_hash_password_uses_a_fresh_salt_each_time() -> None:
    first = hash_password("correct-horse-battery")
    second = hash_password("correct-horse-battery")
    assert first != second


@pytest.mark.unit
def test_verify_password_accepts_the_correct_password() -> None:
    hashed = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", hashed) is True


@pytest.mark.unit
def test_verify_password_rejects_the_wrong_password() -> None:
    hashed = hash_password("correct-horse-battery")
    assert verify_password("wrong-password", hashed) is False


@pytest.mark.unit
def test_verify_password_rejects_a_malformed_hash_without_raising() -> None:
    assert verify_password("anything", "not-a-real-hash") is False


@pytest.mark.unit
def test_access_token_round_trips_through_decode() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(
        user_id, secret=SECRET, expires_delta=timedelta(minutes=5), jti="jti-1"
    )

    payload = decode_token(token, secret=SECRET, expected_type=TokenType.ACCESS)

    assert payload.sub == user_id
    assert payload.type is TokenType.ACCESS
    assert payload.jti == "jti-1"


@pytest.mark.unit
def test_refresh_token_round_trips_through_decode() -> None:
    user_id = uuid.uuid4()
    token = create_refresh_token(
        user_id, secret=SECRET, expires_delta=timedelta(days=1), jti="jti-2"
    )

    payload = decode_token(token, secret=SECRET, expected_type=TokenType.REFRESH)

    assert payload.sub == user_id
    assert payload.type is TokenType.REFRESH


@pytest.mark.unit
def test_access_token_is_rejected_when_verified_as_a_refresh_token() -> None:
    token = create_access_token(
        uuid.uuid4(), secret=SECRET, expires_delta=timedelta(minutes=5), jti="jti-3"
    )

    with pytest.raises(AuthenticationError):
        decode_token(token, secret=SECRET, expected_type=TokenType.REFRESH)


@pytest.mark.unit
def test_refresh_token_is_rejected_when_verified_as_an_access_token() -> None:
    token = create_refresh_token(
        uuid.uuid4(), secret=SECRET, expires_delta=timedelta(days=1), jti="jti-4"
    )

    with pytest.raises(AuthenticationError):
        decode_token(token, secret=SECRET, expected_type=TokenType.ACCESS)


@pytest.mark.unit
def test_expired_token_is_rejected() -> None:
    token = create_access_token(
        uuid.uuid4(), secret=SECRET, expires_delta=timedelta(seconds=-1), jti="jti-5"
    )

    with pytest.raises(AuthenticationError):
        decode_token(token, secret=SECRET, expected_type=TokenType.ACCESS)


@pytest.mark.unit
def test_token_signed_with_a_different_secret_is_rejected() -> None:
    token = create_access_token(
        uuid.uuid4(), secret=SECRET, expires_delta=timedelta(minutes=5), jti="jti-6"
    )

    with pytest.raises(AuthenticationError):
        decode_token(
            token,
            secret="a-different-secret-value-of-sufficient-length",
            expected_type=TokenType.ACCESS,
        )


@pytest.mark.unit
def test_malformed_token_is_rejected() -> None:
    with pytest.raises(AuthenticationError):
        decode_token("not-a-jwt", secret=SECRET, expected_type=TokenType.ACCESS)


@pytest.mark.unit
def test_token_signed_with_an_unexpected_algorithm_is_rejected() -> None:
    """Guards against algorithm-confusion attacks (design §9.2)."""
    forged = pyjwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "jti": "forged"},
        SECRET,
        algorithm="HS512",
    )

    with pytest.raises(AuthenticationError):
        decode_token(forged, secret=SECRET, expected_type=TokenType.ACCESS)
