from django.urls import path
from . import views
from . import file_views
from .payment_views import (
    create_payment, payment_success, payment_cancelled, 
    stripe_webhook, release_payment, payment_dashboard, payment_options,
    paypal_payment, paypal_success, paypal_cancel, paypal_return,
    cancel_payment, cleanup_stuck_payments, debug_payments  # Added new debug functions
)

app_name = 'Portal'
urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup_user, name='signup'),
    path('get_started/', views.get_started, name='get_started'),
    path('services/', views.services, name='services'),
    path('contactus/', views.contactus, name='contactus'),
    path('check_username/', views.check_username, name='check_username'),
    path('check_email/', views.check_email, name='check_email'),
    path('auth/callback/<token>', views.auth_callback_token, name='login_iiits'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('open_close_project/', views.open_close_project,name="open_close_project"),
    path('home/', views.home, name='home'),
    path('browse_jobs/', views.browse_jobs, name='browse_jobs'),
    path('jobs_update/', views.jobs_update, name='jobs_update'),
    path('form_state/', views.form_state, name='form_state'),
    path('post_project/', views.post_project, name='post_project'),
    path('project_description/<int:project_id>/', views.project_description, name='project_description'),
    path('<int:project_id>/add_task/', views.add_task, name='add_task'),
    path('<int:project_id>/task_description/<int:task_id>/', views.task_description, name='task_description'),
    path('<int:project_id>/task_edit/<int:task_id>/', views.task_editfunction, name='task_edit'),
    path('profile/<username>/', views.user_profile, name="profile"),
    path('myprojects/', views.myprojects, name="myprojects"),
    path('applicants/<int:task_id>/', views.applicants, name="applicants"),
    path('browse_projects/', views.browse_projects, name='browse_projects'),
    path('post_project_enhanced/', views.post_project_enhanced, name='post_project_enhanced'),
    path('join_wait_list/', views.join_wait_list, name='join_wait_list'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('accept-bid/<int:bid_id>/', views.accept_bid, name='accept_bid'),
    
    # Payment URLs (Stripe & General)
    path('payment/options/<int:project_id>/', payment_options, name='payment_options'),
    path('payment/create/<int:project_id>/', create_payment, name='create_payment'),
    path('payment/success/<str:payment_id>/', payment_success, name='payment_success'),
    path('payment/cancelled/<str:payment_id>/', payment_cancelled, name='payment_cancelled'),
    path('payment/cancel/<int:project_id>/', cancel_payment, name='cancel_payment'),
    path('payment/cleanup/<int:project_id>/', cleanup_stuck_payments, name='cleanup_stuck_payments'),  # NEW: Manual cleanup
    path('payment/debug/<int:project_id>/', debug_payments, name='debug_payments'),  # NEW: Debug view
    path('payment/release/<str:payment_id>/', release_payment, name='release_payment'),
    path('payment/dashboard/', payment_dashboard, name='payment_dashboard'),
    path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),
    
    # PayPal URLs (Complete integration)
    path('payment/paypal/<int:project_id>/', paypal_payment, name='paypal_payment'),
    path('payment/paypal/return/<int:project_id>/', paypal_return, name='paypal_return'),
    path('payment/paypal/cancel/<int:project_id>/', paypal_cancel, name='paypal_cancel'),
    path('payment/paypal/success/<str:payment_id>/', paypal_success, name='paypal_success'),
    
    # ===== FILE MANAGEMENT & WORKSPACE URLS =====
    
    # Client file upload system
    path('project/<int:project_id>/upload-files/', file_views.upload_project_files, name='upload_project_files'),
    path('project/<int:project_id>/files/', file_views.project_file_manager, name='project_file_manager'),
    path('download-file/<int:file_id>/', file_views.download_file, name='download_file'),
    
    # Freelancer workspace system
    path('workspace/', file_views.freelancer_workspace, name='freelancer_workspace'),
    path('workspace/project/<int:project_id>/', file_views.project_workspace, name='project_workspace'),
    
    # Work submission system
    path('project/<int:project_id>/submit-work/', file_views.submit_work, name='submit_work'),
    path('submission/<int:submission_id>/', file_views.view_submission, name='view_submission'),
    path('download-submission/<int:file_id>/', file_views.download_submission_file, name='download_submission_file'),
    
    # Review system
    path('review-submission/<int:submission_id>/', file_views.review_submission, name='review_submission'),
]