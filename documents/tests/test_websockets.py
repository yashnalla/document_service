import json
import pytest
import uuid
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from documents.models import Document
from documents.consumers import DocumentConsumer
from document_service.routing import websocket_urlpatterns
from channels.routing import URLRouter
from channels.auth import AuthMiddlewareStack


class WebSocketTests(TransactionTestCase):
    """Test WebSocket functionality for document collaboration."""

    def setUp(self):
        """Set up test data."""
        # Use unique usernames to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        self.user1 = User.objects.create_user(
            username=f'testuser1_{unique_id}', 
            email=f'test1_{unique_id}@example.com', 
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username=f'testuser2_{unique_id}', 
            email=f'test2_{unique_id}@example.com', 
            password='testpass123'
        )
        
        self.document = Document.objects.create(
            title="Test Document",
            content={"root": {"children": []}},
            created_by=self.user1
        )

    def tearDown(self):
        """Clean up after tests."""
        # Clear any presence data
        # Note: Standard Django cache doesn't have delete_pattern
        # We need to delete specific keys
        for user in [self.user1, self.user2]:
            presence_key = f"presence:document:{self.document.id}:{user.id}"
            cache.delete(presence_key)

    @database_sync_to_async
    def get_user(self, username):
        """Get user for async tests."""
        return User.objects.get(username=username)

    @database_sync_to_async
    def get_document(self):
        """Get document for async tests."""
        return Document.objects.get(id=self.document.id)

    async def test_websocket_connection_authenticated(self):
        """Test WebSocket connection with authenticated user."""
        application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        communicator = WebsocketCommunicator(
            application,
            f"/ws/documents/{self.document.id}/"
        )
        
        # Set up user authentication
        communicator.scope["user"] = await self.get_user(self.user1.username)
        
        connected, subprotocol = await communicator.connect()
        assert connected
        
        # Send a ping message
        await communicator.send_json_to({
            'type': 'ping',
            'timestamp': 1234567890
        })
        
        # Should receive pong response
        response = await communicator.receive_json_from()
        assert response['type'] == 'pong'
        assert response['timestamp'] == 1234567890
        
        await communicator.disconnect()

    async def test_websocket_connection_unauthenticated(self):
        """Test WebSocket connection rejection for unauthenticated users."""
        from django.contrib.auth.models import AnonymousUser
        
        application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        communicator = WebsocketCommunicator(
            application,
            f"/ws/documents/{self.document.id}/"
        )
        
        # Set up anonymous user
        communicator.scope["user"] = AnonymousUser()
        
        connected, subprotocol = await communicator.connect()
        assert not connected

    async def test_websocket_nonexistent_document(self):
        """Test WebSocket connection to non-existent document."""
        fake_document_id = uuid.uuid4()
        
        application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        communicator = WebsocketCommunicator(
            application,
            f"/ws/documents/{fake_document_id}/"
        )
        
        communicator.scope["user"] = await self.get_user(self.user1.username)
        
        connected, subprotocol = await communicator.connect()
        assert not connected

    # async def test_websocket_typing_indicators(self):
    #     """Test typing indicator functionality."""
    #     # Set up two communicators for different users
    #     communicator1 = WebsocketCommunicator(
    #         DocumentConsumer.as_asgi(),
    #         f"/ws/documents/{self.document.id}/"
    #     )
    #     communicator1.scope["user"] = await self.get_user(self.user1.username)
    #
    #     communicator2 = WebsocketCommunicator(
    #         DocumentConsumer.as_asgi(),
    #         f"/ws/documents/{self.document.id}/"
    #     )
    #     communicator2.scope["user"] = await self.get_user(self.user2.username)
    #
    #     # Connect both users
    #     connected1, _ = await communicator1.connect()
    #     connected2, _ = await communicator2.connect()
    #     assert connected1 and connected2
    #
    #     # Clear initial presence messages
    #     await communicator1.receive_json_from()  # user2 joined
    #     await communicator2.receive_json_from()  # user1 joined
    #
    #     # User1 starts typing
    #     await communicator1.send_json_to({
    #         'type': 'user_typing',
    #         'is_typing': True
    #     })
    #
    #     # User2 should receive typing notification
    #     response = await communicator2.receive_json_from()
    #     assert response['type'] == 'user_typing'
    #     assert response['username'] == self.user1.username
    #     assert response['is_typing'] is True
    #
    #     # User1 stops typing
    #     await communicator1.send_json_to({
    #         'type': 'user_typing',
    #         'is_typing': False
    #     })
    #
    #     # User2 should receive stop typing notification
    #     response = await communicator2.receive_json_from()
    #     assert response['type'] == 'user_typing'
    #     assert response['username'] == self.user1.username
    #     assert response['is_typing'] is False
    #
    #     await communicator1.disconnect()
    #     await communicator2.disconnect()

    # async def test_websocket_presence_updates(self):
    #     """Test user presence update functionality."""
    #     communicator1 = WebsocketCommunicator(
    #         DocumentConsumer.as_asgi(),
    #         f"/ws/documents/{self.document.id}/"
    #     )
    #     communicator1.scope["user"] = await self.get_user(self.user1.username)
    #
    #     communicator2 = WebsocketCommunicator(
    #         DocumentConsumer.as_asgi(),
    #         f"/ws/documents/{self.document.id}/"
    #     )
    #     communicator2.scope["user"] = await self.get_user(self.user2.username)
    #
    #     # Connect first user
    #     connected1, _ = await communicator1.connect()
    #     assert connected1
    #
    #     # Connect second user
    #     connected2, _ = await communicator2.connect()
    #     assert connected2
    #
    #     # User1 should receive notification that user2 joined
    #     response = await communicator1.receive_json_from()
    #     assert response['type'] == 'presence_update'
    #     assert response['action'] == 'user_joined'
    #     assert response['username'] == self.user2.username
    #
    #     # User2 should receive notification that user1 was already there
    #     response = await communicator2.receive_json_from()
    #     assert response['type'] == 'presence_update'
    #     assert response['action'] == 'user_joined'
    #     assert response['username'] == self.user1.username
    #
    #     # Disconnect user2
    #     await communicator2.disconnect()
    #
    #     # User1 should receive notification that user2 left
    #     response = await communicator1.receive_json_from()
    #     assert response['type'] == 'presence_update'
    #     assert response['action'] == 'user_left'
    #     assert response['username'] == self.user2.username
    #
    #     await communicator1.disconnect()


    def test_channel_layer_configuration(self):
        """Test that channel layer is properly configured."""
        channel_layer = get_channel_layer()
        assert channel_layer is not None
        assert hasattr(channel_layer, 'group_add')
        assert hasattr(channel_layer, 'group_send')

    def test_presence_cache_operations(self):
        """Test presence tracking cache operations."""
        document_id = str(self.document.id)
        user_id = str(self.user1.id)
        presence_key = f"presence:document:{document_id}"
        user_presence_key = f"{presence_key}:{user_id}"
        
        # Set presence data
        presence_data = {
            'username': self.user1.username,
            'user_id': user_id,
            'connected_at': 'test_timestamp'
        }
        cache.set(user_presence_key, presence_data, timeout=300)
        
        # Retrieve and verify presence data
        retrieved_data = cache.get(user_presence_key)
        assert retrieved_data is not None
        assert retrieved_data['username'] == self.user1.username
        assert retrieved_data['user_id'] == user_id
        
        # Clean up
        cache.delete(user_presence_key)
        assert cache.get(user_presence_key) is None


