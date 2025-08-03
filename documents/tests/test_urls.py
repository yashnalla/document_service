import pytest
from django.test import Client
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient
from documents.views import DocumentViewSet
from documents.models import Document


@pytest.mark.django_db
def test_document_list_url_name():
    """Test document list URL name resolution."""
    url = reverse("document-list")
    assert url == "/api/documents/"


@pytest.mark.django_db
def test_document_detail_url_name(user):
    """Test document detail URL name resolution."""
    document = Document.objects.create(
        title="Test Document",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    url = reverse("document-detail", kwargs={"pk": document.pk})
    assert url == f"/api/documents/{document.pk}/"


@pytest.mark.django_db
def test_document_list_url_resolves():
    """Test that document list URL resolves to correct view."""
    url = "/api/documents/"
    resolved = resolve(url)

    assert resolved.func.cls == DocumentViewSet
    assert resolved.url_name == "document-list"


@pytest.mark.django_db
def test_document_detail_url_resolves(user):
    """Test that document detail URL resolves to correct view."""
    document = Document.objects.create(
        title="Test Document",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    url = f"/api/documents/{document.pk}/"
    resolved = resolve(url)

    assert resolved.func.cls == DocumentViewSet
    assert resolved.url_name == "document-detail"
    assert resolved.kwargs["pk"] == str(document.pk)


@pytest.mark.django_db
def test_router_configuration():
    """Test that router is configured correctly."""
    from api.urls import router

    assert isinstance(router, DefaultRouter)

    # Check registered routes
    urls = router.get_urls()
    url_names = [url.name for url in urls]

    expected_names = ["document-list", "document-detail"]
    for name in expected_names:
        assert name in url_names


@pytest.mark.django_db
def test_document_list_url_methods():
    """Test document list URL supports correct HTTP methods."""
    client = Client()

    url = reverse("document-list")

    # GET should work
    response = client.get(url)
    assert response.status_code in [200, 401]  # 200 OK or 401 if auth required

    # POST should work
    response = client.post(url, {}, content_type="application/json")
    assert response.status_code != 405  # Not Method Not Allowed


@pytest.mark.django_db
def test_document_detail_url_methods(user):
    """Test document detail URL supports correct HTTP methods."""
    client = Client()

    document = Document.objects.create(
        title="Test Document",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    url = reverse("document-detail", kwargs={"pk": document.pk})

    # GET should work with authentication
    response = client.get(url)
    assert response.status_code == 401  # Requires authentication

    # PUT should work (might require auth)
    response = client.put(url, {}, content_type="application/json")
    assert response.status_code != 405  # Not Method Not Allowed

    # DELETE should work (might require auth)
    response = client.delete(url)
    assert response.status_code != 405  # Not Method Not Allowed


@pytest.mark.django_db
def test_invalid_uuid_url(user):
    """Test URL with invalid UUID format."""
    client = APIClient()
    client.force_authenticate(user=user)

    url = "/api/documents/invalid-uuid/"
    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_document_url(user):
    """Test URL with non-existent but valid UUID."""
    import uuid
    
    client = APIClient()
    client.force_authenticate(user=user)

    nonexistent_id = uuid.uuid4()
    url = f"/api/documents/{nonexistent_id}/"
    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_url_patterns_include():
    """Test that URL patterns are properly included."""
    from documents.urls import urlpatterns

    # Should have 3 patterns: web routes only (API moved to api/urls.py)
    assert len(urlpatterns) == 3

    # Check that web routes are present
    pattern_strings = [str(pattern.pattern) for pattern in urlpatterns]
    assert "" in pattern_strings  # document_list
    assert "create/" in pattern_strings  # document_create


@pytest.mark.django_db
def test_api_namespace(user):
    """Test that documents are under /api/ namespace."""
    url = reverse("document-list")
    assert url == "/api/documents/"

    document = Document.objects.create(
        title="Test Document",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    detail_url = reverse("document-detail", kwargs={"pk": document.pk})
    assert detail_url == f"/api/documents/{document.pk}/"


@pytest.mark.django_db
def test_trailing_slash_consistency(user):
    """Test that URLs have consistent trailing slash behavior."""
    # List URL should have trailing slash
    list_url = reverse("document-list")
    assert list_url.endswith("/")

    # Detail URL should have trailing slash
    document = Document.objects.create(
        title="Test Document",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    detail_url = reverse("document-detail", kwargs={"pk": document.pk})
    assert detail_url.endswith("/")


@pytest.mark.django_db
def test_router_basename():
    """Test router basename configuration."""
    from api.urls import router

    # Get the registered routes
    registry = router.registry

    # Find documents registration
    documents_registration = None
    for prefix, viewset, basename in registry:
        if prefix == "documents":
            documents_registration = (prefix, viewset, basename)
            break

    assert documents_registration is not None
    assert documents_registration[0] == "documents"
    assert documents_registration[1] == DocumentViewSet
    # basename should be 'document' (singular)
    assert documents_registration[2] == "document"