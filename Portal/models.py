from django.apps import AppConfig
from django.db import models
from django.contrib.auth.models import User
import stripe
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from django.core.files.storage import default_storage
import uuid
import os

class PortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Portal'

class CustomUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    phone_number = models.CharField(max_length=11, default=None)
    bio = models.TextField(max_length=500, default=None)
    image = models.ImageField(upload_to='profiles/')
    batchYear = models.CharField(max_length=4, choices=[
        ("None", "None"), ("UG-1", "UG-1"), ("UG-2", "UG-2"), ("UG-3", "UG-3"), 
        ("UG-4", "UG-4"), ("MS", "MS"), ("Ph.D", "Ph.D")
    ], default='None')
    gender = models.CharField(max_length=10, choices=[
        ("Male", "Male"), ("Female", "Female")
    ], default="Male", blank=False)

    def __str__(self):
        return self.user.username

    def delete(self, *args, **kwargs):
        if self.image and self.image.path:
            try:
                os.remove(self.image.path)
            except:
                pass
        super(CustomUser, self).delete(*args, **kwargs)

class Skill(models.Model):
    skill_name = models.CharField(max_length=50, unique=True, primary_key=True)

    def __str__(self):
        return self.skill_name

class UsersSkill(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    level_of_proficiency = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.user.user.username}/{self.skill.skill_name}/{self.level_of_proficiency}"

class CommunicationLanguage(models.Model):
    language_name = models.CharField(max_length=30, unique=True, primary_key=True)

    def __str__(self):
        return self.language_name

class UsersCommunicationLanguage(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    language = models.ForeignKey(CommunicationLanguage, on_delete=models.CASCADE)
    level_of_fluency = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.user.user.username}/{self.language.language_name}/{self.level_of_fluency}"

# Updated Project model with Upwork-style features
class Project(models.Model):
    STATUS_CHOICES = [
        ('posted', 'Posted'),
        ('bidding', 'Receiving Bids'),
        ('hired', 'Freelancer Hired'),
        ('in_progress', 'Work in Progress'),
        ('submitted', 'Work Submitted'),
        ('revision', 'Revision Requested'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    project_name = models.CharField(max_length=100)  # Removed unique=True
    description = models.CharField(max_length=300, default=None)
    postedOn = models.DateTimeField(auto_now_add=True)
    leader = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    isCompleted = models.BooleanField(default=False)
    deadline = models.DateField()
    task_count = models.IntegerField(default=0)
    
    # NEW FIELDS FOR UPWORK-STYLE FEATURES
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    project_type = models.CharField(max_length=20, choices=[
        ("Fixed", "Fixed Price"), ("Hourly", "Hourly Rate")
    ], default="Fixed")
    experience_level = models.CharField(max_length=20, choices=[
        ("Entry", "Entry Level"), ("Intermediate", "Intermediate"), ("Expert", "Expert")
    ], default="Intermediate")
    project_duration = models.CharField(max_length=30, choices=[
        ("Less than 1 month", "Less than 1 month"),
        ("1 to 3 months", "1 to 3 months"), 
        ("3 to 6 months", "3 to 6 months"),
        ("More than 6 months", "More than 6 months")
    ], default="1 to 3 months")
    proposals_count = models.IntegerField(default=0)
    
    # ADD PROJECT STATUS TRACKING
    project_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='posted')
    
    def __str__(self):
        return self.project_name

# TASK MODEL
class Task(models.Model):
    task_name = models.CharField(max_length=100)
    task_description = models.CharField(max_length=300, default=None)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    deadline = models.DateField()
    addedOn = models.DateTimeField(auto_now_add=True)
    isCompleted = models.BooleanField(default=False)
    credits = models.CharField(max_length=20, choices=[
        ("Academic", "Academic"), ("Paid", "Paid"), ("Other", "Other")
    ], default="Academic")
    amount = models.IntegerField(default=0)
    mention = models.CharField(max_length=100, default=None, blank=True)
    task_link = models.URLField(max_length=200, default=None, blank=True, null=True)
    rating = models.DecimalField(default=0, max_digits=2, decimal_places=1, blank=True, null=True)

    def __str__(self):
        return self.task_name

# UPDATED PROJECT BID MODEL WITH STATUS FIELD
class ProjectBid(models.Model):
    # Status choices for bid tracking
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bids')
    freelancer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time = models.IntegerField(help_text="Delivery time in days")
    cover_letter = models.TextField(max_length=1000)
    submitted_on = models.DateTimeField(auto_now_add=True)
    
    # ADDED STATUS FIELD - THIS WAS MISSING!
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Keep backward compatibility
    is_selected = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('project', 'freelancer')
    
    def save(self, *args, **kwargs):
        # Keep is_selected in sync with status for backward compatibility
        if self.status == 'accepted':
            self.is_selected = True
        else:
            self.is_selected = False
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.freelancer.user.username} - {self.project.project_name} ({self.status})"

