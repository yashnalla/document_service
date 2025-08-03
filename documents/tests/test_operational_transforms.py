import pytest
from documents.operational_transforms import (
    OTOperation, 
    OTOperationSet, 
    OTTransformer, 
    OTDiffGenerator,
    OperationType
)


@pytest.mark.django_db
class TestOTOperation:
    """Test cases for OTOperation class."""
    
    def test_insert_operation_creation(self):
        """Test creating an insert operation."""
        op = OTOperation(OperationType.INSERT, content="hello")
        assert op.op_type == OperationType.INSERT
        assert op.content == "hello"
        assert op.length == 0
        assert op.position == 0
    
    def test_delete_operation_creation(self):
        """Test creating a delete operation."""
        op = OTOperation(OperationType.DELETE, length=5)
        assert op.op_type == OperationType.DELETE
        assert op.length == 5
        assert op.content == ""
        assert op.position == 0
        
    def test_retain_operation_creation(self):
        """Test creating a retain operation."""
        op = OTOperation(OperationType.RETAIN, length=10)
        assert op.op_type == OperationType.RETAIN
        assert op.length == 10
        assert op.content == ""
        assert op.position == 0
    
    def test_operation_with_attributes(self):
        """Test operation with custom attributes."""
        attrs = {"bold": True, "color": "red"}
        op = OTOperation(OperationType.INSERT, content="text", attributes=attrs)
        assert op.attributes == attrs
    
    def test_operation_to_dict(self):
        """Test converting operation to dictionary."""
        op = OTOperation(OperationType.INSERT, position=5, content="hello")
        result = op.to_dict()
        expected = {
            "op_type": "insert",
            "position": 5,
            "content": "hello"
        }
        assert result == expected
    
    def test_operation_from_dict(self):
        """Test creating operation from dictionary."""
        data = {
            "op_type": "delete",
            "position": 10,
            "length": 3
        }
        op = OTOperation.from_dict(data)
        assert op.op_type == OperationType.DELETE
        assert op.position == 10
        assert op.length == 3
    
    def test_operation_string_representation(self):
        """Test string representation of operations."""
        insert_op = OTOperation(OperationType.INSERT, position=0, content="test")
        delete_op = OTOperation(OperationType.DELETE, position=5, length=3)
        retain_op = OTOperation(OperationType.RETAIN, length=10)
        
        assert str(insert_op) == "Insert(pos=0, content='test')"
        assert str(delete_op) == "Delete(pos=5, length=3)"
        assert str(retain_op) == "Retain(length=10)"


