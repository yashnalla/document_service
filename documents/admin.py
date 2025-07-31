from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "version", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at", "created_by")
    search_fields = ("title", "created_by__username")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-updated_at",)
