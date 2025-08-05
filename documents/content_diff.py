"""
Content diff generator for converting web form changes to Operational Transform operations.

This module provides utilities to analyze differences between document content
and generate appropriate OT operations for the API.
"""

import logging
from typing import List, Dict, Any, Tuple
from .operational_transforms import OTOperationSet, OTDiffGenerator

logger = logging.getLogger(__name__)


class ContentDiffGenerator:
    """
    Generates OT operations from web form content changes.
    
    This class analyzes the differences between old and new content from
    web forms and creates appropriate OT operations that can be sent to
    the API for processing.
    """
    
    @staticmethod
    def generate_operations_from_form_data(
        old_content: str,
        new_content: str,
        document_version: int,
        cursor_position: int = None
    ) -> Dict[str, Any]:
        """
        Generate OT operations from web form content changes.
        
        Args:
            old_content: The original document content (plain text)
            new_content: The new document content (plain text)
            document_version: Current document version for conflict detection
            cursor_position: Optional cursor position for optimization
            
        Returns:
            Dictionary containing version and OT operations for API submission
        """
        # Use the OT diff generator to create operations
        if cursor_position is not None:
            operation_set = OTDiffGenerator.generate_incremental_operations(
                old_content, new_content, cursor_position
            )
        else:
            operation_set = OTDiffGenerator.generate_operations(
                old_content, new_content
            )
        
        # Convert OT operations to sequential API format (proper OT)
        api_operations = []
        
        for ot_op in operation_set.operations:
            if ot_op.op_type.value == "retain":
                # Retain: skip over characters
                api_operations.append({
                    "operation": "retain",
                    "length": ot_op.length
                })
            elif ot_op.op_type.value == "delete":
                # Delete: remove characters sequentially
                api_operations.append({
                    "operation": "delete", 
                    "length": ot_op.length
                })
            elif ot_op.op_type.value == "insert":
                # Insert: add characters sequentially
                api_operations.append({
                    "operation": "insert",
                    "content": ot_op.content
                })
        
        return {
            "version": document_version,
            "changes": api_operations
        }
    
    @staticmethod
    def optimize_operations(operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize a list of OT operations by merging adjacent operations where possible.
        
        Args:
            operations: List of OT operations
            
        Returns:
            Optimized list of operations
        """
        if not operations:
            return operations
        
        optimized = []
        current_op = operations[0].copy()
        
        for next_op in operations[1:]:
            # Try to merge adjacent insert operations
            if (current_op.get("operation") == "ot_insert" and 
                next_op.get("operation") == "ot_insert" and
                current_op.get("position", 0) + len(current_op.get("content", "")) == next_op.get("position", 0)):
                
                # Merge the inserts
                current_op["content"] = current_op.get("content", "") + next_op.get("content", "")
                continue
            
            # Try to merge adjacent delete operations
            elif (current_op.get("operation") == "ot_delete" and
                  next_op.get("operation") == "ot_delete" and
                  current_op.get("position", 0) == next_op.get("position", 0)):
                
                # Merge the deletes
                current_op["length"] = current_op.get("length", 0) + next_op.get("length", 0)
                continue
            
            # Try to merge adjacent retain operations
            elif (current_op.get("operation") == "ot_retain" and
                  next_op.get("operation") == "ot_retain"):
                
                # Merge the retains
                current_op["length"] = current_op.get("length", 0) + next_op.get("length", 0)
                continue
            
            # Can't merge, add current operation and move to next
            optimized.append(current_op)
            current_op = next_op.copy()
        
        # Add the last operation
        optimized.append(current_op)
        
        return optimized
    
    @staticmethod
    def detect_change_type(old_content: str, new_content: str) -> str:
        """
        Detect the type of change made to the content.
        
        Args:
            old_content: Original content
            new_content: New content
            
        Returns:
            String describing the change type: 'insert', 'delete', 'replace', 'none'
        """
        if old_content == new_content:
            return "none"
        
        old_len = len(old_content)
        new_len = len(new_content)
        
        if old_len == 0:
            return "insert"
        elif new_len == 0:
            return "delete"
        elif new_len > old_len:
            # Check if it's a pure insertion
            if old_content in new_content:
                return "insert"
            else:
                return "replace"
        elif new_len < old_len:
            # Check if it's a pure deletion
            if new_content in old_content:
                return "delete"
            else:
                return "replace"
        else:
            return "replace"
    
    @staticmethod
    def validate_operations(operations: List[Dict[str, Any]], original_text: str) -> bool:
        """
        Validate that operations can be applied to the original text.
        
        Args:
            operations: List of OT operations to validate
            original_text: The text to apply operations to
            
        Returns:
            True if operations are valid, False otherwise
        """
        try:
            # Try to apply operations to see if they're valid
            current_text = original_text
            
            # Sort operations for safe application
            deletes = [op for op in operations if op.get("operation") == "ot_delete"]
            inserts = [op for op in operations if op.get("operation") == "ot_insert"]
            
            # Apply deletes in reverse order
            deletes.sort(key=lambda op: op.get("position", 0), reverse=True)
            for op in deletes:
                pos = op.get("position", 0)
                length = op.get("length", 0)
                
                if pos < 0 or pos > len(current_text):
                    return False
                if pos + length > len(current_text):
                    return False
                
                current_text = current_text[:pos] + current_text[pos + length:]
            
            # Apply inserts in forward order
            inserts.sort(key=lambda op: op.get("position", 0))
            for op in inserts:
                pos = op.get("position", 0)
                content = op.get("content", "")
                
                if pos < 0 or pos > len(current_text):
                    return False
                
                current_text = current_text[:pos] + content + current_text[pos:]
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def normalize_line_endings(text: str) -> str:
        """
        Normalize line endings to Unix format (\n).
        
        Converts Windows (\r\n) and classic Mac (\r) line endings to Unix (\n).
        This ensures consistent line ending handling across different platforms
        and web form submissions.
        
        Args:
            text: Text with potentially mixed line endings
            
        Returns:
            Text with normalized Unix line endings
        """
        # First convert \r\n to \n (Windows to Unix)
        # Then convert remaining \r to \n (classic Mac to Unix)
        return text.replace('\r\n', '\n').replace('\r', '\n')

    @staticmethod
    def create_api_payload(
        document_id: str,
        old_content: str,
        new_content: str,
        document_version: int,
        cursor_position: int = None,
        optimize: bool = True
    ) -> Dict[str, Any]:
        """
        Create a complete API payload for document changes.
        
        Args:
            document_id: UUID of the document
            old_content: Original content
            new_content: New content
            document_version: Current document version
            cursor_position: Optional cursor position
            optimize: Whether to optimize operations
            
        Returns:
            Complete payload ready for API submission
        """
        logger.info(f"Creating API payload for document {document_id}")
        logger.info(f"Old content length: {len(old_content)}, New content length: {len(new_content)}")
        logger.info(f"Old content repr: {repr(old_content)}")
        logger.info(f"New content repr: {repr(new_content)}")
        logger.info(f"Old content visual: {old_content.replace(chr(10), '¶LF').replace(chr(13), '¶CR')}")
        logger.info(f"New content visual: {new_content.replace(chr(10), '¶LF').replace(chr(13), '¶CR')}")
        
        # Normalize line endings to ensure consistency
        normalized_old_content = ContentDiffGenerator.normalize_line_endings(old_content)
        normalized_new_content = ContentDiffGenerator.normalize_line_endings(new_content)
        
        logger.info(f"Normalized old content repr: {repr(normalized_old_content)}")
        logger.info(f"Normalized new content repr: {repr(normalized_new_content)}")
        
        change_data = ContentDiffGenerator.generate_operations_from_form_data(
            normalized_old_content, normalized_new_content, document_version, cursor_position
        )
        
        logger.info(f"Generated {len(change_data['changes'])} operations")
        
        if optimize and change_data["changes"]:
            original_count = len(change_data["changes"])
            change_data["changes"] = ContentDiffGenerator.optimize_operations(
                change_data["changes"]
            )
            logger.info(f"Optimized operations from {original_count} to {len(change_data['changes'])}")
        
        # Validate operations before creating payload using normalized content
        if not ContentDiffGenerator.validate_operations(change_data["changes"], normalized_old_content):
            logger.error("Generated operations failed validation")
            raise ValueError("Generated operations are invalid")
        
        payload = {
            "document_id": document_id,
            "version": change_data["version"],
            "changes": change_data["changes"],
            "change_type": ContentDiffGenerator.detect_change_type(old_content, new_content),
            "operation_count": len(change_data["changes"])
        }
        
        logger.info(f"Created API payload: {payload}")
        return payload


class FormChangeAnalyzer:
    """
    Analyzes web form changes to provide additional context for OT operations.
    
    This class helps optimize OT operation generation by understanding the
    context of how users interact with web forms.
    """
    
    @staticmethod
    def detect_typing_pattern(old_content: str, new_content: str) -> Dict[str, Any]:
        """
        Detect if the change represents a typing pattern (common in text editing).
        
        Args:
            old_content: Original content
            new_content: New content
            
        Returns:
            Dictionary with pattern information
        """
        # Find common prefix and suffix to identify change location
        old_len = len(old_content)
        new_len = len(new_content)
        
        # Find common prefix
        prefix_len = 0
        while (prefix_len < old_len and prefix_len < new_len and
               old_content[prefix_len] == new_content[prefix_len]):
            prefix_len += 1
        
        # Find common suffix
        suffix_len = 0
        while (suffix_len < (old_len - prefix_len) and
               suffix_len < (new_len - prefix_len) and
               old_content[old_len - 1 - suffix_len] == new_content[new_len - 1 - suffix_len]):
            suffix_len += 1
        
        # Analyze the change
        changed_old = old_content[prefix_len:old_len - suffix_len]
        changed_new = new_content[prefix_len:new_len - suffix_len]
        
        pattern_info = {
            "change_position": prefix_len,
            "old_text": changed_old,
            "new_text": changed_new,
            "is_insertion": len(changed_old) == 0,
            "is_deletion": len(changed_new) == 0,
            "is_replacement": len(changed_old) > 0 and len(changed_new) > 0,
            "character_delta": len(changed_new) - len(changed_old)
        }
        
        # Detect common typing patterns
        if pattern_info["is_insertion"] and len(changed_new) == 1:
            pattern_info["pattern_type"] = "single_character_insert"
        elif pattern_info["is_deletion"] and len(changed_old) == 1:
            pattern_info["pattern_type"] = "single_character_delete"
        elif pattern_info["is_insertion"] and changed_new.isspace():
            pattern_info["pattern_type"] = "whitespace_insert"
        elif pattern_info["is_replacement"] and len(changed_new) == 1 and len(changed_old) == 1:
            pattern_info["pattern_type"] = "character_replacement"
        else:
            pattern_info["pattern_type"] = "bulk_change"
            
        return pattern_info
    
    @staticmethod
    def suggest_cursor_position(old_content: str, new_content: str) -> int:
        """
        Suggest likely cursor position after the change.
        
        Args:
            old_content: Original content
            new_content: New content
            
        Returns:
            Suggested cursor position
        """
        pattern = FormChangeAnalyzer.detect_typing_pattern(old_content, new_content)
        
        if pattern["is_insertion"]:
            # Cursor likely at end of inserted text
            return pattern["change_position"] + len(pattern["new_text"])
        elif pattern["is_deletion"]:
            # Cursor likely at deletion point
            return pattern["change_position"]
        else:
            # For replacements, cursor likely at end of new text
            return pattern["change_position"] + len(pattern["new_text"])