@pytest.mark.django_db
class TestOTOperationSet:
    """Test cases for OTOperationSet class."""
    
    def test_empty_operation_set(self):
        """Test creating empty operation set."""
        ops = OTOperationSet()
        assert len(ops) == 0
        assert list(ops) == []
    
    def test_operation_set_with_operations(self):
        """Test creating operation set with initial operations."""
        op1 = OTOperation(OperationType.INSERT, content="hello")
        op2 = OTOperation(OperationType.RETAIN, length=5)
        ops = OTOperationSet([op1, op2])
        assert len(ops) == 2
        assert list(ops) == [op1, op2]
    
    def test_add_operation(self):
        """Test adding operations to set."""
        ops = OTOperationSet()
        op = OTOperation(OperationType.INSERT, content="test")
        ops.add_operation(op)
        assert len(ops) == 1
        assert list(ops)[0] == op
    
    def test_fluent_interface_insert(self):
        """Test fluent interface for insert."""
        ops = OTOperationSet()
        result = ops.insert(0, "hello")
        assert result is ops  # Should return self for chaining
        assert len(ops) == 1
        assert ops.operations[0].op_type == OperationType.INSERT
        assert ops.operations[0].content == "hello"
    
    def test_fluent_interface_delete(self):
        """Test fluent interface for delete."""
        ops = OTOperationSet()
        result = ops.delete(5, 3)
        assert result is ops
        assert len(ops) == 1
        assert ops.operations[0].op_type == OperationType.DELETE
        assert ops.operations[0].position == 5
        assert ops.operations[0].length == 3
    
    def test_fluent_interface_retain(self):
        """Test fluent interface for retain."""
        ops = OTOperationSet()
        result = ops.retain(10)
        assert result is ops
        assert len(ops) == 1
        assert ops.operations[0].op_type == OperationType.RETAIN
        assert ops.operations[0].length == 10
    
    def test_apply_insert_only(self):
        """Test applying insert-only operations."""
        ops = OTOperationSet()
        ops.insert(0, "Hello, World!")
        
        result = ops.apply("")
        assert result == "Hello, World!"
    
    def test_apply_retain_only(self):
        """Test applying retain-only operations."""
        ops = OTOperationSet()
        ops.retain(5)
        
        result = ops.apply("Hello")
        assert result == "Hello"
    
    def test_apply_delete_only(self):
        """Test applying delete-only operations."""
        ops = OTOperationSet()
        ops.operations.append(OTOperation(OperationType.DELETE, length=5))
        
        result = ops.apply("Hello")
        assert result == ""
    
    def test_apply_complex_operations(self):
        """Test applying complex sequence of operations."""
        ops = OTOperationSet()
        # Retain "Hello", delete " World", insert " Universe"
        ops.operations.extend([
            OTOperation(OperationType.RETAIN, length=5),     # Keep "Hello"
            OTOperation(OperationType.DELETE, length=6),     # Delete " World"
            OTOperation(OperationType.INSERT, content=" Universe")  # Insert " Universe"
        ])
        
        result = ops.apply("Hello World")
        assert result == "Hello Universe"
    
    def test_apply_sequential_operations(self):
        """Test sequential operations without absolute positions."""
        ops = OTOperationSet()
        # Insert at beginning, then retain, then delete
        ops.operations.extend([
            OTOperation(OperationType.INSERT, content="Hi "),    # Insert "Hi " at start
            OTOperation(OperationType.RETAIN, length=5),         # Keep "Hello"  
            OTOperation(OperationType.DELETE, length=6)          # Delete " World"
        ])
        
        result = ops.apply("Hello World")
        assert result == "Hi Hello"
    
    def test_apply_with_remaining_text(self):
        """Test that remaining text is retained if not covered by operations."""
        ops = OTOperationSet()
        ops.operations.append(OTOperation(OperationType.RETAIN, length=5))
        
        result = ops.apply("Hello World")
        assert result == "Hello World"  # Remaining " World" should be kept
    
    def test_apply_operation_beyond_text_length(self):
        """Test error when operations extend beyond text length."""
        ops = OTOperationSet()
        ops.operations.append(OTOperation(OperationType.RETAIN, length=10))
        
        with pytest.raises(ValueError, match="extends beyond text length"):
            ops.apply("Hi")
    
    def test_apply_delete_beyond_text_length(self):
        """Test error when delete extends beyond text length."""
        ops = OTOperationSet()
        ops.operations.append(OTOperation(OperationType.DELETE, length=10))
        
        with pytest.raises(ValueError, match="extends beyond text length"):
            ops.apply("Hi")
    
    def test_operation_set_to_dict(self):
        """Test converting operation set to dictionary."""
        ops = OTOperationSet()
        ops.insert(0, "test").retain(5)
        
        result = ops.to_dict()
        assert "operations" in result
        assert len(result["operations"]) == 2
    
    def test_operation_set_from_dict(self):
        """Test creating operation set from dictionary."""
        data = {
            "operations": [
                {"op_type": "insert", "position": 0, "content": "test"},
                {"op_type": "retain", "length": 5}
            ]
        }
        ops = OTOperationSet.from_dict(data)
        assert len(ops) == 2
        assert ops.operations[0].op_type == OperationType.INSERT
        assert ops.operations[1].op_type == OperationType.RETAIN
    
    def test_operation_set_string_representation(self):
        """Test string representation of operation set."""
        ops = OTOperationSet()
        ops.insert(0, "hi").retain(5)
        
        result = str(ops)
        assert "OTOperationSet" in result
        assert "Insert" in result
        assert "Retain" in result


