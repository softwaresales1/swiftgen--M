from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template.loader import render_to_string
import json
import uuid
import os
import mimetypes
from datetime import timedelta

from .models import (
    Conversation, Message, MessageFile, UserPresence, 
    MessageNotification, UserMessageSettings, CustomUser, Project, Task
)

# ===== MAIN MESSAGING PAGES =====

@login_required
def messages_dashboard(request):
    """Main messages dashboard showing all conversations"""
    try:
        # Get user's conversations with additional data
        conversations = Conversation.objects.filter(
            participants=request.user
        ).select_related().prefetch_related('participants', 'messages')
        
        # Prepare conversations with other participant info
        conversation_data = []
        for conv in conversations:
            other_participant = conv.get_other_participant(request.user)
            if other_participant:
                last_message = conv.get_last_message()
                unread_count = conv.get_unread_count(request.user)
                
                conversation_data.append({
                    'conversation': conv,
                    'other_participant': other_participant,
                    'last_message': last_message,
                    'unread_count': unread_count,
                })
        
        # Sort by last message time
        conversation_data.sort(key=lambda x: x['conversation'].updated_at, reverse=True)
        
        # Paginate conversations
        paginator = Paginator(conversation_data, 20)
        page_number = request.GET.get('page')
        conversations_page = paginator.get_page(page_number)
        
        # Get total unread count
        total_unread = sum(item['unread_count'] for item in conversation_data)
        
        # Update user presence
        update_user_presence(request.user)
        
        context = {
            'conversations': conversations_page,
            'total_unread': total_unread,
            'total_conversations': len(conversation_data),
            'user': request.user,
        }
        
        return render(request, 'messages/dashboard.html', context)
        
    except Exception as e:
        # Fallback for development
        context = {
            'conversations': [],
            'total_unread': 0,
            'total_conversations': 0,
            'user': request.user,
            'error_message': f"Messaging system loading... {str(e)}"
        }
        return render(request, 'messages/dashboard.html', context)

@login_required
def chat_interface(request, conversation_id):
    """Chat interface for a specific conversation"""
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            participants=request.user
        )
        
        # Get other participant
        other_participant = conversation.get_other_participant(request.user)
        
        # Mark messages as read
        Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=request.user).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Get messages (paginated)
        messages = Message.objects.filter(
            conversation=conversation
        ).select_related('sender').prefetch_related('files').order_by('timestamp')
        
        # Update user presence
        update_user_presence(request.user)
        
        # Get user's message settings
        try:
            message_settings = UserMessageSettings.objects.get(user=request.user)
        except UserMessageSettings.DoesNotExist:
            # Create default settings
            message_settings = UserMessageSettings.objects.create(user=request.user)
        
        context = {
            'conversation': conversation,
            'other_participant': other_participant,
            'messages': messages,
            'user': request.user,
            'message_settings': message_settings,
            'project': conversation.project if conversation.project else None,
        }
        
        return render(request, 'messages/chat.html', context)
        
    except Exception as e:
        return redirect('Portal:messages')

@login_required
def start_conversation(request, user_id):
    """Start a new conversation with a specific user"""
    try:
        other_user = get_object_or_404(User, id=user_id)
        
        if other_user == request.user:
            return redirect('Portal:messages')
        
        # Check if conversation already exists
        existing_conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).first()
        
        if existing_conversation:
            return redirect('Portal:chat_interface', conversation_id=existing_conversation.id)
        
        # Create new conversation
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
        
        # Send initial notification
        MessageNotification.objects.create(
            recipient=other_user,
            sender=request.user,
            conversation=conversation,
            notification_type='conversation_started'
        )
        
        return redirect('Portal:chat_interface', conversation_id=conversation.id)
        
    except Exception as e:
        return redirect('Portal:messages')

