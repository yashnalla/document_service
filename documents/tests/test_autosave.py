import pytest
import json
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from documents.models import Document


@pytest.mark.django_db
class TestDocumentAutosave:
    """Test suite for document auto-save functionality"""
    
    def test_autosave_anonymous_user_redirects(self, user):
        """Test that anonymous users are redirected to login"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        response = client.post(url, {
            'title': 'Updated Title',
            'content': 'Updated content'
        })
        
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_autosave_authenticated_user_own_document(self, user):
        """Test autosave for authenticated user's own document"""
        document = Document.objects.create(
            title='Original Title',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        original_version = document.version
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        response = client.post(url, {
            'title': 'Updated Title',
            'content': 'Updated content'
        })
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] is True
        assert 'saved successfully' in response_data['message']
        assert 'version' in response_data
        
        # Check document was updated
        document.refresh_from_db()
        assert document.title == 'Updated Title'
        assert document.get_plain_text() == 'Updated content'
        assert document.last_modified_by == user
        assert document.version > original_version
    
    def test_autosave_other_user_document_404(self, user):
        """Test that users can't autosave other users' documents"""
        other_user = User.objects.create_user(username='other', password='pass')
        document = Document.objects.create(
            title='Other User Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=other_user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        response = client.post(url, {
            'title': 'Hacked Title',
            'content': 'Hacked content'
        })
        
        assert response.status_code == 404
        
        # Document should remain unchanged
        document.refresh_from_db()
        assert document.title == 'Other User Document'
        assert document.get_plain_text() == ''
    
    def test_autosave_empty_content(self, user):
        """Test autosave with empty content"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': [{'text': 'Original content'}]}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        response = client.post(url, {
            'title': 'Updated Title',
            'content': ''  # Empty content
        })
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] is True
        
        # Check document was updated with empty content structure
        document.refresh_from_db()
        assert document.title == 'Updated Title'
        assert document.get_plain_text() == ''
        assert document.content['root']['children'] == []
    
    def test_autosave_whitespace_only_content(self, user):
        """Test autosave with whitespace-only content"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        response = client.post(url, {
            'title': 'Updated Title',
            'content': '   \n\t   '  # Whitespace only
        })
        
        assert response.status_code == 200
        
        # Whitespace-only content should be treated as empty
        document.refresh_from_db()
        assert document.get_plain_text() == ''
        assert document.content['root']['children'] == []
    
    def test_autosave_title_only_update(self, user):
        """Test autosave with only title update"""
        document = Document.objects.create(
            title='Original Title',
            content={'root': {'type': 'root', 'children': [
                {'children': [{'text': 'Original content', 'type': 'text'}]}
            ]}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        response = client.post(url, {
            'title': 'Updated Title'
            # No content parameter
        })
        
        assert response.status_code == 200
        
        # Title should be updated, content should become empty (no content param)
        document.refresh_from_db()
        assert document.title == 'Updated Title'
    
    def test_autosave_content_formatting(self, user):
        """Test that autosave properly formats content for Lexical"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        test_content = 'This is some test content with multiple words'
        
        response = client.post(url, {
            'title': 'Test Title',
            'content': test_content
        })
        
        assert response.status_code == 200
        
        # Check that content is properly formatted for Lexical
        document.refresh_from_db()
        assert document.get_plain_text() == test_content
        
        # Verify Lexical structure
        content = document.content
        assert content['root']['type'] == 'root'
        assert len(content['root']['children']) == 1
        
        paragraph = content['root']['children'][0]
        assert paragraph['type'] == 'paragraph'
        assert len(paragraph['children']) == 1
        
        text_node = paragraph['children'][0]
        assert text_node['type'] == 'text'
        assert text_node['text'] == test_content
        assert text_node['format'] == 0
        assert text_node['mode'] == 'normal'
    
    def test_autosave_version_increment(self, user):
        """Test that autosave increments document version"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        original_version = document.version
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        
        # First autosave
        response = client.post(url, {
            'title': 'Updated Title 1',
            'content': 'Content 1'
        })
        
        assert response.status_code == 200
        document.refresh_from_db()
        version_1 = document.version
        assert version_1 > original_version
        
        # Second autosave
        response = client.post(url, {
            'title': 'Updated Title 2',
            'content': 'Content 2'
        })
        
        assert response.status_code == 200
        document.refresh_from_db()
        version_2 = document.version
        assert version_2 > version_1
    
    def test_autosave_last_modified_by_update(self, user):
        """Test that autosave updates last_modified_by field"""
        # Create another user to be the original creator
        creator = User.objects.create_user(username='creator', password='pass')
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=creator,
            last_modified_by=creator
        )
        
        # Change ownership for this test
        document.created_by = user
        document.save()
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        response = client.post(url, {
            'title': 'Updated by User',
            'content': 'Updated content'
        })
        
        assert response.status_code == 200
        
        document.refresh_from_db()
        assert document.last_modified_by == user
        assert document.created_by == user
    
    def test_autosave_post_method_required(self, user):
        """Test that autosave endpoint only accepts POST requests"""
        document = Document.objects.create(
            title='Test Document',
            content={'root': {'type': 'root', 'children': []}},
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        url = reverse('document_autosave', kwargs={'pk': document.pk})
        
        # GET request should not be allowed
        response = client.get(url)
        assert response.status_code == 405  # Method Not Allowed
        
        # PUT request should not be allowed
        response = client.put(url, {
            'title': 'Updated Title',
            'content': 'Updated content'
        })
        assert response.status_code == 405  # Method Not Allowed