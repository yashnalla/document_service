import pytest
import json
from unittest.mock import Mock, patch
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from documents.api_client import (
    DocumentAPIClient,
    APIClientError,
    APIAuthenticationError,
    APIValidationError,
    APIConflictError,
    APIClientMixin
)
from documents.models import Document


@pytest.mark.django_db
class TestDocumentAPIClient:
    """Test cases for DocumentAPIClient class."""
    
    def test_client_initialization(self, user):
        """Test API client initialization."""
        client = DocumentAPIClient(user)
        
        assert client.user == user
        assert client.base_url == "http://localhost:8000/api"
        assert client._token is None
    
    def test_client_initialization_with_custom_base_url(self, user):
        """Test API client initialization with custom base URL."""
        custom_url = "https://example.com/api"
        client = DocumentAPIClient(user, base_url=custom_url)
        
        assert client.base_url == custom_url
    
    def test_token_property_creates_token(self, user):
        """Test that token property creates token for authenticated user."""
        client = DocumentAPIClient(user)
        
        # Should create token on first access
        token = client.token
        assert token is not None
        assert isinstance(token, str)
        
        # Should return same token on subsequent access
        token2 = client.token
        assert token == token2
        
        # Verify token was created in database
        db_token = Token.objects.get(user=user)
        assert db_token.key == token
    
    def test_token_property_unauthenticated_user(self):
        """Test that token property raises error for unauthenticated user."""
        user = Mock()
        user.is_authenticated = False
        
        client = DocumentAPIClient(user)
        
        with pytest.raises(APIAuthenticationError, match="User is not authenticated"):
            _ = client.token
    
    def test_is_testing_detection(self):
        """Test that client correctly detects test environment."""
        with patch('documents.api_client.sys.modules', {'pytest': Mock()}):
            user = Mock()
            user.is_authenticated = True
            client = DocumentAPIClient(user)
            assert client._is_testing() is True
    
    def test_test_client_initialization(self, user):
        """Test that test client is initialized in test mode."""
        client = DocumentAPIClient(user)
        
        # In test environment, should use test client
        assert client._use_test_client is True
        assert hasattr(client, '_test_client')
    
    def test_get_document_success(self, user, document_factory):
        """Test successful document retrieval."""
        document = document_factory(title="Test Doc", content_text="Test content")
        client = DocumentAPIClient(user)
        
        result = client.get_document(str(document.id))
        
        assert result["id"] == str(document.id)
        assert result["title"] == "Test Doc"
        assert "content" in result
    
    def test_get_document_not_found(self, user):
        """Test document retrieval with non-existent document."""
        client = DocumentAPIClient(user)
        
        with pytest.raises(APIClientError, match="Document not found"):
            client.get_document("00000000-0000-0000-0000-000000000000")
    
    def test_create_document_success(self, user):
        """Test successful document creation."""
        client = DocumentAPIClient(user)
        
        title = "New Test Document"
        content = "This is test content"
        
        result = client.create_document(title, content)
        
        assert result["title"] == title
        assert result["content"] == content
        assert "id" in result
        assert "version" in result
    
    def test_create_document_validation_error(self, user):
        """Test document creation with validation error."""
        client = DocumentAPIClient(user)
        
        # Empty title should cause validation error
        with pytest.raises(APIValidationError):
            client.create_document("", {})
    
    def test_update_document_success(self, user, document_factory):
        """Test successful document update."""
        document = document_factory(title="Original", content_text="Original content")
        client = DocumentAPIClient(user)
        
        new_title = "Updated Title"
        result = client.update_document(str(document.id), title=new_title)
        
        assert result["title"] == new_title
        assert result["id"] == str(document.id)
    
    def test_update_document_not_found(self, user):
        """Test document update with non-existent document."""
        client = DocumentAPIClient(user)
        
        with pytest.raises(APIClientError, match="Document not found"):
            client.update_document("00000000-0000-0000-0000-000000000000", title="New Title")
    
    def test_update_document_no_data(self, user, document_factory):
        """Test document update with no data provided."""
        document = document_factory(title="Test", content_text="Test")
        client = DocumentAPIClient(user)
        
        with pytest.raises(APIClientError, match="No data provided for update"):
            client.update_document(str(document.id))
    
    def test_apply_changes_success(self, user, document_factory):
        """Test successful application of changes."""
        document = document_factory(title="Test", content_text="Hello World")
        client = DocumentAPIClient(user)
        
        changes = [
            {"operation": "retain", "length": 6},
            {"operation": "delete", "length": 5},
            {"operation": "insert", "content": "Universe"}
        ]
        
        result = client.apply_changes(str(document.id), document.version, changes)
        
        assert result["id"] == str(document.id)
        assert result["version"] == document.version + 1
        # Verify the content was changed
        document.refresh_from_db()
        assert "Universe" in document.get_plain_text
    
    def test_apply_changes_version_conflict(self, user, document_factory):
        """Test apply changes with version conflict."""
        document = document_factory(title="Test", content_text="Hello World")
        client = DocumentAPIClient(user)
        
        changes = [{"operation": "insert", "content": "Hi "}]
        wrong_version = 999
        
        with pytest.raises(APIConflictError) as exc_info:
            client.apply_changes(str(document.id), wrong_version, changes)
        
        assert exc_info.value.current_version == document.version
    
    def test_apply_changes_validation_error(self, user, document_factory):
        """Test apply changes with invalid changes."""
        document = document_factory(title="Test", content_text="Hello")
        client = DocumentAPIClient(user)
        
        # Invalid operation type
        changes = [{"operation": "invalid", "content": "test"}]
        
        with pytest.raises((APIValidationError, APIClientError)):
            client.apply_changes(str(document.id), document.version, changes)
    
    def test_get_change_history_success(self, user, document_factory):
        """Test successful retrieval of change history."""
        document = document_factory(title="Test", content_text="Test content")
        client = DocumentAPIClient(user)
        
        # Make a change to ensure there's history
        changes = [{"operation": "retain", "length": 4}, {"operation": "insert", "content": " more"}]
        client.apply_changes(str(document.id), document.version, changes)
        
        result = client.get_change_history(str(document.id))
        
        assert "results" in result or isinstance(result, list)
        # Should have at least one change now
        if "results" in result:
            assert len(result["results"]) >= 1
        else:
            assert len(result) >= 1
    
    def test_get_change_history_with_pagination(self, user, document_factory):
        """Test change history retrieval with pagination."""
        document = document_factory(title="Test", content_text="Test content")
        client = DocumentAPIClient(user)
        
        result = client.get_change_history(str(document.id), limit=5, offset=0)
        
        assert isinstance(result, (list, dict))
    
    def test_preview_changes_success(self, user, document_factory):
        """Test successful change preview."""
        document = document_factory(title="Test", content_text="Hello World")
        client = DocumentAPIClient(user)
        
        changes = [
            {"operation": "retain", "length": 6},
            {"operation": "insert", "content": "Beautiful "}
        ]
        
        result = client.preview_changes(str(document.id), changes)
        
        assert "document_id" in result
        assert "preview" in result
    
    def test_preview_changes_validation_error(self, user, document_factory):
        """Test change preview with invalid changes."""
        document = document_factory(title="Test", content_text="Hello")
        client = DocumentAPIClient(user)
        
        # Invalid changes
        changes = [{"operation": "invalid", "content": "test"}]
        
        with pytest.raises(APIValidationError):
            client.preview_changes(str(document.id), changes)


