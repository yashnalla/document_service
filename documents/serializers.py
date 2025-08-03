import logging
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, DocumentChange
from .services import DocumentService

logger = logging.getLogger(__name__)


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
        # Use DocumentService for consistent updates
        user = self.context.get("request").user if "request" in self.context else None
        title = validated_data.get("title")
        content = validated_data.get("content")
        
        return DocumentService.update_document(
            document=instance,
            title=title,
            content=content,
            user=user
        )


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
        title = validated_data["title"]
        content = validated_data.get("content")
        
        return DocumentService.create_document(
            title=title,
            content=content,
            user=user if user.is_authenticated else None
        )


class ChangeOperationSerializer(serializers.Serializer):
    """Serializer for sequential Operational Transform operations."""

    operation = serializers.CharField()
    # Sequential OT operation fields (no absolute positions)
    content = serializers.CharField(required=False, allow_blank=True)
    length = serializers.IntegerField(required=False)

    def validate(self, data):
        operation = data.get("operation")
        logger.info(f"Validating operation: {operation} with data: {data}")
        
        # Handle sequential OT operations
        if operation in ["retain", "insert", "delete"]:
            result = self._validate_sequential_ot_operation(data)
            logger.info(f"Operation validation passed for {operation}")
            return result
        else:
            logger.error(f"Unsupported operation: {operation}")
            raise serializers.ValidationError(
                f"Unsupported operation: {operation}. "
                f"Supported operations: 'retain', 'insert', 'delete'"
            )
    
    def _validate_sequential_ot_operation(self, data):
        """Validate sequential OT operations (retain, insert, delete)."""
        operation = data.get("operation")
        
        if operation == "insert":
            # Insert operation needs content
            if "content" not in data:
                raise serializers.ValidationError("insert operation requires 'content' field")
            
            content = data["content"]
            if not isinstance(content, str):
                raise serializers.ValidationError("Content must be a string")
            
            if len(content) == 0:
                raise serializers.ValidationError("Insert content cannot be empty")
        
        elif operation == "delete":
            # Delete operation needs length
            if "length" not in data:
                raise serializers.ValidationError("delete operation requires 'length' field")
            
            length = data["length"]
            if not isinstance(length, int) or length <= 0:
                raise serializers.ValidationError("Length must be a positive integer")
        
        elif operation == "retain":
            # Retain operation needs length
            if "length" not in data:
                raise serializers.ValidationError("retain operation requires 'length' field")
            
            length = data["length"]
            if not isinstance(length, int) or length <= 0:
                raise serializers.ValidationError("Length must be a positive integer")
        
        return data


class DocumentChangeSerializer(serializers.Serializer):
    """Serializer for applying changes to a document."""

    version = serializers.IntegerField()
    changes = ChangeOperationSerializer(many=True)

    def validate(self, data):
        logger.info(f"DocumentChangeSerializer validating data: {data}")
        
        if not data.get("changes"):
            logger.error("No changes provided in DocumentChangeSerializer")
            raise serializers.ValidationError("At least one change is required")
        
        logger.info(f"DocumentChangeSerializer validation passed with {len(data.get('changes', []))} changes")
        return data

    def update(self, instance, validated_data):
        """Apply changes to the document."""
        expected_version = validated_data["version"]
        changes = validated_data["changes"]
        user = self.context["request"].user

        logger.info(f"DocumentChangeSerializer applying {len(changes)} changes to document {instance.id}")
        logger.info(f"Expected version: {expected_version}, current version: {instance.version}")

        return DocumentService.apply_changes(
            document=instance,
            changes=changes,
            user=user,
            expected_version=expected_version
        )


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
