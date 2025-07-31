import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError
from documents.models import Document
from documents.serializers import (
    UserSerializer,
    DocumentListSerializer,
    DocumentSerializer,
    DocumentCreateSerializer
)


@pytest.mark.django_db
class TestUserSerializer(TestCase):
    """Test UserSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_user_serializer_fields(self):
        """Test UserSerializer includes correct fields."""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        expected_fields = ['id', 'username', 'first_name', 'last_name']
        for field in expected_fields:
            self.assertIn(field, data)
        
        # Email should not be included
        self.assertNotIn('email', data)
        self.assertNotIn('password', data)

    def test_user_serializer_data(self):
        """Test UserSerializer returns correct data."""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['id'], self.user.id)


@pytest.mark.django_db
class TestDocumentListSerializer(TestCase):
    """Test DocumentListSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.document = Document.objects.create(
            title='Test Document',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )

    def test_document_list_serializer_fields(self):
        """Test DocumentListSerializer includes correct fields."""
        serializer = DocumentListSerializer(self.document)
        data = serializer.data
        
        expected_fields = [
            'id', 'title', 'version', 'created_at', 
            'updated_at', 'created_by'
        ]
        for field in expected_fields:
            self.assertIn(field, data)
        
        # Content should not be included in list serializer
        self.assertNotIn('content', data)

    def test_document_list_serializer_nested_user(self):
        """Test DocumentListSerializer includes nested user data."""
        serializer = DocumentListSerializer(self.document)
        data = serializer.data
        
        self.assertIn('created_by', data)
        self.assertIsInstance(data['created_by'], dict)
        self.assertIn('username', data['created_by'])
        self.assertEqual(data['created_by']['username'], 'testuser')

    def test_document_list_serializer_read_only_fields(self):
        """Test DocumentListSerializer read-only fields."""
        serializer = DocumentListSerializer()
        read_only_fields = serializer.Meta.read_only_fields
        
        expected_read_only = [
            'id', 'version', 'created_at', 'updated_at', 'created_by'
        ]
        for field in expected_read_only:
            self.assertIn(field, read_only_fields)


