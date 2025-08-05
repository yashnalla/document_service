import pytest
from documents.content_diff import ContentDiffGenerator
from documents.models import Document
from documents.operational_transforms import OTOperation, OTOperationSet, OperationType


def apply_operations_to_text(operations_data, text):
    """Helper function to apply operation dictionaries to text using OTOperationSet."""
    ot_operations = []
    for op_data in operations_data:
        operation = op_data.get("operation")
        if operation == "retain":
            ot_operations.append(OTOperation(OperationType.RETAIN, length=op_data["length"]))
        elif operation == "insert":
            ot_operations.append(OTOperation(OperationType.INSERT, content=op_data["content"]))
        elif operation == "delete":
            ot_operations.append(OTOperation(OperationType.DELETE, length=op_data["length"]))
    
    operation_set = OTOperationSet(ot_operations)
    return operation_set.apply(text)


@pytest.mark.django_db
class TestContentDiffGenerator:
    """Test cases for ContentDiffGenerator class."""
    
    def test_create_api_payload_no_changes(self):
        """Test creating API payload when there are no changes."""
        document_id = "test-doc-id"
        old_content = "Hello World"
        new_content = "Hello World"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert payload["document_id"] == document_id
        assert payload["version"] == version
        assert payload["change_type"] == "none"
        # Should have a single retain operation for the entire text
        assert len(payload["changes"]) == 1
        assert payload["changes"][0]["operation"] == "retain"
        assert payload["changes"][0]["length"] == len(old_content)
    
    def test_create_api_payload_simple_insertion(self):
        """Test creating API payload for simple text insertion."""
        document_id = "test-doc-id"
        old_content = "Hello"
        new_content = "Hello World"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert payload["document_id"] == document_id
        assert payload["version"] == version
        assert len(payload["changes"]) > 0
        
        # Should contain operations to transform old to new
        changes = payload["changes"]
        
        # Verify that the changes are in proper OT format
        for change in changes:
            assert "operation" in change
            assert change["operation"] in ["retain", "insert", "delete"]
    
    def test_create_api_payload_simple_deletion(self):
        """Test creating API payload for simple text deletion."""
        document_id = "test-doc-id"
        old_content = "Hello World"
        new_content = "Hello"
        version = 2
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert payload["document_id"] == document_id
        assert payload["version"] == version
        assert len(payload["changes"]) > 0
        
        # Should contain delete operations
        changes = payload["changes"]
        has_delete = any(change["operation"] == "delete" for change in changes)
        assert has_delete
    
    def test_create_api_payload_replacement(self):
        """Test creating API payload for text replacement."""
        document_id = "test-doc-id"
        old_content = "Hello World"
        new_content = "Hello Universe"
        version = 3
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert payload["document_id"] == document_id
        assert payload["version"] == version
        assert len(payload["changes"]) > 0
        
        changes = payload["changes"]
        
        # Should have retain (for "Hello "), delete (for "World"), insert (for "Universe")
        operations = [change["operation"] for change in changes]
        assert "retain" in operations
        assert "delete" in operations
        assert "insert" in operations
    
    def test_create_api_payload_insertion_at_beginning(self):
        """Test creating API payload for insertion at beginning."""
        document_id = "test-doc-id"
        old_content = "World"
        new_content = "Hello World"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        changes = payload["changes"]
        assert len(changes) > 0
        
        # First operation should be insert
        assert changes[0]["operation"] == "insert"
        assert changes[0]["content"] == "Hello "
    
    def test_create_api_payload_insertion_at_end(self):
        """Test creating API payload for insertion at end."""
        document_id = "test-doc-id"
        old_content = "Hello"
        new_content = "Hello World"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        changes = payload["changes"]
        assert len(changes) > 0
        
        # Should have retain for "Hello" and insert for " World"
        operations = [change["operation"] for change in changes]
        assert "retain" in operations
        assert "insert" in operations
    
    def test_create_api_payload_deletion_at_beginning(self):
        """Test creating API payload for deletion at beginning."""
        document_id = "test-doc-id"
        old_content = "Hello World"
        new_content = "World"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        changes = payload["changes"]
        assert len(changes) > 0
        
        # Should start with delete operation
        assert changes[0]["operation"] == "delete"
        assert changes[0]["length"] == 6  # "Hello "
    
    def test_create_api_payload_deletion_at_end(self):
        """Test creating API payload for deletion at end."""
        document_id = "test-doc-id"
        old_content = "Hello World"
        new_content = "Hello"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        changes = payload["changes"]
        assert len(changes) > 0
        
        # Should have retain for "Hello" and delete for " World"
        operations = [change["operation"] for change in changes]
        assert "retain" in operations
        assert "delete" in operations
    
    def test_create_api_payload_complex_changes(self):
        """Test creating API payload for complex changes."""
        document_id = "test-doc-id"
        old_content = "The quick brown fox jumps over the lazy dog"
        new_content = "A fast red fox runs over the sleepy cat"
        version = 5
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert payload["document_id"] == document_id
        assert payload["version"] == version
        assert len(payload["changes"]) > 0
        
        # Verify that applying the changes would work
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_create_api_payload_empty_to_text(self):
        """Test creating API payload from empty string to text."""
        document_id = "test-doc-id"
        old_content = ""
        new_content = "Hello World"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        changes = payload["changes"]
        assert len(changes) == 1
        assert changes[0]["operation"] == "insert"
        assert changes[0]["content"] == "Hello World"
    
    def test_create_api_payload_text_to_empty(self):
        """Test creating API payload from text to empty string."""
        document_id = "test-doc-id"
        old_content = "Hello World"
        new_content = ""
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        changes = payload["changes"]
        assert len(changes) == 1
        assert changes[0]["operation"] == "delete"
        assert changes[0]["length"] == len(old_content)
    
    def test_create_api_payload_whitespace_changes(self):
        """Test creating API payload for whitespace changes."""
        document_id = "test-doc-id"
        old_content = "Hello   World"  # Multiple spaces
        new_content = "Hello World"    # Single space
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert len(payload["changes"]) > 0
        
        # Verify the transformation works
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_create_api_payload_multiline_text(self):
        """Test creating API payload for multiline text changes."""
        document_id = "test-doc-id"
        old_content = "Line 1\nLine 2\nLine 3"
        new_content = "Line 1\nModified Line 2\nLine 3"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert len(payload["changes"]) > 0
        
        # Verify the transformation works
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_create_api_payload_special_characters(self):
        """Test creating API payload with special characters."""
        document_id = "test-doc-id"
        old_content = "Hello @#$%^&*()"
        new_content = "Hello 你好 @#$%^&*()"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert len(payload["changes"]) > 0
        
        # Verify the transformation works with special characters
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_create_api_payload_unicode_text(self):
        """Test creating API payload with Unicode text."""
        document_id = "test-doc-id"
        old_content = "Hello 世界"
        new_content = "Hi 世界!"
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert len(payload["changes"]) > 0
        
        # Verify the transformation works with Unicode
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_create_api_payload_large_text(self):
        """Test creating API payload for large text changes."""
        document_id = "test-doc-id"
        old_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100
        new_content = "Modified lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100
        version = 1
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert len(payload["changes"]) > 0
        
        # For large texts, we should still be able to apply the changes
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_create_api_payload_maintains_data_types(self):
        """Test that API payload maintains correct data types."""
        document_id = "test-doc-id"
        old_content = "Hello"
        new_content = "Hello World"
        version = 42
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        # Check data types
        assert isinstance(payload["document_id"], str)
        assert isinstance(payload["version"], int)
        assert isinstance(payload["changes"], list)
        
        for change in payload["changes"]:
            assert isinstance(change, dict)
            assert isinstance(change["operation"], str)
            
            if "length" in change:
                assert isinstance(change["length"], int)
                assert change["length"] > 0
            
            if "content" in change:
                assert isinstance(change["content"], str)
                assert len(change["content"]) > 0