# Integration tests using pytest marks
@pytest.mark.django_db
class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def document(self, user):
        """Create a test document."""
        return Document.objects.create(
            title="Test Document",
            content={"root": {"children": []}},
            created_by=user
        )
    
    def test_websocket_routing_pattern(self, document):
        """Test that WebSocket routing pattern matches correctly."""
        from document_service.routing import websocket_urlpatterns
        from django.urls import resolve, NoReverseMatch
        import re
        
        # Test that the routing pattern exists
        assert len(websocket_urlpatterns) > 0
        
        # Test pattern matching
        pattern = websocket_urlpatterns[0].pattern
        test_path = f'ws/documents/{document.id}/'
        match = pattern.regex.match(test_path)
        assert match is not None
        assert match.groupdict()['document_id'] == str(document.id)
    
    # @pytest.mark.asyncio
    # async def test_websocket_full_flow(self, user, document):
    #     """Test complete WebSocket interaction flow."""
    #     application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
    #     communicator = WebsocketCommunicator(
    #         application,
    #         f"/ws/documents/{document.id}/"
    #     )
    #     communicator.scope["user"] = user
    #
    #     # Connect
    #     connected, _ = await communicator.connect()
    #     assert connected
    #
    #     # Test ping/pong
    #     await communicator.send_json_to({'type': 'ping', 'timestamp': 123})
    #     response = await communicator.receive_json_from()
    #     assert response['type'] == 'pong'
    #
    #     # Test typing
    #     await communicator.send_json_to({'type': 'user_typing', 'is_typing': True})
    #     # No response expected for own typing
    #
    #     # Test cursor position
    #     await communicator.send_json_to({'type': 'cursor_position', 'position': 100})
    #     # No response expected for own cursor movement
    #
    #     await communicator.disconnect()