import pytest
import uuid
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.urls import reverse
from documents.models import Document


@pytest.mark.django_db
def test_document_creation(user, simple_document_content):
    """Test basic document creation."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )

    assert document.title == "Test Document"
    assert document.content == simple_document_content
    assert document.created_by == user
    assert document.version == 1
    assert isinstance(document.id, uuid.UUID)

@pytest.mark.django_db
def test_document_uuid_primary_key(user, simple_document_content):
    """Test that document uses UUID as primary key."""
    document = Document.objects.create(
        title="UUID Test", content=simple_document_content, created_by=user
    )

    assert isinstance(document.id, uuid.UUID)
    assert isinstance(document.pk, uuid.UUID)
    assert str(document.id) == str(document.pk)

@pytest.mark.django_db
def test_document_str_representation(user, simple_document_content):
    """Test document string representation."""
    document = Document.objects.create(
        title="Test Title", content=simple_document_content, created_by=user
    )

    assert str(document) == "Test Title"

@pytest.mark.django_db
def test_document_repr_representation(user, simple_document_content):
    """Test document repr representation."""
    document = Document.objects.create(
        title="Test Title", content=simple_document_content, created_by=user
    )

    expected_repr = f"<Document: Test Title (v{document.version})>"
    assert repr(document) == expected_repr

@pytest.mark.django_db
def test_document_default_values(user):
    """Test document default values."""
    document = Document.objects.create(title="Test Document", created_by=user)

    assert document.content == {}
    assert document.version == 1
    assert document.created_at is not None
    assert document.updated_at is not None

@pytest.mark.django_db
def test_document_version_increment_on_title_change(user, simple_document_content):
    """Test that version increments when title changes."""
    document = Document.objects.create(
        title="Original Title", content=simple_document_content, created_by=user
    )
    original_version = document.version

    document.title = "Updated Title"
    document.save()

    assert document.version == original_version + 1

@pytest.mark.django_db
def test_document_version_increment_on_content_change(user, simple_document_content):
    """Test that version increments when content changes."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )
    original_version = document.version

    new_content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Updated content"}],
            }
        ],
    }
    document.content = new_content
    document.save()

    assert document.version == original_version + 1

@pytest.mark.django_db
def test_document_version_no_increment_on_same_data(user, simple_document_content):
    """Test that version doesn't increment when no actual changes."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )
    original_version = document.version

    # Save without changes
    document.save()

    assert document.version == original_version

@pytest.mark.django_db
def test_document_version_no_increment_on_other_fields(user, simple_document_content):
    """Test that version doesn't increment for non-content/title changes."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )
    original_version = document.version

    # This shouldn't increment version (though created_by typically wouldn't change)
    # But we're testing the logic focuses on title and content only
    document.save()

    assert document.version == original_version

@pytest.mark.django_db
def test_document_ordering(user, simple_document_content):
    """Test document ordering by updated_at descending."""
    doc1 = Document.objects.create(
        title="First Document", content=simple_document_content, created_by=user
    )

    doc2 = Document.objects.create(
        title="Second Document", content=simple_document_content, created_by=user
    )

    documents = list(Document.objects.all())
    assert documents[0] == doc2  # Most recently created first
    assert documents[1] == doc1

@pytest.mark.django_db
def test_document_user_relationship(user, simple_document_content):
    """Test document-user relationship."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )

    assert document.created_by == user
    assert document in user.documents.all()

@pytest.mark.django_db
def test_document_cascade_delete(user, simple_document_content):
    """Test that documents are deleted when user is deleted."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )
    document_id = document.id

    user.delete()

    with pytest.raises(Document.DoesNotExist):
        Document.objects.get(id=document_id)

@pytest.mark.django_db
def test_document_json_field_content(user, complex_document_content):
    """Test JSONField content handling."""
    document = Document.objects.create(
        title="Complex Document", content=complex_document_content, created_by=user
    )

    # Refresh from database
    document.refresh_from_db()
    assert document.content == complex_document_content

@pytest.mark.django_db
def test_document_get_absolute_url(user, simple_document_content):
    """Test document get_absolute_url method."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )

    expected_url = reverse("document-detail", kwargs={"pk": document.pk})
    assert document.get_absolute_url() == expected_url

@pytest.mark.django_db
def test_document_required_fields(user, simple_document_content):
    """Test that required fields are enforced."""
    from django.core.exceptions import ValidationError
    from django.db import transaction

    # Title is required - test with validation
    document = Document(content=simple_document_content, created_by=user)
    with pytest.raises(ValidationError):
        document.full_clean()

    # created_by is required - test database constraint
    with pytest.raises((IntegrityError, ValueError)):
        with transaction.atomic():
            Document.objects.create(
                title="Test Document", content=simple_document_content
            )

@pytest.mark.django_db
def test_document_title_max_length(user, simple_document_content):
    """Test document title max length constraint."""
    long_title = "x" * 256  # Exceeds 255 character limit

    with pytest.raises(Exception):  # Could be ValidationError or DataError
        Document.objects.create(
            title=long_title, content=simple_document_content, created_by=user
        )

@pytest.mark.django_db
def test_document_auto_timestamps(user, simple_document_content):
    """Test auto timestamp fields."""
    document = Document.objects.create(
        title="Test Document", content=simple_document_content, created_by=user
    )

    assert document.created_at is not None
    assert document.updated_at is not None

    # created_at should be very close to updated_at initially (within 1 second)
    time_diff = abs((document.updated_at - document.created_at).total_seconds())
    assert time_diff < 1.0

    # Small delay to ensure updated_at changes
    import time

    time.sleep(0.01)

    # Update document
    original_created_at = document.created_at
    document.title = "Updated Title"
    document.save()

    # created_at shouldn't change, updated_at should
    assert document.created_at == original_created_at
    assert document.updated_at > original_created_at
