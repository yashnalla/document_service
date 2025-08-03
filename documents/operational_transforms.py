"""
Operational Transform (OT) system for collaborative document editing.

This module implements operational transforms for real-time collaborative editing,
allowing multiple users to edit the same document simultaneously while maintaining
consistency and resolving conflicts.

The OT system supports three basic operations:
1. Insert - Insert text at a specific position
2. Delete - Delete text from a specific position and length
3. Retain - Keep existing text unchanged (for composing operations)
"""

from typing import List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operational transform operations."""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"


@dataclass
class OTOperation:
    """
    Represents a single operational transform operation.
    
    Attributes:
        op_type: The type of operation (insert, delete, retain)
        position: Character position in the document (for insert/delete)
        content: Text content (for insert operations)
        length: Number of characters (for delete/retain operations)
        attributes: Additional attributes (for future formatting support)
    """
    op_type: OperationType
    position: int = 0
    content: str = ""
    length: int = 0
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary for serialization."""
        result = {
            "op_type": self.op_type.value,
            "position": self.position
        }
        
        if self.op_type == OperationType.INSERT:
            result["content"] = self.content
        elif self.op_type in (OperationType.DELETE, OperationType.RETAIN):
            result["length"] = self.length
            
        if self.attributes:
            result["attributes"] = self.attributes
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OTOperation':
        """Create operation from dictionary."""
        op_type = OperationType(data["op_type"])
        
        return cls(
            op_type=op_type,
            position=data.get("position", 0),
            content=data.get("content", ""),
            length=data.get("length", 0),
            attributes=data.get("attributes", {})
        )
    
    def __str__(self) -> str:
        if self.op_type == OperationType.INSERT:
            return f"Insert(pos={self.position}, content='{self.content}')"
        elif self.op_type == OperationType.DELETE:
            return f"Delete(pos={self.position}, length={self.length})"
        else:  # RETAIN
            return f"Retain(length={self.length})"


