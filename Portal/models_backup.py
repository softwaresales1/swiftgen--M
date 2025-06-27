from django.apps import AppConfig
from django.db import models
from django.contrib.auth.models import User
import stripe
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
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