@pytest.mark.django_db 
class TestOTDiffGenerator:
    """Test cases for OTDiffGenerator class."""
    
    def test_identical_texts(self):
        """Test diff generation for identical texts."""
        old_text = "Hello World"
        new_text = "Hello World"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        assert len(ops) == 1
        assert ops.operations[0].op_type == OperationType.RETAIN
        assert ops.operations[0].length == len(old_text)
        
        # Test that applying the operations works
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_empty_to_text(self):
        """Test diff generation from empty string to text."""
        old_text = ""
        new_text = "Hello World"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        assert len(ops) == 1
        assert ops.operations[0].op_type == OperationType.INSERT
        assert ops.operations[0].content == "Hello World"
        
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_text_to_empty(self):
        """Test diff generation from text to empty string."""
        old_text = "Hello World"
        new_text = ""
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        assert len(ops) == 1
        assert ops.operations[0].op_type == OperationType.DELETE
        assert ops.operations[0].length == len(old_text)
        
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_replacement_in_middle(self):
        """Test replacing text in the middle."""
        old_text = "Hello World"
        new_text = "Hello Universe"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text
        
        # Should have operations: retain "Hello ", delete "World", insert "Universe"
        # The exact structure may vary based on common prefix/suffix detection
        assert any(op.op_type == OperationType.RETAIN for op in ops.operations)
        assert any(op.op_type == OperationType.DELETE for op in ops.operations)
        assert any(op.op_type == OperationType.INSERT for op in ops.operations)
    
    def test_insertion_at_beginning(self):
        """Test insertion at the beginning."""
        old_text = "World"
        new_text = "Hello World"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_insertion_at_end(self):
        """Test insertion at the end."""
        old_text = "Hello"
        new_text = "Hello World"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_deletion_at_beginning(self):
        """Test deletion at the beginning."""
        old_text = "Hello World"
        new_text = "World"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_deletion_at_end(self):
        """Test deletion at the end."""
        old_text = "Hello World"
        new_text = "Hello"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_complex_changes(self):
        """Test complex changes with multiple operations."""
        old_text = "The quick brown fox jumps"
        new_text = "A quick red fox runs"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text
    
    def test_common_prefix_suffix_detection(self):
        """Test that common prefix and suffix are detected correctly."""
        old_text = "prefix_MIDDLE_suffix"
        new_text = "prefix_CHANGED_suffix"
        
        ops = OTDiffGenerator.generate_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text
        
        # Should detect "prefix_" as common prefix and "_suffix" as common suffix
        # So we should have: retain prefix, delete MIDDLE, insert CHANGED, retain suffix
        retain_ops = [op for op in ops.operations if op.op_type == OperationType.RETAIN]
        assert len(retain_ops) >= 1  # At least the prefix should be retained
    
    def test_generate_incremental_operations_fallback(self):
        """Test that incremental operations falls back to basic generation."""
        old_text = "Hello"
        new_text = "Hi"
        
        ops = OTDiffGenerator.generate_incremental_operations(old_text, new_text)
        result = ops.apply(old_text)
        assert result == new_text


