import redis
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse
import os


def health_check(request):
    """Health check endpoint that returns database and Redis connectivity status."""
    status = {"status": "healthy", "database": "unknown", "redis": "unknown"}

    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "unhealthy"

    # Check Redis connectivity
    try:
        cache.set("health_check", "test", 10)
        cache.get("health_check")
        status["redis"] = "connected"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"
        status["status"] = "unhealthy"

    return JsonResponse(status)


def root_redirect(request):
    """
    Root URL handler that redirects users based on authentication status:
    - Authenticated users -> documents list
    - Unauthenticated users -> login page
    """
    if request.user.is_authenticated:
        return redirect('document_list')
    else:
        return redirect('login')
