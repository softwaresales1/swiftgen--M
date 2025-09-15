import stripe
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from .models import Project, Payment, Milestone, CustomUser, ProjectBid
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Configure Stripe with safe fallback
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

@login_required 
def payment_options(request, project_id):
    """Show payment method selection page with proper forms"""
    try:
        project = get_object_or_404(Project, id=project_id)
        client = get_object_or_404(CustomUser, user=request.user)
        
        # Ensure user is the project owner
        if request.user.customuser != project.leader:
            messages.error(request, "You can only pay for your own projects.")
            return redirect('Portal:project_detail', project_id=project_id)
        
        # Get the accepted bid
        accepted_bid = project.bids.filter(status='accepted').first()
        if not accepted_bid:
            messages.error(request, "No accepted bid found for this project.")
            return redirect('Portal:project_detail', project_id=project_id)
        
        # Check if there's already a pending payment
        existing_payment = Payment.objects.filter(
            project=project,
            client=client,
            status='pending'
        ).first()
        
        # Debug logging
        print(f"DEBUG: Checking for existing payments for project {project_id}")
        all_payments = Payment.objects.filter(project=project, client=client)
        for p in all_payments:
            print(f"Payment {p.payment_id}: Status={p.status}, Method={p.payment_method}, Created={p.created_at}")
        
        # If there's a pending payment older than 15 minutes, mark it as failed
        if existing_payment:
            time_diff = timezone.now() - existing_payment.created_at
            print(f"DEBUG: Found pending payment {existing_payment.payment_id}, age: {time_diff.total_seconds()} seconds")
            
            if time_diff.total_seconds() > 900:  # 15 minutes
                print(f"DEBUG: Payment {existing_payment.payment_id} is old, marking as failed")
                existing_payment.status = 'failed'
                existing_payment.save()
                existing_payment = None
        
        # If there's still a recent pending payment, show processing page
        if existing_payment:
            print(f"DEBUG: Showing processing page for payment {existing_payment.payment_id}")
            return render(request, 'payment_processing.html', {
                'payment': existing_payment,
                'project': project,
                'can_cancel': True  # Allow cancellation
            })
        
        # Check if payment already completed
        completed_payment = Payment.objects.filter(project=project, status='completed').first()
        if completed_payment:
            messages.info(request, "Payment has already been completed for this project.")
            return redirect('Portal:project_detail', project_id=project_id)
        
        # Calculate fees
        gross_amount = Decimal(str(accepted_bid.bid_amount))
        platform_fee = gross_amount * Decimal('0.10')  # 10%
        processing_fee = gross_amount * Decimal('0.03')  # ~3%
        net_amount = gross_amount - platform_fee
        
        context = {
            'project': project,
            'accepted_bid': accepted_bid,
            'freelancer': accepted_bid.freelancer,
            'gross_amount': gross_amount,
            'platform_fee': platform_fee,
            'processing_fee': processing_fee,
            'net_amount': net_amount,
            'stripe_public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
            'paypal_client_id': getattr(settings, 'PAYPAL_CLIENT_ID', ''),
        }
        
        return render(request, 'payment_options.html', context)
        
    except Exception as e:
        print(f"DEBUG: Error in payment_options: {str(e)}")
        messages.error(request, f'Error loading payment options: {str(e)}')
        return redirect('Portal:project_detail', project_id=project_id)

@login_required
def cancel_payment(request, project_id):
    """Cancel a pending payment and allow restart"""
    try:
        project = get_object_or_404(Project, id=project_id)
        client = get_object_or_404(CustomUser, user=request.user)
        
        print(f"DEBUG: Attempting to cancel payments for project {project_id}, user {client.user.username}")
        
        # Find and cancel any pending payments for this project by this user
        pending_payments = Payment.objects.filter(
            project=project,
            client=client,
            status='pending'
        )
        
        # Debug: Log what we found
        print(f"DEBUG: Found {pending_payments.count()} pending payments to cancel")
        for payment in pending_payments:
            print(f"DEBUG: Cancelling payment: {payment.payment_id} - {payment.payment_method} - Status: {payment.status}")
        
        # Mark them as cancelled/failed
        updated_count = pending_payments.update(status='failed', updated_at=timezone.now())
        print(f"DEBUG: Successfully cancelled {updated_count} payments")
        
        # Double-check the update worked
        remaining_pending = Payment.objects.filter(
            project=project,
            client=client,
            status='pending'
        ).count()
        print(f"DEBUG: Remaining pending payments after cancellation: {remaining_pending}")
        
        messages.success(request, 'Payment cancelled. You can start a new payment.')
        return redirect('Portal:payment_options', project_id=project_id)
        
    except Exception as e:
        print(f"DEBUG: Error in cancel_payment: {str(e)}")
        messages.error(request, f'Error cancelling payment: {str(e)}')
        return redirect('Portal:project_detail', project_id=project_id)

@login_required
def cleanup_stuck_payments(request, project_id):
    """Manually cleanup all stuck payments for a project"""
    try:
        project = get_object_or_404(Project, id=project_id)
        client = get_object_or_404(CustomUser, user=request.user)
        
        print(f"DEBUG: Manual cleanup for project {project_id}")
        
        # Find ALL payments (not just pending) for this project by this user
        all_payments = Payment.objects.filter(
            project=project,
            client=client
        ).exclude(status='completed')  # Don't touch completed payments
        
        count = all_payments.count()
        print(f"DEBUG: Found {count} non-completed payments to clean up")
        
        for payment in all_payments:
            print(f"DEBUG: Cleaning payment {payment.payment_id} - Status: {payment.status}")
        
        all_payments.update(status='failed', updated_at=timezone.now())
        
        messages.success(request, f'Cleared {count} stuck payment(s). You can start fresh now.')
        return redirect('Portal:payment_options', project_id=project_id)
        
    except Exception as e:
        print(f"DEBUG: Error in cleanup_stuck_payments: {str(e)}")
        messages.error(request, f'Error cleaning up payments: {str(e)}')
        return redirect('Portal:project_detail', project_id=project_id)

@login_required
def debug_payments(request, project_id):
    """Debug view to see all payments for a project"""
    try:
        project = get_object_or_404(Project, id=project_id)
        payments = Payment.objects.filter(project=project).order_by('-created_at')
        
        debug_info = []
        for payment in payments:
            debug_info.append({
                'id': payment.payment_id,
                'status': payment.status,
                'method': payment.payment_method,
                'created': payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'client': payment.client.user.username,
                'amount': str(payment.gross_amount)
            })
        
        return JsonResponse({
            'project_id': project_id,
            'project_name': project.project_name,
            'payments': debug_info
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})