@pytest.mark.django_db 
class TestAPIClientMixin:
    """Test cases for APIClientMixin class."""
    
    class TestView(APIClientMixin):
        """Mock view class for testing mixin."""
        def __init__(self, user):
            self.request = Mock()
            self.request.user = user
    
    def test_get_api_client(self, user):
        """Test getting API client from mixin."""
        view = self.TestView(user)
        
        client = view.get_api_client()
        
        assert isinstance(client, DocumentAPIClient)
        assert client.user == user
    
    def test_get_api_client_caching(self, user):
        """Test that API client is cached."""
        view = self.TestView(user)
        
        client1 = view.get_api_client()
        client2 = view.get_api_client()
        
        assert client1 is client2  # Should be same instance
    
    def test_handle_api_conflict_error(self, user):
        """Test handling API conflict error."""
        view = self.TestView(user)
        error = APIConflictError("Version conflict", current_version=5)
        
        response = view.handle_api_error(error)
        
        assert response.status_code == 409
        data = json.loads(response.content)
        assert data["success"] is False
        assert data["error_type"] == "version_conflict"
        assert data["current_version"] == 5
    
    def test_handle_api_validation_error(self, user):
        """Test handling API validation error."""
        view = self.TestView(user)
        error = APIValidationError("Invalid data")
        
        response = view.handle_api_error(error)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["success"] is False
        assert data["error_type"] == "validation_error"
    
    def test_handle_api_authentication_error(self, user):
        """Test handling API authentication error."""
        view = self.TestView(user)
        error = APIAuthenticationError("Access denied")
        
        response = view.handle_api_error(error)
        
        assert response.status_code == 403
        data = json.loads(response.content)
        assert data["success"] is False
        assert data["error_type"] == "authentication_error"
    
    def test_handle_generic_api_error(self, user):
        """Test handling generic API error."""
        view = self.TestView(user)
        error = APIClientError("Something went wrong")
        
        response = view.handle_api_error(error)
        
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data["success"] is False
        assert data["error_type"] == "api_error"
    
    def test_api_success_response(self, user):
        """Test creating API success response."""
        view = self.TestView(user)
        data = {"id": "123", "title": "Test"}
        message = "Success!"
        
        response = view.api_success_response(data, message)
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["success"] is True
        assert response_data["data"] == data
        assert response_data["message"] == message
    
    def test_api_success_response_no_message(self, user):
        """Test creating API success response without message."""
        view = self.TestView(user)
        data = {"id": "123", "title": "Test"}
        
        response = view.api_success_response(data)
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["success"] is True
        assert response_data["data"] == data
        assert "message" not in response_data


