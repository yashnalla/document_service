from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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
from .services import DocumentService


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
            preview_result = DocumentService.preview_changes(document, changes)
            return Response(preview_result)

        except (ValueError, InvalidChangeError) as e:
            return Response(
                {"error": str(e)},
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
        """Handle document updates via AJAX"""
        document = self.get_object()
        form = DocumentForm(request.POST, instance=document)
        
        if form.is_valid():
            try:
                title = form.cleaned_data.get('title')
                content_text = form.cleaned_data.get('content', '')
                
                # Use DocumentService for consistent updates
                updated_document = DocumentService.update_document(
                    document=document,
                    title=title,
                    content_text=content_text,
                    user=request.user
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Document saved successfully!'})
                else:
                    messages.success(request, 'Document saved successfully!')
                    return redirect('document_detail', pk=updated_document.pk)
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
                else:
                    messages.error(request, f'Error updating document: {str(e)}')
                    return self.render_to_response(self.get_context_data(form=form))
        else:
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
            
            # Use DocumentService for consistent creation
            document = DocumentService.create_document(
                title=title,
                content_text=content_text,
                user=self.request.user
            )
            
            messages.success(self.request, f'Document "{document.title}" created successfully!')
            return redirect('document_detail', pk=document.pk)
        except Exception as e:
            messages.error(self.request, f'Error creating document: {str(e)}')
            return self.form_invalid(form)


class DocumentWebDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    success_url = reverse_lazy('document_list')
    
    def get_queryset(self):
        return Document.objects.filter(created_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        document = self.get_object()
        document_title = document.title
        response = super().delete(request, *args, **kwargs)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Document "{document_title}" deleted successfully!'})
        else:
            messages.success(request, f'Document "{document_title}" deleted successfully!')
            return response


@login_required
@require_POST
def document_autosave(request, pk):
    """Handle auto-save via AJAX"""
    document = get_object_or_404(Document, pk=pk, created_by=request.user)
    
    try:
        # Get the plain text content from POST data
        title = request.POST.get('title', document.title)
        content_text = request.POST.get('content', '')
        
        # Use DocumentService for consistent updates
        updated_document = DocumentService.update_document(
            document=document,
            title=title,
            content_text=content_text,
            user=request.user
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Document saved successfully!',
            'version': updated_document.version
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
