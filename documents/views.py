from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.http import HttpResponse
from .models import Document
from .serializers import (
    DocumentSerializer,
    DocumentListSerializer,
    DocumentCreateSerializer,
    DocumentChangeSerializer,
    DocumentChangeHistorySerializer,
)
from .exceptions import VersionConflictError, InvalidChangeError
from .change_operations import ChangeProcessor


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        elif self.action == "create":
            return DocumentCreateSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        """Create a document and return full document data."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        # Return full document data using DocumentSerializer
        response_serializer = DocumentSerializer(document, context={"request": request})
        headers = self.get_success_headers(response_serializer.data)
        response = Response(
            response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

        # Add ETag header
        response["ETag"] = f'"{document.etag}"'
        return response

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a document with ETag header."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response = Response(serializer.data)

        # Add ETag header
        response["ETag"] = f'"{instance.etag}"'
        return response

    def update(self, request, *args, **kwargs):
        """Update a document with ETag header."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        response = Response(serializer.data)

        # Add ETag header
        response["ETag"] = f'"{instance.etag}"'
        return response

    def get_queryset(self):
        queryset = Document.objects.all()
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        return queryset

    @action(detail=True, methods=["patch"], url_path="changes")
    def apply_changes(self, request, pk=None):
        """Apply changes to a document with version control."""
        document = self.get_object()
        serializer = DocumentChangeSerializer(
            document, data=request.data, context={"request": request}
        )

        try:
            serializer.is_valid(raise_exception=True)
            updated_document = serializer.save()

            # Return updated document data
            response_serializer = DocumentSerializer(
                updated_document, context={"request": request}
            )
            response = Response(response_serializer.data)
            response["ETag"] = f'"{updated_document.etag}"'
            return response

        except VersionConflictError as e:
            return Response(
                {"error": str(e), "current_version": document.version},
                status=status.HTTP_409_CONFLICT,
            )
        except InvalidChangeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="preview")
    def preview_changes(self, request, pk=None):
        """Preview changes without applying them."""
        document = self.get_object()

        try:
            changes = request.data.get("changes", [])
            if not changes:
                return Response(
                    {"error": "No changes provided"}, status=status.HTTP_400_BAD_REQUEST
                )

            processor = ChangeProcessor(changes)
            original_text = document.get_plain_text()
            preview_result = processor.preview_changes(original_text)

            return Response(
                {
                    "document_id": document.id,
                    "current_version": document.version,
                    "preview": preview_result,
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Preview failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"], url_path="history")
    def change_history(self, request, pk=None):
        """Get change history for a document."""
        document = self.get_object()
        changes = document.changes.all()

        # Paginate the results
        page = self.paginate_queryset(changes)
        if page is not None:
            serializer = DocumentChangeHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DocumentChangeHistorySerializer(changes, many=True)
        return Response(serializer.data)
