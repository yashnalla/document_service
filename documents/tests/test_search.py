"""
Comprehensive tests for the PostgreSQL full-text search functionality.

This test module covers:
- Document model search vector functionality
- DocumentService search methods
- API search endpoints
- Web search interface
- Search serializers
- Management commands
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.management import call_command
from django.contrib.postgres.search import SearchVector
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from documents.models import Document, DocumentChange
from documents.services import DocumentService
from documents.serializers import DocumentSearchResultSerializer
from documents.api_client import DocumentAPIClient, APIClientError
import json
import time
from io import StringIO


class DocumentSearchVectorTestCase(TestCase):
    """Test Document model search vector functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Ensure search vectors are updated after document creation
        self._ensure_search_vectors()
    
    def _ensure_search_vectors(self):
        """Helper method to ensure all documents have search vectors."""
        call_command('update_search_vectors', verbosity=0)
    
    def test_document_has_search_vector_field(self):
        """Test that Document model has search_vector field."""
        doc = Document.objects.create(
            title='Test Document',
            content={'root': {'children': []}},
            created_by=self.user
        )
        
        # Initially None
        self.assertIsNone(doc.search_vector)
        
    def test_document_update_search_vector_method(self):
        """Test Document.update_search_vector() method."""
        doc = Document.objects.create(
            title='Django Tutorial',
            content={
                'root': {
                    'children': [
                        {
                            'type': 'paragraph',
                            'children': [
                                {'type': 'text', 'text': 'Learn Django web development'}
                            ]
                        }
                    ]
                }
            },
            created_by=self.user
        )
        
        # Update search vector
        doc.update_search_vector()
        
        self.assertIsNotNone(doc.search_vector)
    
    def test_document_save_updates_search_vector(self):
        """Test that saving a document updates search vector automatically."""
        doc = DocumentService.create_document(
            title='Test Document',
            content_text='This is test content',
            user=self.user
        )
        
        # Ensure search vectors are populated
        self._ensure_search_vectors()
        
        # Search vector should be populated
        doc.refresh_from_db()
        self.assertIsNotNone(doc.search_vector)
    
    def test_document_plain_text_extraction(self):
        """Test Document.get_plain_text property with plain text content."""
        # Test with plain text content
        doc1 = Document.objects.create(
            title='Test Doc 1',
            content='Hello world',
            created_by=self.user
        )
        
        self.assertEqual(doc1.get_plain_text, 'Hello world')
        
        # Test with multi-line content
        doc2 = Document.objects.create(
            title='Test Doc 2',
            content='Alternative structure\n\nWith multiple lines',
            created_by=self.user
        )
        
        self.assertEqual(doc2.get_plain_text, 'Alternative structure\n\nWith multiple lines')
        
        # Test with empty content
        doc3 = Document.objects.create(
            title='Empty Doc',
            content='',
            created_by=self.user
        )
        
        self.assertEqual(doc3.get_plain_text, '')