# PROJECT SKILLS REQUIRED MODEL
class ProjectSkillsRequired(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.project.project_name} - {self.skill.skill_name}"

class TaskSkillsRequired(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    proficiency_level_required = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.task.task_name}[id={self.task.id}]"

class TaskLanguagesRequired(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    language = models.ForeignKey(CommunicationLanguage, on_delete=models.CASCADE)
    fluency_level_required = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.task.task_name}[id={self.task.id}]"

class Applicant(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    time_of_application = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username}[id={self.user.id}]"

class Contributor(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    isCreditVerified = models.BooleanField(default=False)
    time_of_selection = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username}[id={self.user.id}]"

class UserRating(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, primary_key=True)
    emp = models.ForeignKey(CustomUser, related_name='rating_by', on_delete=models.CASCADE, null=True, blank=True)
    fre = models.ForeignKey(CustomUser, related_name='rating_to', on_delete=models.CASCADE, null=True, blank=True)
    f_rating = models.DecimalField(default=0, max_digits=2, decimal_places=1)
    e_rating = models.DecimalField(default=0, max_digits=2, decimal_places=1)

    def __str__(self):
        return f"{self.task.id}--{self.fre.user.username if self.fre else 'None'}--{self.emp.user.username if self.emp else 'None'}"

class Notification(models.Model):
    _from = models.ForeignKey(CustomUser, related_name="msgfrom", on_delete=models.CASCADE)
    _to = models.ForeignKey(CustomUser, related_name='msgto', on_delete=models.CASCADE)
    message = models.CharField(default=None, max_length=300)
    has_read = models.BooleanField(default=False)
    sending_time = models.DateTimeField(auto_now_add=True)
    recieving_time = models.DateTimeField(default=None, blank=True, null=True)

    def __str__(self):
        return f"From: {self._from.user.username}, To: {self._to.user.username}"

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('disputed', 'Disputed'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('project_payment', 'Project Payment'),
        ('milestone_payment', 'Milestone Payment'),
        ('tip', 'Tip'),
        ('subscription', 'Subscription'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
        ('alipay', 'Alipay'),
    ]

    # Payment Details
    payment_id = models.CharField(max_length=100, unique=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True, null=True)
    stripe_checkout_session_id = models.CharField(max_length=200, blank=True, null=True)
    
    # ADDED PAYPAL FIELDS
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='stripe')
    paypal_order_id = models.CharField(max_length=200, blank=True, null=True)
    paypal_payer_id = models.CharField(max_length=200, blank=True, null=True)
    paypal_transaction_id = models.CharField(max_length=200, blank=True, null=True)
    
    # Parties
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments_made')
    freelancer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments_received')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='payments')
    
    # Amount Details
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Total client pays
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Our commission
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Stripe fees
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Freelancer receives
    
    # Status and Type
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='project_payment')
    
    # Escrow Management
    escrow_held = models.BooleanField(default=True)  # Money held until work approved
    released_at = models.DateTimeField(null=True, blank=True)  # When money released to freelancer
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata
    description = models.TextField(blank=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY_{self.project.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate platform fee (10% like Upwork)
        if not self.platform_fee:
            self.platform_fee = self.gross_amount * Decimal('0.10')
        
        # Calculate processing fee (Stripe ~3%)
        if not self.processing_fee:
            self.processing_fee = self.gross_amount * Decimal('0.029') + Decimal('0.30')
        
        # Calculate net amount (what freelancer gets)
        if not self.net_amount:
            self.net_amount = self.gross_amount - self.platform_fee - self.processing_fee
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Payment {self.payment_id} - ${self.gross_amount}"

class Milestone(models.Model):
    """For breaking projects into payment milestones like Upwork"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    
    # Status
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    approved_by_client = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Associated payment
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.project.project_name} - {self.title}"

class Dispute(models.Model):
    """Handle payment disputes like Fiverr/Upwork"""
    DISPUTE_STATUS_CHOICES = [
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated to Admin'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    opened_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='open')
    
    admin_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Dispute for {self.payment.payment_id}"

# ===== NEW MODELS FOR FILE MANAGEMENT & WORKSPACE =====

class ProjectFile(models.Model):
    """Files uploaded by client for project requirements"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to='project_files/')
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)  # document, image, video, etc.
    file_size = models.BigIntegerField()  # in bytes
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Access level field
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Available During Bidding'),
            ('private', 'Available After Hiring'),
        ],
        default='private',
        help_text="Choose when freelancers can access this file"
    )
    
    # NEW CATEGORY FIELD - THIS WAS MISSING!
    category = models.CharField(
        max_length=30,
        choices=[
            ('requirement', 'Project Requirement'),
            ('reference', 'Reference Material'),
            ('example', 'Example Work'),
            ('specification', 'Technical Specification'),
            ('other', 'Other'),
        ],
        default='requirement',
        help_text="Categorize this file for better organization"
    )
    
    # NEW PRIORITY FIELD - THIS WAS MISSING!
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='normal',
        help_text="Priority level of this file"
    )
    
    # Access control
    is_requirement = models.BooleanField(default=True)  # True = requirement file, False = reference
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.project.project_name} - {self.original_filename}"
    
    def get_file_size_display(self):
        """Human readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

class WorkSubmission(models.Model):
    """Files and work submitted by freelancer"""
    SUBMISSION_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('revision_requested', 'Revision Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='submissions')
    freelancer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    submission_title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS_CHOICES, default='draft')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Client feedback
    client_feedback = models.TextField(blank=True)
    revision_notes = models.TextField(blank=True)
    
    # Version control
    version_number = models.IntegerField(default=1)
    is_final = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.project_name} - {self.submission_title} (v{self.version_number})"

class SubmissionFile(models.Model):
    """Individual files in a work submission"""
    submission = models.ForeignKey(WorkSubmission, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='submissions/')
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.submission.submission_title} - {self.original_filename}"

class ProjectStatus(models.Model):
    """Track project status updates (like Upwork)"""
    STATUS_CHOICES = [
        ('posted', 'Posted'),
        ('bidding', 'Receiving Bids'),
        ('hired', 'Freelancer Hired'),
        ('in_progress', 'Work in Progress'),
        ('submitted', 'Work Submitted'),
        ('revision', 'Revision Requested'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.project_name} - {self.status}"

class FreelancerAccess(models.Model):
    """Control what freelancers can access after being hired"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    freelancer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    bid = models.ForeignKey(ProjectBid, on_delete=models.CASCADE)
    
    # Access permissions
    can_download_files = models.BooleanField(default=False)
    can_submit_work = models.BooleanField(default=False)
    can_communicate = models.BooleanField(default=False)
    
    # Access granted when payment is completed
    access_granted_at = models.DateTimeField(null=True, blank=True)
    granted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='access_granted')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('project', 'freelancer')
    
    def __str__(self):
        return f"{self.freelancer.user.username} - {self.project.project_name}"

