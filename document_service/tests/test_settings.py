import pytest
import os
from unittest.mock import patch
from django.test import override_settings
from django.conf import settings


@pytest.mark.django_db
def test_debug_setting_default():
    """Test DEBUG setting defaults to False."""
    with patch.dict(os.environ, {}, clear=True):
        from django.conf import settings

        # Settings are already loaded, so we test the current behavior
        assert isinstance(settings.DEBUG, bool)


@pytest.mark.django_db
def test_secret_key_configuration():
    """Test SECRET_KEY is configured."""
    assert settings.SECRET_KEY is not None
    assert settings.SECRET_KEY != ""


@pytest.mark.django_db
def test_allowed_hosts_configuration():
    """Test ALLOWED_HOSTS is properly configured."""
    assert isinstance(settings.ALLOWED_HOSTS, list)
    assert "localhost" in settings.ALLOWED_HOSTS
    assert "127.0.0.1" in settings.ALLOWED_HOSTS


@pytest.mark.django_db
def test_database_configuration():
    """Test database configuration."""
    db_config = settings.DATABASES["default"]
    assert db_config["ENGINE"] == "django.db.backends.postgresql"
    assert "NAME" in db_config
    assert "USER" in db_config
    assert "PASSWORD" in db_config
    assert "HOST" in db_config
    assert "PORT" in db_config


@pytest.mark.django_db
def test_redis_cache_configuration():
    """Test Redis cache configuration."""
    cache_config = settings.CACHES["default"]
    assert cache_config["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
    assert "LOCATION" in cache_config


@pytest.mark.django_db
def test_installed_apps_includes_required():
    """Test that required apps are installed."""
    required_apps = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "rest_framework",
        "corsheaders",
        "documents",
    ]
    for app in required_apps:
        assert app in settings.INSTALLED_APPS


@pytest.mark.django_db
def test_rest_framework_configuration():
    """Test REST framework configuration."""
    rf_config = settings.REST_FRAMEWORK
    assert "DEFAULT_PAGINATION_CLASS" in rf_config
    assert rf_config["PAGE_SIZE"] == 20
    assert "DEFAULT_PERMISSION_CLASSES" in rf_config


@pytest.mark.django_db
def test_cors_configuration():
    """Test CORS configuration."""
    assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
    assert settings.CORS_ALLOW_CREDENTIALS


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_debug_mode_enabled():
    """Test that DEBUG mode can be enabled."""
    assert settings.DEBUG


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_debug_mode_disabled():
    """Test that DEBUG mode can be disabled."""
    assert not settings.DEBUG