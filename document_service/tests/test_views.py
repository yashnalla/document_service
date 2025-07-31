import pytest
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.db import connection
from django.core.cache import cache


@pytest.mark.django_db
class TestHealthCheckView(TestCase):
    """Test health check endpoint functionality."""

    def setUp(self):
        self.client = Client()
        self.health_url = reverse('health_check')

    def test_health_check_success(self):
        """Test health check returns success when all services are healthy."""
        response = self.client.get(self.health_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertIn('status', data)
        self.assertIn('database', data)
        self.assertIn('redis', data)

    def test_health_check_healthy_response_structure(self):
        """Test that healthy response has correct structure."""
        response = self.client.get(self.health_url)
        data = json.loads(response.content)
        
        expected_keys = ['status', 'database', 'redis']
        for key in expected_keys:
            self.assertIn(key, data)
        
        # Status should be either 'healthy' or 'unhealthy'
        self.assertIn(data['status'], ['healthy', 'unhealthy'])

    @patch('django.db.connection.cursor')
    def test_health_check_database_error(self, mock_cursor):
        """Test health check handles database connection errors."""
        mock_cursor.side_effect = Exception("Database connection failed")
        
        response = self.client.get(self.health_url)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'unhealthy')
        self.assertIn('error', data['database'])
        self.assertIn('Database connection failed', data['database'])

    @patch('django.core.cache.cache.set')
    def test_health_check_redis_error(self, mock_cache_set):
        """Test health check handles Redis connection errors."""
        mock_cache_set.side_effect = Exception("Redis connection failed")
        
        response = self.client.get(self.health_url)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'unhealthy')
        self.assertIn('error', data['redis'])
        self.assertIn('Redis connection failed', data['redis'])

    @patch('django.core.cache.cache.set')
    @patch('django.db.connection.cursor')
    def test_health_check_both_services_fail(self, mock_cursor, mock_cache_set):
        """Test health check when both database and Redis fail."""
        mock_cursor.side_effect = Exception("DB error")
        mock_cache_set.side_effect = Exception("Redis error")
        
        response = self.client.get(self.health_url)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'unhealthy')
        self.assertIn('error', data['database'])
        self.assertIn('error', data['redis'])

    def test_health_check_database_connectivity(self):
        """Test that health check actually tests database connectivity."""
        response = self.client.get(self.health_url)
        data = json.loads(response.content)
        
        # If we're here, database should be connected
        self.assertEqual(data['database'], 'connected')

    def test_health_check_redis_connectivity(self):
        """Test that health check actually tests Redis connectivity."""
        response = self.client.get(self.health_url)
        data = json.loads(response.content)
        
        # Test that cache operations work
        cache.set('test_key', 'test_value', 10)
        self.assertEqual(cache.get('test_key'), 'test_value')
        
        # Redis should be connected if cache operations work
        self.assertEqual(data['redis'], 'connected')

    def test_health_check_url_resolution(self):
        """Test that health check URL resolves correctly."""
        url = reverse('health_check')
        self.assertEqual(url, '/health/')

    def test_health_check_http_methods(self):
        """Test health check endpoint accepts GET requests."""
        # GET should work
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)
        
        # POST should also work (no method restriction in view)
        response = self.client.post(self.health_url)
        self.assertEqual(response.status_code, 200)

    def test_health_check_json_response(self):
        """Test that response is valid JSON."""
        response = self.client.get(self.health_url)
        
        try:
            data = json.loads(response.content)
            self.assertIsInstance(data, dict)
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON")