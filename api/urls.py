from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from documents import views as document_views

# DRF API routes
router = DefaultRouter()
router.register(r"documents", document_views.DocumentViewSet)

urlpatterns = [
    path("", views.api_root, name="api-root"),
    path("docs/", views.api_docs, name="api-docs"),
    # Include DRF router URLs
    path("", include(router.urls)),
]
