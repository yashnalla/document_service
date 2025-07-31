import pytest
import uuid
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from documents.models import Document


# User Fixtures
@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser", 
        email="test@example.com", 
        password="testpass123",
        first_name="Test",
        last_name="User"
    )


@pytest.fixture
def admin_user():
    """Create a test admin user."""
    return User.objects.create_superuser(
        username="admin", 
        email="admin@example.com", 
        password="admin123",
        first_name="Admin",
        last_name="User"
    )


@pytest.fixture
def anonymous_user():
    """Get or create the anonymous user for testing."""
    user, created = User.objects.get_or_create(
        username="anonymous",
        defaults={
            "first_name": "Anonymous",
            "last_name": "User",
            "email": "anonymous@example.com",
        },
    )
    return user


# Sample Content Fixtures
@pytest.fixture
def simple_document_content():
    """Simple document content for testing."""
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Simple test content"}],
            }
        ],
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "title": "Test Document",
        "content": {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "This is a test document content."}
                    ],
                }
            ],
        },
    }


@pytest.fixture
def complex_document_content():
    """Complex document content for testing."""
    return {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Main Title"}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "This is a "},
                    {"type": "text", "marks": [{"type": "strong"}], "text": "complex"},
                    {"type": "text", "text": " document with multiple elements."},
                ],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "First item"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Second item"}],
                            }
                        ],
                    },
                ],
            },
        ],
    }


# Document Fixtures
@pytest.fixture
def document(user, sample_document_data):
    """Create a test document."""
    return Document.objects.create(
        title=sample_document_data["title"],
        content=sample_document_data["content"],
        created_by=user,
    )


@pytest.fixture
def multiple_documents(user, anonymous_user):
    """Create multiple test documents for list/search testing."""
    documents = []

    # Document by regular user
    doc1 = Document.objects.create(
        title="Python Programming Guide",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Learn Python programming basics."}
                    ],
                }
            ],
        },
        created_by=user,
    )
    documents.append(doc1)

    # Document by anonymous user
    doc2 = Document.objects.create(
        title="JavaScript Tutorial",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "JavaScript fundamentals and advanced concepts.",
                        }
                    ],
                }
            ],
        },
        created_by=anonymous_user,
    )
    documents.append(doc2)

    # Another document by regular user
    doc3 = Document.objects.create(
        title="Django REST Framework",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Building APIs with Django REST Framework.",
                        }
                    ],
                }
            ],
        },
        created_by=user,
    )
    documents.append(doc3)

    return documents


# API Client Fixtures
@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_authenticated_client(api_client, admin_user):
    """Create an admin authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


# Token Fixtures
@pytest.fixture
def user_token(user):
    """Create an API token for the test user."""
    token, created = Token.objects.get_or_create(user=user)
    return token


@pytest.fixture
def admin_token(admin_user):
    """Create an API token for the admin user."""
    token, created = Token.objects.get_or_create(user=admin_user)
    return token


@pytest.fixture
def token_authenticated_client(api_client, user_token):
    """Create a token authenticated API client."""
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {user_token.key}')
    return api_client


# Factory Fixtures for Bulk Creation
@pytest.fixture
def document_factory(user):
    """Factory for creating test documents."""
    def _create_document(title="Test Document", content=None, created_by=None):
        if content is None:
            content = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Test content"}],
                    }
                ],
            }
        if created_by is None:
            created_by = user
        
        return Document.objects.create(
            title=title,
            content=content,
            created_by=created_by,
        )
    
    return _create_document


@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def _create_user(username=None, email=None, is_superuser=False, **kwargs):
        if username is None:
            username = f"user_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{username}@example.com"
        
        if is_superuser:
            return User.objects.create_superuser(
                username=username,
                email=email,
                password="testpass123",
                **kwargs
            )
        else:
            return User.objects.create_user(
                username=username,
                email=email,
                password="testpass123",
                **kwargs
            )
    
    return _create_user


# Content Fixtures for Different Testing Scenarios
@pytest.fixture
def integration_test_content():
    """Content specifically for integration testing."""
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Integration test content"}],
            }
        ],
    }


@pytest.fixture
def search_test_documents(user, anonymous_user):
    """Create documents specifically for search testing."""
    documents = []
    
    # Python content documents
    doc1 = Document.objects.create(
        title="Python Tutorial",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Learn Python programming language"}
                    ],
                }
            ],
        },
        created_by=user,
    )
    documents.append(doc1)
    
    # JavaScript content documents
    doc2 = Document.objects.create(
        title="JavaScript Guide",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "JavaScript fundamentals and advanced concepts"}
                    ],
                }
            ],
        },
        created_by=user,
    )
    documents.append(doc2)
    
    # Django content (contains Python in content)
    doc3 = Document.objects.create(
        title="Django Framework",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Python web framework for rapid development"}
                    ],
                }
            ],
        },
        created_by=user,
    )
    documents.append(doc3)
    
    return documents