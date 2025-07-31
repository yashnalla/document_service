from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document


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

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "version",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at", "created_by"]

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content must be a valid JSON object.")
        return value


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
                    "email": "anonymous@example.com"
                }
            )
            validated_data["created_by"] = default_user
        return super().create(validated_data)
