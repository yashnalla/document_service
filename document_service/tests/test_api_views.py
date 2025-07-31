import pytest
import json
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_api_root_response():
    """Test API root endpoint returns correct structure."""
    client = Client()
    url = reverse("api-root")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content)
    expected_keys = ["documents", "admin", "health"]

    for key in expected_keys:
        assert key in data
        assert isinstance(data[key], str)
        assert data[key].startswith("http")


@pytest.mark.django_db
def test_api_root_links_validity(user):
    """Test that API root returns valid URLs."""
    client = Client()
    api_client = APIClient()
    
    url = reverse("api-root")
    response = client.get(url)
    data = json.loads(response.content)

    # Test that documents link works with authentication
    api_client.force_authenticate(user=user)
    documents_response = api_client.get(data["documents"])
    assert documents_response.status_code == 200

    # Test that health link works
    health_response = client.get(data["health"])
    assert health_response.status_code == 200


@pytest.mark.django_db
def test_api_docs_response():
    """Test API documentation endpoint returns correct structure."""
    client = Client()
    url = reverse("api-docs")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content)
    expected_keys = [
        "title",
        "version",
        "description",
        "endpoints",
        "authentication",
        "permissions",
        "pagination",
        "search",
    ]

    for key in expected_keys:
        assert key in data


@pytest.mark.django_db
def test_api_docs_endpoints_documentation():
    """Test that API docs include all documented endpoints."""
    client = Client()
    url = reverse("api-docs")
    response = client.get(url)
    data = json.loads(response.content)

    endpoints = data["endpoints"]
    expected_endpoints = [
        "GET /api/",
        "GET /api/documents/",
        "POST /api/documents/",
        "GET /api/documents/{id}/",
        "PUT /api/documents/{id}/",
        "PATCH /api/documents/{id}/",
        "DELETE /api/documents/{id}/",
        "GET /health/",
    ]

    for endpoint in expected_endpoints:
        assert endpoint in endpoints


@pytest.mark.django_db
def test_api_docs_metadata():
    """Test API documentation metadata."""
    client = Client()
    url = reverse("api-docs")
    response = client.get(url)
    data = json.loads(response.content)

    assert data["title"] == "Document Service API"
    assert data["version"] == "1.0.0"
    assert "Lexical editor" in data["description"]
    assert data["pagination"] == "Page-based pagination with 20 items per page"


@pytest.mark.django_db
def test_api_root_url_resolution():
    """Test API root URL resolution."""
    url = reverse("api-root")
    assert url == "/api/"


@pytest.mark.django_db
def test_api_docs_url_resolution():
    """Test API docs URL resolution."""
    url = reverse("api-docs")
    assert url == "/api/docs/"


@pytest.mark.django_db
def test_api_root_accepts_get_only():
    """Test API root accepts GET requests."""
    client = Client()
    url = reverse("api-root")

    # GET should work
    response = client.get(url)
    assert response.status_code == 200

    # POST should not work (view is decorated with @api_view(['GET']))
    response = client.post(url)
    # Could be 405 (Method Not Allowed) or 403 (Forbidden due to CSRF)
    assert response.status_code in [403, 405]


@pytest.mark.django_db
def test_api_docs_accepts_get_only():
    """Test API docs accepts GET requests."""
    client = Client()
    url = reverse("api-docs")

    # GET should work
    response = client.get(url)
    assert response.status_code == 200

    # POST should not work (view is decorated with @api_view(['GET']))
    response = client.post(url)
    # Could be 405 (Method Not Allowed) or 403 (Forbidden due to CSRF)
    assert response.status_code in [403, 405]


@pytest.mark.django_db
def test_api_root_with_authentication(user):
    """Test API root works with authenticated user."""
    client = Client()
    # Use the user fixture
    client.force_login(user)

    url = reverse("api-root")
    response = client.get(url)

    assert response.status_code == 200
    data = json.loads(response.content)
    assert "documents" in data


@pytest.mark.django_db
def test_api_docs_content_accuracy():
    """Test that API docs content matches actual implementation."""
    client = Client()
    url = reverse("api-docs")
    response = client.get(url)
    data = json.loads(response.content)

    # Check authentication description
    assert "Token-based" in data["authentication"]

    # Check permissions description
    assert "Authentication required" in data["permissions"]

    # Check search functionality
    assert "?search=query" in data["search"]