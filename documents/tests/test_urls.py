import pytest
from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from rest_framework.routers import DefaultRouter
from documents.views import DocumentViewSet
from documents.models import Document


@pytest.mark.django_db
class TestDocumentURLs(TestCase):
    """Test Document app URL configuration."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_document_list_url_name(self):
        """Test document list URL name resolution."""
        url = reverse('document-list')
        self.assertEqual(url, '/api/documents/')

    def test_document_detail_url_name(self):
        """Test document detail URL name resolution."""
        document = Document.objects.create(
            title='Test Document',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        url = reverse('document-detail', kwargs={'pk': document.pk})
        self.assertEqual(url, f'/api/documents/{document.pk}/')

    def test_document_list_url_resolves(self):
        """Test that document list URL resolves to correct view."""
        url = '/api/documents/'
        resolved = resolve(url)
        
        self.assertEqual(resolved.func.cls, DocumentViewSet)
        self.assertEqual(resolved.url_name, 'document-list')

    def test_document_detail_url_resolves(self):
        """Test that document detail URL resolves to correct view."""
        document = Document.objects.create(
            title='Test Document',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        url = f'/api/documents/{document.pk}/'
        resolved = resolve(url)
        
        self.assertEqual(resolved.func.cls, DocumentViewSet)
        self.assertEqual(resolved.url_name, 'document-detail')
        self.assertEqual(resolved.kwargs['pk'], str(document.pk))

    def test_router_configuration(self):
        """Test that router is configured correctly."""
        from documents.urls import router
        
        self.assertIsInstance(router, DefaultRouter)
        
        # Check registered routes
        urls = router.get_urls()
        url_names = [url.name for url in urls]
        
        expected_names = ['document-list', 'document-detail']
        for name in expected_names:
            self.assertIn(name, url_names)

    def test_document_list_url_methods(self):
        """Test document list URL supports correct HTTP methods."""
        from django.test import Client
        client = Client()
        
        url = reverse('document-list')
        
        # GET should work
        response = client.get(url)
        self.assertIn(response.status_code, [200, 401])  # 200 OK or 401 if auth required
        
        # POST should work
        response = client.post(url, {}, content_type='application/json')
        self.assertNotEqual(response.status_code, 405)  # Not Method Not Allowed

    def test_document_detail_url_methods(self):
        """Test document detail URL supports correct HTTP methods."""
        from django.test import Client
        client = Client()
        
        document = Document.objects.create(
            title='Test Document',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        url = reverse('document-detail', kwargs={'pk': document.pk})
        
        # GET should work
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # PUT should work (might require auth)
        response = client.put(url, {}, content_type='application/json')
        self.assertNotEqual(response.status_code, 405)  # Not Method Not Allowed
        
        # DELETE should work (might require auth)
        response = client.delete(url)
        self.assertNotEqual(response.status_code, 405)  # Not Method Not Allowed

    def test_invalid_uuid_url(self):
        """Test URL with invalid UUID format."""
        from django.test import Client
        client = Client()
        
        url = '/api/documents/invalid-uuid/'
        response = client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_document_url(self):
        """Test URL with non-existent but valid UUID."""
        import uuid
        from django.test import Client
        client = Client()
        
        nonexistent_id = uuid.uuid4()
        url = f'/api/documents/{nonexistent_id}/'
        response = client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_url_patterns_include(self):
        """Test that URL patterns are properly included."""
        from documents.urls import urlpatterns
        
        # Should have one pattern that includes router URLs
        self.assertEqual(len(urlpatterns), 1)
        
        # The pattern should include 'api/' prefix
        pattern = urlpatterns[0]
        self.assertEqual(str(pattern.pattern), 'api/')

    def test_api_namespace(self):
        """Test that documents are under /api/ namespace."""
        url = reverse('document-list')
        self.assertTrue(url.startswith('/api/'))
        
        document = Document.objects.create(
            title='Test Document',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        detail_url = reverse('document-detail', kwargs={'pk': document.pk})
        self.assertTrue(detail_url.startswith('/api/'))

    def test_trailing_slash_consistency(self):
        """Test that URLs have consistent trailing slash behavior."""
        # List URL should have trailing slash
        list_url = reverse('document-list')
        self.assertTrue(list_url.endswith('/'))
        
        # Detail URL should have trailing slash
        document = Document.objects.create(
            title='Test Document',
            content={'type': 'doc', 'content': []},
            created_by=self.user
        )
        
        detail_url = reverse('document-detail', kwargs={'pk': document.pk})
        self.assertTrue(detail_url.endswith('/'))

    def test_router_basename(self):
        """Test router basename configuration."""
        from documents.urls import router
        
        # Get the registered routes
        registry = router.registry
        
        # Find documents registration
        documents_registration = None
        for prefix, viewset, basename in registry:
            if prefix == 'documents':
                documents_registration = (prefix, viewset, basename)
                break
        
        self.assertIsNotNone(documents_registration)
        self.assertEqual(documents_registration[0], 'documents')
        self.assertEqual(documents_registration[1], DocumentViewSet)
        # basename should be 'document' (singular)
        self.assertEqual(documents_registration[2], 'document')