# ===== MESSAGING SYSTEM MODELS =====

class Conversation(models.Model):
    """Model for message conversations between users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(User, related_name='conversations')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participants = list(self.participants.all())
        if len(participants) == 2:
            return f"Conversation between {participants[0].username} and {participants[1].username}"
        return f"Conversation ({self.id})"
    
    def get_other_participant(self, user):
        """Get the other participant in a 2-person conversation"""
        participants = self.participants.exclude(id=user.id)
        return participants.first() if participants.exists() else None
    
    def get_last_message(self):
        """Get the last message in this conversation"""
        return self.messages.order_by('-timestamp').first()
    
    def get_unread_count(self, user):
        """Get count of unread messages for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()

class Message(models.Model):
    """Model for individual messages"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('image', 'Image'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"
    
    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class MessageFile(models.Model):
    """Model for file attachments in messages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='message_files/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"File: {self.filename}"
    
    def get_file_size_display(self):
        """Get human readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted"""
        if self.file:
            if default_storage.exists(self.file.name):
                default_storage.delete(self.file.name)
        super().delete(*args, **kwargs)

class UserPresence(models.Model):
    """Model to track user online presence"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='presence')
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"
    
    def get_status_display(self):
        """Get human readable status"""
        if self.is_online:
            return "Online"
        
        if not self.last_seen:
            return "Never seen"
        
        now = timezone.now()
        diff = now - self.last_seen
        
        if diff.days > 0:
            return f"Last seen {diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"Last seen {hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"Last seen {minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Last seen moments ago"

class MessageNotification(models.Model):
    """Model for message notifications"""
    NOTIFICATION_TYPES = [
        ('new_message', 'New Message'),
        ('file_shared', 'File Shared'),
        ('conversation_started', 'Conversation Started'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.get_notification_type_display()}"

class UserMessageSettings(models.Model):
    """Model for user message preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='message_settings')
    email_notifications = models.BooleanField(default=True)
    browser_notifications = models.BooleanField(default=True)
    sound_notifications = models.BooleanField(default=False)
    notification_frequency = models.CharField(
        max_length=20,
        choices=[
            ('realtime', 'Real-time'),
            ('5min', 'Every 5 minutes'),
            ('15min', 'Every 15 minutes'),
            ('30min', 'Every 30 minutes'),
            ('1hour', 'Every hour'),
        ],
        default='realtime'
    )
    read_receipts = models.BooleanField(default=True)
    online_status = models.BooleanField(default=True)
    typing_indicators = models.BooleanField(default=True)
    message_permissions = models.CharField(
        max_length=20,
        choices=[
            ('everyone', 'Everyone'),
            ('clients', 'Clients Only'),
            ('freelancers', 'Freelancers Only'),
            ('project_members', 'Project Members Only'),
            ('none', 'No One'),
        ],
        default='everyone'
    )
    preview_length = models.IntegerField(default=50)
    auto_scroll = models.BooleanField(default=True)
    show_timestamps = models.BooleanField(default=True)
    theme = models.CharField(
        max_length=20,
        choices=[
            ('default', 'Default'),
            ('dark', 'Dark Mode'),
            ('minimal', 'Minimal'),
            ('compact', 'Compact'),
        ],
        default='default'
    )
    auto_download_images = models.BooleanField(default=True)
    file_size_warning = models.IntegerField(default=10)  # MB
    compress_images = models.BooleanField(default=False)
    dnd_start = models.TimeField(default='22:00')
    dnd_end = models.TimeField(default='08:00')
    message_retention = models.CharField(
        max_length=20,
        choices=[
            ('forever', 'Forever'),
            ('1year', '1 Year'),
            ('6months', '6 Months'),
            ('3months', '3 Months'),
            ('1month', '1 Month'),
        ],
        default='forever'
    )
    
    def __str__(self):
        return f"Message settings for {self.user.username}"


