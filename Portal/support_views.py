# Support System Views
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import json
import re
from .models import (
    SupportCategory, SupportTicket, SupportMessage, BotResponse, 
    SupportKnowledgeBase, SupportSession
)

class SupportBot:
    """AI Support Bot for handling user queries"""
    
    def __init__(self):
        self.confidence_threshold = 0.7
        
    def analyze_message(self, message_text, category_id=None):
        """Analyze user message and return appropriate bot response"""
        message_lower = message_text.lower().strip()
        
        # Get category if provided
        category = None
        if category_id:
            try:
                category = SupportCategory.objects.get(id=category_id)
            except SupportCategory.DoesNotExist:
                pass
        
        # Find matching bot responses
        bot_responses = self._find_matching_responses(message_lower, category)
        
        if bot_responses:
            best_response = bot_responses[0]
            confidence = self._calculate_confidence(message_lower, best_response)
            
            return {
                'response': best_response.response_text,
                'response_html': best_response.response_html,
                'confidence': confidence,
                'suggest_escalation': best_response.suggest_escalation,
                'require_human_followup': best_response.require_human_followup,
                'bot_response_id': best_response.id,
                'trigger_keywords': best_response.trigger_keywords,
                'category': best_response.category.name if best_response.category else None
            }
        
        # Fallback response
        return self._get_fallback_response(category)
    
    def _find_matching_responses(self, message_lower, category=None):
        """Find bot responses that match the user message"""
        query = Q(is_active=True)
        
        if category:
            query &= Q(category=category)
        
        # Get all active bot responses ordered by priority
        responses = BotResponse.objects.filter(query).order_by('-priority', 'name')
        
        matching_responses = []
        
        for response in responses:
            score = 0
            
            # Check keyword matches
            if response.trigger_keywords:
                for keyword in response.trigger_keywords:
                    if keyword.lower() in message_lower:
                        score += 1
            
            # Check pattern matches
            if response.trigger_patterns:
                try:
                    if re.search(response.trigger_patterns, message_lower, re.IGNORECASE):
                        score += 2  # Pattern matches get higher score
                except re.error:
                    pass  # Invalid regex pattern
            
            if score > 0:
                matching_responses.append((response, score))
        
        # Sort by score (descending) and return responses
        matching_responses.sort(key=lambda x: x[1], reverse=True)
        return [response for response, score in matching_responses]
    
    def _calculate_confidence(self, message_lower, bot_response):
        """Calculate confidence score for a bot response"""
        score = 0
        total_possible = 0
        
        # Keyword matching confidence
        if bot_response.trigger_keywords:
            matched_keywords = 0
            for keyword in bot_response.trigger_keywords:
                total_possible += 1
                if keyword.lower() in message_lower:
                    matched_keywords += 1
            
            if total_possible > 0:
                score += (matched_keywords / total_possible) * 0.8
        
        # Pattern matching confidence
        if bot_response.trigger_patterns:
            try:
                if re.search(bot_response.trigger_patterns, message_lower, re.IGNORECASE):
                    score += 0.9
                total_possible += 1
            except re.error:
                pass
        
        # Normalize score
        if total_possible > 0:
            return min(score / total_possible, 1.0)
        
        return 0.5  # Default confidence
    
    def _get_fallback_response(self, category=None):
        """Get fallback response when no specific match is found"""
        fallback_text = """I understand your concern. For the best assistance with your specific issue, I recommend:

1. Checking our FAQ section for common solutions
2. Contacting our human support team at <strong>info@swifttalentforge.com</strong>

Our support team is available 24/7 and will respond within 2-4 hours. Please include as much detail as possible about your issue."""
        
        if category:
            if category.name.lower() == 'payment':
                fallback_text = """For payment-related issues, please contact our support team at <strong>info@swifttalentforge.com</strong> with:

• Your transaction ID
• Description of the issue
• Screenshots (if applicable)

Our payment specialists will resolve your issue within 24 hours."""
        
        return {
            'response': fallback_text,
            'response_html': fallback_text,
            'confidence': 0.3,
            'suggest_escalation': True,
            'require_human_followup': True,
            'bot_response_id': None,
            'trigger_keywords': [],
            'category': category.name if category else 'General'
        }

# Initialize global bot instance
support_bot = SupportBot()

