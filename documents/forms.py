from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Div
from .models import Document


class DocumentForm(forms.ModelForm):
    # Override content field to accept plain text
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 15,
            'placeholder': 'Start typing your document content...'
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
        # For now, just use the standard Django ModelForm save
        # Content processing and user assignment is handled in the view
        return super().save(commit=commit)


class DocumentCreateForm(DocumentForm):
    """Specialized form for creating documents"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make content optional for creation
        self.fields['content'].required = False
        self.fields['content'].widget.attrs['placeholder'] = 'Start typing your document content... (optional)'