@pytest.mark.django_db
class TestDocumentSerializer(TestCase):
    """Test DocumentSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.document = Document.objects.create(
            title='Test Document',
            content={
                'type': 'doc',
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {'type': 'text', 'text': 'Test content'}
                        ]
                    }
                ]
            },
            created_by=self.user
        )

    def test_document_serializer_fields(self):
        """Test DocumentSerializer includes all fields."""
        serializer = DocumentSerializer(self.document)
        data = serializer.data
        
        expected_fields = [
            'id', 'title', 'content', 'version', 
            'created_at', 'updated_at', 'created_by'
        ]
        for field in expected_fields:
            self.assertIn(field, data)

    def test_document_serializer_content_included(self):
        """Test DocumentSerializer includes content field."""
        serializer = DocumentSerializer(self.document)
        data = serializer.data
        
        self.assertIn('content', data)
        self.assertEqual(data['content'], self.document.content)

    def test_document_serializer_content_validation_valid(self):
        """Test DocumentSerializer content validation with valid data."""
        serializer = DocumentSerializer()
        valid_content = {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {'type': 'text', 'text': 'Valid content'}
                    ]
                }
            ]
        }
        
        # Should not raise exception
        validated_content = serializer.validate_content(valid_content)
        self.assertEqual(validated_content, valid_content)

    def test_document_serializer_content_validation_invalid(self):
        """Test DocumentSerializer content validation with invalid data."""
        serializer = DocumentSerializer()
        
        # String instead of dict
        with self.assertRaises(ValidationError):
            serializer.validate_content("invalid content")
        
        # Number instead of dict
        with self.assertRaises(ValidationError):
            serializer.validate_content(123)
        
        # List instead of dict
        with self.assertRaises(ValidationError):
            serializer.validate_content(['invalid'])


@pytest.mark.django_db
class TestDocumentCreateSerializer(TestCase):
    """Test DocumentCreateSerializer."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_document_create_serializer_fields(self):
        """Test DocumentCreateSerializer includes only necessary fields."""
        serializer = DocumentCreateSerializer()
        fields = serializer.fields.keys()
        
        expected_fields = ['title', 'content']
        for field in expected_fields:
            self.assertIn(field, fields)
        
        # Should not include read-only fields
        unexpected_fields = ['id', 'version', 'created_at', 'updated_at', 'created_by']
        for field in unexpected_fields:
            self.assertNotIn(field, fields)

    def test_document_create_serializer_title_validation_valid(self):
        """Test title validation with valid data."""
        serializer = DocumentCreateSerializer()
        
        # Valid title
        valid_title = serializer.validate_title('Valid Title')
        self.assertEqual(valid_title, 'Valid Title')
        
        # Title with whitespace should be stripped
        valid_title = serializer.validate_title('  Valid Title  ')
        self.assertEqual(valid_title, 'Valid Title')

    def test_document_create_serializer_title_validation_invalid(self):
        """Test title validation with invalid data."""
        serializer = DocumentCreateSerializer()
        
        # Empty title
        with self.assertRaises(ValidationError):
            serializer.validate_title('')
        
        # Whitespace only
        with self.assertRaises(ValidationError):
            serializer.validate_title('   ')
        
        # Too long title
        long_title = 'x' * 256
        with self.assertRaises(ValidationError):
            serializer.validate_title(long_title)

    def test_document_create_serializer_content_validation(self):
        """Test content validation in create serializer."""
        serializer = DocumentCreateSerializer()
        
        # Valid content
        valid_content = {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {'type': 'text', 'text': 'Valid content'}
                    ]
                }
            ]
        }
        validated_content = serializer.validate_content(valid_content)
        self.assertEqual(validated_content, valid_content)
        
        # Invalid content
        with self.assertRaises(ValidationError):
            serializer.validate_content("invalid")

    def test_document_create_authenticated_user(self):
        """Test document creation with authenticated user."""
        request = self.factory.post('/api/documents/')
        request.user = self.user
        
        serializer = DocumentCreateSerializer(context={'request': request})
        validated_data = {
            'title': 'Test Document',
            'content': {'type': 'doc', 'content': []}
        }
        
        document = serializer.create(validated_data)
        
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.created_by, self.user)

    def test_document_create_anonymous_user(self):
        """Test document creation with anonymous user."""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.post('/api/documents/')
        request.user = AnonymousUser()
        
        serializer = DocumentCreateSerializer(context={'request': request})
        validated_data = {
            'title': 'Anonymous Document',
            'content': {'type': 'doc', 'content': []}
        }
        
        document = serializer.create(validated_data)
        
        self.assertEqual(document.title, 'Anonymous Document')
        self.assertEqual(document.created_by.username, 'anonymous')
        self.assertEqual(document.created_by.first_name, 'Anonymous')
        self.assertEqual(document.created_by.last_name, 'User')

    def test_document_create_anonymous_user_reuse(self):
        """Test that anonymous user is reused, not recreated."""
        from django.contrib.auth.models import AnonymousUser
        
        # Create anonymous user first
        anonymous_user = User.objects.create_user(
            username='anonymous',
            first_name='Anonymous',
            last_name='User',
            email='anonymous@example.com'
        )
        
        request = self.factory.post('/api/documents/')
        request.user = AnonymousUser()
        
        serializer = DocumentCreateSerializer(context={'request': request})
        validated_data = {
            'title': 'Anonymous Document',
            'content': {'type': 'doc', 'content': []}
        }
        
        document = serializer.create(validated_data)
        
        # Should reuse existing anonymous user
        self.assertEqual(document.created_by, anonymous_user)
        
        # Should not create duplicate anonymous users
        anonymous_users = User.objects.filter(username='anonymous')
        self.assertEqual(anonymous_users.count(), 1)

    def test_document_create_serializer_full_flow(self):
        """Test full serialization and creation flow."""
        request = self.factory.post('/api/documents/')
        request.user = self.user
        
        data = {
            'title': '  Test Document  ',  # With whitespace
            'content': {
                'type': 'doc',
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {'type': 'text', 'text': 'Test content'}
                        ]
                    }
                ]
            }
        }
        
        serializer = DocumentCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        
        document = serializer.save()
        
        self.assertEqual(document.title, 'Test Document')  # Whitespace stripped
        self.assertEqual(document.content, data['content'])
        self.assertEqual(document.created_by, self.user)
        self.assertEqual(document.version, 1)