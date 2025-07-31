from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, DocumentChange
from .exceptions import VersionConflictError, InvalidChangeError
from .change_operations import ChangeProcessor
from .utils import update_lexical_content_with_text


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class DocumentListSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "version",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at", "created_by"]


class DocumentSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    last_modified_by = UserSerializer(read_only=True)
    etag = serializers.CharField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    last_modified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "version",
            "etag",
            "created_at",
            "updated_at",
            "created_by",
            "last_modified_by",
            "created_by_name",
            "last_modified_by_name",
        ]
        read_only_fields = [
            "id",
            "version",
            "etag",
            "created_at",
            "updated_at",
            "created_by",
            "last_modified_by",
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_last_modified_by_name(self, obj):
        if obj.last_modified_by:
            return obj.last_modified_by.get_full_name() or obj.last_modified_by.username
        return None

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content must be a valid JSON object.")
        return value

    def update(self, instance, validated_data):
        # Set last_modified_by to current user
        if "request" in self.context:
            validated_data["last_modified_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class DocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["title", "content"]

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        if len(value) > 255:
            raise serializers.ValidationError("Title cannot exceed 255 characters.")
        return value.strip()

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content must be a valid JSON object.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        if user.is_authenticated:
            validated_data["created_by"] = user
        else:
            # For anonymous users, create or get a default user
            from django.contrib.auth.models import User

            default_user, created = User.objects.get_or_create(
                username="anonymous",
                defaults={
                    "first_name": "Anonymous",
                    "last_name": "User",
                    "email": "anonymous@example.com",
                },
            )
            validated_data["created_by"] = default_user
        return super().create(validated_data)


class ChangeOperationSerializer(serializers.Serializer):
    """Serializer for individual change operations."""

    operation = serializers.CharField()
    target = serializers.DictField(required=False)
    range = serializers.DictField(required=False)
    replacement = serializers.CharField(required=False, allow_blank=True)
    text = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        operation = data.get("operation")
        if operation != "replace":
            raise serializers.ValidationError("Only 'replace' operation is supported")

        # Validate text-based change
        if "target" in data:
            target = data["target"]
            if not isinstance(target, dict) or "text" not in target:
                raise serializers.ValidationError("Target must have 'text' field")

            occurrence = target.get("occurrence", 1)
            if not isinstance(occurrence, int) or occurrence < 1:
                raise serializers.ValidationError(
                    "Occurrence must be a positive integer"
                )

            if "replacement" not in data:
                raise serializers.ValidationError(
                    "Text-based change requires 'replacement' field"
                )

        # Validate position-based change
        elif "range" in data:
            range_data = data["range"]
            if not isinstance(range_data, dict):
                raise serializers.ValidationError("Range must be a dictionary")

            start = range_data.get("start")
            end = range_data.get("end")

            if not isinstance(start, int) or not isinstance(end, int):
                raise serializers.ValidationError(
                    "Range start and end must be integers"
                )

            if start < 0 or end < 0:
                raise serializers.ValidationError("Range values must be non-negative")

            if start > end:
                raise serializers.ValidationError("Range start must be <= end")

            if "text" not in data:
                raise serializers.ValidationError(
                    "Position-based change requires 'text' field"
                )

        else:
            raise serializers.ValidationError(
                "Change must have either 'target' or 'range'"
            )

        return data


class DocumentChangeSerializer(serializers.Serializer):
    """Serializer for applying changes to a document."""

    version = serializers.IntegerField()
    changes = ChangeOperationSerializer(many=True)

    def validate(self, data):
        if not data.get("changes"):
            raise serializers.ValidationError("At least one change is required")
        return data

    def update(self, instance, validated_data):
        """Apply changes to the document."""
        expected_version = validated_data["version"]
        changes = validated_data["changes"]
        user = self.context["request"].user

        # Check version conflict
        if instance.version != expected_version:
            raise VersionConflictError(
                f"Version conflict: expected {expected_version}, got {instance.version}"
            )

        # Get current plain text
        original_text = instance.get_plain_text()

        # Apply changes
        try:
            processor = ChangeProcessor(changes)
            new_text = processor.apply_changes(original_text)
        except Exception as e:
            raise InvalidChangeError(f"Failed to apply changes: {str(e)}")

        # Update document content
        instance.content = update_lexical_content_with_text(instance.content, new_text)
        instance.last_modified_by = user
        instance.save()

        # Record the change
        DocumentChange.objects.create(
            document=instance,
            change_data=changes,
            applied_by=user,
            from_version=expected_version,
            to_version=instance.version,
        )

        return instance


class DocumentChangeHistorySerializer(serializers.ModelSerializer):
    """Serializer for document change history."""

    applied_by = UserSerializer(read_only=True)
    applied_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChange
        fields = [
            "id",
            "change_data",
            "applied_by",
            "applied_by_name",
            "applied_at",
            "from_version",
            "to_version",
        ]

    def get_applied_by_name(self, obj):
        return obj.applied_by.get_full_name() or obj.applied_by.username
