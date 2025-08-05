import pytest
import json
from django.test import TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from documents.models import Document


@pytest.mark.django_db
def test_document_create_read_update_workflow(user, integration_test_content):
    """Test create, read, and update workflow for documents."""
    client = APIClient()
    client.force_authenticate(user=user)

    # CREATE
    create_data = {
        "title": "Integration Test Document",
        "content": integration_test_content,
    }

    create_url = reverse("document-list")
    create_response = client.post(create_url, create_data, format="json")

    assert create_response.status_code == status.HTTP_201_CREATED
    document_id = create_response.data["id"]
    assert create_response.data["version"] == 1

    # READ (List)
    list_response = client.get(create_url)
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data["count"] == 1

    # READ (Detail)
    detail_url = reverse("document-detail", kwargs={"pk": document_id})
    detail_response = client.get(detail_url)

    assert detail_response.status_code == status.HTTP_200_OK
    assert detail_response.data["title"] == "Integration Test Document"
    assert "content" in detail_response.data

    # UPDATE
    update_data = {
        "title": "Updated Integration Test Document",
        "content": "Updated integration test content"
    }

    update_response = client.put(detail_url, update_data, format="json")

    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.data["title"] == "Updated Integration Test Document"
    assert update_response.data["version"] == 2  # Version should increment


@pytest.mark.django_db
def test_anonymous_user_workflow(user, integration_test_content):
    """Test workflow for anonymous users (should fail with authentication required)."""
    client = APIClient()
    
    # Anonymous user cannot create documents (authentication required)
    create_data = {"title": "Anonymous Document", "content": integration_test_content}

    create_url = reverse("document-list")
    create_response = client.post(create_url, create_data, format="json")

    assert create_response.status_code == status.HTTP_401_UNAUTHORIZED

    # Anonymous user cannot read documents (authentication required)
    list_response = client.get(create_url)
    assert list_response.status_code == status.HTTP_401_UNAUTHORIZED

    # Anonymous user cannot read specific document (authentication required)
    # Create a document with authenticated user first
    client.force_authenticate(user=user)
    doc_response = client.post(create_url, create_data, format="json")
    document_id = doc_response.data["id"]
    
    # Remove authentication
    client.force_authenticate(user=None)
    detail_url = reverse("document-detail", kwargs={"pk": document_id})
    detail_response = client.get(detail_url)

    assert detail_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_search_integration(user, search_test_documents):
    """Test search functionality integration."""
    client = APIClient()
    client.force_authenticate(user=user)

    create_url = reverse("document-list")

    # Test search by title
    search_response = client.get(create_url, {"search": "Python"})
    assert search_response.status_code == status.HTTP_200_OK
    assert search_response.data["count"] == 2  # Python Tutorial + Django (Python in content)

    # Test search by content
    search_response = client.get(create_url, {"search": "JavaScript"})
    assert search_response.status_code == status.HTTP_200_OK
    assert search_response.data["count"] == 1

    # Test case-insensitive search
    search_response = client.get(create_url, {"search": "django"})
    assert search_response.status_code == status.HTTP_200_OK
    assert search_response.data["count"] == 1


@pytest.mark.django_db
def test_version_tracking_integration(user, integration_test_content):
    """Test document version tracking across updates."""
    client = APIClient()
    client.force_authenticate(user=user)

    # Create document
    create_data = {"title": "Version Test Document", "content": integration_test_content}

    create_url = reverse("document-list")
    create_response = client.post(create_url, create_data, format="json")

    document_id = create_response.data["id"]
    detail_url = reverse("document-detail", kwargs={"pk": document_id})

    # Initial version should be 1
    assert create_response.data["version"] == 1

    # Update title only
    update_data = {
        "title": "Updated Version Test Document",
        "content": integration_test_content,  # Same content
    }

    update_response = client.put(detail_url, update_data, format="json")
    assert update_response.data["version"] == 2

    # Update content only
    new_content = "Updated content for version tracking"

    update_data = {
        "title": "Updated Version Test Document",  # Same title
        "content": new_content,
    }

    update_response = client.put(detail_url, update_data, format="json")
    assert update_response.data["version"] == 3

    # Update with same data should not increment version
    same_data_response = client.put(detail_url, update_data, format="json")
    assert same_data_response.data["version"] == 3  # Should remain 3