class UserViolation(models.Model):
    """
    Track user violations for content moderation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='violations')
    violation_type = models.CharField(
        max_length=50,
        choices=[
            ('contact_sharing', 'Contact Information Sharing'),
            ('spam', 'Spam'),
            ('harassment', 'Harassment'),
            ('inappropriate_content', 'Inappropriate Content'),
            ('other', 'Other')
        ],
        default='contact_sharing'
    )
    violation_data = models.JSONField(default=dict)  # Store detected content and metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='resolved_violations'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'violation_type', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.violation_type} - {self.created_at.strftime('%Y-%m-%d')}"


class UserSuspension(models.Model):
    """
    Track user account suspensions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='suspensions')
    reason = models.TextField()
    suspended_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='suspended_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    suspension_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='lifted_suspensions'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['suspension_end']),
        ]
    
    def __str__(self):
        status = "Active" if self.is_active else "Lifted"
        return f"{self.user.username} - {status} - {self.created_at.strftime('%Y-%m-%d')}"
    
    def is_expired(self):
        """Check if suspension has expired"""
        return timezone.now() > self.suspension_end


class UserNotification(models.Model):
    """
    User notifications for warnings, suspensions, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=[
            ('info', 'Information'),
            ('warning', 'Warning'),
            ('suspension', 'Suspension'),
            ('violation', 'Violation'),
            ('system', 'System'),
        ],
        default='info'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"{self.user.username} - {self.title} - {status}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class ContentModerationLog(models.Model):
    """
    Log all content moderation actions for audit purposes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderation_logs')
    action = models.CharField(
        max_length=30,
        choices=[
            ('message_blocked', 'Message Blocked'),
            ('warning_sent', 'Warning Sent'),
            ('user_suspended', 'User Suspended'),
            ('account_terminated', 'Account Terminated'),
            ('violation_recorded', 'Violation Recorded'),
        ]
    )
    content_type = models.CharField(max_length=30, default='message')
    original_content = models.TextField(blank=True)  # Original message content
    detected_violations = models.JSONField(default=dict)  # What was detected
    created_at = models.DateTimeField(auto_now_add=True)
    moderator = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='moderation_actions'
    )  # Null for system actions
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# =============================================================================
# SUPPORT SYSTEM MODELS
# =============================================================================

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