@login_required
def create_payment(request, project_id):
    """Process payment based on selected method"""
    project = get_object_or_404(Project, id=project_id)
    
    # Ensure user is the project owner
    if request.user.customuser != project.leader:
        return JsonResponse({'success': False, 'error': 'Unauthorized access'})
    
    # Get the accepted bid
    accepted_bid = project.bids.filter(status='accepted').first()
    if not accepted_bid:
        return JsonResponse({'success': False, 'error': 'No accepted bid found'})
    
    # Check for existing pending payments and clean them up
    existing_pending = Payment.objects.filter(
        project=project,
        client=request.user.customuser,
        status='pending'
    )
    
    if existing_pending.exists():
        print(f"DEBUG: Found {existing_pending.count()} existing pending payments, cleaning up")
        existing_pending.update(status='failed', updated_at=timezone.now())
    
    # Get payment method and details
    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                payment_method_type = data.get('payment_type', 'card')
                payment_method_id = data.get('payment_method_id')
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        else:
            payment_method_type = request.POST.get('payment_type', 'card')
            payment_method_id = request.POST.get('payment_method_id')
    else:
        # Handle GET requests with method parameter
        payment_method_type = request.GET.get('method', 'card')
        payment_method_id = None
    
    # Calculate amounts
    gross_amount = Decimal(str(accepted_bid.bid_amount))
    platform_fee = gross_amount * Decimal('0.10')
    processing_fee = gross_amount * Decimal('0.03')
    net_amount = gross_amount - platform_fee
    
    try:
        # Create payment record
        payment = Payment.objects.create(
            client=request.user.customuser,
            freelancer=accepted_bid.freelancer,
            project=project,
            gross_amount=gross_amount,
            platform_fee=platform_fee,
            processing_fee=processing_fee,
            payment_method=payment_method_type,
            description=f"Payment for project: {project.project_name}",
            client_ip=request.META.get('REMOTE_ADDR'),
            status='pending'
        )
        
        print(f"DEBUG: Created new payment {payment.payment_id} with method {payment_method_type}")
        
        # Handle different payment methods
        if payment_method_type == 'paypal':
            # PayPal payment - redirect to PayPal processing page
            print(f"DEBUG: Processing PayPal payment {payment.payment_id}")
            return JsonResponse({
                'success': True,
                'redirect_url': f'/payment/paypal/{project.id}/',
                'payment_id': payment.payment_id
            })
        
        elif payment_method_type in ['apple_pay', 'google_pay', 'alipay']:
            # Use Stripe Checkout for these methods (only if Stripe is configured)
            if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
                return JsonResponse({'success': False, 'error': 'Credit card payments not available'})
            return create_stripe_checkout_session(request, payment, payment_method_type)
        
        elif payment_method_type == 'card' and payment_method_id:
            # Process card payment with Payment Intent (only if Stripe is configured)
            if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
                return JsonResponse({'success': False, 'error': 'Credit card payments not available'})
            return process_card_payment(request, payment, payment_method_id)
        
        else:
            # Default to PayPal if no Stripe, otherwise Stripe
            if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
                return JsonResponse({
                    'success': True,
                    'redirect_url': f'/payment/paypal/{project.id}/',
                    'payment_id': payment.payment_id
                })
            return create_stripe_checkout_session(request, payment, 'card')
            
    except Exception as e:
        print(f"DEBUG: Payment creation error: {str(e)}")
        logger.error(f"Payment creation error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Payment processing failed'})

def create_stripe_checkout_session(request, payment, payment_method_type):
    """Create Stripe Checkout session for redirect-based payments"""
    try:
        # Define payment method types
        payment_methods = ['card']
        
        if payment_method_type == 'alipay':
            payment_methods = ['alipay', 'card']
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=payment_methods,
            customer_email=request.user.email,
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Project: {payment.project.project_name}',
                        'description': f'Payment to {payment.freelancer.user.get_full_name()}',
                    },
                    'unit_amount': int(payment.gross_amount * 100),  # Stripe uses cents
                },
                'quantity': 1,
            }],
            metadata={
                'payment_id': payment.payment_id,
                'project_id': payment.project.id,
                'freelancer_id': payment.freelancer.pk,
                'client_id': payment.client.pk,
                'payment_method': payment_method_type,
            },
            mode='payment',
            automatic_payment_methods={'enabled': True},
            billing_address_collection='required',
            success_url=request.build_absolute_uri(
                reverse('Portal:payment_success', kwargs={'payment_id': payment.payment_id})
            ),
            cancel_url=request.build_absolute_uri(
                reverse('Portal:payment_cancelled', kwargs={'payment_id': payment.payment_id})
            ),
        )
        
        # Save Stripe session ID
        payment.stripe_checkout_session_id = checkout_session.id
        payment.save()
        
        # Return redirect URL for AJAX requests
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'checkout_url': checkout_session.url,
                'redirect_url': checkout_session.url
            })
        else:
            return redirect(checkout_session.url, code=303)
            
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout session error: {str(e)}")
        payment.status = 'failed'
        payment.save()
        
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'error': str(e)})
        else:
            messages.error(request, f"Payment processing error: {str(e)}")
            return redirect('Portal:project_detail', project_id=payment.project.id)

