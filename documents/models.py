import uuid
import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.urls import reverse


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField(default="", help_text="Document content as plain text")
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="documents"
    )
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="modified_documents",
        null=True,
        blank=True,
    )
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self):
        return self.title

    def __repr__(self):
        return f"<Document: {self.title} (v{self.version})>"

    @property
    def etag(self):
        content_with_version = f"{self.content}:{self.version}"
        return hashlib.md5(content_with_version.encode()).hexdigest()

    def increment_version(self):
        self.version += 1
        self.save()

    def update_search_vector(self):
        """Update the search vector with title and content text."""
        # Create search vector with weighted terms:
        # Title has weight 'A' (highest priority)
        # Content text has weight 'B' (medium priority)
        self.search_vector = (
            SearchVector('title', weight='A') +
            SearchVector('content', weight='B')
        )

    def save(self, *args, **kwargs):
        should_update_search = False
        
        if self.pk:
            existing = Document.objects.filter(pk=self.pk).first()
            if existing and (
                existing.title != self.title or existing.content != self.content
            ):
                self.version += 1
                should_update_search = True
        else:
            # New document
            should_update_search = True
        
        # Update search vector if title or content changed
        if should_update_search:
            self.update_search_vector()
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("document_detail", kwargs={"pk": self.pk})

    @property
    def get_plain_text(self):
        """Return the plain text content for backward compatibility."""
        return self.content or ""


class DocumentChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="changes"
    )
    change_data = models.JSONField(
        help_text="JSON data representing the changes applied"
    )
    applied_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="applied_changes"
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    from_version = models.IntegerField()
    to_version = models.IntegerField()

    class Meta:
        ordering = ["-applied_at"]

    def __str__(self):
        return f"Change to {self.document.title} (v{self.from_version} -> v{self.to_version})"
