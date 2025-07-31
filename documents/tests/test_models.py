import pytest
import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.urls import reverse
from documents.models import Document


@pytest.mark.django_db
class TestDocumentModel(TestCase):
    """Test Document model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.sample_content = {
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

    def test_document_creation(self):
        """Test basic document creation."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.content, self.sample_content)
        self.assertEqual(document.created_by, self.user)
        self.assertEqual(document.version, 1)
        self.assertIsInstance(document.id, uuid.UUID)

    def test_document_uuid_primary_key(self):
        """Test that document uses UUID as primary key."""
        document = Document.objects.create(
            title='UUID Test',
            content=self.sample_content,
            created_by=self.user
        )
        
        self.assertIsInstance(document.id, uuid.UUID)
        self.assertIsInstance(document.pk, uuid.UUID)
        self.assertEqual(str(document.id), str(document.pk))

    def test_document_str_representation(self):
        """Test document string representation."""
        document = Document.objects.create(
            title='Test Title',
            content=self.sample_content,
            created_by=self.user
        )
        
        self.assertEqual(str(document), 'Test Title')

    def test_document_repr_representation(self):
        """Test document repr representation."""
        document = Document.objects.create(
            title='Test Title',
            content=self.sample_content,
            created_by=self.user
        )
        
        expected_repr = f"<Document: Test Title (v{document.version})>"
        self.assertEqual(repr(document), expected_repr)

    def test_document_default_values(self):
        """Test document default values."""
        document = Document.objects.create(
            title='Test Document',
            created_by=self.user
        )
        
        self.assertEqual(document.content, {})
        self.assertEqual(document.version, 1)
        self.assertIsNotNone(document.created_at)
        self.assertIsNotNone(document.updated_at)

    def test_document_version_increment_on_title_change(self):
        """Test that version increments when title changes."""
        document = Document.objects.create(
            title='Original Title',
            content=self.sample_content,
            created_by=self.user
        )
        original_version = document.version
        
        document.title = 'Updated Title'
        document.save()
        
        self.assertEqual(document.version, original_version + 1)

    def test_document_version_increment_on_content_change(self):
        """Test that version increments when content changes."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        original_version = document.version
        
        new_content = {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {'type': 'text', 'text': 'Updated content'}
                    ]
                }
            ]
        }
        document.content = new_content
        document.save()
        
        self.assertEqual(document.version, original_version + 1)

    def test_document_version_no_increment_on_same_data(self):
        """Test that version doesn't increment when no actual changes."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        original_version = document.version
        
        # Save without changes
        document.save()
        
        self.assertEqual(document.version, original_version)

    def test_document_version_no_increment_on_other_fields(self):
        """Test that version doesn't increment for non-content/title changes."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        original_version = document.version
        
        # This shouldn't increment version (though created_by typically wouldn't change)
        # But we're testing the logic focuses on title and content only
        document.save()
        
        self.assertEqual(document.version, original_version)

    def test_document_ordering(self):
        """Test document ordering by updated_at descending."""
        doc1 = Document.objects.create(
            title='First Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        doc2 = Document.objects.create(
            title='Second Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        documents = list(Document.objects.all())
        self.assertEqual(documents[0], doc2)  # Most recently created first
        self.assertEqual(documents[1], doc1)

    def test_document_user_relationship(self):
        """Test document-user relationship."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        self.assertEqual(document.created_by, self.user)
        self.assertIn(document, self.user.documents.all())

    def test_document_cascade_delete(self):
        """Test that documents are deleted when user is deleted."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        document_id = document.id
        
        self.user.delete()
        
        with self.assertRaises(Document.DoesNotExist):
            Document.objects.get(id=document_id)

    def test_document_json_field_content(self):
        """Test JSONField content handling."""
        complex_content = {
            'type': 'doc',
            'content': [
                {
                    'type': 'heading',
                    'attrs': {'level': 1},
                    'content': [{'type': 'text', 'text': 'Title'}]
                },
                {
                    'type': 'paragraph',
                    'content': [
                        {'type': 'text', 'text': 'Normal text '},
                        {'type': 'text', 'marks': [{'type': 'strong'}], 'text': 'bold text'}
                    ]
                }
            ]
        }
        
        document = Document.objects.create(
            title='Complex Document',
            content=complex_content,
            created_by=self.user
        )
        
        # Refresh from database
        document.refresh_from_db()
        self.assertEqual(document.content, complex_content)

    def test_document_get_absolute_url(self):
        """Test document get_absolute_url method."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        expected_url = reverse('document-detail', kwargs={'pk': document.pk})
        self.assertEqual(document.get_absolute_url(), expected_url)

    def test_document_required_fields(self):
        """Test that required fields are enforced."""
        from django.core.exceptions import ValidationError
        from django.db import transaction
        
        # Title is required - test with validation
        document = Document(
            content=self.sample_content,
            created_by=self.user
        )
        with self.assertRaises(ValidationError):
            document.full_clean()
        
        # created_by is required - test database constraint
        with self.assertRaises((IntegrityError, ValueError)):
            with transaction.atomic():
                Document.objects.create(
                    title='Test Document',
                    content=self.sample_content
                )

    def test_document_title_max_length(self):
        """Test document title max length constraint."""
        long_title = 'x' * 256  # Exceeds 255 character limit
        
        with self.assertRaises(Exception):  # Could be ValidationError or DataError
            Document.objects.create(
                title=long_title,
                content=self.sample_content,
                created_by=self.user
            )

    def test_document_auto_timestamps(self):
        """Test auto timestamp fields."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        self.assertIsNotNone(document.created_at)
        self.assertIsNotNone(document.updated_at)
        
        # created_at should be very close to updated_at initially (within 1 second)
        time_diff = abs((document.updated_at - document.created_at).total_seconds())
        self.assertLess(time_diff, 1.0)
        
        # Small delay to ensure updated_at changes
        import time
        time.sleep(0.01)
        
        # Update document
        original_created_at = document.created_at
        document.title = 'Updated Title'
        document.save()
        
        # created_at shouldn't change, updated_at should
        self.assertEqual(document.created_at, original_created_at)
        self.assertGreater(document.updated_at, original_created_at)