import pytest
from django.test import RequestFactory
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError
from documents.models import Document
from documents.serializers import (
    UserSerializer,
    DocumentListSerializer,
    DocumentSerializer,
    DocumentCreateSerializer,
)


@pytest.mark.django_db
def test_user_serializer_fields(user):
    """Test UserSerializer includes correct fields."""
    serializer = UserSerializer(user)
    data = serializer.data

    expected_fields = ["id", "username", "first_name", "last_name"]
    for field in expected_fields:
        assert field in data

    # Email should not be included
    assert "email" not in data
    assert "password" not in data


@pytest.mark.django_db
def test_user_serializer_data(user):
    """Test UserSerializer returns correct data."""
    serializer = UserSerializer(user)
    data = serializer.data

    assert data["username"] == "testuser"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["id"] == user.id


@pytest.mark.django_db
def test_document_list_serializer_fields(document):
    """Test DocumentListSerializer includes correct fields."""
    serializer = DocumentListSerializer(document)
    data = serializer.data

    expected_fields = [
        "id",
        "title",
        "version",
        "created_at",
        "updated_at",
        "created_by",
    ]
    for field in expected_fields:
        assert field in data

    # Content should not be included in list serializer
    assert "content" not in data


@pytest.mark.django_db
def test_document_list_serializer_nested_user(document):
    """Test DocumentListSerializer includes nested user data."""
    serializer = DocumentListSerializer(document)
    data = serializer.data

    assert "created_by" in data
    assert isinstance(data["created_by"], dict)
    assert "username" in data["created_by"]
    assert data["created_by"]["username"] == "testuser"


@pytest.mark.django_db
def test_document_list_serializer_read_only_fields():
    """Test DocumentListSerializer read-only fields."""
    serializer = DocumentListSerializer()
    read_only_fields = serializer.Meta.read_only_fields

    expected_read_only = ["id", "version", "created_at", "updated_at", "created_by"]
    for field in expected_read_only:
        assert field in read_only_fields


@pytest.mark.django_db
def test_document_serializer_fields(document):
    """Test DocumentSerializer includes all fields."""
    serializer = DocumentSerializer(document)
    data = serializer.data

    expected_fields = [
        "id",
        "title",
        "content",
        "version",
        "created_at",
        "updated_at",
        "created_by",
    ]
    for field in expected_fields:
        assert field in data


@pytest.mark.django_db
def test_document_serializer_content_included(document):
    """Test DocumentSerializer includes content field."""
    serializer = DocumentSerializer(document)
    data = serializer.data

    assert "content" in data
    assert data["content"] == document.content


@pytest.mark.django_db
def test_document_serializer_content_validation_valid():
    """Test DocumentSerializer content validation with valid data."""
    serializer = DocumentSerializer()
    valid_content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Valid content"}],
            }
        ],
    }

    # Should not raise exception
    validated_content = serializer.validate_content(valid_content)
    assert validated_content == valid_content


@pytest.mark.django_db
def test_document_serializer_content_validation_invalid():
    """Test DocumentSerializer content validation with invalid data."""
    serializer = DocumentSerializer()

    # String instead of dict
    with pytest.raises(ValidationError):
        serializer.validate_content("invalid content")

    # Number instead of dict
    with pytest.raises(ValidationError):
        serializer.validate_content(123)

    # List instead of dict
    with pytest.raises(ValidationError):
        serializer.validate_content(["invalid"])


@pytest.mark.django_db
def test_document_create_serializer_fields():
    """Test DocumentCreateSerializer includes only necessary fields."""
    serializer = DocumentCreateSerializer()
    fields = serializer.fields.keys()

    expected_fields = ["title", "content"]
    for field in expected_fields:
        assert field in fields

    # Should not include read-only fields
    unexpected_fields = ["id", "version", "created_at", "updated_at", "created_by"]
    for field in unexpected_fields:
        assert field not in fields


@pytest.mark.django_db
def test_document_create_serializer_title_validation_valid():
    """Test title validation with valid data."""
    serializer = DocumentCreateSerializer()

    # Valid title
    valid_title = serializer.validate_title("Valid Title")
    assert valid_title == "Valid Title"

    # Title with whitespace should be stripped
    valid_title = serializer.validate_title("  Valid Title  ")
    assert valid_title == "Valid Title"


@pytest.mark.django_db
def test_document_create_serializer_title_validation_invalid():
    """Test title validation with invalid data."""
    serializer = DocumentCreateSerializer()

    # Empty title
    with pytest.raises(ValidationError):
        serializer.validate_title("")

    # Whitespace only
    with pytest.raises(ValidationError):
        serializer.validate_title("   ")

    # Too long title
    long_title = "x" * 256
    with pytest.raises(ValidationError):
        serializer.validate_title(long_title)


@pytest.mark.django_db
def test_document_create_serializer_content_validation():
    """Test content validation in create serializer."""
    serializer = DocumentCreateSerializer()

    # Valid content
    valid_content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Valid content"}],
            }
        ],
    }
    validated_content = serializer.validate_content(valid_content)
    assert validated_content == valid_content

    # Invalid content
    with pytest.raises(ValidationError):
        serializer.validate_content("invalid")


@pytest.mark.django_db
def test_document_create_authenticated_user(user):
    """Test document creation with authenticated user."""
    factory = RequestFactory()
    request = factory.post("/api/documents/")
    request.user = user

    serializer = DocumentCreateSerializer(context={"request": request})
    validated_data = {
        "title": "Test Document",
        "content": {"type": "doc", "content": []},
    }

    document = serializer.create(validated_data)

    assert document.title == "Test Document"
    assert document.created_by == user


@pytest.mark.django_db
def test_document_create_anonymous_user():
    """Test document creation with anonymous user."""
    from django.contrib.auth.models import AnonymousUser

    factory = RequestFactory()
    request = factory.post("/api/documents/")
    request.user = AnonymousUser()

    serializer = DocumentCreateSerializer(context={"request": request})
    validated_data = {
        "title": "Anonymous Document",
        "content": {"type": "doc", "content": []},
    }

    document = serializer.create(validated_data)

    assert document.title == "Anonymous Document"
    assert document.created_by.username == "anonymous"
    assert document.created_by.first_name == "Anonymous"
    assert document.created_by.last_name == "User"


@pytest.mark.django_db
def test_document_create_anonymous_user_reuse(anonymous_user):
    """Test that anonymous user is reused, not recreated."""
    from django.contrib.auth.models import AnonymousUser

    factory = RequestFactory()
    request = factory.post("/api/documents/")
    request.user = AnonymousUser()

    serializer = DocumentCreateSerializer(context={"request": request})
    validated_data = {
        "title": "Anonymous Document",
        "content": {"type": "doc", "content": []},
    }

    document = serializer.create(validated_data)

    # Should reuse existing anonymous user
    assert document.created_by == anonymous_user

    # Should not create duplicate anonymous users
    anonymous_users = User.objects.filter(username="anonymous")
    assert anonymous_users.count() == 1


@pytest.mark.django_db
def test_document_create_serializer_full_flow(user):
    """Test full serialization and creation flow."""
    factory = RequestFactory()
    request = factory.post("/api/documents/")
    request.user = user

    data = {
        "title": "  Test Document  ",  # With whitespace
        "content": {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Test content"}],
                }
            ],
        },
    }

    serializer = DocumentCreateSerializer(data=data, context={"request": request})
    assert serializer.is_valid()

    document = serializer.save()

    assert document.title == "Test Document"  # Whitespace stripped
    assert document.content == data["content"]
    assert document.created_by == user
    assert document.version == 1