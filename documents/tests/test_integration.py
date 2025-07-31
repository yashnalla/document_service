import pytest
import json
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from documents.models import Document


@pytest.mark.django_db
class TestAPIIntegration(TestCase):
    """Test end-to-end API integration scenarios."""

    def setUp(self):
        self.client = APIClient()
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
                        {'type': 'text', 'text': 'Integration test content'}
                    ]
                }
            ]
        }

    def test_full_document_crud_workflow(self):
        """Test complete CRUD workflow for documents."""
        self.client.force_authenticate(user=self.user)
        
        # CREATE
        create_data = {
            'title': 'Integration Test Document',
            'content': self.sample_content
        }
        
        create_url = reverse('document-list')
        create_response = self.client.post(create_url, create_data, format='json')
        
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        document_id = create_response.data['id']
        self.assertEqual(create_response.data['version'], 1)
        
        # READ (List)
        list_response = self.client.get(create_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        
        # READ (Detail)
        detail_url = reverse('document-detail', kwargs={'pk': document_id})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['title'], 'Integration Test Document')
        self.assertIn('content', detail_response.data)
        
        # UPDATE
        update_data = {
            'title': 'Updated Integration Test Document',
            'content': {
                'type': 'doc',
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {'type': 'text', 'text': 'Updated integration test content'}
                        ]
                    }
                ]
            }
        }
        
        update_response = self.client.put(detail_url, update_data, format='json')
        
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['title'], 'Updated Integration Test Document')
        self.assertEqual(update_response.data['version'], 2)  # Version should increment
        
        # DELETE
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deletion
        verify_response = self.client.get(detail_url)
        self.assertEqual(verify_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_user_workflow(self):
        """Test workflow for anonymous users."""
        # Anonymous user can create documents
        create_data = {
            'title': 'Anonymous Document',
            'content': self.sample_content
        }
        
        create_url = reverse('document-list')
        create_response = self.client.post(create_url, create_data, format='json')
        
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['created_by']['username'], 'anonymous')
        
        # Anonymous user can read documents
        list_response = self.client.get(create_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        
        # Anonymous user can read specific document
        document_id = create_response.data['id']
        detail_url = reverse('document-detail', kwargs={'pk': document_id})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

    def test_search_integration(self):
        """Test search functionality integration."""
        self.client.force_authenticate(user=self.user)
        
        # Create documents with different content
        documents_data = [
            {
                'title': 'Python Tutorial',
                'content': {
                    'type': 'doc',
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [
                                {'type': 'text', 'text': 'Learn Python programming language'}
                            ]
                        }
                    ]
                }
            },
            {
                'title': 'JavaScript Guide',
                'content': {
                    'type': 'doc',
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [
                                {'type': 'text', 'text': 'JavaScript fundamentals and advanced concepts'}
                            ]
                        }
                    ]
                }
            },
            {
                'title': 'Django Framework',
                'content': {
                    'type': 'doc',
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [
                                {'type': 'text', 'text': 'Python web framework for rapid development'}
                            ]
                        }
                    ]
                }
            }
        ]
        
        create_url = reverse('document-list')
        
        # Create all documents
        for doc_data in documents_data:
            self.client.post(create_url, doc_data, format='json')
        
        # Test search by title
        search_response = self.client.get(create_url, {'search': 'Python'})
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(search_response.data['count'], 2)  # Python Tutorial + Django (Python in content)
        
        # Test search by content
        search_response = self.client.get(create_url, {'search': 'JavaScript'})
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(search_response.data['count'], 1)
        
        # Test case-insensitive search
        search_response = self.client.get(create_url, {'search': 'django'})
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(search_response.data['count'], 1)

    def test_version_tracking_integration(self):
        """Test document version tracking across updates."""
        self.client.force_authenticate(user=self.user)
        
        # Create document
        create_data = {
            'title': 'Version Test Document',
            'content': self.sample_content
        }
        
        create_url = reverse('document-list')
        create_response = self.client.post(create_url, create_data, format='json')
        
        document_id = create_response.data['id']
        detail_url = reverse('document-detail', kwargs={'pk': document_id})
        
        # Initial version should be 1
        self.assertEqual(create_response.data['version'], 1)
        
        # Update title only
        update_data = {
            'title': 'Updated Version Test Document',
            'content': self.sample_content  # Same content
        }
        
        update_response = self.client.put(detail_url, update_data, format='json')
        self.assertEqual(update_response.data['version'], 2)
        
        # Update content only
        new_content = {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {'type': 'text', 'text': 'Updated content for version tracking'}
                    ]
                }
            ]
        }
        
        update_data = {
            'title': 'Updated Version Test Document',  # Same title
            'content': new_content
        }
        
        update_response = self.client.put(detail_url, update_data, format='json')
        self.assertEqual(update_response.data['version'], 3)
        
        # Update with same data should not increment version
        same_data_response = self.client.put(detail_url, update_data, format='json')
        self.assertEqual(same_data_response.data['version'], 3)  # Should remain 3

    def test_pagination_integration(self):
        """Test pagination across multiple pages."""
        self.client.force_authenticate(user=self.user)
        
        # Create 25 documents (more than default page size of 20)
        create_url = reverse('document-list')
        
        for i in range(25):
            doc_data = {
                'title': f'Document {i:02d}',
                'content': self.sample_content
            }
            self.client.post(create_url, doc_data, format='json')
        
        # Test first page
        page1_response = self.client.get(create_url)
        self.assertEqual(page1_response.status_code, status.HTTP_200_OK)
        self.assertEqual(page1_response.data['count'], 25)
        self.assertEqual(len(page1_response.data['results']), 20)
        self.assertIsNotNone(page1_response.data['next'])
        self.assertIsNone(page1_response.data['previous'])
        
        # Test second page
        page2_response = self.client.get(create_url, {'page': 2})
        self.assertEqual(page2_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(page2_response.data['results']), 5)
        self.assertIsNone(page2_response.data['next'])
        self.assertIsNotNone(page2_response.data['previous'])

    def test_health_check_integration(self):
        """Test health check endpoint integration."""
        health_url = reverse('health_check')
        response = self.client.get(health_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = json.loads(response.content)
        self.assertIn('status', data)
        self.assertIn('database', data)
        self.assertIn('redis', data)
        
        # Should be healthy in test environment
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')
        self.assertEqual(data['redis'], 'connected')

    def test_api_root_integration(self):
        """Test API root endpoint integration."""
        api_root_url = reverse('api-root')
        response = self.client.get(api_root_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = json.loads(response.content)
        self.assertIn('documents', data)
        self.assertIn('health', data)
        
        # Test that returned URLs are accessible
        documents_response = self.client.get(data['documents'])
        self.assertEqual(documents_response.status_code, status.HTTP_200_OK)
        
        health_response = self.client.get(data['health'])
        self.assertEqual(health_response.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestDatabaseIntegration(TransactionTestCase):
    """Test database-related integration scenarios."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_database_transaction_integrity(self):
        """Test database transaction integrity."""
        # Test that document creation is atomic
        document = Document.objects.create(
            title='Transaction Test',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        # Document should exist and have correct attributes
        self.assertIsNotNone(document.id)
        self.assertEqual(document.version, 1)
        self.assertIsNotNone(document.created_at)
        self.assertIsNotNone(document.updated_at)

    def test_uuid_uniqueness(self):
        """Test UUID uniqueness across documents."""
        doc1 = Document.objects.create(
            title='Document 1',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        doc2 = Document.objects.create(
            title='Document 2',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        # UUIDs should be different
        self.assertNotEqual(doc1.id, doc2.id)
        
        # Both should be valid UUIDs
        import uuid
        self.assertIsInstance(doc1.id, uuid.UUID)
        self.assertIsInstance(doc2.id, uuid.UUID)

    def test_cascade_delete_integration(self):
        """Test cascade delete functionality."""
        # Create document
        document = Document.objects.create(
            title='Cascade Test Document',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        document_id = document.id
        
        # Delete user should cascade delete document
        self.user.delete()
        
        # Document should no longer exist
        with self.assertRaises(Document.DoesNotExist):
            Document.objects.get(id=document_id)


@pytest.mark.django_db
class TestCacheIntegration(TestCase):
    """Test cache integration scenarios."""

    def test_cache_connectivity(self):
        """Test that cache is working properly."""
        # Set a value in cache
        cache.set('test_key', 'test_value', 30)
        
        # Retrieve the value
        cached_value = cache.get('test_key')
        
        self.assertEqual(cached_value, 'test_value')
        
        # Clear the value
        cache.delete('test_key')
        
        # Should be None now
        cached_value = cache.get('test_key')
        self.assertIsNone(cached_value)

    def test_health_check_cache_integration(self):
        """Test health check cache functionality."""
        from django.test import Client
        
        client = Client()
        health_url = reverse('health_check')
        
        response = client.get(health_url)
        data = json.loads(response.content)
        
        # Cache should be working
        self.assertEqual(data['redis'], 'connected')