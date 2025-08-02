import pytest
import json
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from documents.models import Document
from documents.forms import DocumentCreateForm


@pytest.mark.django_db
class TestDocumentWebListView:
    """Test suite for DocumentWebListView"""
    
    def test_list_view_anonymous_user_redirects(self):
        """Test that anonymous users are redirected to login"""
        client = Client()
        url = reverse('document_list')
        response = client.get(url)
        
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_list_view_authenticated_user(self, user):
        """Test list view for authenticated user"""
        client = Client()
        client.force_login(user)
        
        url = reverse('document_list')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'documents/list.html' in [t.name for t in response.templates]
        assert 'documents' in response.context
    
    def test_list_view_shows_user_documents_only(self, user):
        """Test that list view only shows documents created by the logged-in user"""
        # Create another user and document
        other_user = User.objects.create_user(username='other', password='pass')
        other_document = Document.objects.create(
            title='Other User Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=other_user
        )
        
        # Create document for the logged-in user
        user_document = Document.objects.create(
            title='User Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_list')
        response = client.get(url)
        
        documents = response.context['documents']
        assert user_document in documents
        assert other_document not in documents
    
    def test_list_view_pagination(self, user):
        """Test pagination in list view"""
        # Create more than 12 documents (the paginate_by value)
        for i in range(15):
            Document.objects.create(
                title=f'Document {i}',
                content={'root': {'type': 'root', 'children': []}},
                created_by=user
            )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_list')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'is_paginated' in response.context
        assert response.context['is_paginated'] is True
        assert len(response.context['documents']) == 12  # First page


