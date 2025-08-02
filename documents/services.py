from typing import Dict, Any, List, Optional
from django.contrib.auth.models import User
from django.db import transaction
from .models import Document, DocumentChange
from .utils import create_basic_lexical_content, update_lexical_content_with_text
from .exceptions import VersionConflictError, InvalidChangeError
from .change_operations import ChangeProcessor


class DocumentService:
    """
    Centralized service for all document operations.
    
    This service ensures consistent behavior across API and web interfaces
    for document creation, updates, and change tracking.
    """

    @staticmethod
    def create_document(
        title: str,
        content: Optional[Dict[str, Any]] = None,
        content_text: Optional[str] = None,
        user: Optional[User] = None
    ) -> Document:
        """
        Create a new document with proper content handling and user assignment.
        
        Args:
            title: Document title
            content: Lexical content (if provided, takes precedence over content_text)
            content_text: Plain text content (converted to Lexical format)
            user: User creating the document (uses anonymous user if None)
            
        Returns:
            Document: The created document
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
            
        title = title.strip()
        if len(title) > 255:
            raise ValueError("Title cannot exceed 255 characters")

        # Handle user assignment
        if not user or not user.is_authenticated:
            # Create or get anonymous user
            user, _ = User.objects.get_or_create(
                username="anonymous",
                defaults={
                    "first_name": "Anonymous",
                    "last_name": "User",
                    "email": "anonymous@example.com",
                },
            )

        # Handle content processing
        if content is not None:
            # Validate provided Lexical content
            if not isinstance(content, dict):
                raise ValueError("Content must be a valid JSON object")
            final_content = content
        elif content_text is not None:
            content_text = content_text.strip()
            if content_text:
                # Convert plain text to Lexical format
                final_content = create_basic_lexical_content(content_text)
            else:
                # Empty content - create empty structure
                final_content = {
                    "root": {
                        "type": "root",
                        "children": [],
                        "direction": "ltr",
                        "format": "",
                        "indent": 0,
                        "version": 1
                    }
                }
        else:
            # Create empty content
            final_content = {
                "root": {
                    "type": "root",
                    "children": [],
                    "direction": "ltr",
                    "format": "",
                    "indent": 0,
                    "version": 1
                }
            }

        # Create document
        document = Document.objects.create(
            title=title,
            content=final_content,
            created_by=user,
            last_modified_by=user,
        )

        # Create initial change record
        DocumentChange.objects.create(
            document=document,
            change_data={"operation": "create", "initial_content": True},
            applied_by=user,
            from_version=0,
            to_version=document.version,
        )

        return document

    @staticmethod
    def update_document(
        document: Document,
        title: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
        content_text: Optional[str] = None,
        user: User = None,
        expected_version: Optional[int] = None
    ) -> Document:
        """
        Update a document with proper change tracking.
        
        Args:
            document: Document to update
            title: New title (optional)
            content: New Lexical content (optional, takes precedence over content_text)
            content_text: New plain text content (optional, converted to Lexical)
            user: User making the change
            expected_version: Expected current version for conflict detection (optional)
            
        Returns:
            Document: The updated document
        """
        if not user:
            raise ValueError("User is required for document updates")

        # Check version conflict if expected_version is provided
        if expected_version is not None and document.version != expected_version:
            raise VersionConflictError(
                f"Version conflict: expected {expected_version}, got {document.version}"
            )

        changes_made = False
        original_title = document.title
        original_content = document.content

        with transaction.atomic():
            # Update title if provided
            if title is not None:
                title = title.strip()
                if not title:
                    raise ValueError("Title cannot be empty")
                if len(title) > 255:
                    raise ValueError("Title cannot exceed 255 characters")
                if title != document.title:
                    document.title = title
                    changes_made = True

            # Update content if provided
            if content is not None:
                if not isinstance(content, dict):
                    raise ValueError("Content must be a valid JSON object")
                if content != document.content:
                    document.content = content
                    changes_made = True
            elif content_text is not None:
                content_text = content_text.strip()
                if content_text:
                    # Convert plain text to Lexical format
                    new_content = create_basic_lexical_content(content_text)
                else:
                    # Empty content - create empty structure
                    new_content = {
                        "root": {
                            "type": "root",
                            "children": [],
                            "direction": "ltr",
                            "format": "",
                            "indent": 0,
                            "version": 1
                        }
                    }
                if new_content != document.content:
                    document.content = new_content
                    changes_made = True

            if changes_made:
                document.last_modified_by = user
                document.save()

                # Create change record
                change_data = {}
                if title is not None and title != original_title:
                    change_data["title_change"] = {
                        "from": original_title,
                        "to": document.title
                    }
                if (content is not None and content != original_content) or \
                   (content_text is not None and document.content != original_content):
                    change_data["content_change"] = {
                        "operation": "update",
                        "via": "content" if content is not None else "text"
                    }

                DocumentChange.objects.create(
                    document=document,
                    change_data=change_data,
                    applied_by=user,
                    from_version=document.version - 1,
                    to_version=document.version,
                )

        return document

    @staticmethod
    def apply_changes(
        document: Document,
        changes: List[Dict[str, Any]],
        user: User,
        expected_version: int
    ) -> Document:
        """
        Apply structured changes to a document with change tracking.
        
        Args:
            document: Document to modify
            changes: List of change operations
            user: User applying the changes
            expected_version: Expected current version
            
        Returns:
            Document: The updated document
        """
        if not user:
            raise ValueError("User is required for applying changes")

        if not changes:
            raise ValueError("At least one change is required")

        # Check version conflict
        if document.version != expected_version:
            raise VersionConflictError(
                f"Version conflict: expected {expected_version}, got {document.version}"
            )

        # Get current plain text
        original_text = document.get_plain_text()

        # Apply changes
        try:
            processor = ChangeProcessor(changes)
            new_text = processor.apply_changes(original_text)
        except Exception as e:
            raise InvalidChangeError(f"Failed to apply changes: {str(e)}")

        with transaction.atomic():
            # Update document content
            document.content = update_lexical_content_with_text(document.content, new_text)
            document.last_modified_by = user
            document.save()

            # Record the change
            DocumentChange.objects.create(
                document=document,
                change_data=changes,
                applied_by=user,
                from_version=expected_version,
                to_version=document.version,
            )

        return document

    @staticmethod
    def preview_changes(
        document: Document,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Preview changes without applying them to the document.
        
        Args:
            document: Document to preview changes on
            changes: List of change operations
            
        Returns:
            Dict: Preview result with document info and changes
        """
        if not changes:
            raise ValueError("No changes provided")

        try:
            processor = ChangeProcessor(changes)
            original_text = document.get_plain_text()
            preview_result = processor.preview_changes(original_text)

            return {
                "document_id": document.id,
                "current_version": document.version,
                "preview": preview_result,
            }
        except Exception as e:
            raise InvalidChangeError(f"Preview failed: {str(e)}")

    @staticmethod
    def get_change_history(document: Document, limit: Optional[int] = None):
        """
        Get change history for a document.
        
        Args:
            document: Document to get history for
            limit: Maximum number of changes to return (optional)
            
        Returns:
            QuerySet: DocumentChange objects for the document
        """
        queryset = document.changes.all()
        if limit:
            queryset = queryset[:limit]
        return queryset