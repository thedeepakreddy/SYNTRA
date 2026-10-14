"""Unit tests verifying Pydantic runtime configuration validation and security guards."""

import pytest
from pydantic import ValidationError

from syntra.core.config import Settings


@pytest.mark.unit
def test_valid_development_configuration():
    """Verify standard development settings instantiate cleanly."""
    settings = Settings(
        environment="development",
        dev_auth_enabled=True,
        database_url="sqlite+aiosqlite:///./test.db",
    )
    assert settings.environment == "development"
    assert settings.dev_auth_enabled is True


@pytest.mark.unit
def test_production_disallows_dev_auth():
    """Verify that development authentication is strictly rejected in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            dev_auth_enabled=True,
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        )
    assert "Development authentication (dev_auth_enabled=True) cannot be enabled in production environment." in str(
        exc_info.value
    )


@pytest.mark.unit
def test_production_disallows_sqlite():
    """Verify that SQLite is rejected in production environment."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            dev_auth_enabled=False,
            database_url="sqlite+aiosqlite:///./prod.db",
        )
    assert "SQLite database is not permitted in production environment." in str(exc_info.value)


@pytest.mark.unit
def test_valid_production_configuration():
    """Verify production settings instantiate when invariants are satisfied."""
    settings = Settings(
        environment="production",
        dev_auth_enabled=False,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/prod_db",
    )
    assert settings.environment == "production"
    assert settings.dev_auth_enabled is False