class OTOperationSet:
    """
    Represents a set of operational transform operations that can be applied to a document.
    
    This class provides methods for creating, composing, and transforming operations
    for collaborative editing scenarios.
    """
    
    def __init__(self, operations: List[OTOperation] = None):
        self.operations = operations or []
    
    def add_operation(self, operation: OTOperation) -> None:
        """Add an operation to the set."""
        self.operations.append(operation)
    
    def insert(self, position: int, content: str, attributes: Dict[str, Any] = None) -> 'OTOperationSet':
        """Add an insert operation."""
        op = OTOperation(
            op_type=OperationType.INSERT,
            position=position,
            content=content,
            attributes=attributes or {}
        )
        self.operations.append(op)
        return self
    
    def delete(self, position: int, length: int, attributes: Dict[str, Any] = None) -> 'OTOperationSet':
        """Add a delete operation."""
        op = OTOperation(
            op_type=OperationType.DELETE,
            position=position,
            length=length,
            attributes=attributes or {}
        )
        self.operations.append(op)
        return self
    
    def retain(self, length: int, attributes: Dict[str, Any] = None) -> 'OTOperationSet':
        """Add a retain operation."""
        op = OTOperation(
            op_type=OperationType.RETAIN,
            length=length,
            attributes=attributes or {}
        )
        self.operations.append(op)
        return self
    
    def apply(self, text: str) -> str:
        """
        Apply all operations in this set to a text string sequentially.
        
        This implements proper Operational Transform semantics where operations
        are applied in sequence: retain, delete, insert operations work through
        the document sequentially without absolute positions.
        
        Args:
            text: The original text to apply operations to
            
        Returns:
            The text after applying all operations sequentially
            
        Raises:
            ValueError: If operations are invalid or cannot be applied
        """
        logger.info(f"OTOperationSet.apply called with text: '{text}' (length: {len(text)})")
        logger.info(f"Applying {len(self.operations)} operations: {self.operations}")
        
        result = []
        source_index = 0
        
        for i, operation in enumerate(self.operations):
            logger.info(f"Operation {i+1}: {operation}, source_index: {source_index}")
            
            if operation.op_type == OperationType.RETAIN:
                # Retain: copy characters from source to result
                end_index = source_index + operation.length
                if end_index > len(text):
                    logger.error(f"Retain operation extends beyond text length: {end_index} > {len(text)}")
                    raise ValueError(f"Retain operation extends beyond text length: {end_index} > {len(text)}")
                
                retained_text = text[source_index:end_index]
                result.append(retained_text)
                source_index = end_index
                logger.info(f"  Retained: '{retained_text}', new source_index: {source_index}")
                
            elif operation.op_type == OperationType.DELETE:
                # Delete: skip characters in source (don't copy to result)
                end_index = source_index + operation.length
                if end_index > len(text):
                    logger.error(f"Delete operation extends beyond text length: {end_index} > {len(text)}")
                    raise ValueError(f"Delete operation extends beyond text length: {end_index} > {len(text)}")
                
                deleted_text = text[source_index:end_index]
                source_index = end_index  # Skip the deleted characters
                logger.info(f"  Deleted: '{deleted_text}', new source_index: {source_index}")
                
            elif operation.op_type == OperationType.INSERT:
                # Insert: add content to result (don't advance source_index)
                result.append(operation.content)
                logger.info(f"  Inserted: '{operation.content}', source_index unchanged: {source_index}")
            
            current_result = ''.join(result)
            logger.info(f"  Result so far: '{current_result}'")
        
        # Ensure we've processed all source text (implicit retain at end)
        if source_index < len(text):
            remaining_text = text[source_index:]
            result.append(remaining_text)
            logger.info(f"Added remaining text: '{remaining_text}'")
        
        final_result = ''.join(result)
        logger.info(f"Final result: '{final_result}' (length: {len(final_result)})")
        
        return final_result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operation set to dictionary for serialization."""
        return {
            "operations": [op.to_dict() for op in self.operations]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OTOperationSet':
        """Create operation set from dictionary."""
        operations = [OTOperation.from_dict(op_data) for op_data in data.get("operations", [])]
        return cls(operations)
    
    def __len__(self) -> int:
        return len(self.operations)
    
    def __iter__(self):
        return iter(self.operations)
    
    def __str__(self) -> str:
        ops_str = ", ".join(str(op) for op in self.operations)
        return f"OTOperationSet([{ops_str}])"


class OTTransformer:
    """
    Handles transformation of operational transform operations for conflict resolution.
    
    When two users edit a document simultaneously, their operations need to be transformed
    against each other to maintain document consistency.
    """
    
    @staticmethod
    def transform_operations(op1: OTOperation, op2: OTOperation, priority: str = "left") -> Tuple[OTOperation, OTOperation]:
        """
        Transform two operations against each other.
        
        Args:
            op1: First operation
            op2: Second operation  
            priority: Which operation has priority in case of conflicts ("left" or "right")
            
        Returns:
            Tuple of transformed operations (op1', op2')
        """
        # Insert vs Insert
        if op1.op_type == OperationType.INSERT and op2.op_type == OperationType.INSERT:
            return OTTransformer._transform_insert_insert(op1, op2, priority)
        
        # Insert vs Delete
        elif op1.op_type == OperationType.INSERT and op2.op_type == OperationType.DELETE:
            return OTTransformer._transform_insert_delete(op1, op2)
        
        # Delete vs Insert
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.INSERT:
            op2_prime, op1_prime = OTTransformer._transform_insert_delete(op2, op1)
            return op1_prime, op2_prime
        
        # Delete vs Delete
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.DELETE:
            return OTTransformer._transform_delete_delete(op1, op2)
        
        # If retain operations are involved, they don't conflict
        else:
            return op1, op2
    
    @staticmethod
    def _transform_insert_insert(op1: OTOperation, op2: OTOperation, priority: str) -> Tuple[OTOperation, OTOperation]:
        """Transform two insert operations."""
        if op1.position < op2.position:
            # op1 inserts before op2, so op2's position needs to be adjusted
            op2_prime = OTOperation(
                op_type=op2.op_type,
                position=op2.position + len(op1.content),
                content=op2.content,
                attributes=op2.attributes
            )
            return op1, op2_prime
        
        elif op1.position > op2.position:
            # op2 inserts before op1, so op1's position needs to be adjusted
            op1_prime = OTOperation(
                op_type=op1.op_type,
                position=op1.position + len(op2.content),
                content=op1.content,
                attributes=op1.attributes
            )
            return op1_prime, op2
        
        else:  # Same position
            # Use priority to determine order
            if priority == "left":
                op2_prime = OTOperation(
                    op_type=op2.op_type,
                    position=op2.position + len(op1.content),
                    content=op2.content,
                    attributes=op2.attributes
                )
                return op1, op2_prime
            else:
                op1_prime = OTOperation(
                    op_type=op1.op_type,
                    position=op1.position + len(op2.content),
                    content=op1.content,
                    attributes=op1.attributes
                )
                return op1_prime, op2
    
    @staticmethod
    def _transform_insert_delete(insert_op: OTOperation, delete_op: OTOperation) -> Tuple[OTOperation, OTOperation]:
        """Transform insert operation against delete operation."""
        if insert_op.position <= delete_op.position:
            # Insert happens before delete, so delete position needs adjustment
            delete_op_prime = OTOperation(
                op_type=delete_op.op_type,
                position=delete_op.position + len(insert_op.content),
                length=delete_op.length,
                attributes=delete_op.attributes
            )
            return insert_op, delete_op_prime
        
        elif insert_op.position >= delete_op.position + delete_op.length:
            # Insert happens after delete, so insert position needs adjustment
            insert_op_prime = OTOperation(
                op_type=insert_op.op_type,
                position=insert_op.position - delete_op.length,
                content=insert_op.content,
                attributes=insert_op.attributes
            )
            return insert_op_prime, delete_op
        
        else:
            # Insert happens within delete range
            # Insert at the delete position, delete length increases
            insert_op_prime = OTOperation(
                op_type=insert_op.op_type,
                position=delete_op.position,
                content=insert_op.content,
                attributes=insert_op.attributes
            )
            delete_op_prime = OTOperation(
                op_type=delete_op.op_type,
                position=delete_op.position,
                length=delete_op.length + len(insert_op.content),
                attributes=delete_op.attributes
            )
            return insert_op_prime, delete_op_prime
    
    @staticmethod
    def _transform_delete_delete(op1: OTOperation, op2: OTOperation) -> Tuple[OTOperation, OTOperation]:
        """Transform two delete operations."""
        # Calculate ranges
        op1_start, op1_end = op1.position, op1.position + op1.length
        op2_start, op2_end = op2.position, op2.position + op2.length
        
        # No overlap - adjust positions
        if op1_end <= op2_start:
            # op1 deletes before op2
            op2_prime = OTOperation(
                op_type=op2.op_type,
                position=op2.position - op1.length,
                length=op2.length,
                attributes=op2.attributes
            )
            return op1, op2_prime
        
        elif op2_end <= op1_start:
            # op2 deletes before op1
            op1_prime = OTOperation(
                op_type=op1.op_type,
                position=op1.position - op2.length,
                length=op1.length,
                attributes=op1.attributes
            )
            return op1_prime, op2
        
        else:
            # Overlapping deletes - need to handle carefully
            # Find the intersection and adjust both operations
            intersection_start = max(op1_start, op2_start)
            intersection_end = min(op1_end, op2_end)
            intersection_length = intersection_end - intersection_start
            
            # Adjust op1
            if op1_start < intersection_start:
                op1_prime = OTOperation(
                    op_type=op1.op_type,
                    position=op1.position,
                    length=intersection_start - op1_start,
                    attributes=op1.attributes
                )
            else:
                op1_prime = OTOperation(
                    op_type=op1.op_type,
                    position=op2.position,
                    length=op1.length - intersection_length,
                    attributes=op1.attributes
                )
            
            # Adjust op2
            if op2_start < intersection_start:
                op2_prime = OTOperation(
                    op_type=op2.op_type,
                    position=op2.position,
                    length=intersection_start - op2_start,
                    attributes=op2.attributes
                )
            else:
                op2_prime = OTOperation(
                    op_type=op2.op_type,
                    position=op1.position,
                    length=op2.length - intersection_length,
                    attributes=op2.attributes
                )
            
            return op1_prime, op2_prime
    
    @staticmethod
    def transform_operation_sets(ops1: OTOperationSet, ops2: OTOperationSet, priority: str = "left") -> Tuple[OTOperationSet, OTOperationSet]:
        """
        Transform two operation sets against each other.
        
        Args:
            ops1: First operation set
            ops2: Second operation set
            priority: Which set has priority for conflicts
            
        Returns:
            Tuple of transformed operation sets
        """
        # For now, implement a simple approach
        # In a more sophisticated implementation, we would need to consider
        # the composition and interaction of multiple operations
        
        transformed_ops1 = []
        transformed_ops2 = []
        
        # Transform each operation in ops1 against all operations in ops2
        for op1 in ops1.operations:
            current_op1 = op1
            temp_ops2 = list(ops2.operations)
            
            for i, op2 in enumerate(temp_ops2):
                current_op1, transformed_op2 = OTTransformer.transform_operations(
                    current_op1, op2, priority
                )
                temp_ops2[i] = transformed_op2
            
            transformed_ops1.append(current_op1)
            transformed_ops2 = temp_ops2
        
        return OTOperationSet(transformed_ops1), OTOperationSet(transformed_ops2)


class OTDiffGenerator:
    """
    Generates operational transform operations by comparing two text strings.
    
    This class provides utilities to create OT operations that represent the
    differences between two versions of a document.
    """
    
    @staticmethod
    def generate_operations(old_text: str, new_text: str) -> OTOperationSet:
        """
        Generate OT operations to transform old_text into new_text.
        
        Implements proper Operational Transform algorithm that generates a sequence of
        retain, delete, and insert operations. Operations work sequentially through
        the document without absolute positions.
        
        Args:
            old_text: The original text
            new_text: The target text
            
        Returns:
            OTOperationSet containing sequential operations to transform old_text to new_text
        """
        logger.info(f"OTDiffGenerator.generate_operations called")
        logger.info(f"Old text: '{old_text}' (length: {len(old_text)})")
        logger.info(f"New text: '{new_text}' (length: {len(new_text)})")
        
        operations = []
        
        if old_text == new_text:
            logger.info("Texts are identical, generating retain operation")
            # No changes needed - just retain all content
            if old_text:
                operations.append(OTOperation(OperationType.RETAIN, length=len(old_text)))
            logger.info(f"Generated operations: {operations}")
            return OTOperationSet(operations)
        
        old_len = len(old_text)
        new_len = len(new_text)
        
        # Find common prefix
        common_prefix = 0
        while (common_prefix < old_len and 
               common_prefix < new_len and 
               old_text[common_prefix] == new_text[common_prefix]):
            common_prefix += 1
        
        logger.info(f"Common prefix length: {common_prefix}")
        if common_prefix > 0:
            logger.info(f"Common prefix: '{old_text[:common_prefix]}'")
        
        # Find common suffix
        common_suffix = 0
        while (common_suffix < (old_len - common_prefix) and
               common_suffix < (new_len - common_prefix) and
               old_text[old_len - 1 - common_suffix] == new_text[new_len - 1 - common_suffix]):
            common_suffix += 1
        
        logger.info(f"Common suffix length: {common_suffix}")
        if common_suffix > 0:
            logger.info(f"Common suffix: '{old_text[-common_suffix:]}'")
        
        # Calculate middle parts
        old_middle = old_text[common_prefix:old_len - common_suffix]
        new_middle = new_text[common_prefix:new_len - common_suffix]
        logger.info(f"Old middle: '{old_middle}' (length: {len(old_middle)})")
        logger.info(f"New middle: '{new_middle}' (length: {len(new_middle)})")
        
        # Generate sequential operations
        
        # 1. Retain the common prefix
        if common_prefix > 0:
            retain_op = OTOperation(OperationType.RETAIN, length=common_prefix)
            operations.append(retain_op)
            logger.info(f"Added retain operation: {retain_op}")
        
        # 2. Delete the old middle part (characters that need to be removed)
        old_middle_len = old_len - common_prefix - common_suffix
        if old_middle_len > 0:
            delete_op = OTOperation(OperationType.DELETE, length=old_middle_len)
            operations.append(delete_op)
            logger.info(f"Added delete operation: {delete_op}")
        
        # 3. Insert the new middle part (new characters to be added)
        new_middle = new_text[common_prefix:new_len - common_suffix]
        if new_middle:
            insert_op = OTOperation(OperationType.INSERT, content=new_middle)
            operations.append(insert_op)
            logger.info(f"Added insert operation: {insert_op}")
        
        # 4. Retain the common suffix (if any)
        if common_suffix > 0:
            suffix_retain_op = OTOperation(OperationType.RETAIN, length=common_suffix)
            operations.append(suffix_retain_op)
            logger.info(f"Added suffix retain operation: {suffix_retain_op}")
        
        operation_set = OTOperationSet(operations)
        logger.info(f"Final operation set: {operation_set}")
        
        # Test the operations
        try:
            result = operation_set.apply(old_text)
            logger.info(f"Test application result: '{result}'")
            logger.info(f"Test successful: {result == new_text}")
        except Exception as e:
            logger.error(f"Test application failed: {e}")
        
        return operation_set
    
    @staticmethod
    def generate_incremental_operations(
        old_text: str, 
        new_text: str, 
        cursor_position: int = None
    ) -> OTOperationSet:
        """
        Generate operations optimized for incremental changes (like typing).
        
        This method tries to detect common editing patterns like:
        - Typing at cursor position
        - Backspace/delete at cursor
        - Bulk operations
        
        Args:
            old_text: The original text
            new_text: The target text  
            cursor_position: Known cursor position (optional)
            
        Returns:
            OTOperationSet optimized for the detected change pattern
        """
        # If cursor position is known, optimize around that area
        if cursor_position is not None:
            # Check if change is near cursor position
            # This could be implemented to handle common editing scenarios
            pass
        
        # For now, fall back to basic diff generation
        return OTDiffGenerator.generate_operations(old_text, new_text)