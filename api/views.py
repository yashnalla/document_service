from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "documents": reverse("document-list", request=request, format=format),
            "admin": reverse("admin:index", request=request, format=format),
            "health": reverse("health_check", request=request, format=format),
        }
    )


@api_view(["GET"])
def api_docs(request):
    return Response(
        {
            "title": "Document Service API",
            "version": "1.0.0",
            "description": "REST API for document management with Lexical editor support",
            "endpoints": {
                "GET /api/": "API root - lists all available endpoints",
                "GET /api/documents/": "List all documents (paginated)",
                "POST /api/documents/": "Create a new document (requires authentication)",
                "GET /api/documents/{id}/": "Retrieve a specific document",
                "PUT /api/documents/{id}/": "Update a document (requires ownership)",
                "PATCH /api/documents/{id}/": "Partially update a document (requires ownership)",
                "DELETE /api/documents/{id}/": "Delete a document (requires ownership)",
                "GET /api/documents/my_documents/": "List current user's documents",
                "GET /health/": "Health check endpoint",
            },
            "authentication": "Session-based authentication",
            "permissions": "Read-only for anonymous users, full CRUD for authenticated users on their own documents",
            "pagination": "Page-based pagination with 20 items per page",
            "search": "Use ?search=query parameter on document list endpoint",
        }
    )
