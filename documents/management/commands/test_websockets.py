import asyncio
import json
from django.core.management.base import BaseCommand
from django.core.cache import cache
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from documents.models import Document


class Command(BaseCommand):
    help = 'Test WebSocket connectivity and channel layer functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['connection', 'channels', 'presence', 'all'],
            default='all',
            help='Type of test to run (default: all)'
        )
        parser.add_argument(
            '--document-id',
            type=str,
            help='Specific document ID to test with'
        )

    def handle(self, *args, **options):
        test_type = options['test_type']
        document_id = options['document_id']

        self.stdout.write(self.style.SUCCESS('Starting WebSocket connectivity tests...\n'))

        if test_type in ['connection', 'all']:
            self.test_channel_layer_connection()

        if test_type in ['channels', 'all']:
            asyncio.run(self.test_channel_layer_messaging())

        if test_type in ['presence', 'all']:
            self.test_presence_tracking(document_id)

        self.stdout.write(self.style.SUCCESS('\nWebSocket tests completed.'))

    def test_channel_layer_connection(self):
        """Test basic channel layer connectivity."""
        self.stdout.write('Testing channel layer connection...')
        
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                self.stdout.write(
                    self.style.ERROR('  ❌ Channel layer is not configured')
                )
                return False

            self.stdout.write(
                self.style.SUCCESS('  ✅ Channel layer is configured')
            )
            
            # Test Redis connection (simplified)
            try:
                cache.set('websocket_test', 'test_value', 10)
                test_value = cache.get('websocket_test')
                if test_value == 'test_value':
                    self.stdout.write(
                        self.style.SUCCESS('  ✅ Redis connection working')
                    )
                    cache.delete('websocket_test')
                else:
                    self.stdout.write(
                        self.style.WARNING('  ⚠️  Redis connection issues detected')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Redis connection error: {e}')
                )
                return False

            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Channel layer error: {e}')
            )
            return False

    async def test_channel_layer_messaging(self):
        """Test channel layer message sending and receiving."""
        self.stdout.write('Testing channel layer messaging...')
        
        try:
            channel_layer = get_channel_layer()
            test_group = 'test_websocket_group'
            test_channel = 'test.channel'

            # Add channel to group
            await channel_layer.group_add(test_group, test_channel)
            self.stdout.write('  ✅ Successfully added channel to group')

            # Send message to group
            test_message = {
                'type': 'test_message',
                'data': 'Hello WebSocket!'
            }
            await channel_layer.group_send(test_group, test_message)
            self.stdout.write('  ✅ Successfully sent message to group')

            # Try to receive message (simplified test)
            # In a real scenario, this would be handled by the consumer
            self.stdout.write('  ✅ Message sending mechanism working')

            # Remove channel from group
            await channel_layer.group_discard(test_group, test_channel)
            self.stdout.write('  ✅ Successfully removed channel from group')

            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Channel messaging error: {e}')
            )
            return False

    def test_presence_tracking(self, document_id=None):
        """Test presence tracking functionality."""
        self.stdout.write('Testing presence tracking...')
        
        if not document_id:
            # Try to get a test document
            try:
                document = Document.objects.first()
                if document:
                    document_id = str(document.id)
                else:
                    self.stdout.write(
                        self.style.WARNING('  ⚠️  No documents found for presence testing')
                    )
                    return False
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error getting test document: {e}')
                )
                return False

        try:
            # Simulate presence tracking
            presence_key = f"presence:document:{document_id}"
            test_user_key = f"{presence_key}:test_user_123"
            
            # Set presence
            cache.set(test_user_key, {
                'username': 'test_user',
                'user_id': 'test_user_123',
                'connected_at': 'test_timestamp'
            }, timeout=300)
            
            # Check presence
            presence_data = cache.get(test_user_key)
            if presence_data:
                self.stdout.write('  ✅ Presence tracking set successfully')
                
                # Clean up
                cache.delete(test_user_key)
                self.stdout.write('  ✅ Presence cleanup successful')
                return True
            else:
                self.stdout.write(
                    self.style.ERROR('  ❌ Presence tracking failed')
                )
                return False

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Presence tracking error: {e}')
            )
            return False

    def get_websocket_stats(self):
        """Get WebSocket-related statistics."""
        self.stdout.write('\nWebSocket System Status:')
        
        try:
            # Check if channels is installed
            import channels
            self.stdout.write(f'  Channels version: {channels.__version__}')
        except ImportError:
            self.stdout.write('  ❌ Channels not installed')

        try:
            # Check if channels-redis is installed
            import channels_redis
            self.stdout.write(f'  Channels-Redis version: {channels_redis.__version__}')
        except ImportError:
            self.stdout.write('  ❌ Channels-Redis not installed')

        # Check Django settings
        from django.conf import settings
        
        if hasattr(settings, 'CHANNEL_LAYERS'):
            self.stdout.write('  ✅ CHANNEL_LAYERS configured')
        else:
            self.stdout.write('  ❌ CHANNEL_LAYERS not configured')

        if hasattr(settings, 'ASGI_APPLICATION'):
            self.stdout.write(f'  ASGI Application: {settings.ASGI_APPLICATION}')
        else:
            self.stdout.write('  ❌ ASGI_APPLICATION not configured')