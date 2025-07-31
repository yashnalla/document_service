import pytest
import os
from django.contrib.auth.models import User


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user():
    """Create a test admin user."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )


@pytest.fixture
def anonymous_user():
    """Get or create the anonymous user for testing."""
    user, created = User.objects.get_or_create(
        username='anonymous',
        defaults={
            'first_name': 'Anonymous',
            'last_name': 'User',
            'email': 'anonymous@example.com'
        }
    )
    return user