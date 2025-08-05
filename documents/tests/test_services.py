import pytest
from django.contrib.auth.models import User
from django.db import transaction
from documents.models import Document, DocumentChange
from documents.services import DocumentService
from documents.exceptions import VersionConflictError, InvalidChangeError


@pytest.mark.django_db
class TestDocumentService:
    """Test cases for DocumentService."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    @pytest.fixture
    def anonymous_user(self):
        """Get or create anonymous user."""
        user, _ = User.objects.get_or_create(
            username="anonymous",
            defaults={
                "first_name": "Anonymous",
                "last_name": "User",
                "email": "anonymous@example.com",
            },
        )
        return user

    def test_create_document_with_authenticated_user(self, user):
        """Test creating a document with an authenticated user."""
        title = "Test Document"
        content_text = "This is test content"
        
        document = DocumentService.create_document(
            title=title,
            content_text=content_text,
            user=user
        )
        
        assert document.title == title
        assert document.created_by == user
        assert document.last_modified_by == user
        assert document.version == 1
        assert document.get_plain_text == content_text
        
        # Check that change record was created
        changes = document.changes.all()
        assert changes.count() == 1
        change = changes.first()
        assert change.applied_by == user
        assert change.from_version == 0
        assert change.to_version == 1
        assert change.change_data["operation"] == "create"

    def test_create_document_with_anonymous_user(self, anonymous_user):
        """Test creating a document with anonymous user."""
        title = "Anonymous Document"
        
        document = DocumentService.create_document(
            title=title,
            user=None  # Should create anonymous user
        )
        
        assert document.title == title
        assert document.created_by.username == "anonymous"
        assert document.last_modified_by.username == "anonymous"
        
        # Check that change record was created
        changes = document.changes.all()
        assert changes.count() == 1

    def test_create_document_with_plain_text_content(self, user):
        """Test creating a document with plain text content."""
        title = "Plain Text Document"
        plain_text_content = "Custom plain text content"
        
        document = DocumentService.create_document(
            title=title,
            content_text=plain_text_content,
            user=user
        )
        
        assert document.content == plain_text_content
        assert "Custom plain text content" in document.get_plain_text

    def test_create_document_validation_errors(self, user):
        """Test document creation validation."""
        # Empty title
        with pytest.raises(ValueError, match="Title cannot be empty"):
            DocumentService.create_document(title="", user=user)
        
        # Title too long
        long_title = "x" * 256
        with pytest.raises(ValueError, match="Title cannot exceed 255 characters"):
            DocumentService.create_document(title=long_title, user=user)
        
        # Note: Plain text content doesn't require validation anymore
        # This test is no longer applicable since we switched to plain text
        pass

    def test_update_document_title_and_content(self, user):
        """Test updating both title and content."""
        # Create initial document
        document = DocumentService.create_document(
            title="Original Title",
            content_text="Original content",
            user=user
        )
        original_version = document.version
        
        # Update document
        updated_document = DocumentService.update_document(
            document=document,
            title="Updated Title",
            content_text="Updated content",
            user=user
        )
        
        assert updated_document.title == "Updated Title"
        assert updated_document.get_plain_text == "Updated content"
        assert updated_document.version == original_version + 1
        assert updated_document.last_modified_by == user
        
        # Check change record
        changes = document.changes.filter(to_version=updated_document.version)
        assert changes.count() == 1
        change = changes.first()
        assert change.applied_by == user
        assert change.from_version == original_version
        assert "title_change" in change.change_data
        assert "content_change" in change.change_data

    def test_update_document_title_only(self, user):
        """Test updating only the title."""
        document = DocumentService.create_document(
            title="Original Title",
            content_text="Original content",
            user=user
        )
        original_content = document.content
        original_version = document.version
        
        updated_document = DocumentService.update_document(
            document=document,
            title="New Title",
            user=user
        )
        
        assert updated_document.title == "New Title"
        assert updated_document.content == original_content
        assert updated_document.version == original_version + 1
        
        # Check change record
        changes = document.changes.filter(to_version=updated_document.version)
        change = changes.first()
        assert "title_change" in change.change_data
        assert "content_change" not in change.change_data

    def test_update_document_content_only(self, user):
        """Test updating only the content."""
        document = DocumentService.create_document(
            title="Test Title",
            content_text="Original content",
            user=user
        )
        original_title = document.title
        original_version = document.version
        
        updated_document = DocumentService.update_document(
            document=document,
            content_text="New content",
            user=user
        )
        
        assert updated_document.title == original_title
        assert updated_document.get_plain_text == "New content"
        assert updated_document.version == original_version + 1
        
        # Check change record
        changes = document.changes.filter(to_version=updated_document.version)
        change = changes.first()
        assert "content_change" in change.change_data
        assert "title_change" not in change.change_data

    def test_update_document_no_changes(self, user):
        """Test update with no actual changes."""
        document = DocumentService.create_document(
            title="Test Title",
            content_text="Test content",
            user=user
        )
        original_version = document.version
        original_change_count = document.changes.count()
        
        # Update with same values
        updated_document = DocumentService.update_document(
            document=document,
            title="Test Title",
            content_text="Test content",
            user=user
        )
        
        # Should not increment version or create change record
        assert updated_document.version == original_version
        assert document.changes.count() == original_change_count

    def test_update_document_version_conflict(self, user):
        """Test version conflict detection."""
        document = DocumentService.create_document(
            title="Test Title",
            user=user
        )
        
        with pytest.raises(VersionConflictError):
            DocumentService.update_document(
                document=document,
                title="New Title",
                user=user,
                expected_version=999  # Wrong version
            )

    def test_update_document_validation_errors(self, user):
        """Test update validation."""
        document = DocumentService.create_document(title="Test", user=user)
        
        # No user
        with pytest.raises(ValueError, match="User is required"):
            DocumentService.update_document(document=document, title="New Title")
        
        # Empty title
        with pytest.raises(ValueError, match="Title cannot be empty"):
            DocumentService.update_document(document=document, title="", user=user)
        
        # Title too long
        long_title = "x" * 256
        with pytest.raises(ValueError, match="Title cannot exceed 255 characters"):
            DocumentService.update_document(document=document, title=long_title, user=user)

    def test_apply_changes_success(self, user):
        """Test applying structured OT changes."""
        document = DocumentService.create_document(
            title="Test Document",
            content_text="Hello world",
            user=user
        )
        original_version = document.version
        
        # OT operations: retain "Hello ", delete "world", insert "universe"
        changes = [
            {"operation": "retain", "length": 6},  # "Hello "
            {"operation": "delete", "length": 5},  # "world"
            {"operation": "insert", "content": "universe"}  # "universe"
        ]
        
        updated_document = DocumentService.apply_changes(
            document=document,
            changes=changes,
            user=user,
            expected_version=original_version
        )
        
        assert "Hello universe" in updated_document.get_plain_text
        assert updated_document.version == original_version + 1
        
        # Check change record
        change_records = document.changes.filter(to_version=updated_document.version)
        assert change_records.count() == 1
        change_record = change_records.first()
        assert change_record.change_data == changes

    def test_apply_changes_version_conflict(self, user):
        """Test version conflict in apply_changes."""
        document = DocumentService.create_document(title="Test", user=user)
        
        changes = [{"operation": "insert", "content": "new text"}]
        
        with pytest.raises(VersionConflictError):
            DocumentService.apply_changes(
                document=document,
                changes=changes,
                user=user,
                expected_version=999
            )

    def test_apply_changes_validation_errors(self, user):
        """Test apply_changes validation."""
        document = DocumentService.create_document(title="Test", user=user)
        
        # No user
        with pytest.raises(ValueError, match="User is required"):
            DocumentService.apply_changes(document, [], None, document.version)
        
        # No changes
        with pytest.raises(ValueError, match="At least one change is required"):
            DocumentService.apply_changes(document, [], user, document.version)

    def test_preview_changes_success(self, user):
        """Test preview changes functionality."""
        document = DocumentService.create_document(
            title="Test Document",
            content_text="Hello world",
            user=user
        )
        
        # OT operations: retain "Hello ", delete "world", insert "universe"
        changes = [
            {"operation": "retain", "length": 6},  # "Hello "
            {"operation": "delete", "length": 5},  # "world"
            {"operation": "insert", "content": "universe"}  # "universe"
        ]
        
        preview = DocumentService.preview_changes(document, changes)
        
        assert preview["document_id"] == document.id
        assert preview["current_version"] == document.version
        assert "preview" in preview

    def test_preview_changes_validation(self, user):
        """Test preview changes validation."""
        document = DocumentService.create_document(title="Test", user=user)
        
        with pytest.raises(ValueError, match="No changes provided"):
            DocumentService.preview_changes(document, [])

    def test_get_change_history(self, user):
        """Test getting change history."""
        document = DocumentService.create_document(
            title="Test Document",
            content_text="Original content",
            user=user
        )
        
        # Make some updates
        DocumentService.update_document(
            document=document,
            title="Updated Title",
            user=user
        )
        
        DocumentService.update_document(
            document=document,
            content_text="Updated content",
            user=user
        )
        
        # Get history
        history = DocumentService.get_change_history(document)
        
        assert history.count() == 3  # Create + 2 updates
        
        # Test with limit
        limited_history = DocumentService.get_change_history(document, limit=2)
        assert len(list(limited_history)) == 2

    def test_atomic_operations(self, user):
        """Test that operations are atomic."""
        document = DocumentService.create_document(title="Test", user=user)
        
        # Mock a scenario where the change record creation fails
        # This ensures the document update is rolled back
        original_version = document.version
        
        with pytest.raises(Exception):
            with transaction.atomic():
                DocumentService.update_document(
                    document=document,
                    title="New Title",
                    user=user
                )
                # Force an exception after the update
                raise Exception("Simulated failure")
        
        # Refresh from database
        document.refresh_from_db()
        # Should still have original version due to rollback
        assert document.version == original_version
        assert document.title == "Test"