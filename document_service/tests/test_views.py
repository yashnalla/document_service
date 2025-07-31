import pytest
import json
from unittest.mock import patch, MagicMock
from django.test import Client
from django.urls import reverse
from django.db import connection
from django.core.cache import cache


@pytest.mark.django_db
def test_health_check_success():
    """Test health check returns success when all services are healthy."""
    client = Client()
    health_url = reverse("health_check")
    response = client.get(health_url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content)
    assert "status" in data
    assert "database" in data
    assert "redis" in data


@pytest.mark.django_db
def test_health_check_healthy_response_structure():
    """Test that healthy response has correct structure."""
    client = Client()
    health_url = reverse("health_check")
    response = client.get(health_url)
    data = json.loads(response.content)

    expected_keys = ["status", "database", "redis"]
    for key in expected_keys:
        assert key in data

    # Status should be either 'healthy' or 'unhealthy'
    assert data["status"] in ["healthy", "unhealthy"]


@pytest.mark.django_db
@patch("django.db.connection.cursor")
def test_health_check_database_error(mock_cursor):
    """Test health check handles database connection errors."""
    client = Client()
    mock_cursor.side_effect = Exception("Database connection failed")

    health_url = reverse("health_check")
    response = client.get(health_url)
    data = json.loads(response.content)

    assert data["status"] == "unhealthy"
    assert "error" in data["database"]
    assert "Database connection failed" in data["database"]


@pytest.mark.django_db
@patch("django.core.cache.cache.set")
def test_health_check_redis_error(mock_cache_set):
    """Test health check handles Redis connection errors."""
    client = Client()
    mock_cache_set.side_effect = Exception("Redis connection failed")

    health_url = reverse("health_check")
    response = client.get(health_url)
    data = json.loads(response.content)

    assert data["status"] == "unhealthy"
    assert "error" in data["redis"]
    assert "Redis connection failed" in data["redis"]


@pytest.mark.django_db
@patch("django.core.cache.cache.set")
@patch("django.db.connection.cursor")
def test_health_check_both_services_fail(mock_cursor, mock_cache_set):
    """Test health check when both database and Redis fail."""
    client = Client()
    mock_cursor.side_effect = Exception("DB error")
    mock_cache_set.side_effect = Exception("Redis error")

    health_url = reverse("health_check")
    response = client.get(health_url)
    data = json.loads(response.content)

    assert data["status"] == "unhealthy"
    assert "error" in data["database"]
    assert "error" in data["redis"]


@pytest.mark.django_db
def test_health_check_database_connectivity():
    """Test that health check actually tests database connectivity."""
    client = Client()
    health_url = reverse("health_check")
    response = client.get(health_url)
    data = json.loads(response.content)

    # If we're here, database should be connected
    assert data["database"] == "connected"


@pytest.mark.django_db
def test_health_check_redis_connectivity():
    """Test that health check actually tests Redis connectivity."""
    client = Client()
    health_url = reverse("health_check")
    response = client.get(health_url)
    data = json.loads(response.content)

    # Test that cache operations work
    cache.set("test_key", "test_value", 10)
    assert cache.get("test_key") == "test_value"

    # Redis should be connected if cache operations work
    assert data["redis"] == "connected"


@pytest.mark.django_db
def test_health_check_url_resolution():
    """Test that health check URL resolves correctly."""
    url = reverse("health_check")
    assert url == "/health/"


@pytest.mark.django_db
def test_health_check_http_methods():
    """Test health check endpoint accepts GET requests."""
    client = Client()
    health_url = reverse("health_check")
    
    # GET should work
    response = client.get(health_url)
    assert response.status_code == 200

    # POST should also work (no method restriction in view)
    response = client.post(health_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_check_json_response():
    """Test that response is valid JSON."""
    client = Client()
    health_url = reverse("health_check")
    response = client.get(health_url)

    try:
        data = json.loads(response.content)
        assert isinstance(data, dict)
    except json.JSONDecodeError:
        pytest.fail("Response is not valid JSON")