@pytest.mark.django_db
class TestContentDiffGeneratorIntegration:
    """Integration tests for ContentDiffGenerator with real scenarios."""
    
    def test_integration_with_document_model(self, document_factory):
        """Test integration with actual Document model."""
        document = document_factory(
            title="Test Document",
            content_text="Hello World"
        )
        
        old_content = document.get_plain_text
        new_content = "Hello Beautiful World"
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=str(document.id),
            old_content=old_content,
            new_content=new_content,
            document_version=document.version
        )
        
        assert payload["document_id"] == str(document.id)
        assert payload["version"] == document.version
        assert len(payload["changes"]) > 0
        
        # Verify we can apply these changes
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_real_typing_scenario(self):
        """Test a realistic typing scenario."""
        document_id = "typing-test"
        version = 1
        
        # Simulate typing "Hello World" step by step
        typing_steps = [
            ("", "H"),
            ("H", "He"),
            ("He", "Hel"),
            ("Hel", "Hell"),
            ("Hell", "Hello"),
            ("Hello", "Hello "),
            ("Hello ", "Hello W"),
            ("Hello W", "Hello Wo"),
            ("Hello Wo", "Hello Wor"),
            ("Hello Wor", "Hello Worl"),
            ("Hello Worl", "Hello World")
        ]
        
        for old_text, new_text in typing_steps:
            payload = ContentDiffGenerator.create_api_payload(
                document_id=document_id,
                old_content=old_text,
                new_content=new_text,
                document_version=version
            )
            
            # Each step should produce valid operations
            if old_text != new_text:
                assert len(payload["changes"]) > 0
                
                # Verify the operations work
                result = apply_operations_to_text(payload["changes"], old_text)
                assert result == new_text
    
    def test_backspace_scenario(self):
        """Test a realistic backspace scenario."""
        document_id = "backspace-test"
        version = 1
        
        # Start with text and simulate backspacing
        backspace_steps = [
            ("Hello World", "Hello Worl"),
            ("Hello Worl", "Hello Wor"),
            ("Hello Wor", "Hello Wo"),
            ("Hello Wo", "Hello W"),
            ("Hello W", "Hello "),
            ("Hello ", "Hello"),
            ("Hello", "Hell"),
            ("Hell", "Hel"),
            ("Hel", "He"),
            ("He", "H"),
            ("H", "")
        ]
        
        for old_text, new_text in backspace_steps:
            payload = ContentDiffGenerator.create_api_payload(
                document_id=document_id,
                old_content=old_text,
                new_content=new_text,
                document_version=version
            )
            
            assert len(payload["changes"]) > 0
            
            # Verify the operations work
            result = apply_operations_to_text(payload["changes"], old_text)
            assert result == new_text
    
    def test_word_replacement_scenario(self):
        """Test realistic word replacement scenarios."""
        document_id = "replace-test"
        version = 1
        
        # Test various word replacements
        replacement_tests = [
            ("The cat sat", "The dog sat"),
            ("Quick brown fox", "Fast red fox"),
            ("I am happy", "I am very happy"),
            ("Remove this word", "Remove word"),
            ("Add word here", "Add new word here"),
        ]
        
        for old_text, new_text in replacement_tests:
            payload = ContentDiffGenerator.create_api_payload(
                document_id=document_id,
                old_content=old_text,
                new_content=new_text,
                document_version=version
            )
            
            assert len(payload["changes"]) > 0
            
            # Verify the operations work
            result = apply_operations_to_text(payload["changes"], old_text)
            assert result == new_text
    
    def test_copy_paste_scenario(self):
        """Test copy-paste like operations."""
        document_id = "copy-paste-test"
        version = 1
        
        # Simulate copying text from one place and pasting elsewhere
        old_content = "The quick brown fox jumps over the lazy dog"
        new_content = "The brown fox jumps over the lazy dog. The quick brown fox was fast."
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert len(payload["changes"]) > 0
        
        # Verify the operations work
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_paragraph_editing_scenario(self):
        """Test editing paragraphs with line breaks."""
        document_id = "paragraph-test"
        version = 1
        
        old_content = """First paragraph.
Second paragraph.
Third paragraph."""
        
        new_content = """First paragraph is modified.
Second paragraph.
Third paragraph is also changed."""
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        assert len(payload["changes"]) > 0
        
        # Verify the operations work
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content
    
    def test_performance_with_large_documents(self):
        """Test performance characteristics with large documents."""
        document_id = "performance-test"
        version = 1
        
        # Create a large document
        base_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        old_content = base_text * 1000  # ~57KB of text
        
        # Make a small change in the middle
        middle_pos = len(old_content) // 2
        new_content = old_content[:middle_pos] + "MODIFIED " + old_content[middle_pos:]
        
        # This should complete in reasonable time
        import time
        start_time = time.time()
        
        payload = ContentDiffGenerator.create_api_payload(
            document_id=document_id,
            old_content=old_content,
            new_content=new_content,
            document_version=version
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete in under 1 second for this size
        assert execution_time < 1.0
        assert len(payload["changes"]) > 0
        
        # Verify correctness
        result = apply_operations_to_text(payload["changes"], old_content)
        assert result == new_content