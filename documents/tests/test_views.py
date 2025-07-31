import pytest
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from documents.models import Document
from documents.serializers import DocumentListSerializer, DocumentSerializer


@pytest.mark.django_db
class TestDocumentViewSet(TestCase):
    """Test DocumentViewSet functionality."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
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

    def test_document_list_anonymous_user(self):
        """Test document list access for anonymous users."""
        # Create some documents
        Document.objects.create(
            title='Public Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        url = reverse('document-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_document_list_authenticated_user(self):
        """Test document list access for authenticated users."""
        self.client.force_authenticate(user=self.user)
        
        # Create some documents
        Document.objects.create(
            title='User Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        url = reverse('document-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_document_create_authenticated_user(self):
        """Test document creation with authenticated user."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'title': 'New Document',
            'content': self.sample_content
        }
        
        url = reverse('document-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Document')
        self.assertEqual(response.data['created_by']['username'], 'testuser')

    def test_document_create_anonymous_user(self):
        """Test document creation with anonymous user creates anonymous user."""
        data = {
            'title': 'Anonymous Document',
            'content': self.sample_content
        }
        
        url = reverse('document-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Anonymous Document')
        self.assertEqual(response.data['created_by']['username'], 'anonymous')

    def test_document_retrieve(self):
        """Test document retrieval."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        url = reverse('document-detail', kwargs={'pk': document.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Document')
        self.assertEqual(response.data['id'], str(document.id))

    def test_document_update_authenticated_user(self):
        """Test document update with authenticated user."""
        self.client.force_authenticate(user=self.user)
        
        document = Document.objects.create(
            title='Original Title',
            content=self.sample_content,
            created_by=self.user
        )
        
        data = {
            'title': 'Updated Title',
            'content': {
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
        }
        
        url = reverse('document-detail', kwargs={'pk': document.pk})
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')
        
        # Check version increment
        document.refresh_from_db()
        self.assertEqual(document.version, 2)

    def test_document_partial_update(self):
        """Test document partial update (PATCH)."""
        self.client.force_authenticate(user=self.user)
        
        document = Document.objects.create(
            title='Original Title',
            content=self.sample_content,
            created_by=self.user
        )
        
        data = {'title': 'Partially Updated Title'}
        
        url = reverse('document-detail', kwargs={'pk': document.pk})
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Partially Updated Title')
        
        # Content should remain unchanged
        document.refresh_from_db()
        self.assertEqual(document.content, self.sample_content)

    def test_document_delete(self):
        """Test document deletion."""
        self.client.force_authenticate(user=self.user)
        
        document = Document.objects.create(
            title='Document to Delete',
            content=self.sample_content,
            created_by=self.user
        )
        document_id = document.id
        
        url = reverse('document-detail', kwargs={'pk': document.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Document should be deleted
        with self.assertRaises(Document.DoesNotExist):
            Document.objects.get(id=document_id)

    def test_document_search_by_title(self):
        """Test document search functionality by title."""
        Document.objects.create(
            title='Python Programming',
            content=self.sample_content,
            created_by=self.user
        )
        Document.objects.create(
            title='JavaScript Tutorial',
            content=self.sample_content,
            created_by=self.user
        )
        Document.objects.create(
            title='Django Guide',
            content=self.sample_content,
            created_by=self.user
        )
        
        url = reverse('document-list')
        response = self.client.get(url, {'search': 'Python'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Python Programming')

    def test_document_search_by_content(self):
        """Test document search functionality by content."""
        Document.objects.create(
            title='Document 1',
            content={
                'type': 'doc',
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {'type': 'text', 'text': 'This document contains Python code'}
                        ]
                    }
                ]
            },
            created_by=self.user
        )
        Document.objects.create(
            title='Document 2',
            content={
                'type': 'doc',
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {'type': 'text', 'text': 'This document is about JavaScript'}
                        ]
                    }
                ]
            },
            created_by=self.user
        )
        
        url = reverse('document-list')
        response = self.client.get(url, {'search': 'Python'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Document 1')

    def test_document_search_case_insensitive(self):
        """Test that document search is case insensitive."""
        Document.objects.create(
            title='Python Programming',
            content=self.sample_content,
            created_by=self.user
        )
        
        url = reverse('document-list')
        response = self.client.get(url, {'search': 'python'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Python Programming')

    def test_document_search_no_results(self):
        """Test document search with no matching results."""
        Document.objects.create(
            title='Python Programming',
            content=self.sample_content,
            created_by=self.user
        )
        
        url = reverse('document-list')
        response = self.client.get(url, {'search': 'nonexistent'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

    def test_get_serializer_class_list_action(self):
        """Test that list action uses DocumentListSerializer."""
        url = reverse('document-list')
        response = self.client.get(url)
        
        # DocumentListSerializer should not include content field
        if response.data['results']:
            self.assertNotIn('content', response.data['results'][0])

    def test_get_serializer_class_retrieve_action(self):
        """Test that retrieve action uses DocumentSerializer."""
        document = Document.objects.create(
            title='Test Document',
            content=self.sample_content,
            created_by=self.user
        )
        
        url = reverse('document-detail', kwargs={'pk': document.pk})
        response = self.client.get(url)
        
        # DocumentSerializer should include content field
        self.assertIn('content', response.data)

    def test_get_serializer_class_create_action(self):
        """Test that create action uses DocumentCreateSerializer."""
        data = {
            'title': 'New Document',
            'content': self.sample_content
        }
        
        url = reverse('document-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Response should include all fields after creation
        self.assertIn('content', response.data)
        self.assertIn('created_by', response.data)

    def test_document_pagination(self):
        """Test document list pagination."""
        # Create more than 20 documents (default page size)
        for i in range(25):
            Document.objects.create(
                title=f'Document {i}',
                content=self.sample_content,
                created_by=self.user
            )
        
        url = reverse('document-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 25)
        self.assertEqual(len(response.data['results']), 20)  # Default page size
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

    def test_document_pagination_second_page(self):
        """Test document list second page."""
        # Create more than 20 documents
        for i in range(25):
            Document.objects.create(
                title=f'Document {i}',
                content=self.sample_content,
                created_by=self.user
            )
        
        url = reverse('document-list')
        response = self.client.get(url, {'page': 2})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)  # Remaining documents
        self.assertIsNone(response.data['next'])
        self.assertIsNotNone(response.data['previous'])

    def test_document_ordering(self):
        """Test that documents are ordered by updated_at descending."""
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
        
        url = reverse('document-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        
        # Second document should be first (most recent)
        self.assertEqual(results[0]['title'], 'Second Document')
        self.assertEqual(results[1]['title'], 'First Document')

    def test_document_not_found(self):
        """Test document retrieval with non-existent ID."""
        import uuid
        non_existent_id = uuid.uuid4()
        
        url = reverse('document-detail', kwargs={'pk': non_existent_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_document_invalid_uuid(self):
        """Test document retrieval with invalid UUID format."""
        url = '/api/documents/invalid-uuid/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_document_create_validation_error(self):
        """Test document creation with validation errors."""
        data = {
            'title': '',  # Empty title should fail
            'content': self.sample_content
        }
        
        url = reverse('document-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_document_create_invalid_content(self):
        """Test document creation with invalid content."""
        data = {
            'title': 'Test Document',
            'content': 'invalid content'  # Should be dict, not string
        }
        
        url = reverse('document-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)