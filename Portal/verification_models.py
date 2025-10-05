# Client Verification Models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

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