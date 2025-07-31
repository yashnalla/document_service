class DocumentChangeError(Exception):
    """Base exception for document change operations."""

    pass


class VersionConflictError(DocumentChangeError):
    """Raised when attempting to apply changes to an outdated document version."""

    pass


class InvalidChangeError(DocumentChangeError):
    """Raised when a change operation is invalid or malformed."""

    pass


class TextNotFoundError(DocumentChangeError):
    """Raised when trying to replace text that doesn't exist in the document."""

    pass


class InvalidRangeError(DocumentChangeError):
    """Raised when a position-based change has an invalid range."""

    pass
