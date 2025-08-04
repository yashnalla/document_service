from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path("", views.root_redirect, name="root"),
    path("admin/", admin.site.urls),
    path("health/", views.health_check, name="health_check"),
    
    # Authentication URLs
    path("accounts/", include("django.contrib.auth.urls")),
    
    # API routes
    path("api/", include("api.urls")),
    
    # Web interface routes  
    path("documents/", include("documents.urls")),
]

# Serve static files in development when using Daphne
if settings.DEBUG and settings.STATICFILES_DIRS:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
