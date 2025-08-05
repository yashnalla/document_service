from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Div
from .models import Document


class DocumentForm(forms.ModelForm):
    """Form for editing document content only (title is immutable after creation)"""
    # Override content field to accept plain text
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 15,
            'placeholder': 'Start typing your document content...'
        }),
        required=False,
        help_text="Enter your document content as plain text"
    )
    
    def clean_content(self):
        """Clean and normalize line endings in content."""
        content = self.cleaned_data.get('content', '')
        # Normalize line endings to Unix format for consistency
        # First convert \r\n to \n (Windows to Unix)
        # Then convert remaining \r to \n (classic Mac to Unix)
        normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
        return normalized_content
    
    class Meta:
        model = Document
        fields = ['content']  # Only content field - title is immutable

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('content', css_class='mb-3'),
        )
        # Don't add form tags - we'll handle them in templates
        self.helper.form_tag = False

    def save(self, commit=True, user=None):
        # Content processing and user assignment is handled in the view
        return super().save(commit=commit)


class DocumentCreateForm(forms.ModelForm):
    """Form for creating new documents with title and content"""
    # Override content field to accept plain text
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 15,
            'placeholder': 'Start typing your document content... (optional)'
        }),
        required=False,
        help_text="Enter your document content as plain text"
    )
    
    class Meta:
        model = Document
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter document title...',
                'class': 'form-control-lg'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('title', css_class='mb-3'),
            Field('content', css_class='mb-3'),
        )
        # Don't add form tags - we'll handle them in templates
        self.helper.form_tag = False

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise forms.ValidationError('Title is required.')
        return title.strip()

    def save(self, commit=True, user=None):
        # Content processing and user assignment is handled in the view
        return super().save(commit=commit)