def process_card_payment(request, payment, payment_method_id):
    """Process direct card payment with Payment Intent"""
    try:
        # Create Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=int(payment.gross_amount * 100),  # Amount in cents
            currency='usd',
            payment_method=payment_method_id,
            confirm=True,
            return_url=request.build_absolute_uri(
                reverse('Portal:payment_success', kwargs={'payment_id': payment.payment_id})
            ),
            metadata={
                'payment_id': payment.payment_id,
                'project_id': payment.project.id,
                'freelancer_id': payment.freelancer.pk,
                'client_id': payment.client.pk,
            },
        )
        
        # Save Payment Intent ID
        payment.stripe_payment_intent_id = intent.id
        payment.save()
        
        # Handle different intent statuses
        if intent.status == 'succeeded':
            payment.status = 'completed'
            payment.save()
            
            # Update project status
            payment.project.project_status = 'in_progress'
            payment.project.save()
            
            # Send notifications
            send_payment_confirmation_emails(payment)
            
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('Portal:payment_success', kwargs={'payment_id': payment.payment_id})
            })
            
        elif intent.status == 'requires_action':
            return JsonResponse({
                'success': True,
                'requires_action': True,
                'client_secret': intent.client_secret
            })
            
        else:
            return JsonResponse({
                'success': False,
                'error': 'Payment confirmation required'
            })
            
    except stripe.error.StripeError as e:
        logger.error(f"Card payment error: {str(e)}")
        payment.status = 'failed'
        payment.save()
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def payment_success(request, payment_id):
    """Handle successful payment"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    # Ensure user has access to this payment
    if request.user.customuser not in [payment.client, payment.freelancer]:
        messages.error(request, "Access denied.")
        return redirect('Portal:home')
    
    context = {
        'payment': payment,
        'project': payment.project,
        'freelancer': payment.freelancer,
        'client': payment.client,
    }
    return render(request, 'payment_success.html', context)

@login_required
def payment_cancelled(request, payment_id):
    """Handle cancelled payment"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    # Only allow client to see cancelled payments
    if request.user.customuser != payment.client:
        messages.error(request, "Access denied.")
        return redirect('Portal:home')
    
    payment.status = 'failed'
    payment.save()
    
    messages.warning(request, "Payment was cancelled. You can try again anytime.")
    return redirect('Portal:project_detail', project_id=payment.project.id)

# PayPal Integration Views

