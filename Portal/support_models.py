# Support System Models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class SupportCategory(models.Model):
    """Categories for support tickets (Payment, Account, Project, General)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='fas fa-question-circle')
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Support Categories"
        ordering = ['sort_order', 'name']
        
    def __str__(self):
        return self.name

class SupportTicket(models.Model):
    """Main support ticket model"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_user', 'Pending User Response'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets', null=True, blank=True)
    guest_email = models.EmailField(null=True, blank=True)  # For non-registered users
    guest_name = models.CharField(max_length=100, null=True, blank=True)
    
    category = models.ForeignKey(SupportCategory, on_delete=models.SET_NULL, null=True)
    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Bot interaction fields
    bot_handled = models.BooleanField(default=False)
    escalated_to_human = models.BooleanField(default=False)
    escalation_reason = models.TextField(null=True, blank=True)
    
    # Tracking fields
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # User satisfaction
    satisfaction_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    satisfaction_feedback = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            # Generate unique ticket ID (e.g., STF-2025-001234)
            current_year = timezone.now().year
            last_ticket = SupportTicket.objects.filter(
                ticket_id__startswith=f'STF-{current_year}-'
            ).order_by('-created_at').first()
            
            if last_ticket:
                last_number = int(last_ticket.ticket_id.split('-')[-1])
                next_number = last_number + 1
            else:
                next_number = 1
                
            self.ticket_id = f'STF-{current_year}-{next_number:06d}'
        
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.ticket_id} - {self.subject}"
    
    @property
    def user_display_name(self):
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        return self.guest_name or 'Anonymous'
    
    @property
    def user_email(self):
        return self.user.email if self.user else self.guest_email

class SupportMessage(models.Model):
    """Individual messages within a support ticket"""
    MESSAGE_TYPE_CHOICES = [
        ('user', 'User Message'),
        ('bot', 'Bot Response'),
        ('human', 'Human Agent'),
        ('system', 'System Message'),
    ]
    
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sender_name = models.CharField(max_length=100, null=True, blank=True)  # For bot/system messages
    
    content = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal notes not visible to user
    
    # Bot response metadata
    bot_confidence = models.FloatField(null=True, blank=True)  # 0.0 to 1.0
    bot_trigger_keywords = models.JSONField(default=list, blank=True)
    suggested_escalation = models.BooleanField(default=False)
    
    # Attachments (for future use)
    attachments = models.JSONField(default=list, blank=True)
    
    # Read status
    read_by_user = models.BooleanField(default=False)
    read_by_agent = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"{self.ticket.ticket_id} - {self.message_type} message"

class BotResponse(models.Model):
    """Pre-defined bot responses for common questions"""
    TRIGGER_TYPE_CHOICES = [
        ('keyword', 'Keyword Match'),
        ('category', 'Category Based'),
        ('pattern', 'Pattern Match'),
        ('fallback', 'Fallback Response'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.ForeignKey(SupportCategory, on_delete=models.CASCADE, related_name='bot_responses')
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES)
    
    # Trigger conditions
    trigger_keywords = models.JSONField(default=list, help_text="Keywords that trigger this response")
    trigger_patterns = models.TextField(null=True, blank=True, help_text="Regex patterns for matching")
    priority = models.IntegerField(default=0, help_text="Higher priority responses are checked first")
    
    # Response content
    response_text = models.TextField()
    response_html = models.TextField(null=True, blank=True)  # Rich formatted response
    
    # Response behavior
    suggest_escalation = models.BooleanField(default=False)
    require_human_followup = models.BooleanField(default=False)
    close_ticket_after = models.BooleanField(default=False)
    
    # Quick actions that can be triggered
    quick_actions = models.JSONField(default=list, blank=True)  # e.g., ["reset_password", "verify_email"]
    
    # Usage statistics
    usage_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)  # Based on user satisfaction
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'name']
        
    def __str__(self):
        return f"{self.name} ({self.category.name})"

class SupportKnowledgeBase(models.Model):
    """FAQ and knowledge base articles"""
    ARTICLE_TYPE_CHOICES = [
        ('faq', 'FAQ'),
        ('guide', 'How-to Guide'),
        ('troubleshooting', 'Troubleshooting'),
        ('policy', 'Policy Document'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    article_type = models.CharField(max_length=20, choices=ARTICLE_TYPE_CHOICES, default='faq')
    category = models.ForeignKey(SupportCategory, on_delete=models.CASCADE, related_name='kb_articles')
    
    summary = models.TextField(help_text="Brief summary for search results")
    content = models.TextField()
    content_html = models.TextField(null=True, blank=True)
    
    # SEO and search
    meta_description = models.CharField(max_length=160, null=True, blank=True)
    search_keywords = models.JSONField(default=list, blank=True)
    
    # Usage tracking
    view_count = models.IntegerField(default=0)
    helpful_votes = models.IntegerField(default=0)
    not_helpful_votes = models.IntegerField(default=0)
    
    # Publishing
    is_published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-featured', 'sort_order', '-created_at']
        
    def __str__(self):
        return self.title
    
    @property
    def helpfulness_ratio(self):
        total_votes = self.helpful_votes + self.not_helpful_votes
        if total_votes == 0:
            return 0
        return (self.helpful_votes / total_votes) * 100

class SupportSession(models.Model):
    """Track user support sessions for analytics"""
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Session data
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Interaction data
    messages_sent = models.IntegerField(default=0)
    bot_responses_received = models.IntegerField(default=0)
    escalated_to_human = models.BooleanField(default=False)
    ticket_created = models.BooleanField(default=False)
    
    # User satisfaction for this session
    satisfaction_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    feedback = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        
    def __str__(self):
        return f"Session {self.session_id} - {self.started_at}"

class SupportAnalytics(models.Model):
    """Daily analytics for support system performance"""
    date = models.DateField(unique=True)
    
    # Ticket metrics
    tickets_created = models.IntegerField(default=0)
    tickets_resolved = models.IntegerField(default=0)
    tickets_escalated = models.IntegerField(default=0)
    
    # Response metrics
    avg_first_response_time = models.FloatField(null=True, blank=True)  # in minutes
    avg_resolution_time = models.FloatField(null=True, blank=True)  # in hours
    
    # Bot metrics
    bot_interactions = models.IntegerField(default=0)
    bot_success_rate = models.FloatField(default=0.0)
    
    # User satisfaction
    avg_satisfaction_rating = models.FloatField(null=True, blank=True)
    total_feedback_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Support Analytics"
        
    def __str__(self):
        return f"Analytics for {self.date}"