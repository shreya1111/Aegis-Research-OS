"""Unit tests for typed settings behaviour."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


@pytest.mark.unit
def test_cors_origins_accepts_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://a.test, http://b.test")
    assert settings.cors_origins == ["http://a.test", "http://b.test"]


@pytest.mark.unit
def test_cors_origins_accepts_list() -> None:
    settings = Settings(cors_origins=["http://a.test"])
    assert settings.cors_origins == ["http://a.test"]


@pytest.mark.unit
def test_log_level_is_normalised_to_upper_case() -> None:
    settings = Settings(log_level="debug")
    assert settings.log_level == "DEBUG"


@pytest.mark.unit
def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="qa")


@pytest.mark.unit
def test_docs_are_disabled_in_production() -> None:
    assert (
        Settings(environment="production", jwt_secret="a-real-production-secret-value").docs_enabled
        is False
    )
    assert Settings(environment="development").docs_enabled is True


@pytest.mark.unit
def test_production_rejects_the_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production")


@pytest.mark.unit
def test_production_accepts_a_custom_jwt_secret() -> None:
    settings = Settings(environment="production", jwt_secret="a-real-production-secret-value")
    assert settings.jwt_secret == "a-real-production-secret-value"


@pytest.mark.unit
def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()