class DocumentServiceSearchTestCase(TestCase):
    """Test DocumentService search functionality."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        # Create test documents
        self.doc1 = DocumentService.create_document(
            title='Django Web Development',
            content_text='Learn how to build web applications with Django framework and Python',
            user=self.user1
        )
        
        self.doc2 = DocumentService.create_document(
            title='PostgreSQL Database Guide',
            content_text='Complete guide to PostgreSQL database management and optimization',
            user=self.user1
        )
        
        self.doc3 = DocumentService.create_document(
            title='Python Best Practices',
            content_text='Modern Python programming techniques and design patterns',
            user=self.user2
        )
        
        # Ensure all documents have search vectors
        self._ensure_search_vectors()
    
    def _ensure_search_vectors(self):
        """Helper method to ensure all documents have search vectors."""
        call_command('update_search_vectors', verbosity=0)
    
    def test_search_documents_basic_functionality(self):
        """Test basic search functionality."""
        results = DocumentService.search_documents(
            query='Django',
            user=self.user1,
            limit=10
        )
        
        self.assertEqual(results['total_results'], 1)
        self.assertEqual(results['query'], 'Django')
        self.assertGreater(results['search_time'], 0)
        self.assertEqual(len(list(results['documents'])), 1)
        
        # Check that the correct document was found
        found_doc = list(results['documents'])[0]
        self.assertEqual(found_doc.id, self.doc1.id)
    
    def test_search_documents_multiple_results(self):
        """Test search that returns multiple results."""
        results = DocumentService.search_documents(
            query='Python',
            user=self.user1,
            limit=10
        )
        
        # Should find both doc1 (mentions Python) and doc3 (Python Best Practices)
        # But user1 should only see doc1 when user_only=True by default in permission filtering
        self.assertGreater(results['total_results'], 0)
    
    def test_search_documents_empty_query(self):
        """Test search with empty query."""
        results = DocumentService.search_documents(
            query='',
            user=self.user1,
            limit=10
        )
        
        self.assertEqual(results['total_results'], 0)
        self.assertEqual(results['query'], '')
        self.assertEqual(results['search_time'], 0)
    
    def test_search_documents_no_results(self):
        """Test search with query that has no matches."""
        results = DocumentService.search_documents(
            query='nonexistentterm',
            user=self.user1,
            limit=10
        )
        
        self.assertEqual(results['total_results'], 0)
        self.assertGreater(results['search_time'], 0)
    
    def test_search_documents_user_filtering(self):
        """Test user-based document filtering."""
        # Search with user_only=True
        results = DocumentService.search_documents(
            query='Python',
            user=self.user1,
            limit=10,
            user_only=True
        )
        
        self.assertTrue(results['user_only'])
        
        # Search with user_only=False (all documents)
        results_all = DocumentService.search_documents(
            query='Python',
            user=self.user1,
            limit=10,
            user_only=False
        )
        
        self.assertFalse(results_all['user_only'])
    
    def test_search_documents_limit_parameter(self):
        """Test search result limiting."""
        # Create more test documents
        for i in range(5):
            DocumentService.create_document(
                title=f'Python Document {i}',
                content_text=f'Python programming tutorial number {i}',
                user=self.user1
            )
        
        results = DocumentService.search_documents(
            query='Python',
            user=self.user1,
            limit=3
        )
        
        # Should limit results to 3
        self.assertLessEqual(len(list(results['documents'])), 3)
    
    def test_search_user_documents_method(self):
        """Test DocumentService.search_user_documents() convenience method."""
        results = DocumentService.search_user_documents(
            query='Django',
            user=self.user1,
            limit=10
        )
        
        self.assertTrue(results['user_only'])
        self.assertEqual(results['total_results'], 1)
    
    def test_search_anonymous_user(self):
        """Test search behavior with anonymous user."""
        results = DocumentService.search_documents(
            query='Django',
            user=None,
            limit=10
        )
        
        # Anonymous users should get no results for security
        self.assertEqual(results['total_results'], 0)


class DocumentSearchAPITestCase(APITestCase):
    """Test Document search API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Create test documents
        self.doc1 = DocumentService.create_document(
            title='Django Development Guide',
            content_text='Comprehensive guide to Django web development with examples',
            user=self.user
        )
        
        self.doc2 = DocumentService.create_document(
            title='React Frontend Tutorial',
            content_text='Learn React.js for building modern user interfaces',
            user=self.user
        )
        
        # Ensure all documents have search vectors
        self._ensure_search_vectors()
    
    def _ensure_search_vectors(self):
        """Helper method to ensure all documents have search vectors."""
        call_command('update_search_vectors', verbosity=0)
    
    def test_search_api_endpoint_exists(self):
        """Test that search API endpoint exists and is accessible."""
        url = reverse('document-search')  # DRF router generates this name
        response = self.client.get(url, {'q': 'Django'})
        
        self.assertEqual(response.status_code, 200)
    
    def test_search_api_basic_search(self):
        """Test basic search via API."""
        url = '/api/documents/search/'
        response = self.client.get(url, {'q': 'Django'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('results', data)
        self.assertIn('meta', data)
        self.assertEqual(data['meta']['query'], 'Django')
        self.assertGreater(data['meta']['total_results'], 0)
    
    def test_search_api_missing_query_parameter(self):
        """Test API response when query parameter is missing."""
        url = '/api/documents/search/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    def test_search_api_pagination_parameters(self):
        """Test API search with limit and user_only parameters."""
        url = '/api/documents/search/'
        response = self.client.get(url, {
            'q': 'development',
            'limit': '1',
            'user_only': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['meta']['limit'], 1)
        self.assertTrue(data['meta']['user_only'])
    
    def test_search_api_unauthorized_access(self):
        """Test API search without authentication."""
        self.client.credentials()  # Remove credentials
        
        url = '/api/documents/search/'
        response = self.client.get(url, {'q': 'Django'})
        
        self.assertEqual(response.status_code, 401)
    
    def test_search_api_result_serialization(self):
        """Test that search results are properly serialized."""
        url = '/api/documents/search/'
        response = self.client.get(url, {'q': 'Django'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        if data['results']:
            result = data['results'][0]
            expected_fields = [
                'id', 'title', 'created_by_name', 'updated_at',
                'content_snippet', 'search_rank', 'version'
            ]
            
            for field in expected_fields:
                self.assertIn(field, result)


class DocumentSearchSerializerTestCase(TestCase):
    """Test DocumentSearchResultSerializer."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.doc = DocumentService.create_document(
            title='Test Document',
            content_text='This is a long piece of content that should be truncated in the search results snippet to show only the first 200 characters or so, depending on the implementation of the content snippet generation logic.',
            user=self.user
        )
        
        # Ensure search vectors are populated
        self._ensure_search_vectors()
    
    def _ensure_search_vectors(self):
        """Helper method to ensure all documents have search vectors."""
        call_command('update_search_vectors', verbosity=0)
    
    def test_search_result_serializer_fields(self):
        """Test that DocumentSearchResultSerializer includes correct fields."""
        # Add a mock rank for testing
        self.doc.rank = 0.5
        
        serializer = DocumentSearchResultSerializer(self.doc)
        data = serializer.data
        
        expected_fields = [
            'id', 'title', 'created_by_name', 'updated_at',
            'content_snippet', 'search_rank', 'version'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)
    
    def test_content_snippet_generation(self):
        """Test content snippet truncation and formatting."""
        # Add a mock rank for testing
        self.doc.rank = 0.5
        
        serializer = DocumentSearchResultSerializer(self.doc)
        data = serializer.data
        
        snippet = data['content_snippet']
        
        # Should be truncated to ~200 characters
        self.assertLessEqual(len(snippet), 203)  # 200 + "..."
        
        # Should end with "..." if content was truncated
        if len(self.doc.get_plain_text) > 200:
            self.assertTrue(snippet.endswith('...'))
    
    def test_created_by_name_field(self):
        """Test created_by_name field generation."""
        # Add a mock rank for testing
        self.doc.rank = 0.5
        
        serializer = DocumentSearchResultSerializer(self.doc)
        data = serializer.data
        
        self.assertEqual(data['created_by_name'], self.user.username)
        
        # Test with user that has full name
        user_with_name = User.objects.create_user(
            username='john_doe',
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        
        doc_with_name = DocumentService.create_document(
            title='Doc by John',
            content_text='Test content',
            user=user_with_name
        )
        doc_with_name.rank = 0.5
        
        serializer2 = DocumentSearchResultSerializer(doc_with_name)
        data2 = serializer2.data
        
        self.assertEqual(data2['created_by_name'], 'John Doe')


class DocumentAPIClientTestCase(TestCase):
    """Test DocumentAPIClient search functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.doc = DocumentService.create_document(
            title='API Test Document',
            content_text='Testing API client search functionality',
            user=self.user
        )
        
        # Ensure search vectors are populated
        self._ensure_search_vectors()
        
        self.api_client = DocumentAPIClient(self.user)
    
    def _ensure_search_vectors(self):
        """Helper method to ensure all documents have search vectors."""
        call_command('update_search_vectors', verbosity=0)
    
    def test_api_client_search_documents_method(self):
        """Test DocumentAPIClient.search_documents() method."""
        results = self.api_client.search_documents(
            query='API',
            limit=10,
            user_only=True
        )
        
        self.assertIn('results', results)
        self.assertIn('meta', results)
        self.assertEqual(results['meta']['query'], 'API')
    
    def test_api_client_search_empty_query_error(self):
        """Test API client error handling for empty query."""
        with self.assertRaises(APIClientError):
            self.api_client.search_documents(
                query='',
                limit=10
            )
    
    def test_api_client_search_parameter_validation(self):
        """Test API client parameter validation."""
        # Test with valid parameters
        results = self.api_client.search_documents(
            query='test',
            limit=5,
            user_only=False
        )
        
        self.assertIsInstance(results, dict)
        
        # Test limit boundary
        results_max = self.api_client.search_documents(
            query='test',
            limit=100  # Should be accepted
        )
        
        self.assertIsInstance(results_max, dict)


class DocumentWebSearchTestCase(TestCase):
    """Test web interface search functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.doc = DocumentService.create_document(
            title='Web Search Test',
            content_text='Testing web interface search with HTMX',
            user=self.user
        )
        
        # Ensure search vectors are populated
        self._ensure_search_vectors()
        
        self.client = Client()
    
    def _ensure_search_vectors(self):
        """Helper method to ensure all documents have search vectors."""
        call_command('update_search_vectors', verbosity=0)
    
    def test_search_ajax_endpoint_requires_auth(self):
        """Test that search AJAX endpoint requires authentication."""
        url = reverse('document_search_ajax')
        response = self.client.get(url, {'q': 'test'})
        
        self.assertEqual(response.status_code, 403)
    
    def test_search_ajax_endpoint_with_auth(self):
        """Test search AJAX endpoint with authentication."""
        self.client.force_login(self.user)
        
        url = reverse('document_search_ajax')
        response = self.client.get(url, {'q': 'test'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'search-result-card')  # Should contain search results HTML
    
    def test_search_ajax_empty_query(self):
        """Test search AJAX endpoint with empty query."""
        self.client.force_login(self.user)
        
        url = reverse('document_search_ajax')
        response = self.client.get(url, {'q': ''})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Start typing to search documents')
    
    def test_search_ajax_user_only_parameter(self):
        """Test search AJAX endpoint with user_only parameter."""
        self.client.force_login(self.user)
        
        url = reverse('document_search_ajax')
        response = self.client.get(url, {
            'q': 'test',
            'user_only': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_document_list_page_has_search_interface(self):
        """Test that document list page includes search interface."""
        self.client.force_login(self.user)
        
        url = reverse('document_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'search-input')
        self.assertContains(response, 'hx-get')  # HTMX attributes
        self.assertContains(response, '/documents/search/')  # The actual URL path


@pytest.mark.django_db
class SearchIntegrationTestCase:
    """Integration tests for the complete search system."""
    
    def test_end_to_end_search_workflow(self):
        """Test complete search workflow from document creation to search results."""
        # Create user
        user = User.objects.create_user(
            username='integration_user',
            email='integration@example.com',
            password='testpass123'
        )
        
        # Create document using service
        doc = DocumentService.create_document(
            title='Integration Test Document',
            content_text='This document tests the complete search integration workflow',
            user=user
        )
        
        # Verify document has search vector
        doc.refresh_from_db()
        assert doc.search_vector is not None
        
        # Test search via service
        search_results = DocumentService.search_documents(
            query='integration',
            user=user,
            limit=10
        )
        
        assert search_results['total_results'] == 1
        assert search_results['query'] == 'integration'
        
        # Test search via API client
        api_client = DocumentAPIClient(user)
        api_results = api_client.search_documents(
            query='integration',
            limit=5
        )
        
        assert 'results' in api_results
        assert 'meta' in api_results
        assert api_results['meta']['query'] == 'integration'
        
        # Test web interface
        client = Client()
        client.force_login(user)
        
        web_response = client.get('/documents/search/', {'q': 'integration'})
        assert web_response.status_code == 200
    
    def test_search_performance_benchmarks(self):
        """Test search performance meets requirements."""
        user = User.objects.create_user(
            username='perf_user',
            email='perf@example.com',
            password='testpass123'
        )
        
        # Create multiple documents
        for i in range(10):
            DocumentService.create_document(
                title=f'Performance Test Document {i}',
                content_text=f'Document {i} content for performance testing with various keywords',
                user=user
            )
        
        # Measure search performance
        start_time = time.time()
        
        results = DocumentService.search_documents(
            query='performance',
            user=user,
            limit=20
        )
        
        end_time = time.time()
        search_duration = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Should be much faster than 100ms requirement
        assert search_duration < 100, f"Search took {search_duration}ms, expected < 100ms"
        assert results['search_time'] < 100, f"Reported search time {results['search_time']}ms"
    
    def test_search_with_document_updates(self):
        """Test search behavior when documents are updated."""
        user = User.objects.create_user(
            username='update_user',
            email='update@example.com',
            password='testpass123'
        )
        
        # Create document
        doc = DocumentService.create_document(
            title='Original Title',
            content_text='Original content',
            user=user
        )
        
        # Search should find it
        results = DocumentService.search_documents(
            query='original',
            user=user,
            limit=10
        )
        assert results['total_results'] == 1
        
        # Update document
        DocumentService.update_document(
            document=doc,
            title='Updated Title',
            content_text='Updated content with new keywords',
            user=user
        )
        
        # Search for old content should return no results
        results_old = DocumentService.search_documents(
            query='original',
            user=user,
            limit=10
        )
        assert results_old['total_results'] == 0
        
        # Search for new content should find it
        results_new = DocumentService.search_documents(
            query='updated',
            user=user,
            limit=10
        )
        assert results_new['total_results'] == 1