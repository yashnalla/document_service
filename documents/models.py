import uuid
import hashlib
import json
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.JSONField(default=dict, help_text="Lexical editor content")
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

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    def __repr__(self):
        return f"<Document: {self.title} (v{self.version})>"

    @property
    def etag(self):
        content_str = json.dumps(self.content, sort_keys=True)
        content_with_version = f"{content_str}:{self.version}"
        return hashlib.md5(content_with_version.encode()).hexdigest()

    def increment_version(self):
        self.version += 1
        self.save()

    def get_plain_text(self):
        if not self.content or not isinstance(self.content, dict):
            return ""

        def extract_text_from_nodes(nodes):
            text_parts = []
            if not isinstance(nodes, list):
                return ""

            for node in nodes:
                if not isinstance(node, dict):
                    continue

                if node.get("type") == "text":
                    text_parts.append(node.get("text", ""))
                elif "children" in node:
                    text_parts.append(extract_text_from_nodes(node["children"]))
                elif "content" in node:
                    text_parts.append(extract_text_from_nodes(node["content"]))

            return " ".join(text_parts)

        # Handle both standard Lexical format (root.children) and alternative format (content)
        root_children = self.content.get("root", {}).get("children", [])
        if not root_children:
            root_children = self.content.get("content", [])
        
        return extract_text_from_nodes(root_children).strip()

    def save(self, *args, **kwargs):
        if self.pk:
            existing = Document.objects.filter(pk=self.pk).first()
            if existing and (
                existing.title != self.title or existing.content != self.content
            ):
                self.version += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("document_detail", kwargs={"pk": self.pk})


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