@login_required
def paypal_payment(request, project_id):
    """Initiate PayPal payment for a project"""
    try:
        project = get_object_or_404(Project, id=project_id)
        client = get_object_or_404(CustomUser, user=request.user)
        
        # Ensure user is the project owner
        if request.user.customuser != project.leader:
            messages.error(request, "You can only pay for your own projects.")
            return redirect('Portal:project_detail', project_id=project_id)
        
        # Get the accepted bid
        accepted_bid = project.bids.filter(status='accepted').first()
        if not accepted_bid:
            messages.error(request, "No accepted bid found for this project.")
            return redirect('Portal:project_detail', project_id=project_id)
        
        # Check for existing pending payment and handle timeout
        existing_payment = Payment.objects.filter(
            project=project,
            client=client,
            status='pending',
            payment_method='paypal'  # Only check PayPal payments
        ).first()
        
        if existing_payment:
            time_diff = timezone.now() - existing_payment.created_at
            print(f"DEBUG: PayPal - Found existing payment {existing_payment.payment_id}, age: {time_diff.total_seconds()} seconds")
            
            if time_diff.total_seconds() > 900:  # 15 minutes
                print(f"DEBUG: PayPal - Payment {existing_payment.payment_id} is old, marking as failed")
                existing_payment.status = 'failed'
                existing_payment.save()
            else:
                # Don't show processing page - proceed with PayPal payment form
                print(f"DEBUG: PayPal - Using existing payment {existing_payment.payment_id} for PayPal form")
                context = {
                    'payment': existing_payment,
                    'project': project,
                    'freelancer': accepted_bid.freelancer,
                    'gross_amount': existing_payment.gross_amount,
                    'paypal_client_id': getattr(settings, 'PAYPAL_CLIENT_ID', ''),
                }
                return render(request, 'paypal_payment.html', context)
        
        # Check if payment already completed
        completed_payment = Payment.objects.filter(project=project, status='completed').first()
        if completed_payment:
            messages.info(request, "Payment has already been completed for this project.")
            return redirect('Portal:project_detail', project_id=project_id)
        
        # Calculate amounts
        gross_amount = Decimal(str(accepted_bid.bid_amount))
        platform_fee = gross_amount * Decimal('0.10')
        processing_fee = gross_amount * Decimal('0.03')
        net_amount = gross_amount - platform_fee
        
        # Create payment record
        payment = Payment.objects.create(
            client=request.user.customuser,
            freelancer=accepted_bid.freelancer,
            project=project,
            gross_amount=gross_amount,
            platform_fee=platform_fee,
            processing_fee=processing_fee,
            payment_method='paypal',
            description=f"Payment for project: {project.project_name}",
            client_ip=request.META.get('REMOTE_ADDR'),
            status='pending'
        )
        
        print(f"DEBUG: Created PayPal payment {payment.payment_id}")
        
        context = {
            'payment': payment,
            'project': project,
            'freelancer': accepted_bid.freelancer,
            'gross_amount': gross_amount,
            'paypal_client_id': getattr(settings, 'PAYPAL_CLIENT_ID', ''),
        }
        
        return render(request, 'paypal_payment.html', context)
        
    except Exception as e:
        print(f"DEBUG: PayPal payment initiation error: {str(e)}")
        logger.error(f"PayPal payment initiation error: {str(e)}")
        messages.error(request, f'Error initiating PayPal payment: {str(e)}')
        return redirect('Portal:project_detail', project_id=project_id)

@login_required
def paypal_return(request, project_id):
    """Handle PayPal return (success)"""
    try:
        project = get_object_or_404(Project, id=project_id)
        client = get_object_or_404(CustomUser, user=request.user)
        
        # Find the pending payment
        payment = Payment.objects.filter(
            project=project,
            client=client,
            status='pending',
            payment_method='paypal'
        ).first()
        
        if not payment:
            messages.error(request, "No pending PayPal payment found.")
            return redirect('Portal:project_detail', project_id=project_id)
        
        print(f"DEBUG: PayPal return for payment {payment.payment_id}")
        
        # Mark payment as completed
        payment.status = 'completed'
        payment.paypal_order_id = request.GET.get('token', '')
        payment.paypal_payer_id = request.GET.get('PayerID', '')
        payment.save()
        
        # Update project status  
        payment.project.project_status = 'in_progress'
        payment.project.save()
        
        # Send confirmation emails
        send_payment_confirmation_emails(payment)
        
        messages.success(request, "PayPal payment completed successfully!")
        return redirect('Portal:payment_success', payment_id=payment.payment_id)
        
    except Exception as e:
        print(f"DEBUG: PayPal return error: {str(e)}")
        logger.error(f"PayPal return error: {str(e)}")
        messages.error(request, "Error processing PayPal return.")
        return redirect('Portal:project_detail', project_id=project_id)