@pytest.mark.django_db
def test_pagination_integration(user, integration_test_content):
    """Test pagination across multiple pages."""
    client = APIClient()
    client.force_authenticate(user=user)

    # Create 25 documents (more than default page size of 20)
    create_url = reverse("document-list")

    for i in range(25):
        doc_data = {"title": f"Document {i:02d}", "content": integration_test_content}
        client.post(create_url, doc_data, format="json")

    # Test first page
    page1_response = client.get(create_url)
    assert page1_response.status_code == status.HTTP_200_OK
    assert page1_response.data["count"] == 25
    assert len(page1_response.data["results"]) == 20
    assert page1_response.data["next"] is not None
    assert page1_response.data["previous"] is None

    # Test second page
    page2_response = client.get(create_url, {"page": 2})
    assert page2_response.status_code == status.HTTP_200_OK
    assert len(page2_response.data["results"]) == 5
    assert page2_response.data["next"] is None
    assert page2_response.data["previous"] is not None


@pytest.mark.django_db
def test_health_check_integration():
    """Test health check endpoint integration."""
    client = APIClient()
    
    health_url = reverse("health_check")
    response = client.get(health_url)

    assert response.status_code == status.HTTP_200_OK

    data = json.loads(response.content)
    assert "status" in data
    assert "database" in data
    assert "redis" in data

    # Should be healthy in test environment
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"


@pytest.mark.django_db
def test_api_root_integration():
    """Test API root endpoint integration."""
    client = APIClient()
    
    api_root_url = reverse("api-root")
    response = client.get(api_root_url)

    assert response.status_code == status.HTTP_200_OK

    data = json.loads(response.content)
    assert "documents" in data
    assert "health" in data

    # Test that returned URLs respond appropriately
    # Documents endpoint requires authentication, so expect 401
    documents_response = client.get(data["documents"])
    assert documents_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Health endpoint should work without authentication
    health_response = client.get(data["health"])
    assert health_response.status_code == status.HTTP_200_OK


@pytest.mark.django_db(transaction=True)
def test_database_transaction_integrity(user):
    """Test database transaction integrity."""
    # Test that document creation is atomic
    document = Document.objects.create(
        title="Transaction Test",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    # Document should exist and have correct attributes
    assert document.id is not None
    assert document.version == 1
    assert document.created_at is not None
    assert document.updated_at is not None


@pytest.mark.django_db(transaction=True)
def test_uuid_uniqueness(user):
    """Test UUID uniqueness across documents."""
    doc1 = Document.objects.create(
        title="Document 1",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    doc2 = Document.objects.create(
        title="Document 2",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    # UUIDs should be different
    assert doc1.id != doc2.id

    # Both should be valid UUIDs
    import uuid

    assert isinstance(doc1.id, uuid.UUID)
    assert isinstance(doc2.id, uuid.UUID)


@pytest.mark.django_db(transaction=True)
def test_cascade_delete_integration(user):
    """Test cascade delete functionality."""
    # Create document
    document = Document.objects.create(
        title="Cascade Test Document",
        content={"type": "doc", "content": []},
        created_by=user,
    )

    document_id = document.id

    # Delete user should cascade delete document
    user.delete()

    # Document should no longer exist
    with pytest.raises(Document.DoesNotExist):
        Document.objects.get(id=document_id)


@pytest.mark.django_db
def test_cache_connectivity():
    """Test that cache is working properly."""
    # Set a value in cache
    cache.set("test_key", "test_value", 30)

    # Retrieve the value
    cached_value = cache.get("test_key")

    assert cached_value == "test_value"

    # Clear the value
    cache.delete("test_key")

    # Should be None now
    cached_value = cache.get("test_key")
    assert cached_value is None


@pytest.mark.django_db
def test_health_check_cache_integration():
    """Test health check cache functionality."""
    client = APIClient()
    
    health_url = reverse("health_check")

    response = client.get(health_url)
    data = json.loads(response.content)

    # Cache should be working
    assert data["redis"] == "connected"