from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.files.storage import default_storage
from django.conf import settings
import os
import mimetypes
from .models import (
    Project, ProjectFile, WorkSubmission, SubmissionFile, 
    FreelancerAccess, ProjectBid, CustomUser, Payment, ProjectStatus
)

# ===== ENHANCED CLIENT FILE UPLOAD SYSTEM =====

@login_required
def upload_project_files(request, project_id):
    """Client uploads requirement files for their project with access control"""
    project = get_object_or_404(Project, id=project_id)
    custom_user = get_object_or_404(CustomUser, user=request.user)
    
    # Only project owner can upload files
    if project.leader != custom_user:
        messages.error(request, "You can only upload files to your own projects.")
        return redirect('Portal:project_detail', project_id=project.id)
    
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('files')
        description = request.POST.get('description', '')
        category = request.POST.get('category', 'requirement')
        priority = request.POST.get('priority', 'normal')
        access_level = request.POST.get('access_level', 'private')
        
        if not uploaded_files:
            messages.error(request, "Please select at least one file to upload.")
            return redirect('Portal:upload_project_files', project_id=project.id)
        
        try:
            with transaction.atomic():
                uploaded_count = 0
                for uploaded_file in uploaded_files:
                    # Get file info
                    file_size = uploaded_file.size
                    original_filename = uploaded_file.name
                    
                    # Determine file type based on extension and content type
                    file_type = determine_file_type(uploaded_file)
                    
                    # Validate file size (50MB limit)
                    if file_size > 50 * 1024 * 1024:  # 50MB
                        messages.warning(request, f"File '{original_filename}' skipped - exceeds 50MB limit.")
                        continue
                    
                    # Create ProjectFile record with enhanced fields
                    project_file = ProjectFile.objects.create(
                        project=project,
                        uploaded_by=custom_user,
                        file=uploaded_file,
                        original_filename=original_filename,
                        file_type=file_type,
                        file_size=file_size,
                        description=description,
                        category=category,
                        priority=priority,
                        access_level=access_level,
                        is_requirement=(category == 'requirement')
                    )
                    uploaded_count += 1
                
                if uploaded_count > 0:
                    messages.success(request, f"Successfully uploaded {uploaded_count} file(s)!")
                    return redirect('Portal:project_file_manager', project_id=project.id)
                else:
                    messages.error(request, "No files were uploaded. Please check file sizes and try again.")
                
        except Exception as e:
            messages.error(request, f"Error uploading files: {str(e)}")
    
    # Get existing files for display
    existing_files = project.files.all().order_by('-uploaded_at')
    
    return render(request, 'Portal/file_management/upload_files.html', {
        'project': project,
        'existing_files': existing_files
    })