@login_required
def start_project_conversation(request, project_id):
    """Start a conversation related to a specific project"""
    try:
        project = get_object_or_404(Project, id=project_id)
        
        # Determine who to chat with
        if hasattr(request.user, 'customuser') and request.user.customuser == project.leader:
            # Client wants to chat with freelancer
            # Get the hired freelancer
            hired_bid = project.bids.filter(status='accepted').first()
            if not hired_bid:
                return JsonResponse({'error': 'No freelancer hired for this project'}, status=400)
            other_user = hired_bid.freelancer.user
        else:
            # Freelancer wants to chat with client
            other_user = project.leader.user
        
        # Check if conversation already exists for this project
        existing_conversation = Conversation.objects.filter(
            participants=request.user,
            project=project
        ).filter(
            participants=other_user
        ).first()
        
        if existing_conversation:
            return redirect('Portal:chat_interface', conversation_id=existing_conversation.id)
        
        # Create new project-related conversation
        conversation = Conversation.objects.create(project=project)
        conversation.participants.add(request.user, other_user)
        
        # Send initial notification
        MessageNotification.objects.create(
            recipient=other_user,
            sender=request.user,
            conversation=conversation,
            notification_type='conversation_started'
        )
        
        return redirect('Portal:chat_interface', conversation_id=conversation.id)
        
    except Exception as e:
        return redirect('Portal:messages')

# ===== AJAX API ENDPOINTS =====

