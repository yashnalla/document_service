from django.urls import re_path
from documents import consumers

websocket_urlpatterns = [
    re_path(r'ws/documents/(?P<document_id>[0-9a-f-]+)/$', consumers.DocumentConsumer.as_asgi()),
]