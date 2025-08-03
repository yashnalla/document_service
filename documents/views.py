import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)
from .models import Document
from .forms import DocumentForm, DocumentCreateForm
from .serializers import (
    DocumentSerializer,
    DocumentListSerializer,
    DocumentCreateSerializer,
    DocumentChangeSerializer,
    DocumentChangeHistorySerializer,
)
from .exceptions import VersionConflictError, InvalidChangeError
from .api_client import DocumentAPIClient, APIClientError, APIConflictError, APIValidationError
from .content_diff import ContentDiffGenerator


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
        
        logger.info(f"Apply changes request for document {pk}")
        logger.info(f"Request data: {request.data}")
        logger.info(f"Document current version: {document.version}")
        logger.info(f"Document content length: {len(document.get_plain_text())}")
        
        serializer = DocumentChangeSerializer(
            document, data=request.data, context={"request": request}
        )

        try:
            logger.info("Validating serializer...")
            serializer.is_valid(raise_exception=True)
            logger.info("Serializer validation passed, applying changes...")
            
            updated_document = serializer.save()
            logger.info(f"Changes applied successfully, new version: {updated_document.version}")

            # Return updated document data
            response_serializer = DocumentSerializer(
                updated_document, context={"request": request}
            )
            response = Response(response_serializer.data)
            response["ETag"] = f'"{updated_document.etag}"'
            return response

        except VersionConflictError as e:
            logger.warning(f"Version conflict: {str(e)}")
            return Response(
                {"error": str(e), "current_version": document.version},
                status=status.HTTP_409_CONFLICT,
            )
        except InvalidChangeError as e:
            logger.error(f"Invalid change error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in apply_changes: {str(e)}", exc_info=True)
            if hasattr(serializer, 'errors') and serializer.errors:
                logger.error(f"Serializer errors: {serializer.errors}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

            # Use DocumentService for preview (now uses OT operations directly)
            from .services import DocumentService
            preview_result = DocumentService.preview_changes(document, changes)
            
            return Response(preview_result)

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

    # Delete functionality is available through standard ModelViewSet


# Template-based views for web interface
class DocumentWebListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'documents/list.html'
    context_object_name = 'documents'
    paginate_by = 12

    def get_queryset(self):
        return Document.objects.filter(created_by=self.request.user)


class DocumentWebDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'documents/detail.html'
    context_object_name = 'document'

    def get_queryset(self):
        return Document.objects.filter(created_by=self.request.user)

    def post(self, request, *args, **kwargs):
        """Handle document updates via API with OT operations"""
        document = self.get_object()
        
        logger.info(f"Web view POST request for document {document.id}")
        logger.info(f"User: {request.user}")
        logger.info(f"POST data keys: {list(request.POST.keys())}")
        
        form = DocumentForm(request.POST, instance=document)
        
        if form.is_valid():
            try:
                content_text = form.cleaned_data.get('content', '')
                
                # Refresh document from database to get latest content
                document.refresh_from_db()
                old_content_text = document.get_plain_text()
                
                logger.info(f"Document Lexical content: {document.content}")
                logger.info(f"Old content text: '{old_content_text}'")
                logger.info(f"Old content length: {len(old_content_text)}")
                logger.info(f"New content length: {len(content_text)}")
                logger.info(f"Content changed: {old_content_text != content_text}")
                
                # Create API client
                api_client = DocumentAPIClient(request.user)
                
                # Generate OT operations from form changes
                logger.info("Generating OT operations...")
                api_payload = ContentDiffGenerator.create_api_payload(
                    document_id=str(document.id),
                    old_content=old_content_text,
                    new_content=content_text,
                    document_version=document.version
                )
                
                logger.info(f"Generated API payload: {api_payload}")
                
                # Apply changes via API
                if api_payload['changes']:  # Only send request if there are changes
                    logger.info("Applying changes via API...")
                    updated_document_data = api_client.apply_changes(
                        document_id=str(document.id),
                        version=api_payload['version'],
                        changes=api_payload['changes']
                    )
                    logger.info("Changes applied successfully via API")
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True, 
                            'message': 'Document saved successfully!',
                            'version': updated_document_data.get('version')
                        })
                    else:
                        messages.success(request, 'Document saved successfully!')
                        return redirect('document_detail', pk=document.pk)
                else:
                    # No changes made
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'message': 'No changes to save'})
                    else:
                        return redirect('document_detail', pk=document.pk)
                        
            except APIConflictError as e:
                logger.warning(f"API conflict error in web view: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': 'Document was modified by another user. Please refresh and try again.',
                        'error_type': 'version_conflict',
                        'current_version': e.current_version
                    }, status=409)
                else:
                    messages.error(request, 'Document was modified by another user. Please refresh and try again.')
                    return redirect('document_detail', pk=document.pk)
                    
            except (APIValidationError, APIClientError) as e:
                logger.error(f"API client error in web view: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
                else:
                    messages.error(request, f'Error updating document: {str(e)}')
                    return self.render_to_response(self.get_context_data(form=form))
                    
            except Exception as e:
                logger.error(f"Unexpected error in web view: {str(e)}", exc_info=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'An unexpected error occurred'}, status=500)
                else:
                    messages.error(request, 'An unexpected error occurred')
                    return self.render_to_response(self.get_context_data(form=form))
        else:
            logger.error(f"Form validation failed in web view: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            else:
                return self.render_to_response(self.get_context_data(form=form))


class DocumentWebCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentCreateForm
    template_name = 'documents/create.html'
    
    def form_valid(self, form):
        try:
            title = form.cleaned_data['title']
            content_text = form.cleaned_data.get('content', '')
            
            # Convert content text to Lexical format for API
            from .utils import create_basic_lexical_content
            lexical_content = create_basic_lexical_content(content_text)
            
            # Create API client
            api_client = DocumentAPIClient(self.request.user)
            
            # Create document via API
            document_data = api_client.create_document(
                title=title,
                content=lexical_content
            )
            
            messages.success(self.request, f'Document "{document_data["title"]}" created successfully!')
            return redirect('document_detail', pk=document_data['id'])
            
        except (APIValidationError, APIClientError) as e:
            messages.error(self.request, f'Error creating document: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, 'An unexpected error occurred while creating the document')
            return self.form_invalid(form)




