from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
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
