import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Conversation, Message, CustomUser
from .content_moderation import content_moderator

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get conversation ID from URL
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Get user from scope
        self.user = self.scope["user"]
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
            
        # Check if user has access to this conversation
        has_access = await self.check_conversation_access()
        if not has_access:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Update user presence
        await self.update_user_presence(True)
        
        # Send presence update to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_presence',
                'user_id': str(self.user.id),  # Convert UUID to string
                'username': self.user.username,
                'is_online': True
            }
        )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Update user presence
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.update_user_presence(False)
            
            # Send presence update to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_presence',
                    'user_id': str(self.user.id),  # Convert UUID to string
                    'username': self.user.username,
                    'is_online': False
                }
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'send_message':
                await self.handle_send_message(text_data_json)
            elif action == 'typing':
                await self.handle_typing(text_data_json)
            elif action == 'mark_read':
                await self.handle_mark_read(text_data_json)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")

    async def handle_send_message(self, data):
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        
        if not content:
            return
        
        # 🛡️ CONTENT MODERATION - Check for contact information sharing
        moderation_result = await self.moderate_content(content)
        
        if not moderation_result['allowed']:
            # Message blocked - send error to user
            await self.send(text_data=json.dumps({
                'type': 'moderation_blocked',
                'message': moderation_result['message'],
                'action': moderation_result['action'],
                'severity': moderation_result['severity'],
                'detected_content': moderation_result.get('detected_content', {}),
                'timestamp': timezone.now().isoformat()
            }))
            return
            
        # Save message to database only if it passes moderation
        message = await self.save_message(content, message_type)
        
        if message:
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': str(message.id),  # Convert UUID to string
                        'content': message.content,
                        'message_type': message.message_type,
                        'timestamp': message.timestamp.isoformat(),
                        'sender': {
                            'id': str(message.sender.id),  # Convert UUID to string
                            'username': message.sender.username,
                            'first_name': message.sender.first_name,
                            'last_name': message.sender.last_name,
                        }
                    }
                }
            )

    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        # Send typing indicator to room group (excluding sender)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),  # Convert UUID to string
                'username': self.user.username,
                'first_name': self.user.first_name,
                'is_typing': is_typing,
                'sender_channel': self.channel_name  # Exclude sender
            }
        )

    async def handle_mark_read(self, data):
        # Mark messages as read
        await self.mark_messages_read()
        
        # Notify other participants that messages were read
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'messages_read',
                'user_id': str(self.user.id),  # Convert UUID to string
                'username': self.user.username
            }
        )

    async def chat_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    async def typing_indicator(self, event):
        # Don't send typing indicator to the sender
        if event.get('sender_channel') == self.channel_name:
            return
            
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'first_name': event['first_name'],
            'is_typing': event['is_typing']
        }))

    async def user_presence(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online']
        }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    @database_sync_to_async
    def check_conversation_access(self):
        """Check if user has access to this conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, message_type):
        """Save message to database"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                message_type=message_type,
                timestamp=timezone.now()
            )
            return message
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None

    @database_sync_to_async
    def mark_messages_read(self):
        """Mark all messages in conversation as read for current user"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            Message.objects.filter(
                conversation=conversation,
                is_read=False
            ).exclude(sender=self.user).update(is_read=True)
        except Exception as e:
            logger.error(f"Error marking messages as read: {str(e)}")

    @database_sync_to_async
    def update_user_presence(self, is_online):
        """Update user presence status"""
        try:
            from .models import UserPresence
            presence, created = UserPresence.objects.get_or_create(
                user=self.user,
                defaults={'is_online': is_online, 'last_seen': timezone.now()}
            )
            if not created:
                presence.is_online = is_online
                presence.last_seen = timezone.now()
                presence.save()
        except Exception as e:
            logger.error(f"Error updating user presence: {str(e)}")
    
    @database_sync_to_async
    def moderate_content(self, message_content):
        """
        🛡️ Moderate message content for contact information sharing
        
        Returns:
            Dictionary with moderation result
        """
        try:
            # Use the content moderation service
            result = content_moderator.moderate_message(self.user, message_content)
            
            # Log the moderation action
            if not result['allowed']:
                from .models import ContentModerationLog
                ContentModerationLog.objects.create(
                    user=self.user,
                    action='message_blocked',
                    content_type='message',
                    original_content=message_content,
                    detected_violations=result.get('detected_content', {}),
                    moderator=None  # System action
                )
                
                logger.warning(f"Message blocked for user {self.user.username}: {result['detected_content']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in content moderation: {str(e)}")
            # In case of error, allow the message but log the issue
            return {
                'allowed': True,
                'action': 'error',
                'message': 'Moderation service unavailable'
            }