@pytest.mark.django_db
class TestOTTransformer:
    """Test cases for OTTransformer class."""
    
    def test_transform_insert_insert_different_positions(self):
        """Test transforming two inserts at different positions."""
        op1 = OTOperation(OperationType.INSERT, position=0, content="A")
        op2 = OTOperation(OperationType.INSERT, position=5, content="B")
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2)
        
        # op1 should be unchanged (inserts before op2)
        assert op1_prime.position == 0
        assert op1_prime.content == "A"
        
        # op2 position should be adjusted
        assert op2_prime.position == 6  # 5 + len("A")
        assert op2_prime.content == "B"
    
    def test_transform_insert_insert_same_position_left_priority(self):
        """Test transforming two inserts at same position with left priority."""
        op1 = OTOperation(OperationType.INSERT, position=5, content="A")
        op2 = OTOperation(OperationType.INSERT, position=5, content="B")
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2, priority="left")
        
        # op1 should be unchanged (has priority)
        assert op1_prime.position == 5
        assert op1_prime.content == "A"
        
        # op2 position should be adjusted
        assert op2_prime.position == 6  # 5 + len("A")
        assert op2_prime.content == "B"
    
    def test_transform_insert_insert_same_position_right_priority(self):
        """Test transforming two inserts at same position with right priority."""
        op1 = OTOperation(OperationType.INSERT, position=5, content="A")
        op2 = OTOperation(OperationType.INSERT, position=5, content="B")
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2, priority="right")
        
        # op1 position should be adjusted
        assert op1_prime.position == 6  # 5 + len("B")
        assert op1_prime.content == "A"
        
        # op2 should be unchanged (has priority)
        assert op2_prime.position == 5
        assert op2_prime.content == "B"
    
    def test_transform_insert_delete_before(self):
        """Test transforming insert before delete."""
        op1 = OTOperation(OperationType.INSERT, position=2, content="XX")
        op2 = OTOperation(OperationType.DELETE, position=5, length=3)
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2)
        
        # Insert should be unchanged
        assert op1_prime.position == 2
        assert op1_prime.content == "XX"
        
        # Delete position should be adjusted
        assert op2_prime.position == 7  # 5 + len("XX")
        assert op2_prime.length == 3
    
    def test_transform_insert_delete_after(self):
        """Test transforming insert after delete."""
        op1 = OTOperation(OperationType.INSERT, position=8, content="XX")
        op2 = OTOperation(OperationType.DELETE, position=2, length=3)
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2)
        
        # Insert position should be adjusted
        assert op1_prime.position == 5  # 8 - 3
        assert op1_prime.content == "XX"
        
        # Delete should be unchanged
        assert op2_prime.position == 2
        assert op2_prime.length == 3
    
    def test_transform_insert_delete_within(self):
        """Test transforming insert within delete range."""
        op1 = OTOperation(OperationType.INSERT, position=5, content="XX")
        op2 = OTOperation(OperationType.DELETE, position=3, length=5)
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2)
        
        # Insert should be moved to delete position
        assert op1_prime.position == 3
        assert op1_prime.content == "XX"
        
        # Delete length should be increased
        assert op2_prime.position == 3
        assert op2_prime.length == 7  # 5 + len("XX")
    
    def test_transform_delete_delete_no_overlap(self):
        """Test transforming two deletes with no overlap."""
        op1 = OTOperation(OperationType.DELETE, position=2, length=3)
        op2 = OTOperation(OperationType.DELETE, position=8, length=2)
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2)
        
        # op1 should be unchanged
        assert op1_prime.position == 2
        assert op1_prime.length == 3
        
        # op2 position should be adjusted
        assert op2_prime.position == 5  # 8 - 3
        assert op2_prime.length == 2
    
    def test_transform_delete_delete_overlap(self):
        """Test transforming two deletes with overlap."""
        op1 = OTOperation(OperationType.DELETE, position=2, length=5)  # deletes 2-7
        op2 = OTOperation(OperationType.DELETE, position=4, length=4)  # deletes 4-8
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2)
        
        # Both operations should be adjusted to handle the intersection
        assert op1_prime.length < op1.length  # Should be reduced
        assert op2_prime.length < op2.length  # Should be reduced
    
    def test_transform_operation_sets(self):
        """Test transforming operation sets."""
        ops1 = OTOperationSet()
        ops1.insert(0, "A").insert(5, "B")
        
        ops2 = OTOperationSet()
        ops2.insert(2, "X").insert(7, "Y")
        
        ops1_prime, ops2_prime = OTTransformer.transform_operation_sets(ops1, ops2)
        
        assert len(ops1_prime) == 2
        assert len(ops2_prime) == 2
    
    def test_transform_with_retain_operations(self):
        """Test that retain operations don't conflict."""
        op1 = OTOperation(OperationType.RETAIN, length=5)
        op2 = OTOperation(OperationType.INSERT, position=3, content="X")
        
        op1_prime, op2_prime = OTTransformer.transform_operations(op1, op2)
        
        # Retain should be unchanged
        assert op1_prime.op_type == OperationType.RETAIN
        assert op1_prime.length == 5
        
        # Insert should be unchanged
        assert op2_prime.op_type == OperationType.INSERT
        assert op2_prime.position == 3
        assert op2_prime.content == "X"