# Client Verification Models
class ClientVerification(models.Model):
    """Model to store client verification information"""
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('resubmission_required', 'Resubmission Required'),
    ]
    
    DOCUMENT_TYPE_CHOICES = [
        ('passport', 'Passport'),
        ('drivers_license', 'Driver\'s License'),
        ('national_id', 'National ID Card'),
        ('other', 'Other Government ID'),
    ]
    
    # Basic Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification')
    verification_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=25, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20)
    
    # Address Information
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Document Information
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    document_number = models.CharField(max_length=100)
    document_expiry_date = models.DateField()
    document_front_image = models.ImageField(upload_to='verification/documents/front/')
    document_back_image = models.ImageField(upload_to='verification/documents/back/', blank=True, null=True)
    
    # PayPal Information
    paypal_email = models.EmailField()
    paypal_account_verified = models.BooleanField(default=False)
    
    # Additional Verification Documents
    proof_of_address_image = models.ImageField(upload_to='verification/proof_of_address/')
    selfie_with_document = models.ImageField(upload_to='verification/selfies/')
    
    # Business Information (Optional)
    is_business_account = models.BooleanField(default=False)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_registration_number = models.CharField(max_length=100, blank=True, null=True)
    business_tax_id = models.CharField(max_length=100, blank=True, null=True)
    business_license_image = models.ImageField(upload_to='verification/business/', blank=True, null=True)
    
    # Review Information
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_clients')
    rejection_reason = models.TextField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Client Verification"
        verbose_name_plural = "Client Verifications"
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_verified(self):
        return self.status == 'approved'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def can_receive_payments(self):
        return self.status == 'approved' and self.paypal_account_verified
    
    def approve_verification(self, admin_user, notes=None):
        """Approve the verification"""
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save()
    
    def reject_verification(self, admin_user, reason, notes=None):
        """Reject the verification"""
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        if notes:
            self.admin_notes = notes
        self.save()
    
    def require_resubmission(self, admin_user, reason, notes=None):
        """Require resubmission with specific feedback"""
        self.status = 'resubmission_required'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        if notes:
            self.admin_notes = notes
        self.save()

class VerificationHistory(models.Model):
    """Track verification status changes"""
    
    verification = models.ForeignKey(ClientVerification, on_delete=models.CASCADE, related_name='history')
    previous_status = models.CharField(max_length=25)
    new_status = models.CharField(max_length=25)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    change_reason = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Verification History"
        verbose_name_plural = "Verification Histories"
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.verification.user.username}: {self.previous_status} → {self.new_status}"