@csrf_exempt
@require_http_methods(["POST"])
def support_chat_message(request):
    """Handle incoming support chat messages"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        category_id = data.get('category_id')
        session_id = data.get('session_id')
        
        if not message_text:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Get or create support session
        session = None
        if session_id:
            try:
                session = SupportSession.objects.get(session_id=session_id)
            except SupportSession.DoesNotExist:
                session = None
        
        if not session:
            # Create new session
            session = SupportSession.objects.create(
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        
        # Update session message count
        session.messages_sent += 1
        session.save()
        
        # Get bot response
        bot_result = support_bot.analyze_message(message_text, category_id)
        
        # Update session with bot response
        session.bot_responses_received += 1
        if bot_result['suggest_escalation']:
            session.escalated_to_human = True
        session.save()
        
        response_data = {
            'bot_response': bot_result['response'],
            'bot_response_html': bot_result.get('response_html'),
            'confidence': bot_result['confidence'],
            'suggest_escalation': bot_result['suggest_escalation'],
            'require_human_followup': bot_result['require_human_followup'],
            'category': bot_result['category'],
            'session_id': str(session.session_id),
            'timestamp': timezone.now().isoformat()
        }
        
        # If high confidence and requires escalation, suggest creating a ticket
        if bot_result['confidence'] > 0.7 and bot_result['suggest_escalation']:
            response_data['suggest_ticket_creation'] = True
            response_data['escalation_message'] = """For complex issues like this, I recommend creating a support ticket so our human agents can provide personalized assistance. Would you like me to help you create a ticket?"""
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def support_create_ticket(request):
    """Create a support ticket from chat session"""
    try:
        data = json.loads(request.body)
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        category_id = data.get('category_id')
        session_id = data.get('session_id')
        
        if not subject or not message:
            return JsonResponse({'error': 'Subject and message are required'}, status=400)
        
        # Get category
        category = None
        if category_id:
            try:
                category = SupportCategory.objects.get(id=category_id)
            except SupportCategory.DoesNotExist:
                pass
        
        # Create ticket
        ticket = SupportTicket.objects.create(
            user=request.user if request.user.is_authenticated else None,
            guest_email=data.get('email') if not request.user.is_authenticated else None,
            guest_name=data.get('name') if not request.user.is_authenticated else None,
            category=category,
            subject=subject,
            priority='medium'
        )
        
        # Create initial message
        SupportMessage.objects.create(
            ticket=ticket,
            message_type='user',
            sender=request.user if request.user.is_authenticated else None,
            content=message
        )
        
        # Update session
        if session_id:
            try:
                session = SupportSession.objects.get(session_id=session_id)
                session.ticket_created = True
                session.save()
            except SupportSession.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'ticket_id': ticket.ticket_id,
            'message': f'Ticket {ticket.ticket_id} created successfully. Our team will respond within 2-4 hours.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def support_categories(request):
    """Get available support categories"""
    categories = SupportCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    category_data = [
        {
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'description': cat.description,
            'icon': cat.icon
        }
        for cat in categories
    ]
    
    return JsonResponse({'categories': category_data})

def support_knowledge_base(request):
    """Get knowledge base articles"""
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    
    articles = SupportKnowledgeBase.objects.filter(is_published=True)
    
    if category_slug:
        articles = articles.filter(category__slug=category_slug)
    
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(search_keywords__contains=[search_query])
        )
    
    articles = articles.order_by('-featured', 'sort_order', '-created_at')[:20]
    
    article_data = [
        {
            'id': article.id,
            'title': article.title,
            'slug': article.slug,
            'summary': article.summary,
            'article_type': article.article_type,
            'category': article.category.name,
            'view_count': article.view_count,
            'helpfulness_ratio': article.helpfulness_ratio
        }
        for article in articles
    ]
    
    return JsonResponse({'articles': article_data})

@login_required
def support_my_tickets(request):
    """Get user's support tickets"""
    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
    
    ticket_data = [
        {
            'ticket_id': ticket.ticket_id,
            'subject': ticket.subject,
            'status': ticket.status,
            'priority': ticket.priority,
            'category': ticket.category.name if ticket.category else 'General',
            'created_at': ticket.created_at.isoformat(),
            'last_update': ticket.updated_at.isoformat(),
            'message_count': ticket.messages.count()
        }
        for ticket in tickets
    ]
    
    return JsonResponse({'tickets': ticket_data})

@csrf_exempt
@require_http_methods(["POST"])
def support_feedback(request):
    """Handle support feedback/satisfaction ratings"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        rating = data.get('rating')  # 1-5
        feedback = data.get('feedback', '').strip()
        
        if not session_id or not rating:
            return JsonResponse({'error': 'Session ID and rating are required'}, status=400)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return JsonResponse({'error': 'Rating must be between 1 and 5'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Rating must be a number'}, status=400)
        
        # Update session with feedback
        try:
            session = SupportSession.objects.get(session_id=session_id)
            session.satisfaction_rating = rating
            session.feedback = feedback
            session.ended_at = timezone.now()
            
            if session.started_at:
                duration = session.ended_at - session.started_at
                session.duration_seconds = int(duration.total_seconds())
            
            session.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for your feedback!'
            })
            
        except SupportSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)