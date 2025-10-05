from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

# Register your models here.
from .models import *

# Custom admin for Client Verification
@admin.register(ClientVerification)
class ClientVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'paypal_email', 'document_type', 'created_at', 'verification_actions']
    list_filter = ['status', 'document_type', 'created_at', 'paypal_account_verified']
    search_fields = ['user__username', 'user__email', 'paypal_email', 'first_name', 'last_name']
    readonly_fields = ['verification_id', 'created_at', 'updated_at', 'verification_documents']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'verification_id', 'status')
        }),
        ('Personal Details', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'phone_number')
        }),
        ('Address Information', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country')
        }),
        ('Document Information', {
            'fields': ('document_type', 'document_number', 'document_expiry_date', 'verification_documents')
        }),
        ('PayPal Information', {
            'fields': ('paypal_email', 'paypal_account_verified')
        }),
        ('Admin Actions', {
            'fields': ('admin_notes', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def verification_documents(self, obj):
        """Display document images in admin"""
        html = ""
        if obj.document_front_image:
            html += f'<p><strong>Front ID:</strong> <a href="{obj.document_front_image.url}" target="_blank">View Document</a></p>'
        if obj.document_back_image:
            html += f'<p><strong>Back ID:</strong> <a href="{obj.document_back_image.url}" target="_blank">View Document</a></p>'
        if obj.proof_of_address_image:
            html += f'<p><strong>Proof of Address:</strong> <a href="{obj.proof_of_address_image.url}" target="_blank">View Document</a></p>'
        if obj.selfie_with_document:
            html += f'<p><strong>Selfie:</strong> <a href="{obj.selfie_with_document.url}" target="_blank">View Document</a></p>'
        return mark_safe(html) if html else "No documents uploaded"
    
    verification_documents.short_description = "Uploaded Documents"
    
    def verification_actions(self, obj):
        """Display action buttons for verification"""
        if obj.status == 'pending':
            approve_url = reverse('admin:approve_verification', args=[obj.pk])
            reject_url = reverse('admin:reject_verification', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}">Approve</a>&nbsp;'
                '<a class="button" href="{}">Reject</a>',
                approve_url, reject_url
            )
        elif obj.status == 'approved':
            return format_html('<span style="color: green; font-weight: bold;">✓ Approved</span>')
        elif obj.status == 'rejected':
            return format_html('<span style="color: red; font-weight: bold;">✗ Rejected</span>')
        return "No actions available"
    
    verification_actions.short_description = "Actions"
    verification_actions.allow_tags = True
    
    def get_urls(self):
        """Add custom URLs for approval/rejection actions"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:verification_id>/', self.admin_site.admin_view(self.approve_verification), name='approve_verification'),
            path('reject/<int:verification_id>/', self.admin_site.admin_view(self.reject_verification), name='reject_verification'),
        ]
        return custom_urls + urls
    
    def approve_verification(self, request, verification_id):
        """Approve a verification"""
        from django.shortcuts import redirect
        from django.contrib import messages
        
        try:
            verification = ClientVerification.objects.get(pk=verification_id)
            verification.approve_verification(admin_user=request.user)
            messages.success(request, f'Verification for {verification.user.username} has been approved.')
        except ClientVerification.DoesNotExist:
            messages.error(request, 'Verification record not found.')
        
        return redirect('admin:Portal_clientverification_changelist')
    
    def reject_verification(self, request, verification_id):
        """Reject a verification"""
        from django.shortcuts import redirect
        from django.contrib import messages
        
        try:
            verification = ClientVerification.objects.get(pk=verification_id)
            reason = "Documents did not meet verification requirements"
            verification.reject_verification(admin_user=request.user, reason=reason)
            messages.success(request, f'Verification for {verification.user.username} has been rejected.')
        except ClientVerification.DoesNotExist:
            messages.error(request, 'Verification record not found.')
        
        return redirect('admin:Portal_clientverification_changelist')

admin.site.register([CustomUser,
                     Skill,
                     CommunicationLanguage,
                     UsersSkill,
                     UsersCommunicationLanguage,
                     Project,
                     Task,
                     TaskSkillsRequired,
                     TaskLanguagesRequired,
                     Applicant,
                     Contributor,
                     UserRating,
                     ])
