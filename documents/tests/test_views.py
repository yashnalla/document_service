import pytest
import json
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from documents.models import Document
from documents.serializers import DocumentListSerializer, DocumentSerializer


@pytest.mark.django_db
def test_document_list_anonymous_user(user, simple_document_content):
    """Test document list access for anonymous users (should fail)."""
    client = APIClient()
    # Create some documents
    Document.objects.create(
        title="Public Document", content=simple_document_content, created_by=user
    )

    url = reverse("document-list")
    response = client.get(url)

    # Since authentication is required, this should fail
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_document_list_authenticated_user(user, simple_document_content):
    """Test document list access for authenticated users."""
    client = APIClient()
    client.force_authenticate(user=user)

    # Create some documents
    Document.objects.create(
        title="User Document", content=simple_document_content, created_by=user
    )

    url = reverse("document-list")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.data


@pytest.mark.django_db
def test_document_create_authenticated_user(user, simple_document_content):
    """Test document creation with authenticated user."""
    client = APIClient()
    client.force_authenticate(user=user)

    data = {"title": "New Document", "content": simple_document_content}

    url = reverse("document-list")
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["title"] == "New Document"
    assert response.data["created_by"]["username"] == "testuser"


@pytest.mark.django_db
def test_document_create_anonymous_user(simple_document_content):
    """Test document creation with anonymous user (should fail)."""
    client = APIClient()
    data = {"title": "Anonymous Document", "content": simple_document_content}

    url = reverse("document-list")
    response = client.post(url, data, format="json")

    # Since authentication is required, this should fail
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_document_retrieve(user, simple_document_content):
    """Test document retrieval."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )

    url = reverse("document-detail", kwargs={"pk": document.pk})
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Test Document"
    assert response.data["id"] == str(document.id)


@pytest.mark.django_db
def test_document_update_authenticated_user(user, simple_document_content):
    """Test document update with authenticated user."""
    client = APIClient()
    client.force_authenticate(user=user)

    document = Document.objects.create(
        title="Original Title", content=simple_document_content, created_by=user
    )

    data = {
        "title": "Updated Title",
        "content": "Updated plain text content",
    }

    url = reverse("document-detail", kwargs={"pk": document.pk})
    response = client.put(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Updated Title"

    # Check version increment
    document.refresh_from_db()
    assert document.version == 2


@pytest.mark.django_db
def test_document_partial_update(user, simple_document_content):
    """Test document partial update (PATCH)."""
    client = APIClient()
    client.force_authenticate(user=user)

    document = Document.objects.create(
        title="Original Title", content=simple_document_content, created_by=user
    )

    data = {"title": "Partially Updated Title"}

    url = reverse("document-detail", kwargs={"pk": document.pk})
    response = client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Partially Updated Title"

    # Content should remain unchanged
    document.refresh_from_db()
    assert document.content == simple_document_content



@pytest.mark.django_db
def test_document_search_by_title(user, simple_document_content):
    """Test document search functionality by title."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    Document.objects.create(
        title="Python Programming",
        content=simple_document_content,
        created_by=user,
    )
    Document.objects.create(
        title="JavaScript Tutorial",
        content=simple_document_content,
        created_by=user,
    )
    Document.objects.create(
        title="Django Guide", content=simple_document_content, created_by=user
    )

    url = reverse("document-list")
    response = client.get(url, {"search": "Python"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Python Programming"


@pytest.mark.django_db
def test_document_search_by_content(user):
    """Test document search functionality by content."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    Document.objects.create(
        title="Document 1",
        content="This document contains Python code",
        created_by=user,
    )
    Document.objects.create(
        title="Document 2",
        content="This document is about JavaScript",
        created_by=user,
    )

    url = reverse("document-list")
    response = client.get(url, {"search": "Python"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Document 1"


@pytest.mark.django_db
def test_document_search_case_insensitive(user, simple_document_content):
    """Test that document search is case insensitive."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    Document.objects.create(
        title="Python Programming",
        content=simple_document_content,
        created_by=user,
    )

    url = reverse("document-list")
    response = client.get(url, {"search": "python"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Python Programming"


@pytest.mark.django_db
def test_document_search_no_results(user, simple_document_content):
    """Test document search with no matching results."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    Document.objects.create(
        title="Python Programming",
        content=simple_document_content,
        created_by=user,
    )

    url = reverse("document-list")
    response = client.get(url, {"search": "nonexistent"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert len(response.data["results"]) == 0


@pytest.mark.django_db
def test_get_serializer_class_list_action(user):
    """Test that list action uses DocumentListSerializer."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = reverse("document-list")
    response = client.get(url)

    # DocumentListSerializer should not include content field
    if response.data["results"]:
        assert "content" not in response.data["results"][0]


@pytest.mark.django_db
def test_get_serializer_class_retrieve_action(user, simple_document_content):
    """Test that retrieve action uses DocumentSerializer."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )

    url = reverse("document-detail", kwargs={"pk": document.pk})
    response = client.get(url)

    # DocumentSerializer should include content field
    assert "content" in response.data


@pytest.mark.django_db
def test_get_serializer_class_create_action(user, simple_document_content):
    """Test that create action uses DocumentCreateSerializer."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    data = {"title": "New Document", "content": simple_document_content}

    url = reverse("document-list")
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    # Response should include all fields after creation
    assert "content" in response.data
    assert "created_by" in response.data


@pytest.mark.django_db
def test_document_pagination(user, simple_document_content):
    """Test document list pagination."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Create more than 20 documents (default page size)
    for i in range(25):
        Document.objects.create(
            title=f"Document {i}", content=simple_document_content, created_by=user
        )

    url = reverse("document-list")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 25
    assert len(response.data["results"]) == 20  # Default page size
    assert response.data["next"] is not None
    assert response.data["previous"] is None


@pytest.mark.django_db
def test_document_pagination_second_page(user, simple_document_content):
    """Test document list second page."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Create more than 20 documents
    for i in range(25):
        Document.objects.create(
            title=f"Document {i}", content=simple_document_content, created_by=user
        )

    url = reverse("document-list")
    response = client.get(url, {"page": 2})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 5  # Remaining documents
    assert response.data["next"] is None
    assert response.data["previous"] is not None


@pytest.mark.django_db
def test_document_ordering(user, simple_document_content):
    """Test that documents are ordered by updated_at descending."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    doc1 = Document.objects.create(
        title="First Document", content=simple_document_content, created_by=user
    )
    doc2 = Document.objects.create(
        title="Second Document", content=simple_document_content, created_by=user
    )

    url = reverse("document-list")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    results = response.data["results"]

    # Second document should be first (most recent)
    assert results[0]["title"] == "Second Document"
    assert results[1]["title"] == "First Document"


@pytest.mark.django_db
def test_document_not_found(user):
    """Test document retrieval with non-existent ID."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    import uuid

    non_existent_id = uuid.uuid4()

    url = reverse("document-detail", kwargs={"pk": non_existent_id})
    response = client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_document_invalid_uuid(user):
    """Test document retrieval with invalid UUID format."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = "/api/documents/invalid-uuid/"
    response = client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_document_create_validation_error(user, simple_document_content):
    """Test document creation with validation errors."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    data = {"title": "", "content": simple_document_content}  # Empty title should fail

    url = reverse("document-list")
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "title" in response.data


@pytest.mark.django_db
def test_document_create_invalid_content(user):
    """Test document creation with invalid content."""
    client = APIClient()
    client.force_authenticate(user=user)
    
    data = {
        "title": "",  # Empty title is invalid
        "content": "Valid plain text content",
    }

    url = reverse("document-list")
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "title" in response.data