@pytest.mark.django_db
class TestAPIClientIntegration:
    """Integration tests for API client with real API endpoints."""
    
    def test_full_document_workflow(self, user):
        """Test complete document workflow through API client."""
        client = DocumentAPIClient(user)
        
        # 1. Create document
        title = "Integration Test Document"
        content = "Initial content"
        
        created_doc = client.create_document(title, content)
        doc_id = created_doc["id"]
        
        assert created_doc["title"] == title
        assert created_doc["version"] == 1
        
        # 2. Retrieve document
        retrieved_doc = client.get_document(doc_id)
        assert retrieved_doc["id"] == doc_id
        assert retrieved_doc["title"] == title
        
        # 3. Apply changes
        changes = [
            {"operation": "retain", "length": 7},     # Keep "Initial"
            {"operation": "delete", "length": 8},     # Delete " content"
            {"operation": "insert", "content": " text updated"}  # Insert new text
        ]
        
        updated_doc = client.apply_changes(doc_id, 1, changes)
        assert updated_doc["version"] == 2
        
        # 4. Get change history
        history = client.get_change_history(doc_id)
        # Should have creation + update changes
        if "results" in history:
            assert len(history["results"]) >= 2
        else:
            assert len(history) >= 2
        
        # 5. Preview more changes
        preview_changes = [{"operation": "insert", "content": "Preview: "}]
        preview = client.preview_changes(doc_id, preview_changes)
        assert "preview" in preview
        
        # 6. Verify final document state (skip delete as it's removed from design)
        # Title is immutable after creation, so we just verify the document is in expected state
        final_doc = client.get_document(doc_id)
        assert final_doc["title"] == title  # Original title should be unchanged
        assert final_doc["version"] == 2  # Should be version 2 from the changes we applied
    
    def test_concurrent_operations_handling(self, user):
        """Test handling concurrent operations and version conflicts."""
        client1 = DocumentAPIClient(user)
        client2 = DocumentAPIClient(user)
        
        # Create document with client1
        title = "Concurrent Test"
        content = ""
        doc = client1.create_document(title, content)
        doc_id = doc["id"]
        
        # Both clients try to make changes
        changes1 = [{"operation": "insert", "content": "Client 1 change"}]
        changes2 = [{"operation": "insert", "content": "Client 2 change"}]
        
        # First change should succeed
        updated_doc = client1.apply_changes(doc_id, 1, changes1)
        assert updated_doc["version"] == 2
        
        # Second change should fail due to version conflict
        with pytest.raises(APIConflictError) as exc_info:
            client2.apply_changes(doc_id, 1, changes2)  # Still using version 1
        
        assert exc_info.value.current_version == 2
        
        # Client2 can succeed with correct version
        updated_doc2 = client2.apply_changes(doc_id, 2, changes2)
        assert updated_doc2["version"] == 3
    
    def test_large_document_operations(self, user):
        """Test API client with large documents."""
        client = DocumentAPIClient(user)
        
        # Create a large document
        large_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 500
        content = large_text
        
        doc = client.create_document("Large Document", content)
        doc_id = doc["id"]
        
        # Make changes to large document
        changes = [
            {"operation": "retain", "length": 100},
            {"operation": "insert", "content": "INSERTED CONTENT "},
            {"operation": "retain", "length": 100}
        ]
        
        updated_doc = client.apply_changes(doc_id, 1, changes)
        assert updated_doc["version"] == 2
        
        # Verify the change was applied
        retrieved = client.get_document(doc_id)
        # Document should contain the inserted content
        doc_text = Document.objects.get(id=doc_id).get_plain_text
        assert "INSERTED CONTENT" in doc_text
    
    def test_error_handling_edge_cases(self, user):
        """Test API client error handling in edge cases."""
        client = DocumentAPIClient(user)
        
        # Test with malformed UUID
        with pytest.raises(APIClientError):
            client.get_document("not-a-uuid")
        
        # Test with empty changes - this should raise a validation error
        doc = client.create_document("Test", "")
        
        # Empty changes should raise validation error
        with pytest.raises((APIValidationError, APIClientError)):
            client.apply_changes(doc["id"], 1, [])
    
    def test_unicode_and_special_characters(self, user):
        """Test API client with Unicode and special characters."""
        client = DocumentAPIClient(user)
        
        # Create document with Unicode content
        title = "Unicode Test 测试 🚀"
        content = "Hello 世界! 🌍 Special chars: @#$%^&*()"
        
        doc = client.create_document(title, content)
        assert doc["title"] == title
        
        # Apply changes with Unicode  
        # Get the actual content to calculate correct retain length
        doc_obj = Document.objects.get(id=doc["id"])
        current_text = doc_obj.get_plain_text
        remaining_length = len(current_text) - 5
        
        changes = [
            {"operation": "retain", "length": 5},  # "Hello"
            {"operation": "insert", "content": " 你好"},
            {"operation": "retain", "length": remaining_length}  # Rest of content
        ]
        
        updated_doc = client.apply_changes(doc["id"], 1, changes)
        assert updated_doc["version"] == 2
        
        # Verify Unicode handling
        retrieved = client.get_document(doc["id"])
        doc_obj = Document.objects.get(id=doc["id"])
        doc_text = doc_obj.get_plain_text
        assert "你好" in doc_text