import pytest
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestAPIViews(TestCase):
    """Test API root and documentation views."""

    def setUp(self):
        self.client = Client()

    def test_api_root_response(self):
        """Test API root endpoint returns correct structure."""
        url = reverse('api-root')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        expected_keys = ['documents', 'admin', 'health']
        
        for key in expected_keys:
            self.assertIn(key, data)
            self.assertIsInstance(data[key], str)
            self.assertTrue(data[key].startswith('http'))

    def test_api_root_links_validity(self):
        """Test that API root returns valid URLs."""
        url = reverse('api-root')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        # Test that documents link works
        documents_response = self.client.get(data['documents'])
        self.assertEqual(documents_response.status_code, 200)
        
        # Test that health link works
        health_response = self.client.get(data['health'])
        self.assertEqual(health_response.status_code, 200)

    def test_api_docs_response(self):
        """Test API documentation endpoint returns correct structure."""
        url = reverse('api-docs')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        expected_keys = [
            'title', 'version', 'description', 'endpoints',
            'authentication', 'permissions', 'pagination', 'search'
        ]
        
        for key in expected_keys:
            self.assertIn(key, data)

    def test_api_docs_endpoints_documentation(self):
        """Test that API docs include all documented endpoints."""
        url = reverse('api-docs')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        endpoints = data['endpoints']
        expected_endpoints = [
            'GET /api/',
            'GET /api/documents/',
            'POST /api/documents/',
            'GET /api/documents/{id}/',
            'PUT /api/documents/{id}/',
            'PATCH /api/documents/{id}/',
            'DELETE /api/documents/{id}/',
            'GET /health/',
        ]
        
        for endpoint in expected_endpoints:
            self.assertIn(endpoint, endpoints)

    def test_api_docs_metadata(self):
        """Test API documentation metadata."""
        url = reverse('api-docs')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        self.assertEqual(data['title'], 'Document Service API')
        self.assertEqual(data['version'], '1.0.0')
        self.assertIn('Lexical editor', data['description'])
        self.assertEqual(data['pagination'], 'Page-based pagination with 20 items per page')

    def test_api_root_url_resolution(self):
        """Test API root URL resolution."""
        url = reverse('api-root')
        self.assertEqual(url, '/api/')

    def test_api_docs_url_resolution(self):
        """Test API docs URL resolution."""
        url = reverse('api-docs')
        self.assertEqual(url, '/api/docs/')

    def test_api_root_accepts_get_only(self):
        """Test API root accepts GET requests."""
        url = reverse('api-root')
        
        # GET should work
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST should not work (view is decorated with @api_view(['GET']))
        response = self.client.post(url)
        # Could be 405 (Method Not Allowed) or 403 (Forbidden due to CSRF)
        self.assertIn(response.status_code, [403, 405])

    def test_api_docs_accepts_get_only(self):
        """Test API docs accepts GET requests."""
        url = reverse('api-docs')
        
        # GET should work
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST should not work (view is decorated with @api_view(['GET']))
        response = self.client.post(url)
        # Could be 405 (Method Not Allowed) or 403 (Forbidden due to CSRF)
        self.assertIn(response.status_code, [403, 405])

    def test_api_root_with_authentication(self):
        """Test API root works with authenticated user."""
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_login(user)
        
        url = reverse('api-root')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('documents', data)

    def test_api_docs_content_accuracy(self):
        """Test that API docs content matches actual implementation."""
        url = reverse('api-docs')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        # Check authentication description
        self.assertIn('Session-based', data['authentication'])
        
        # Check permissions description
        self.assertIn('Read-only for anonymous', data['permissions'])
        self.assertIn('full CRUD for authenticated', data['permissions'])
        
        # Check search functionality
        self.assertIn('?search=query', data['search'])