from typing import Dict, Any, List, Optional
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import transaction
from django.db.models import Q
from .models import Document, DocumentChange
# No utility imports needed - working directly with plain text
from .exceptions import VersionConflictError, InvalidChangeError
from .operational_transforms import OTOperation, OTOperationSet, OperationType
import logging
import time

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Centralized service for all document operations.
    
    This service ensures consistent behavior across API and web interfaces
    for document creation, updates, and change tracking.
    """

    @staticmethod
    def _convert_changes_to_ot_operations(changes: List[Dict[str, Any]]) -> List[OTOperation]:
        """
        Convert operation dictionaries to OTOperation objects.
        
        Args:
            changes: List of operation dictionaries
            
        Returns:
            List of OTOperation objects
            
        Raises:
            InvalidChangeError: If operations are invalid
        """
        if not changes:
            raise InvalidChangeError("At least one operation is required")
        
        ot_operations = []
        
        for i, change in enumerate(changes):
            if not isinstance(change, dict):
                raise InvalidChangeError(f"Operation {i+1} must be a dictionary")
                
            operation = change.get("operation")
            if operation not in ["retain", "insert", "delete"]:
                raise InvalidChangeError(
                    f"Operation {i+1}: Unsupported operation '{operation}'. "
                    f"Supported operations: 'retain', 'insert', 'delete'"
                )
            
            try:
                if operation == "retain":
                    length = change.get("length")
                    if not isinstance(length, int) or length <= 0:
                        raise InvalidChangeError(f"Operation {i+1}: Retain operation requires positive length")
                    ot_operations.append(OTOperation(OperationType.RETAIN, length=length))
                    
                elif operation == "insert":
                    content = change.get("content")
                    if not isinstance(content, str) or len(content) == 0:
                        raise InvalidChangeError(f"Operation {i+1}: Insert operation requires non-empty content")
                    ot_operations.append(OTOperation(OperationType.INSERT, content=content))
                    
                elif operation == "delete":
                    length = change.get("length")
                    if not isinstance(length, int) or length <= 0:
                        raise InvalidChangeError(f"Operation {i+1}: Delete operation requires positive length")
                    ot_operations.append(OTOperation(OperationType.DELETE, length=length))
                    
            except Exception as e:
                raise InvalidChangeError(f"Operation {i+1}: {str(e)}")
        
        logger.info(f"Converted {len(changes)} operations to OT operations")
        return ot_operations

    @staticmethod
    def create_document(
        title: str,
        content_text: Optional[str] = None,
        user: Optional[User] = None
    ) -> Document:
        """
        Create a new document with plain text content.
        
        Args:
            title: Document title
            content_text: Plain text content
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

        # Handle content - just use the plain text directly
        final_content = content_text.strip() if content_text else ""

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
        content_text: Optional[str] = None,
        user: User = None,
        expected_version: Optional[int] = None
    ) -> Document:
        """
        Update a document with proper change tracking.
        
        Args:
            document: Document to update
            title: New title (optional)
            content_text: New plain text content (optional)
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
            if content_text is not None:
                new_content = content_text.strip()
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
                if content_text is not None and document.content != original_content:
                    change_data["content_change"] = {
                        "operation": "update", 
                        "via": "text"
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

        # Get current plain text (content is already plain text)
        original_text = document.content

        # Apply changes using OT operations
        try:
            logger.info(f"DocumentService.apply_changes: Converting {len(changes)} operations")
            ot_operations = DocumentService._convert_changes_to_ot_operations(changes)
            operation_set = OTOperationSet(ot_operations)
            
            logger.info(f"Applying OT operations to text: '{original_text}' (length: {len(original_text)})")
            new_text = operation_set.apply(original_text)
            logger.info(f"OT result: '{new_text}' (length: {len(new_text)})")
        except Exception as e:
            logger.error(f"Failed to apply changes: {str(e)}")
            raise InvalidChangeError(f"Failed to apply changes: {str(e)}")

        with transaction.atomic():
            # Update document content directly with plain text
            document.content = new_text
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
            logger.info(f"DocumentService.preview_changes: Converting {len(changes)} operations")
            ot_operations = DocumentService._convert_changes_to_ot_operations(changes)
            operation_set = OTOperationSet(ot_operations)
            
            original_text = document.content
            logger.info(f"Previewing OT operations on text: '{original_text}' (length: {len(original_text)})")
            
            # Apply operations to get preview result
            preview_text = operation_set.apply(original_text)
            logger.info(f"Preview result: '{preview_text}' (length: {len(preview_text)})")
            
            preview_result = {
                "original_text": original_text,
                "preview_text": preview_text,
                "operations": [op.to_dict() for op in ot_operations],
                "operation_count": len(ot_operations)
            }

            return {
                "document_id": document.id,
                "current_version": document.version,
                "preview": preview_result,
            }
        except Exception as e:
            logger.error(f"Preview failed: {str(e)}")
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

    @staticmethod
    def search_documents(
        query: str, 
        user: Optional[User] = None, 
        limit: int = 20,
        user_only: bool = False
    ) -> Dict[str, Any]:
        """
        Search documents using PostgreSQL full-text search.
        
        Args:
            query: Search query string
            user: User performing the search (for permission filtering)
            limit: Maximum number of results to return
            user_only: If True, search only the user's documents
            
        Returns:
            Dict containing search results and metadata
        """
        start_time = time.time()
        
        # Handle empty query
        if not query or not query.strip():
            return {
                "documents": Document.objects.none(),
                "query": query,
                "total_results": 0,
                "search_time": 0,
                "user_only": user_only
            }
        
        query = query.strip()
        
        # Create search query and ranking
        search_query = SearchQuery(query)
        
        # Base queryset with search filtering and ranking
        queryset = Document.objects.annotate(
            rank=SearchRank('search_vector', search_query)
        ).filter(
            search_vector=search_query
        ).filter(
            rank__gt=0  # Only include documents with positive relevance
        ).order_by('-rank', '-updated_at')
        
        # Apply permission filtering
        if user_only and user and user.is_authenticated:
            # Search only user's documents
            queryset = queryset.filter(created_by=user)
        elif user and user.is_authenticated:
            # For now, users can search all documents
            # In the future, this could be refined for permission-based filtering
            pass
        else:
            # Anonymous users - limit to some public scope or no results
            # For security, return no results for anonymous users
            queryset = Document.objects.none()
        
        # Apply limit
        if limit and limit > 0:
            # Limit to reasonable maximum
            limit = min(limit, 100)
            total_count = queryset.count()
            queryset = queryset[:limit]
        else:
            total_count = queryset.count()
            queryset = queryset[:20]  # Default limit
        
        search_time = round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds
        
        logger.info(f"Search query '{query}' returned {total_count} results in {search_time}ms")
        
        return {
            "documents": queryset,
            "query": query,
            "total_results": total_count,
            "search_time": search_time,
            "user_only": user_only
        }

    @staticmethod
    def search_user_documents(
        query: str, 
        user: User, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search only the user's own documents.
        
        Args:
            query: Search query string
            user: User whose documents to search
            limit: Maximum number of results to return
            
        Returns:
            Dict containing search results and metadata
        """
        return DocumentService.search_documents(
            query=query,
            user=user,
            limit=limit,
            user_only=True
        )