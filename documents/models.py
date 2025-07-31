import uuid
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

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    def __repr__(self):
        return f"<Document: {self.title} (v{self.version})>"

    def save(self, *args, **kwargs):
        if self.pk:
            existing = Document.objects.filter(pk=self.pk).first()
            if existing and (
                existing.title != self.title or existing.content != self.content
            ):
                self.version += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("document-detail", kwargs={"pk": self.pk})
