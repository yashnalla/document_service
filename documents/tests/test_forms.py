import pytest
from django import forms
from django.contrib.auth.models import User
from documents.forms import DocumentForm, DocumentCreateForm
from documents.models import Document


@pytest.mark.django_db
class TestDocumentForm:
    """Test suite for DocumentForm"""
    
    def test_document_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            'content': 'This is test content'
        }
        form = DocumentForm(data=form_data)
        assert form.is_valid()
    
    def test_document_form_no_title_field(self):
        """Test that DocumentForm does not have title field (immutable after creation)"""
        form = DocumentForm()
        assert 'title' not in form.fields
        assert 'content' in form.fields
    
    def test_document_form_content_not_required(self):
        """Test that content is not required in DocumentForm"""
        form_data = {}
        form = DocumentForm(data=form_data)
        assert form.is_valid()
    
    def test_document_form_empty_content(self):
        """Test form with empty content should be valid"""
        form_data = {
            'content': ''
        }
        form = DocumentForm(data=form_data)
        assert form.is_valid()
    
    def test_document_form_save_commit_false(self):
        """Test form save with commit=False"""
        form_data = {
            'content': 'This is test content'
        }
        form = DocumentForm(data=form_data)
        assert form.is_valid()
        
        document = form.save(commit=False)
        # DocumentForm only handles content, not title
        # Note: Since our form's save method just calls super().save(commit=commit),
        # the document might still get a UUID assigned even with commit=False
        # The important thing is that it's not saved to the database
        initial_count = Document.objects.count()
        # Document should not be in database yet
        if document.pk:
            assert not Document.objects.filter(pk=document.pk).exists()
    
    def test_document_form_crispy_helper(self):
        """Test that crispy forms helper is configured"""
        form = DocumentForm()
        assert hasattr(form, 'helper')
        assert form.helper.form_tag is False
    
    def test_document_form_content_widget(self):
        """Test that content field has proper widget configuration"""
        form = DocumentForm()
        content_field = form.fields['content']
        widget = content_field.widget
        assert widget.attrs['rows'] == 15
        assert 'Start typing your document content...' in widget.attrs['placeholder']


@pytest.mark.django_db
class TestDocumentCreateForm:
    """Test suite for DocumentCreateForm"""
    
    def test_document_create_form_inherits_from_model_form(self):
        """Test that DocumentCreateForm inherits from ModelForm"""
        form = DocumentCreateForm()
        assert isinstance(form, forms.ModelForm)
        # DocumentCreateForm is separate from DocumentForm now
        assert 'title' in form.fields
        assert 'content' in form.fields
    
    def test_document_create_form_content_not_required(self):
        """Test that content is not required for creation"""
        form_data = {
            'title': 'Test Document'
            # No content provided
        }
        form = DocumentCreateForm(data=form_data)
        assert form.is_valid()
    
    def test_document_create_form_with_content(self):
        """Test form with both title and content"""
        form_data = {
            'title': 'Test Document',
            'content': 'This is test content'
        }
        form = DocumentCreateForm(data=form_data)
        assert form.is_valid()
    
    def test_document_create_form_placeholder_text(self):
        """Test that the content field has the correct placeholder"""
        form = DocumentCreateForm()
        content_widget = form.fields['content'].widget
        assert 'Start typing your document content... (optional)' in content_widget.attrs['placeholder']


@pytest.mark.django_db
class TestDocumentFormIntegration:
    """Integration tests for document forms with views"""
    
    def test_form_creates_document_with_lexical_format(self, user):
        """Test that form properly stores content as plain text"""
        form_data = {
            'title': 'Test Document',
            'content': 'This is test content'
        }
        form = DocumentCreateForm(data=form_data)
        assert form.is_valid()
        
        # Simulate what the view does - store content as plain text
        document = form.save(commit=False)
        document.created_by = user
        document.last_modified_by = user
        
        # Content is stored as plain text directly
        content_text = form.cleaned_data.get('content', '').strip()
        document.content = content_text
        
        document.save()
        
        # Verify the document was created properly
        assert document.pk is not None
        assert document.title == 'Test Document'
        assert document.created_by == user
        assert document.last_modified_by == user
        assert document.get_plain_text == 'This is test content'
        assert document.content == 'This is test content'
    
    def test_form_creates_document_with_empty_content(self, user):
        """Test that form properly handles empty content"""
        form_data = {
            'title': 'Empty Document'
            # No content
        }
        form = DocumentCreateForm(data=form_data)
        assert form.is_valid()
        
        # Simulate what the view does - store content as plain text
        document = form.save(commit=False)
        document.created_by = user
        document.last_modified_by = user
        
        # Content is stored as plain text directly (empty string)
        content_text = form.cleaned_data.get('content', '').strip()
        document.content = content_text
        
        document.save()
        
        # Verify the document was created properly
        assert document.pk is not None
        assert document.title == 'Empty Document'
        assert document.get_plain_text == ''
        assert document.content == ''


@pytest.mark.django_db
class TestDocumentFormLineEndingNormalization:
    """Test line ending normalization in forms."""
    
    def setup_method(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_document_form_normalizes_crlf_line_endings(self):
        """Test that DocumentForm normalizes CRLF line endings."""
        form_data = {'content': 'line 1\r\nline 2\r\nline 3'}
        form = DocumentForm(data=form_data)
        
        assert form.is_valid()
        
        # Content should be normalized to Unix line endings
        normalized_content = form.cleaned_data['content']
        assert normalized_content == 'line 1\nline 2\nline 3'
        assert '\r\n' not in normalized_content
        assert '\r' not in normalized_content
    
    def test_document_form_normalizes_cr_line_endings(self):
        """Test that DocumentForm normalizes CR-only line endings."""
        form_data = {'content': 'line 1\rline 2\rline 3'}
        form = DocumentForm(data=form_data)
        
        assert form.is_valid()
        
        # Content should be normalized to Unix line endings
        normalized_content = form.cleaned_data['content']
        assert normalized_content == 'line 1\nline 2\nline 3'
        assert '\r' not in normalized_content
    
    def test_document_form_preserves_unix_line_endings(self):
        """Test that DocumentForm preserves existing Unix line endings."""
        form_data = {'content': 'line 1\nline 2\nline 3'}
        form = DocumentForm(data=form_data)
        
        assert form.is_valid()
        
        # Content should remain unchanged
        normalized_content = form.cleaned_data['content']
        assert normalized_content == 'line 1\nline 2\nline 3'
    
    def test_document_form_normalizes_mixed_line_endings(self):
        """Test that DocumentForm handles mixed line endings."""
        form_data = {'content': 'line 1\r\nline 2\nline 3\rline 4'}
        form = DocumentForm(data=form_data)
        
        assert form.is_valid()
        
        # All line endings should be normalized to Unix
        normalized_content = form.cleaned_data['content']
        assert normalized_content == 'line 1\nline 2\nline 3\nline 4'
        assert '\r\n' not in normalized_content
        assert '\r' not in normalized_content