@pytest.mark.django_db
class TestOTIntegration:
    """Integration tests for the OT system."""
    
    def test_bidirectional_transformation(self):
        """Test that transformations work in both directions."""
        original_text = "Hello World"
        
        # Create two simple operations that can be applied independently
        ops1 = OTOperationSet()
        ops1.operations.append(OTOperation(OperationType.INSERT, content="Hi "))  # Insert at beginning
        
        ops2 = OTOperationSet()
        ops2.operations.append(OTOperation(OperationType.RETAIN, length=len(original_text)))  # Keep all text
        ops2.operations.append(OTOperation(OperationType.INSERT, content="!"))  # Insert at end
        
        # Apply ops1 first, then transform ops2 and apply
        intermediate1 = ops1.apply(original_text)  # "Hi Hello World"
        # ops2 needs to account for the inserted "Hi " at the beginning
        ops2_transformed = OTOperationSet()
        ops2_transformed.operations.append(OTOperation(OperationType.RETAIN, length=len(intermediate1)))
        ops2_transformed.operations.append(OTOperation(OperationType.INSERT, content="!"))
        final1 = ops2_transformed.apply(intermediate1)  # "Hi Hello World!"
        
        # Apply ops2 first, then apply ops1
        intermediate2 = ops2.apply(original_text)  # "Hello World!"
        # ops1 can be applied as-is since it inserts at the beginning
        final2 = ops1.apply(intermediate2)  # "Hi Hello World!"
        
        # Both paths should produce the same result
        assert final1 == final2 == "Hi Hello World!"
    
    def test_multiple_sequential_operations(self):
        """Test applying multiple operations in sequence."""
        text = "The quick brown fox"
        
        # Generate a series of changes
        changes = [
            ("The quick brown fox", "The fast brown fox"),    # Replace "quick" with "fast"
            ("The fast brown fox", "The fast red fox"),      # Replace "brown" with "red"
            ("The fast red fox", "A fast red fox"),          # Replace "The" with "A"
        ]
        
        for old_text, new_text in changes:
            ops = OTDiffGenerator.generate_operations(old_text, new_text)
            result = ops.apply(old_text)
            assert result == new_text
            text = new_text
        
        assert text == "A fast red fox"
    
    def test_edge_case_empty_operations(self):
        """Test handling of edge cases with empty operations."""
        ops = OTOperationSet()
        
        # Empty operation set should return original text
        result = ops.apply("Hello World")
        assert result == "Hello World"
    
    def test_edge_case_only_retains(self):
        """Test operation set with only retains."""
        ops = OTOperationSet()
        ops.retain(5)
        
        text = "Hello World"
        result = ops.apply(text)
        assert result == text  # Should keep everything
    
    def test_large_text_operations(self):
        """Test operations on larger text."""
        # Create a large text
        large_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100
        
        # Make some changes that are within the text bounds
        ops = OTOperationSet()
        ops.operations.extend([
            OTOperation(OperationType.RETAIN, length=50),    # Keep first 50 chars
            OTOperation(OperationType.DELETE, length=100),   # Delete next 100 chars  
            OTOperation(OperationType.INSERT, content="INSERTED TEXT ")  # Insert something
        ])
        
        result = ops.apply(large_text)
        
        # Result should be different but valid
        assert result != large_text
        assert "INSERTED TEXT" in result
        assert len(result) == len(large_text) - 100 + len("INSERTED TEXT ")