@login_required
@require_POST
@csrf_exempt
def send_message(request):
    """Send a new message via AJAX with content moderation"""
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        
        if not conversation_id or not content:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            participants=request.user
        )
        
        # 🛡️ CONTENT MODERATION - Check for contact information sharing
        from .content_moderation import content_moderator
        from .models import ContentModerationLog
        
        moderation_result = content_moderator.moderate_message(request.user, content)
        
        if not moderation_result['allowed']:
            # Message blocked - log the action and return error
            ContentModerationLog.objects.create(
                user=request.user,
                action='message_blocked',
                content_type='message',
                original_content=content,
                detected_violations=moderation_result.get('detected_content', {}),
                moderator=None  # System action
            )
            
            return JsonResponse({
                'error': 'message_blocked',
                'moderation_message': moderation_result['message'],
                'action': moderation_result['action'],
                'severity': moderation_result['severity'],
                'detected_content': moderation_result.get('detected_content', {}),
                'blocked': True
            }, status=403)
        
        # Create message only if it passes moderation
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=message_type
        )
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Create notification for other participants
        other_participants = conversation.participants.exclude(id=request.user.id)
        for participant in other_participants:
            MessageNotification.objects.create(
                recipient=participant,
                sender=request.user,
                message=message,
                conversation=conversation,
                notification_type='new_message'
            )
        
        # Update user presence
        update_user_presence(request.user)
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': str(message.id),
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'sender': message.sender.username,
                'message_type': message.message_type,
                'sender_name': f"{message.sender.first_name} {message.sender.last_name}".strip() or message.sender.username
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def load_messages(request, conversation_id):
    """Load messages for a conversation via AJAX"""
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            participants=request.user
        )
        
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))
        
        # Get messages
        messages = Message.objects.filter(
            conversation=conversation
        ).select_related('sender').prefetch_related('files').order_by('-timestamp')
        
        # Paginate
        paginator = Paginator(messages, per_page)
        messages_page = paginator.get_page(page)
        
        # Format messages for JSON
        messages_data = []
        for message in messages_page:
            message_data = {
                'id': str(message.id),
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'sender': {
                    'id': message.sender.id,
                    'username': message.sender.username,
                    'first_name': message.sender.first_name,
                    'last_name': message.sender.last_name,
                    'full_name': f"{message.sender.first_name} {message.sender.last_name}".strip() or message.sender.username
                },
                'message_type': message.message_type,
                'is_read': message.is_read,
                'files': [
                    {
                        'id': str(file.id),
                        'filename': file.filename,
                        'file_size': file.get_file_size_display(),
                        'file_type': file.file_type,
                        'download_url': f'/messages/download/{file.id}/'
                    } for file in message.files.all()
                ]
            }
            messages_data.append(message_data)
        
        return JsonResponse({
            'messages': messages_data,
            'has_next': messages_page.has_next(),
            'has_previous': messages_page.has_previous(),
            'total_pages': paginator.num_pages,
            'current_page': page
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def mark_messages_read(request, conversation_id):
    """Mark all messages in a conversation as read"""
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            participants=request.user
        )
        
        # Mark unread messages as read
        updated_count = Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=request.user).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'marked_read': updated_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def message_stats(request):
    """Get message statistics for the current user"""
    try:
        unread_count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        
        total_conversations = Conversation.objects.filter(
            participants=request.user
        ).count()
        
        return JsonResponse({
            'unread_count': unread_count,
            'total_conversations': total_conversations
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def check_new_messages(request):
    """Check for new messages since last check"""
    try:
        last_check = request.GET.get('last_check')
        
        if last_check:
            try:
                last_check_time = timezone.datetime.fromisoformat(last_check.replace('Z', '+00:00'))
            except:
                last_check_time = timezone.now() - timedelta(minutes=5)
        else:
            last_check_time = timezone.now() - timedelta(minutes=5)
        
        # Get new messages
        new_messages = Message.objects.filter(
            conversation__participants=request.user,
            timestamp__gt=last_check_time,
            is_read=False
        ).exclude(sender=request.user).select_related('sender').order_by('-timestamp')
        
        has_new_messages = new_messages.exists()
        latest_message = None
        
        if has_new_messages:
            latest = new_messages.first()
            latest_message = {
                'sender': f"{latest.sender.first_name} {latest.sender.last_name}".strip() or latest.sender.username,
                'content': latest.content[:50] + '...' if len(latest.content) > 50 else latest.content,
                'timestamp': latest.timestamp.isoformat()
            }
        
        return JsonResponse({
            'has_new_messages': has_new_messages,
            'new_message_count': new_messages.count(),
            'latest_message': latest_message,
            'check_time': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
@csrf_exempt
def update_typing_status(request):
    """Update typing status for real-time indicators"""
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        is_typing = data.get('is_typing', False)
        
        # In a real implementation, this would use WebSockets or Server-Sent Events
        # For now, we'll just return success
        # You could store typing status in cache (Redis) with expiration
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ===== FILE SHARING =====

@login_required
@require_POST
def upload_message_file(request):
    """Upload a file to be shared in a message"""
    try:
        conversation_id = request.POST.get('conversation_id')
        file = request.FILES.get('file')
        
        if not conversation_id or not file:
            return JsonResponse({'error': 'Missing conversation_id or file'}, status=400)
        
        # Check file size (limit to 50MB)
        if file.size > 50 * 1024 * 1024:  # 50MB limit
            return JsonResponse({'error': 'File too large. Maximum size is 50MB.'}, status=400)
        
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            participants=request.user
        )
        
        # Create message with file
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=f"📎 Shared file: {file.name}",
            message_type='file'
        )
        
        # Create file attachment
        message_file = MessageFile.objects.create(
            message=message,
            file=file,
            filename=file.name,
            file_size=file.size,
            file_type=file.content_type or 'application/octet-stream'
        )
        
        # Update conversation
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Create notifications
        other_participants = conversation.participants.exclude(id=request.user.id)
        for participant in other_participants:
            MessageNotification.objects.create(
                recipient=participant,
                sender=request.user,
                message=message,
                conversation=conversation,
                notification_type='file_shared'
            )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': str(message.id),
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'sender': message.sender.username,
                'message_type': message.message_type,
                'file': {
                    'id': str(message_file.id),
                    'filename': message_file.filename,
                    'file_size': message_file.get_file_size_display(),
                    'file_type': message_file.file_type,
                    'download_url': f'/messages/download/{message_file.id}/'
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def download_message_file(request, file_id):
    """Download a message file"""
    try:
        message_file = get_object_or_404(MessageFile, id=file_id)
        
        # Check if user has access to this file
        if not message_file.message.conversation.participants.filter(id=request.user.id).exists():
            raise Http404("File not found")
        
        try:
            file_path = message_file.file.path
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    response = HttpResponse(
                        file.read(), 
                        content_type=message_file.file_type or 'application/octet-stream'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{message_file.filename}"'
                    return response
            else:
                raise Http404("File not found on disk")
        except Exception as e:
            raise Http404("File not accessible")
            
    except Exception as e:
        raise Http404("File not found")

# ===== USER PRESENCE =====

def update_user_presence(user):
    """Update user's online presence"""
    try:
        presence, created = UserPresence.objects.get_or_create(user=user)
        presence.is_online = True
        presence.last_activity = timezone.now()
        presence.last_seen = timezone.now()
        presence.save()
    except Exception as e:
        pass

@login_required
@require_POST
def update_presence(request):
    """Update user presence via AJAX"""
    try:
        update_user_presence(request.user)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_user_status(request, user_id):
    """Get online status of a specific user"""
    try:
        user = User.objects.get(id=user_id)
        presence = UserPresence.objects.filter(user=user).first()
        
        if presence:
            return JsonResponse({
                'is_online': presence.is_online,
                'last_seen': presence.last_seen.isoformat() if presence.last_seen else None,
                'status_display': presence.get_status_display()
            })
        else:
            return JsonResponse({
                'is_online': False,
                'last_seen': None,
                'status_display': 'Never seen'
            })
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ===== CONVERSATION MANAGEMENT =====

@login_required
def list_conversations(request):
    """API endpoint to list user's conversations"""
    try:
        conversations = Conversation.objects.filter(
            participants=request.user
        ).annotate(
            last_message_time=Max('messages__timestamp'),
            unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
        ).order_by('-last_message_time')
        
        conversations_data = []
        for conv in conversations:
            other_participant = conv.get_other_participant(request.user)
            last_message = conv.get_last_message()
            
            if other_participant:
                conversations_data.append({
                    'id': str(conv.id),
                    'other_participant': {
                        'id': other_participant.id,
                        'username': other_participant.username,
                        'first_name': other_participant.first_name,
                        'last_name': other_participant.last_name,
                        'full_name': f"{other_participant.first_name} {other_participant.last_name}".strip() or other_participant.username
                    },
                    'last_message': {
                        'content': last_message.content[:50] + '...' if last_message and len(last_message.content) > 50 else (last_message.content if last_message else ''),
                        'timestamp': last_message.timestamp.isoformat() if last_message else None,
                        'sender': last_message.sender.username if last_message else None
                    } if last_message else None,
                    'unread_count': conv.get_unread_count(request.user),
                    'updated_at': conv.updated_at.isoformat()
                })
        
        return JsonResponse({'conversations': conversations_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def search_conversations(request):
    """Search conversations and users"""
    try:
        query = request.GET.get('q', '').strip()
        
        if not query:
            return JsonResponse({'results': []})
        
        # Search existing conversations
        conversations = Conversation.objects.filter(
            participants=request.user,
            participants__username__icontains=query
        ).distinct()
        
        # Search users for new conversations
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)[:10]
        
        results = []
        
        # Add existing conversations
        for conv in conversations:
            other_participant = conv.get_other_participant(request.user)
            if other_participant:
                results.append({
                    'type': 'conversation',
                    'id': str(conv.id),
                    'title': f"{other_participant.first_name} {other_participant.last_name}".strip() or other_participant.username,
                    'subtitle': 'Existing conversation',
                    'url': f'/messages/chat/{conv.id}/'
                })
        
        # Add users for new conversations
        for user in users:
            results.append({
                'type': 'user',
                'id': user.id,
                'title': f"{user.first_name} {user.last_name}".strip() or user.username,
                'subtitle': 'Start new conversation',
                'url': f'/messages/start/{user.id}/'
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def archive_conversation(request, conversation_id):
    """Archive a conversation (hide from main list)"""
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            participants=request.user
        )
        
        conversation.is_archived = True
        conversation.save()
        
        return JsonResponse({'success': True, 'message': 'Conversation archived'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def delete_conversation(request, conversation_id):
    """Delete a conversation"""
    try:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id, 
            participants=request.user
        )
        
        # In a real app, you might want to just remove the user from participants
        # rather than deleting the entire conversation
        conversation.participants.remove(request.user)
        
        if conversation.participants.count() == 0:
            conversation.delete()
        
        return JsonResponse({'success': True, 'message': 'Conversation deleted'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ===== SETTINGS & PREFERENCES =====

@login_required
def message_settings(request):
    """Message settings page"""
    try:
        # Get or create user message settings
        message_settings, created = UserMessageSettings.objects.get_or_create(
            user=request.user
        )
        
        context = {
            'message_settings': message_settings,
            'user': request.user,
        }
        
        return render(request, 'messages/settings.html', context)
        
    except Exception as e:
        context = {
            'error_message': str(e),
            'user': request.user,
        }
        return render(request, 'messages/settings.html', context)

@login_required
@require_POST
@csrf_exempt
def update_message_settings(request):
    """Update message settings"""
    try:
        data = json.loads(request.body)
        
        # Get or create user message settings
        message_settings, created = UserMessageSettings.objects.get_or_create(
            user=request.user
        )
        
        # Update settings based on data
        for field, value in data.items():
            if hasattr(message_settings, field):
                setattr(message_settings, field, value)
        
        message_settings.save()
        
        return JsonResponse({'success': True, 'message': 'Settings updated successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def toggle_email_notifications(request):
    """Toggle email notifications for messages"""
    try:
        message_settings, created = UserMessageSettings.objects.get_or_create(
            user=request.user
        )
        
        message_settings.email_notifications = not message_settings.email_notifications
        message_settings.save()
        
        return JsonResponse({
            'success': True, 
            'email_notifications': message_settings.email_notifications
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = MessageNotification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except MessageNotification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ===== MOBILE API ENDPOINTS =====

@login_required
def mobile_message_sync(request):
    """Sync messages for mobile app"""
    try:
        last_sync = request.GET.get('last_sync')
        
        if last_sync:
            try:
                last_sync_time = timezone.datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            except:
                last_sync_time = timezone.now() - timedelta(days=7)
        else:
            last_sync_time = timezone.now() - timedelta(days=7)
        
        # Get updated conversations
        conversations = Conversation.objects.filter(
            participants=request.user,
            updated_at__gt=last_sync_time
        )
        
        # Get updated messages
        messages = Message.objects.filter(
            conversation__participants=request.user,
            timestamp__gt=last_sync_time
        ).select_related('sender')
        
        sync_data = {
            'conversations': [
                {
                    'id': str(conv.id),
                    'updated_at': conv.updated_at.isoformat(),
                    'participants': [p.id for p in conv.participants.all()]
                } for conv in conversations
            ],
            'messages': [
                {
                    'id': str(msg.id),
                    'conversation_id': str(msg.conversation.id),
                    'sender_id': msg.sender.id,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'is_read': msg.is_read,
                    'message_type': msg.message_type
                } for msg in messages
            ],
            'sync_time': timezone.now().isoformat()
        }
        
        return JsonResponse(sync_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def mobile_conversations_list(request):
    """Get conversations list for mobile app"""
    try:
        conversations = Conversation.objects.filter(
            participants=request.user
        ).annotate(
            last_message_time=Max('messages__timestamp')
        ).order_by('-last_message_time')
        
        conversations_data = []
        for conv in conversations:
            other_participant = conv.get_other_participant(request.user)
            last_message = conv.get_last_message()
            
            if other_participant:
                conversations_data.append({
                    'id': str(conv.id),
                    'other_participant': {
                        'id': other_participant.id,
                        'username': other_participant.username,
                        'full_name': f"{other_participant.first_name} {other_participant.last_name}".strip() or other_participant.username
                    },
                    'last_message': {
                        'content': last_message.content if last_message else '',
                        'timestamp': last_message.timestamp.isoformat() if last_message else None,
                        'is_from_me': last_message.sender == request.user if last_message else False
                    } if last_message else None,
                    'unread_count': conv.get_unread_count(request.user)
                })
        
        return JsonResponse({'conversations': conversations_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)