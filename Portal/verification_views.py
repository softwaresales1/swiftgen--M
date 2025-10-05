from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import ClientVerification
import uuid

@login_required
def verification_dashboard(request):
    """Handle verification form display and submission"""
    
    # Check if user already has a verification record (only if table exists)
    try:
        verification = ClientVerification.objects.get(user=request.user)
        # User already has verification record, show status
        if verification.status == 'pending':
            return render(request, 'verification_pending.html', {'verification': verification})
        elif verification.status == 'approved':
            return render(request, 'verification_approved.html', {'verification': verification})
        elif verification.status == 'rejected':
            return render(request, 'verification_rejected.html', {'verification': verification})
    except (ClientVerification.DoesNotExist, Exception):
        # User doesn't have verification record or table doesn't exist, show form
        pass
    
    if request.method == 'POST':
        try:
            # Check if the table exists first
            from django.db import connection
            table_names = connection.introspection.table_names()
            if 'Portal_clientverification' not in table_names:
                messages.error(request, 'Verification system is not ready. Please contact support.')
                return render(request, 'verification_dashboard.html')
            
            # Extract form data
            full_name = request.POST.get('full_name', '').strip()
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Validate required fields
            required_fields = ['full_name', 'date_of_birth', 'phone_number', 'address', 
                             'id_type', 'id_number', 'paypal_email', 'confirm_paypal_email']
            
            for field in required_fields:
                if not request.POST.get(field):
                    messages.error(request, f'Please fill in the {field.replace("_", " ")} field.')
                    return render(request, 'verification_dashboard.html')
            
            # Validate PayPal email confirmation
            if request.POST.get('paypal_email') != request.POST.get('confirm_paypal_email'):
                messages.error(request, 'PayPal email addresses do not match.')
                return render(request, 'verification_dashboard.html')
            
            # Validate file uploads
            if 'id_front' not in request.FILES:
                messages.error(request, 'Please upload the front of your ID document.')
                return render(request, 'verification_dashboard.html')
            
            if 'id_back' not in request.FILES:
                messages.error(request, 'Please upload the back of your ID document.')
                return render(request, 'verification_dashboard.html')
            
            # Check if checkboxes are checked
            if not request.POST.get('terms_agreement'):
                messages.error(request, 'Please agree to the Terms of Service and Privacy Policy.')
                return render(request, 'verification_dashboard.html')
            
            if not request.POST.get('data_accuracy'):
                messages.error(request, 'Please certify that all information is accurate.')
                return render(request, 'verification_dashboard.html')
            
            # Create verification record
            verification = ClientVerification.objects.create(
                user=request.user,
                verification_id=uuid.uuid4(),
                status='pending',
                first_name=first_name,
                last_name=last_name,
                date_of_birth=request.POST.get('date_of_birth'),
                phone_number=request.POST.get('phone_number'),
                
                # Parse address (simplified for now)
                address_line_1=request.POST.get('address'),
                city='Not specified',  # Could be enhanced with separate fields
                state_province='Not specified',
                postal_code='00000',
                country='Not specified',
                
                # Document information
                document_type=request.POST.get('id_type'),
                document_number=request.POST.get('id_number'),
                document_expiry_date=timezone.now().date(),  # Could add expiry field to form
                document_front_image=request.FILES.get('id_front'),
                document_back_image=request.FILES.get('id_back'),
                
                # PayPal information
                paypal_email=request.POST.get('paypal_email'),
                paypal_account_verified=False,
                
                # Required placeholder images (could be made optional)
                proof_of_address_image=request.FILES.get('id_front'),  # Using ID as placeholder
                selfie_with_document=request.FILES.get('id_front'),    # Using ID as placeholder
            )
            
            messages.success(request, 'Verification submitted successfully! Your application is now under review.')
            return redirect('Portal:verification_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error submitting verification: {str(e)}')
            return render(request, 'verification_dashboard.html')
    
    # GET request - show the form
    return render(request, 'verification_dashboard.html')