@login_required
def paypal_cancel(request, project_id):
    """Handle PayPal payment cancellation"""
    try:
        project = get_object_or_404(Project, id=project_id)
        client = get_object_or_404(CustomUser, user=request.user)
        
        print(f"DEBUG: PayPal cancel for project {project_id}")
        
        # Find and cancel the pending payment
        pending_payment = Payment.objects.filter(
            project=project,
            client=client,
            status='pending',
            payment_method='paypal'
        ).first()
        
        if pending_payment:
            print(f"DEBUG: Cancelling PayPal payment {pending_payment.payment_id}")
            pending_payment.status = 'failed'
            pending_payment.updated_at = timezone.now()
            pending_payment.save()
        
        messages.info(request, 'PayPal payment was cancelled. You can start a new payment.')
        return redirect('Portal:payment_options', project_id=project_id)
        
    except Exception as e:
        print(f"DEBUG: PayPal cancel error: {str(e)}")
        logger.error(f"PayPal cancel error: {str(e)}")
        messages.error(request, f'Error handling cancellation: {str(e)}')
        return redirect('Portal:project_detail', project_id=project_id)

@csrf_exempt
@require_POST
def paypal_success(request, payment_id):
    """Handle successful PayPal payment (webhook/AJAX)"""
    try:
        payment = get_object_or_404(Payment, payment_id=payment_id)
        
        # Get PayPal order details from request
        data = json.loads(request.body)
        order_id = data.get('orderID')
        payer_info = data.get('payer', {})
        
        print(f"DEBUG: PayPal success webhook for payment {payment_id}")
        
        # Update payment with PayPal details
        payment.paypal_order_id = order_id
        payment.paypal_payer_id = payer_info.get('payer_id', '')
        payment.status = 'completed'
        payment.save()
        
        # Update project status
        payment.project.project_status = 'in_progress'
        payment.project.save()
        
        # Send confirmation emails
        send_payment_confirmation_emails(payment)
        
        logger.info(f"PayPal payment {payment_id} completed successfully")
        
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('Portal:payment_success', kwargs={'payment_id': payment_id})
        })
        
    except Exception as e:
        print(f"DEBUG: PayPal success error: {str(e)}")
        logger.error(f"PayPal payment error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks for real-time payment updates"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    if not endpoint_secret:
        logger.warning("Stripe webhook secret not configured")
        return HttpResponse(status=400)
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid payload in webhook")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in webhook")
        return HttpResponse(status=400)
    
    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_successful_payment(session)
    
    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_intent_succeeded(payment_intent)
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failed(payment_intent)
    
    return HttpResponse(status=200)

def handle_successful_payment(session):
    """Process successful payment from Stripe webhook"""
    try:
        payment_id = session['metadata'].get('payment_id')
        if not payment_id:
            logger.error("No payment_id in session metadata")
            return
            
        payment = Payment.objects.get(payment_id=payment_id)
        
        # Update payment status
        payment.status = 'completed'
        payment.stripe_payment_intent_id = session.get('payment_intent')
        payment.save()
        
        # Update project status
        project = payment.project
        project.project_status = 'in_progress'
        project.save()
        
        # Send notification emails
        send_payment_confirmation_emails(payment)
        
        logger.info(f"Payment {payment_id} completed successfully")
        
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for session {session.get('id')}")
    except Exception as e:
        logger.error(f"Error handling successful payment: {str(e)}")

def handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent"""
    try:
        # Find payment by payment intent ID
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
        
        if payment.status != 'completed':
            payment.status = 'completed'
            payment.save()
            
            # Update project status
            payment.project.project_status = 'in_progress'
            payment.project.save()
            
            # Send notifications
            send_payment_confirmation_emails(payment)
        
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for payment intent {payment_intent['id']}")

def handle_payment_failed(payment_intent):
    """Handle failed payment"""
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
        payment.status = 'failed'
        payment.save()
        
        logger.info(f"Payment {payment.payment_id} failed")
        
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for failed payment intent {payment_intent['id']}")

def send_payment_confirmation_emails(payment):
    """Send email confirmations to client and freelancer"""
    try:
        # Email to client
        client_subject = f"Payment Confirmation - {payment.project.project_name}"
        client_message = render_to_string('emails/payment_confirmation_client.html', {
            'payment': payment,
            'client_name': payment.client.user.get_full_name(),
            'project': payment.project,
            'freelancer': payment.freelancer,
        })
        
        client_email = EmailMessage(
            client_subject,
            client_message,
            getattr(settings, 'EMAIL_HOST_USER', 'noreply@swifttalentforge.com'),
            [payment.client.user.email]
        )
        client_email.content_subtype = 'html'
        client_email.send()
        
        # Email to freelancer
        freelancer_subject = f"Payment Received - {payment.project.project_name}"
        freelancer_message = render_to_string('emails/payment_notification_freelancer.html', {
            'payment': payment,
            'freelancer_name': payment.freelancer.user.get_full_name(),
            'project': payment.project,
            'client': payment.client,
        })
        
        freelancer_email = EmailMessage(
            freelancer_subject,
            freelancer_message,
            getattr(settings, 'EMAIL_HOST_USER', 'noreply@swifttalentforge.com'),
            [payment.freelancer.user.email]
        )
        freelancer_email.content_subtype = 'html'
        freelancer_email.send()
        
        logger.info(f"Payment confirmation emails sent for payment {payment.payment_id}")
        
    except Exception as e:
        logger.error(f"Error sending payment confirmation emails: {str(e)}")

@login_required
def release_payment(request, payment_id):
    """Release payment from escrow to freelancer (client action)"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    # Only client can release payment
    if request.user.customuser != payment.client:
        messages.error(request, "You can only release payments for your own projects.")
        return redirect('Portal:project_detail', project_id=payment.project.id)
    
    if payment.status != 'completed':
        messages.error(request, "Payment must be completed before it can be released.")
        return redirect('Portal:project_detail', project_id=payment.project.id)
    
    if not payment.escrow_held:
        messages.info(request, "Payment has already been released.")
        return redirect('Portal:project_detail', project_id=payment.project.id)
    
    # Release payment from escrow
    payment.escrow_held = False
    payment.released_at = timezone.now()
    payment.save()
    
    # Update project status
    payment.project.project_status = 'completed'
    payment.project.save()
    
    messages.success(request, f"Payment of ${payment.net_amount} has been released to {payment.freelancer.user.get_full_name()}.")
    
    # Send release notification
    send_payment_release_notification(payment)
    
    return redirect('Portal:project_detail', project_id=payment.project.id)

def send_payment_release_notification(payment):
    """Notify freelancer that payment has been released"""
    try:
        subject = f"Payment Released - ${payment.net_amount}"
        message = render_to_string('emails/payment_released.html', {
            'payment': payment,
            'freelancer_name': payment.freelancer.user.get_full_name(),
            'project': payment.project,
        })
        
        email = EmailMessage(
            subject,
            message,
            getattr(settings, 'EMAIL_HOST_USER', 'noreply@swifttalentforge.com'),
            [payment.freelancer.user.email]
        )
        email.content_subtype = 'html'
        email.send()
        
        logger.info(f"Payment release notification sent for payment {payment.payment_id}")
        
    except Exception as e:
        logger.error(f"Error sending payment release notification: {str(e)}")

@login_required
def payment_dashboard(request):
    """Dashboard showing all payments for user"""
    user = request.user.customuser
    
    # Payments made (as client)
    payments_made = Payment.objects.filter(client=user).order_by('-created_at')
    
    # Payments received (as freelancer)
    payments_received = Payment.objects.filter(freelancer=user).order_by('-created_at')
    
    # Calculate totals safely
    total_paid = sum(
        p.gross_amount for p in payments_made 
        if p.status == 'completed'
    )
    
    total_earned = sum(
        p.net_amount for p in payments_received 
        if p.status == 'completed' and not p.escrow_held
    )
    
    total_in_escrow = sum(
        p.net_amount for p in payments_received 
        if p.status == 'completed' and p.escrow_held
    )
    
    context = {
        'payments_made': payments_made,
        'payments_received': payments_received,
        'total_paid': total_paid,
        'total_earned': total_earned,
        'total_in_escrow': total_in_escrow,
    }
    
    return render(request, 'payment_dashboard.html', context)