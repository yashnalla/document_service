from django.urls import path
from . import views

# Web interface URL patterns only
# API routes are handled in api/urls.py
urlpatterns = [
    # Web interface routes
    path("", views.DocumentWebListView.as_view(), name="document_list"),
    path("create/", views.DocumentWebCreateView.as_view(), name="document_create"),
    path("<uuid:pk>/", views.DocumentWebDetailView.as_view(), name="document_detail"),
    path("<uuid:pk>/delete/", views.DocumentWebDeleteView.as_view(), name="document_delete"),
    path("<uuid:pk>/autosave/", views.document_autosave, name="document_autosave"),
]