@pytest.mark.django_db
class TestDocumentWebCreateView:
    """Test suite for DocumentWebCreateView"""
    
    def test_create_view_anonymous_user_redirects(self):
        """Test that anonymous users are redirected to login"""
        client = Client()
        url = reverse('document_create')
        response = client.get(url)
        
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_create_view_get_authenticated_user(self, user):
        """Test GET request to create view"""
        client = Client()
        client.force_login(user)
        
        url = reverse('document_create')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'documents/create.html' in [t.name for t in response.templates]
        assert 'form' in response.context
        assert isinstance(response.context['form'], DocumentCreateForm)
    
    def test_create_view_post_valid_data(self, user):
        """Test POST request with valid data"""
        client = Client()
        client.force_login(user)
        
        url = reverse('document_create')
        data = {
            'title': 'New Test Document',
            'content': 'This is test content'
        }
        response = client.post(url, data)
        
        # Should redirect to document detail
        assert response.status_code == 302
        
        # Check document was created
        document = Document.objects.get(title='New Test Document')
        assert document.created_by == user
        assert document.last_modified_by == user
        assert document.get_plain_text() == 'This is test content'
        
        # Check redirect URL
        assert f'/documents/{document.pk}/' in response.url
    
    def test_create_view_post_invalid_data(self, user):
        """Test POST request with invalid data"""
        client = Client()
        client.force_login(user)
        
        url = reverse('document_create')
        data = {
            'title': '',  # Empty title should be invalid
            'content': 'This is test content'
        }
        response = client.post(url, data)
        
        # Should stay on create page with errors
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
    
    def test_create_view_success_message(self, user):
        """Test that success message is displayed after creation"""
        client = Client()
        client.force_login(user)
        
        url = reverse('document_create')
        data = {
            'title': 'New Test Document',
            'content': 'This is test content'
        }
        
        # Follow redirects to capture messages
        response = client.post(url, data, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert 'created successfully' in str(messages[0])
    
    def test_create_view_empty_content(self, user):
        """Test creating document with empty content"""
        client = Client()
        client.force_login(user)
        
        url = reverse('document_create')
        data = {
            'title': 'Empty Document'
            # No content
        }
        response = client.post(url, data)
        
        assert response.status_code == 302
        
        document = Document.objects.get(title='Empty Document')
        assert document.get_plain_text() == ''
        assert document.content['root']['children'] == []


@pytest.mark.django_db
class TestDocumentWebDetailView:
    """Test suite for DocumentWebDetailView"""
    
    def test_detail_view_anonymous_user_redirects(self, user):
        """Test that anonymous users are redirected to login"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        url = reverse('document_detail', kwargs={'pk': document.pk})
        response = client.get(url)
        
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_detail_view_authenticated_user(self, user):
        """Test detail view for authenticated user"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_detail', kwargs={'pk': document.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'documents/detail.html' in [t.name for t in response.templates]
        assert response.context['document'] == document
    
    def test_detail_view_other_user_document_404(self, user):
        """Test that users can't access other users' documents"""
        other_user = User.objects.create_user(username='other', password='pass')
        document = Document.objects.create(
            title='Other User Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=other_user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_detail', kwargs={'pk': document.pk})
        response = client.get(url)
        
        assert response.status_code == 404
    
    def test_detail_view_post_update_document(self, user):
        """Test POST request to update document"""
        document = Document.objects.create(
            title='Original Title',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_detail', kwargs={'pk': document.pk})
        data = {
            'title': 'Updated Title',
            'content': 'Updated content'
        }
        response = client.post(url, data)
        
        # Should redirect back to detail view
        assert response.status_code == 302
        
        # Check document was updated
        document.refresh_from_db()
        assert document.title == 'Updated Title'
        assert document.get_plain_text() == 'Updated content'
        assert document.last_modified_by == user


@pytest.mark.django_db
class TestDocumentWebDeleteView:
    """Test suite for DocumentWebDeleteView"""
    
    def test_delete_view_anonymous_user_redirects(self, user):
        """Test that anonymous users are redirected to login"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        url = reverse('document_delete', kwargs={'pk': document.pk})
        response = client.delete(url)
        
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_delete_view_authenticated_user(self, user):
        """Test document deletion by authenticated user"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        document_id = document.pk
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_delete', kwargs={'pk': document.pk})
        response = client.delete(url)
        
        # Should redirect to document list
        assert response.status_code == 302
        assert reverse('document_list') in response.url
        
        # Document should be deleted
        assert not Document.objects.filter(pk=document_id).exists()
    
    def test_delete_view_other_user_document_404(self, user):
        """Test that users can't delete other users' documents"""
        other_user = User.objects.create_user(username='other', password='pass')
        document = Document.objects.create(
            title='Other User Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=other_user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_delete', kwargs={'pk': document.pk})
        response = client.delete(url)
        
        assert response.status_code == 404
        # Document should still exist
        assert Document.objects.filter(pk=document.pk).exists()
    
    def test_delete_view_ajax_request(self, user):
        """Test AJAX delete request returns JSON response"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_delete', kwargs={'pk': document.pk})
        response = client.delete(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] is True
        assert 'deleted successfully' in response_data['message']


@pytest.mark.django_db 
class TestDocumentWebViewsIntegration:
    """Integration tests for web views"""
    
    def test_full_document_lifecycle(self, user):
        """Test full document create -> edit -> delete lifecycle"""
        client = Client()
        client.force_login(user)
        
        # 1. Create document
        create_url = reverse('document_create')
        create_data = {
            'title': 'Lifecycle Test Document',
            'content': 'Initial content'
        }
        response = client.post(create_url, create_data)
        assert response.status_code == 302
        
        document = Document.objects.get(title='Lifecycle Test Document')
        
        # 2. Edit document
        detail_url = reverse('document_detail', kwargs={'pk': document.pk})
        edit_data = {
            'title': 'Updated Lifecycle Document',
            'content': 'Updated content'
        }
        response = client.post(detail_url, edit_data)
        assert response.status_code == 302
        
        document.refresh_from_db()
        assert document.title == 'Updated Lifecycle Document'
        assert document.get_plain_text() == 'Updated content'
        
        # 3. Delete document
        delete_url = reverse('document_delete', kwargs={'pk': document.pk})
        response = client.delete(delete_url)
        assert response.status_code == 302
        
        assert not Document.objects.filter(pk=document.pk).exists()
    
    def test_document_list_after_operations(self, user):
        """Test document list reflects create/delete operations"""
        client = Client()
        client.force_login(user)
        
        # Initial list should be empty
        list_url = reverse('document_list')
        response = client.get(list_url)
        assert len(response.context['documents']) == 0
        
        # Create a document
        create_url = reverse('document_create')
        create_data = {
            'title': 'Test Document 1',
            'content': 'Content 1'
        }
        client.post(create_url, create_data)
        
        # List should now have 1 document
        response = client.get(list_url)
        assert len(response.context['documents']) == 1
        
        # Create another document
        create_data = {
            'title': 'Test Document 2',
            'content': 'Content 2'
        }
        client.post(create_url, create_data)
        
        # List should now have 2 documents
        response = client.get(list_url)
        assert len(response.context['documents']) == 2
        
        # Delete one document
        document = Document.objects.first()
        delete_url = reverse('document_delete', kwargs={'pk': document.pk})
        client.delete(delete_url)
        
        # List should now have 1 document
        response = client.get(list_url)
        assert len(response.context['documents']) == 1