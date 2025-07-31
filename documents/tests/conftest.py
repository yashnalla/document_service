import pytest
import uuid
from django.contrib.auth.models import User
from documents.models import Document


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


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        'title': 'Test Document',
        'content': {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {
                            'type': 'text',
                            'text': 'This is a test document content.'
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def document(user, sample_document_data):
    """Create a test document."""
    return Document.objects.create(
        title=sample_document_data['title'],
        content=sample_document_data['content'],
        created_by=user
    )


@pytest.fixture
def multiple_documents(user, anonymous_user):
    """Create multiple test documents for list/search testing."""
    documents = []
    
    # Document by regular user
    doc1 = Document.objects.create(
        title='Python Programming Guide',
        content={
            'type': 'doc',
            'content': [
                {'type': 'paragraph', 'content': [
                    {'type': 'text', 'text': 'Learn Python programming basics.'}
                ]}
            ]
        },
        created_by=user
    )
    documents.append(doc1)
    
    # Document by anonymous user
    doc2 = Document.objects.create(
        title='JavaScript Tutorial',
        content={
            'type': 'doc',
            'content': [
                {'type': 'paragraph', 'content': [
                    {'type': 'text', 'text': 'JavaScript fundamentals and advanced concepts.'}
                ]}
            ]
        },
        created_by=anonymous_user
    )
    documents.append(doc2)
    
    # Another document by regular user
    doc3 = Document.objects.create(
        title='Django REST Framework',
        content={
            'type': 'doc',
            'content': [
                {'type': 'paragraph', 'content': [
                    {'type': 'text', 'text': 'Building APIs with Django REST Framework.'}
                ]}
            ]
        },
        created_by=user
    )
    documents.append(doc3)
    
    return documents


@pytest.fixture
def complex_document_content():
    """Complex document content for testing."""
    return {
        'type': 'doc',
        'content': [
            {
                'type': 'heading',
                'attrs': {'level': 1},
                'content': [
                    {'type': 'text', 'text': 'Main Title'}
                ]
            },
            {
                'type': 'paragraph',
                'content': [
                    {'type': 'text', 'text': 'This is a '},
                    {'type': 'text', 'marks': [{'type': 'strong'}], 'text': 'complex'},
                    {'type': 'text', 'text': ' document with multiple elements.'}
                ]
            },
            {
                'type': 'bulletList',
                'content': [
                    {
                        'type': 'listItem',
                        'content': [
                            {
                                'type': 'paragraph',
                                'content': [
                                    {'type': 'text', 'text': 'First item'}
                                ]
                            }
                        ]
                    },
                    {
                        'type': 'listItem',
                        'content': [
                            {
                                'type': 'paragraph',
                                'content': [
                                    {'type': 'text', 'text': 'Second item'}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }