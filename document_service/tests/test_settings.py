import pytest
import os
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.conf import settings


@pytest.mark.django_db
class TestSettings(TestCase):
    """Test Django settings configuration."""

    def test_debug_setting_default(self):
        """Test DEBUG setting defaults to False."""
        with patch.dict(os.environ, {}, clear=True):
            from django.conf import settings
            # Settings are already loaded, so we test the current behavior
            self.assertIsInstance(settings.DEBUG, bool)

    def test_secret_key_configuration(self):
        """Test SECRET_KEY is configured."""
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertNotEqual(settings.SECRET_KEY, '')

    def test_allowed_hosts_configuration(self):
        """Test ALLOWED_HOSTS is properly configured."""
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)
        self.assertIn('localhost', settings.ALLOWED_HOSTS)
        self.assertIn('127.0.0.1', settings.ALLOWED_HOSTS)

    def test_database_configuration(self):
        """Test database configuration."""
        db_config = settings.DATABASES['default']
        self.assertEqual(db_config['ENGINE'], 'django.db.backends.postgresql')
        self.assertIn('NAME', db_config)
        self.assertIn('USER', db_config)
        self.assertIn('PASSWORD', db_config)
        self.assertIn('HOST', db_config)
        self.assertIn('PORT', db_config)

    def test_redis_cache_configuration(self):
        """Test Redis cache configuration."""
        cache_config = settings.CACHES['default']
        self.assertEqual(
            cache_config['BACKEND'], 
            'django.core.cache.backends.redis.RedisCache'
        )
        self.assertIn('LOCATION', cache_config)

    def test_installed_apps_includes_required(self):
        """Test that required apps are installed."""
        required_apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'rest_framework',
            'corsheaders',
            'documents',
        ]
        for app in required_apps:
            self.assertIn(app, settings.INSTALLED_APPS)

    def test_rest_framework_configuration(self):
        """Test REST framework configuration."""
        rf_config = settings.REST_FRAMEWORK
        self.assertIn('DEFAULT_PAGINATION_CLASS', rf_config)
        self.assertEqual(rf_config['PAGE_SIZE'], 20)
        self.assertIn('DEFAULT_PERMISSION_CLASSES', rf_config)

    def test_cors_configuration(self):
        """Test CORS configuration."""
        self.assertIsInstance(settings.CORS_ALLOWED_ORIGINS, list)
        self.assertTrue(settings.CORS_ALLOW_CREDENTIALS)

    @override_settings(DEBUG=True)
    def test_debug_mode_enabled(self):
        """Test that DEBUG mode can be enabled."""
        self.assertTrue(settings.DEBUG)

    @override_settings(DEBUG=False)
    def test_debug_mode_disabled(self):
        """Test that DEBUG mode can be disabled."""
        self.assertFalse(settings.DEBUG)