def determine_file_type(uploaded_file):
    """Determine file type based on extension and MIME type"""
    file_name = uploaded_file.name.lower()
    content_type = uploaded_file.content_type or ''
    
    # Image files
    if (file_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg')) or 
        content_type.startswith('image/')):
        return 'image'
    
    # Video files
    elif (file_name.endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm')) or 
          content_type.startswith('video/')):
        return 'video'
    
    # Document files
    elif (file_name.endswith(('.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt')) or 
          content_type in ['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document']):
        return 'document'
    
    # Archive files
    elif (file_name.endswith(('.zip', '.rar', '.7z', '.tar', '.gz')) or 
          content_type in ['application/zip', 'application/x-rar-compressed']):
        return 'archive'
    
    # Spreadsheet files
    elif (file_name.endswith(('.xls', '.xlsx', '.csv')) or 
          content_type in ['application/vnd.ms-excel', 
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']):
        return 'spreadsheet'
    
    # Presentation files
    elif (file_name.endswith(('.ppt', '.pptx')) or 
          content_type in ['application/vnd.ms-powerpoint',
                          'application/vnd.openxmlformats-officedocument.presentationml.presentation']):
        return 'presentation'
    
    else:
        return 'other'

@login_required
def project_file_manager(request, project_id):
    """Enhanced file manager with SAFE access control and error handling"""
    project = get_object_or_404(Project, id=project_id)
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        messages.error(request, "Profile not found. Please complete your profile.")
        return redirect('Portal:home')
    
    # Enhanced access control
    is_owner = project.leader == custom_user
    
    # Check if user has freelancer access
    has_freelancer_access = FreelancerAccess.objects.filter(
        project=project, 
        freelancer=custom_user,
        can_download_files=True
    ).exists()
    
    # Allow viewing for potential bidders (but limit file access based on access_level)
    can_view_for_bidding = (
        project.project_status in ['posted', 'bidding'] and
        not is_owner
    )
    
    if not is_owner and not has_freelancer_access and not can_view_for_bidding:
        messages.error(request, "You don't have access to this project's files.")
        return redirect('Portal:browse_projects')
    
    # Get files with enhanced filtering
    files = project.files.all().order_by('-uploaded_at')
    
    # Filter files based on access level for bidding users
    if can_view_for_bidding and not has_freelancer_access:
        files = files.filter(access_level='public')
    
    # Get submissions if they exist
    try:
        submissions = project.submissions.all().order_by('-created_at')
    except:
        submissions = []
    
    # Get freelancer access info if user is freelancer
    freelancer_access = None
    if not is_owner:
        try:
            freelancer_access = FreelancerAccess.objects.get(
                project=project,
                freelancer=custom_user
            )
        except FreelancerAccess.DoesNotExist:
            pass
    
    # SAFE File statistics with error handling
    file_stats = {
        'total': files.count(),
        'by_type': {},
        'by_access': {
            'public': files.filter(access_level='public').count(),
            'private': files.filter(access_level='private').count(),
        },
        'categories': {},
        'priority': {},
        'total_size': sum(f.file_size for f in files) if files else 0
    }
    
    # Count by file type
    for file_type in ['document', 'image', 'video', 'archive', 'spreadsheet', 'presentation', 'other']:
        file_stats['by_type'][file_type] = files.filter(file_type=file_type).count()
    
    # SAFE category counting - check if field exists
    try:
        # Try to access category field
        test_query = files.filter(category='requirement').exists()
        # If successful, count categories
        for category in ['requirement', 'reference', 'example', 'specification', 'other']:
            file_stats['categories'][category] = files.filter(category=category).count()
    except Exception as e:
        # Field doesn't exist yet, use fallback
        file_stats['categories'] = {
            'requirement': files.filter(is_requirement=True).count(),
            'reference': files.filter(is_requirement=False).count(),
            'example': 0,
            'specification': 0,
            'other': 0
        }
    
    # SAFE priority counting - check if field exists
    try:
        # Try to access priority field
        test_query = files.filter(priority='high').exists()
        # If successful, count priorities
        for priority in ['low', 'normal', 'high', 'critical']:
            file_stats['priority'][priority] = files.filter(priority=priority).count()
    except Exception as e:
        # Field doesn't exist yet, use fallback
        file_stats['priority'] = {
            'low': 0,
            'normal': files.count(),
            'high': 0,
            'critical': 0
        }
    
    return render(request, 'Portal/file_management/project_file_manager.html', {
        'project': project,
        'files': files,
        'submissions': submissions,
        'freelancer_access': freelancer_access,
        'is_owner': is_owner,
        'can_download': is_owner or has_freelancer_access,
        'is_bidding_phase': can_view_for_bidding,
        'file_stats': file_stats,
        'can_view_private': is_owner or has_freelancer_access
    })

@login_required
def download_file(request, file_id):
    """Enhanced file download with access control"""
    project_file = get_object_or_404(ProjectFile, id=file_id)
    project = project_file.project
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('Portal:home')
    
    # Enhanced access permissions
    is_owner = project.leader == custom_user
    is_hired_freelancer = FreelancerAccess.objects.filter(
        project=project,
        freelancer=custom_user,
        can_download_files=True
    ).exists()
    
    # Check access based on file access level
    can_download = False
    
    if is_owner:
        can_download = True
    elif is_hired_freelancer:
        can_download = True
    elif (project_file.access_level == 'public' and 
          project.project_status in ['posted', 'bidding']):
        can_download = True
    
    if not can_download:
        if project.project_status in ['posted', 'bidding'] and not is_owner:
            messages.error(request, 
                "This file is only available after being hired for the project. "
                "Public files can be downloaded during the bidding phase.")
        else:
            messages.error(request, "You don't have permission to download this file.")
        return redirect('Portal:project_detail', project_id=project.id)
    
    try:
        file_path = project_file.file.path
        if os.path.exists(file_path):
            # Determine content type
            content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{project_file.original_filename}"'
                return response
        else:
            messages.error(request, "File not found on server.")
            return redirect('Portal:project_file_manager', project_id=project.id)
    except Exception as e:
        messages.error(request, f"Error downloading file: {str(e)}")
        return redirect('Portal:project_file_manager', project_id=project.id)

# ===== NEW: FILE MANAGEMENT UTILITIES =====

@login_required
def update_file_settings(request, file_id):
    """Update file settings (category, priority, access level, description)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    project_file = get_object_or_404(ProjectFile, id=file_id)
    project = project_file.project
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'})
    
    # Only project owner can update file settings
    if project.leader != custom_user:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        # Update file settings safely
        if hasattr(project_file, 'category'):
            project_file.category = request.POST.get('category', project_file.category)
        if hasattr(project_file, 'priority'):
            project_file.priority = request.POST.get('priority', project_file.priority)
        
        project_file.access_level = request.POST.get('access_level', project_file.access_level)
        project_file.description = request.POST.get('description', project_file.description)
        project_file.save()
        
        return JsonResponse({
            'success': True,
            'message': 'File settings updated successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def delete_file(request, file_id):
    """Delete a project file"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    project_file = get_object_or_404(ProjectFile, id=file_id)
    project = project_file.project
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'})
    
    # Only project owner can delete files
    if project.leader != custom_user:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        filename = project_file.original_filename
        
        # Delete the actual file
        if project_file.file and os.path.exists(project_file.file.path):
            os.remove(project_file.file.path)
        
        # Delete the database record
        project_file.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'File "{filename}" deleted successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def bulk_update_files(request, project_id):
    """Bulk update multiple files' settings"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    project = get_object_or_404(Project, id=project_id)
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'})
    
    # Only project owner can bulk update
    if project.leader != custom_user:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        file_ids = request.POST.getlist('file_ids[]')
        category = request.POST.get('category')
        priority = request.POST.get('priority')
        access_level = request.POST.get('access_level')
        
        if not file_ids:
            return JsonResponse({'success': False, 'error': 'No files selected'})
        
        updated_count = 0
        with transaction.atomic():
            files = ProjectFile.objects.filter(id__in=file_ids, project=project)
            
            for file_obj in files:
                if category and hasattr(file_obj, 'category'):
                    file_obj.category = category
                if priority and hasattr(file_obj, 'priority'):
                    file_obj.priority = priority
                if access_level:
                    file_obj.access_level = access_level
                file_obj.save()
                updated_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully updated {updated_count} files'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ===== FREELANCER WORKSPACE SYSTEM (Enhanced) =====

@login_required
def freelancer_workspace(request):
    """Enhanced dashboard for freelancers showing their active projects"""
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        messages.error(request, "Profile not found. Please complete your profile.")
        return redirect('Portal:home')
    
    # Get projects where freelancer has access
    freelancer_accesses = FreelancerAccess.objects.filter(
        freelancer=custom_user
    ).select_related('project', 'bid').order_by('-created_at')
    
    # Get active projects with enhanced info
    active_projects = []
    for access in freelancer_accesses:
        if access.can_download_files or access.can_submit_work:
            # Check if payment exists and is completed
            payment_exists = Payment.objects.filter(
                project=access.project,
                freelancer=custom_user,
                status='completed'
            ).exists()
            
            # Get file access info
            total_files = access.project.files.count()
            accessible_files = access.project.files.filter(
                access_level='public'
            ).count() if not payment_exists else total_files
            
            active_projects.append({
                'access': access,
                'project': access.project,
                'bid': access.bid,
                'payment_completed': payment_exists,
                'total_files': total_files,
                'accessible_files': accessible_files,
                'submissions_count': access.project.submissions.filter(freelancer=custom_user).count()
            })
    
    return render(request, 'Portal/file_management/freelancer_workspace.html', {
        'active_projects': active_projects
    })

@login_required
def project_workspace(request, project_id):
    """Enhanced individual project workspace for freelancer"""
    project = get_object_or_404(Project, id=project_id)
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
        freelancer_access = FreelancerAccess.objects.get(
            project=project,
            freelancer=custom_user
        )
    except (CustomUser.DoesNotExist, FreelancerAccess.DoesNotExist):
        messages.error(request, "You don't have access to this project workspace.")
        return redirect('Portal:freelancer_workspace')
    
    # Check payment status
    payment = Payment.objects.filter(
        project=project,
        freelancer=custom_user,
        status='completed'
    ).first()
    
    # Get project files based on access level
    if payment:
        # Full access to all files
        project_files = project.files.all().order_by('-uploaded_at')
    else:
        # Only public files during bidding
        project_files = project.files.filter(access_level='public').order_by('-uploaded_at')
    
    my_submissions = project.submissions.filter(freelancer=custom_user).order_by('-created_at')
    
    # File statistics for freelancer
    file_stats = {
        'total_files': project.files.count(),
        'accessible_files': project_files.count(),
        'private_files': project.files.filter(access_level='private').count(),
        'public_files': project.files.filter(access_level='public').count(),
    }
    
    return render(request, 'Portal/file_management/project_workspace.html', {
        'project': project,
        'freelancer_access': freelancer_access,
        'project_files': project_files,
        'my_submissions': my_submissions,
        'payment': payment,
        'can_work': payment is not None,
        'file_stats': file_stats
    })

# ===== WORK SUBMISSION SYSTEM =====

@login_required
def submit_work(request, project_id):
    """Freelancer submits work for a project"""
    project = get_object_or_404(Project, id=project_id)
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
        freelancer_access = FreelancerAccess.objects.get(
            project=project,
            freelancer=custom_user,
            can_submit_work=True
        )
    except (CustomUser.DoesNotExist, FreelancerAccess.DoesNotExist):
        messages.error(request, "You don't have permission to submit work for this project.")
        return redirect('Portal:freelancer_workspace')
    
    # Check if payment is completed
    payment = Payment.objects.filter(
        project=project,
        freelancer=custom_user,
        status='completed'
    ).first()
    
    if not payment:
        messages.error(request, "Payment must be completed before you can submit work.")
        return redirect('Portal:project_workspace', project_id=project.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        uploaded_files = request.FILES.getlist('submission_files')
        
        if not title or not description:
            messages.error(request, "Please provide a title and description for your submission.")
            return redirect('Portal:submit_work', project_id=project.id)
        
        try:
            with transaction.atomic():
                # Create work submission
                submission = WorkSubmission.objects.create(
                    project=project,
                    freelancer=custom_user,
                    submission_title=title,
                    description=description,
                    status='submitted',
                    submitted_at=timezone.now()
                )
                
                # Add files to submission with enhanced info
                for uploaded_file in uploaded_files:
                    file_type = determine_file_type(uploaded_file)
                    SubmissionFile.objects.create(
                        submission=submission,
                        file=uploaded_file,
                        original_filename=uploaded_file.name,
                        file_type=file_type,
                        file_size=uploaded_file.size
                    )
                
                # Update project status
                project.project_status = 'submitted'
                project.save()
                
                messages.success(request, "Work submitted successfully!")
                return redirect('Portal:project_workspace', project_id=project.id)
                
        except Exception as e:
            messages.error(request, f"Error submitting work: {str(e)}")
    
    return render(request, 'Portal/file_management/submit_work.html', {
        'project': project,
        'freelancer_access': freelancer_access
    })

@login_required
def view_submission(request, submission_id):
    """View details of a work submission"""
    submission = get_object_or_404(WorkSubmission, id=submission_id)
    project = submission.project
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('Portal:home')
    
    # Check access permissions
    can_view = (
        project.leader == custom_user or  # Project owner
        submission.freelancer == custom_user  # Submission author
    )
    
    if not can_view:
        messages.error(request, "You don't have permission to view this submission.")
        return redirect('Portal:browse_projects')
    
    submission_files = submission.files.all()
    
    return render(request, 'Portal/file_management/view_submission.html', {
        'submission': submission,
        'submission_files': submission_files,
        'project': project,
        'is_owner': project.leader == custom_user
    })

@login_required
def download_submission_file(request, file_id):
    """Download a submission file"""
    submission_file = get_object_or_404(SubmissionFile, id=file_id)
    submission = submission_file.submission
    project = submission.project
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        raise Http404("Profile not found")
    
    # Check access permissions
    can_download = (
        project.leader == custom_user or  # Project owner
        submission.freelancer == custom_user  # Submission author
    )
    
    if not can_download:
        raise Http404("File not found or access denied")
    
    try:
        file_path = submission_file.file.path
        if os.path.exists(file_path):
            content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{submission_file.original_filename}"'
                return response
        else:
            messages.error(request, "File not found on server.")
            return redirect('Portal:view_submission', submission_id=submission.id)
    except Exception as e:
        messages.error(request, f"Error downloading file: {str(e)}")
        return redirect('Portal:view_submission', submission_id=submission.id)

# ===== ADMIN/CLIENT REVIEW SYSTEM =====

@login_required
def review_submission(request, submission_id):
    """Client reviews and approves/rejects freelancer submission"""
    submission = get_object_or_404(WorkSubmission, id=submission_id)
    project = submission.project
    
    try:
        custom_user = CustomUser.objects.get(user=request.user)
    except CustomUser.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('Portal:home')
    
    # Only project owner can review submissions
    if project.leader != custom_user:
        messages.error(request, "You can only review submissions for your own projects.")
        return redirect('Portal:browse_projects')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        feedback = request.POST.get('feedback', '')
        
        if action == 'approve':
            submission.status = 'approved'
            submission.client_feedback = feedback
            submission.reviewed_at = timezone.now()
            submission.is_final = True
            submission.save()
            
            # Update project status to completed
            project.project_status = 'completed'
            project.isCompleted = True
            project.save()
            
            messages.success(request, "Submission approved! Project marked as completed.")
            
        elif action == 'request_revision':
            submission.status = 'revision_requested'
            submission.client_feedback = feedback
            submission.revision_notes = request.POST.get('revision_notes', '')
            submission.reviewed_at = timezone.now()
            submission.save()
            
            # Update project status
            project.project_status = 'revision'
            project.save()
            
            messages.success(request, "Revision requested. Freelancer has been notified.")
        
        return redirect('Portal:view_submission', submission_id=submission.id)
    
    return render(request, 'Portal/file_management/review_submission.html', {
        'submission': submission,
        'project': project,
        'submission_files': submission.files.all()
    })