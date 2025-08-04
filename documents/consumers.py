import json
import logging
import uuid
from typing import Dict, Set
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from .models import Document

logger = logging.getLogger(__name__)


class DocumentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time document collaboration.
    Handles user presence tracking and real-time communication.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_id = None
        self.document_group_name = None
        self.user = None
        self.user_id = None
        self.username = None

    async def connect(self):
        """Handle WebSocket connection."""
        self.document_id = self.scope['url_route']['kwargs']['document_id']
        self.document_group_name = f'document_{self.document_id}'
        self.user = self.scope.get('user')

        # Authenticate user
        if not self.user or isinstance(self.user, AnonymousUser):
            logger.warning(f"Unauthenticated WebSocket connection attempt for document {self.document_id}")
            await self.close()
            return

        self.user_id = str(self.user.id)
        self.username = self.user.username

        # Verify document exists and user has access
        document_exists = await self.check_document_access()
        if not document_exists:
            logger.warning(f"User {self.username} attempted to access non-existent document {self.document_id}")
            await self.close()
            return

        # Accept connection
        await self.accept()

        # Join document group
        await self.channel_layer.group_add(
            self.document_group_name,
            self.channel_name
        )

        # Add user to presence tracking
        await self.add_user_presence()

        # Broadcast user joined
        await self.broadcast_presence_update('user_joined')

        logger.info(f"User {self.username} connected to document {self.document_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.document_group_name and self.user:
            # Remove user from presence tracking
            await self.remove_user_presence()

            # Broadcast user left
            await self.broadcast_presence_update('user_left')

            # Leave document group
            await self.channel_layer.group_discard(
                self.document_group_name,
                self.channel_name
            )

            logger.info(f"User {self.username} disconnected from document {self.document_id}")

    async def receive(self, text_data):
        """Handle messages received from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.handle_ping(data)
            elif message_type == 'user_typing':
                await self.handle_user_typing(data)
            elif message_type == 'cursor_position':
                await self.handle_cursor_position(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_error("Unknown message type")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received from WebSocket")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            await self.send_error("Internal error processing message")

    async def handle_ping(self, data):
        """Handle ping messages for connection health check."""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': data.get('timestamp')
        }))

    async def handle_user_typing(self, data):
        """Handle user typing indicators."""
        # Broadcast typing status to other users
        await self.channel_layer.group_send(
            self.document_group_name,
            {
                'type': 'typing_message',
                'user_id': self.user_id,
                'username': self.username,
                'is_typing': data.get('is_typing', False)
            }
        )

    async def handle_cursor_position(self, data):
        """Handle cursor position updates (for future enhancement)."""
        # Broadcast cursor position to other users
        await self.channel_layer.group_send(
            self.document_group_name,
            {
                'type': 'cursor_message',
                'user_id': self.user_id,
                'username': self.username,
                'position': data.get('position', 0)
            }
        )

    async def typing_message(self, event):
        """Send typing message to WebSocket."""
        # Don't send typing messages to the sender
        if event['user_id'] != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'user_typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    async def cursor_message(self, event):
        """Send cursor position message to WebSocket."""
        # Don't send cursor messages to the sender
        if event['user_id'] != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'cursor_position',
                'user_id': event['user_id'],
                'username': event['username'],
                'position': event['position']
            }))

    async def presence_message(self, event):
        """Send presence update message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'action': event['action'],
            'user_id': event['user_id'],
            'username': event['username'],
            'active_users': event['active_users']
        }))

    async def send_error(self, message):
        """Send error message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    @database_sync_to_async
    def check_document_access(self):
        """Check if the document exists and user has access."""
        try:
            document = Document.objects.get(id=self.document_id)
            # For now, allow access to any authenticated user
            # In the future, you could add permission checks here
            return True
        except Document.DoesNotExist:
            return False

    async def add_user_presence(self):
        """Add user to presence tracking in Redis."""
        presence_key = f"presence:document:{self.document_id}"
        # Use cache to store user presence with TTL
        cache.set(f"{presence_key}:{self.user_id}", {
            'username': self.username,
            'user_id': self.user_id,
            'connected_at': json.dumps({}, default=str),  # Simple timestamp placeholder
        }, timeout=300)  # 5 minute TTL

    async def remove_user_presence(self):
        """Remove user from presence tracking in Redis."""
        presence_key = f"presence:document:{self.document_id}"
        cache.delete(f"{presence_key}:{self.user_id}")

    async def get_active_users(self):
        """Get list of active users for this document."""
        presence_key = f"presence:document:{self.document_id}"
        active_users = []
        
        # Get all cache keys for this document
        pattern = f"{presence_key}:*"
        # This is a simplified version - in production, you might want to use Redis directly
        # for more efficient pattern matching
        
        # For now, we'll track users in a simpler way using basic cache operations
        # In a full production setup, you'd want to use Redis SCAN or similar
        return active_users

    async def broadcast_presence_update(self, action):
        """Broadcast presence update to all users in the document."""
        active_users = await self.get_active_users()
        
        await self.channel_layer.group_send(
            self.document_group_name,
            {
                'type': 'presence_message',
                'action': action,
                'user_id': self.user_id,
                'username': self.username,
                'active_users': active_users
            }
        )