import re
from typing import List, Dict, Any
from .exceptions import (
    InvalidChangeError,
    TextNotFoundError,
    InvalidRangeError,
)
from .utils import update_lexical_content_with_text


class ChangeOperation:
    """Base class for change operations."""

    def __init__(self, operation_data: Dict[str, Any]):
        self.operation_data = operation_data
        self.validate()

    def validate(self):
        """Validate the operation data. Override in subclasses."""
        if not isinstance(self.operation_data, dict):
            raise InvalidChangeError("Operation data must be a dictionary")

        if self.operation_data.get("operation") != "replace":
            raise InvalidChangeError("Only 'replace' operation is currently supported")

    def apply(self, text: str) -> str:
        """Apply the change to the given text. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement apply method")


class TextBasedChange(ChangeOperation):
    """Change operation that finds and replaces text by occurrence number."""

    def validate(self):
        super().validate()

        target = self.operation_data.get("target")
        if not target or not isinstance(target, dict):
            raise InvalidChangeError("Text-based change must have a 'target' object")

        if not target.get("text"):
            raise InvalidChangeError("Target must have 'text' field")

        occurrence = target.get("occurrence", 1)
        if not isinstance(occurrence, int) or occurrence < 1:
            raise InvalidChangeError("Occurrence must be a positive integer")

        replacement = self.operation_data.get("replacement", "")
        if not isinstance(replacement, str):
            raise InvalidChangeError("Replacement must be a string")

    def apply(self, text: str) -> str:
        """Apply text-based replacement."""
        target = self.operation_data["target"]
        target_text = target["text"]
        occurrence = target.get("occurrence", 1)
        replacement = self.operation_data.get("replacement", "")

        # Find all occurrences of the target text
        matches = []
        start = 0
        while True:
            pos = text.find(target_text, start)
            if pos == -1:
                break
            matches.append((pos, pos + len(target_text)))
            start = pos + 1

        if len(matches) < occurrence:
            raise TextNotFoundError(
                f"Target text '{target_text}' occurrence {occurrence} not found. "
                f"Only {len(matches)} occurrences found."
            )

        # Get the specific occurrence to replace
        start_pos, end_pos = matches[occurrence - 1]

        # Replace the text
        new_text = text[:start_pos] + replacement + text[end_pos:]
        return new_text


class PositionBasedChange(ChangeOperation):
    """Change operation that replaces text by character position range."""

    def validate(self):
        super().validate()

        range_data = self.operation_data.get("range")
        if not range_data or not isinstance(range_data, dict):
            raise InvalidChangeError("Position-based change must have a 'range' object")

        start = range_data.get("start")
        end = range_data.get("end")

        if not isinstance(start, int) or not isinstance(end, int):
            raise InvalidChangeError("Range start and end must be integers")

        if start < 0 or end < 0:
            raise InvalidChangeError("Range start and end must be non-negative")

        if start > end:
            raise InvalidChangeError("Range start must be less than or equal to end")

        text = self.operation_data.get("text", "")
        if not isinstance(text, str):
            raise InvalidChangeError("Text must be a string")

    def apply(self, text: str) -> str:
        """Apply position-based replacement."""
        range_data = self.operation_data["range"]
        start = range_data["start"]
        end = range_data["end"]
        replacement = self.operation_data.get("text", "")

        if start > len(text) or end > len(text):
            raise InvalidRangeError(
                f"Range ({start}, {end}) exceeds text length ({len(text)})"
            )

        # Replace the text in the specified range
        new_text = text[:start] + replacement + text[end:]
        return new_text


class ChangeProcessor:
    """Processes multiple change operations on a document."""

    def __init__(self, changes: List[Dict[str, Any]]):
        self.changes = changes
        self.operations = []
        self._parse_changes()

    def _parse_changes(self):
        """Parse changes into operation objects."""
        for change_data in self.changes:
            if "range" in change_data:
                # Position-based change
                operation = PositionBasedChange(change_data)
            elif "target" in change_data:
                # Text-based change
                operation = TextBasedChange(change_data)
            else:
                raise InvalidChangeError(
                    "Change must have either 'range' or 'target' field"
                )

            self.operations.append(operation)

    def apply_changes(self, original_text: str) -> str:
        """Apply all changes to the text, handling position-based changes first."""
        # Separate position-based and text-based changes
        position_based = []
        text_based = []

        for operation in self.operations:
            if isinstance(operation, PositionBasedChange):
                position_based.append(operation)
            else:
                text_based.append(operation)

        # Sort position-based changes by start position in reverse order
        # This ensures that later changes don't affect earlier positions
        position_based.sort(
            key=lambda op: op.operation_data["range"]["start"], reverse=True
        )

        # Apply position-based changes first
        current_text = original_text
        for operation in position_based:
            current_text = operation.apply(current_text)

        # Apply text-based changes
        for operation in text_based:
            current_text = operation.apply(current_text)

        return current_text

    def preview_changes(self, original_text: str) -> Dict[str, Any]:
        """Preview the changes without applying them permanently."""
        try:
            new_text = self.apply_changes(original_text)
            return {
                "success": True,
                "original_text": original_text,
                "new_text": new_text,
                "changes_count": len(self.operations),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "original_text": original_text}
