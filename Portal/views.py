import json
import logging
from django import forms
import requests
from django.contrib.auth import login, authenticate, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render, reverse, redirect
from django.views.decorators.csrf import csrf_exempt
from .models import *
from .utils import safe_cookie_value, get_cookie_value, safe_string_for_database  
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import timezone

from django.db import connection
from django.shortcuts import render, reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import login
from .models import User, CustomUser, Skill, UsersSkill, CommunicationLanguage, UsersCommunicationLanguage
from .models import Task, Project, Applicant, Contributor, ProjectSkillsRequired, ProjectBid

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from django.db.models import Q
from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from .models import Skill, CommunicationLanguage, CustomUser, UsersSkill, UsersCommunicationLanguage
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import transaction
from django.contrib import messages
from .models import Task, Project, Applicant, Contributor
import logging

import os

from django.core.mail import EmailMessage
from django.urls import reverse
import os

url =  'http://10.0.80.133:3000/oauth/getDetails'

clientSecret = "445b354949599afbcc454441543297a9a827b477dd3eb78d1cdd478f1482b5da08f9b6c3496e650783927e03b20e716483d5b9085143467804a5c6d40933282f"
from django.conf import settings
from django.core.mail import send_mail
logger = logging.getLogger(__name__)

def join_wait_list(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        
        logger.info(f'Received POST request with name: {name}, phone_number: {phone_number}, email: {email}')
        
        try:
            # Send email to user
            send_mail(
                'SwiftTalentForge: You have been added to the wait list',
                f'Dear {name},\n\nYou have been added to our wait list. We will keep you updated with further details.\nStay tuned!',
                settings.EMAIL_HOST_USER,  # Sender's email
                [email],  # Recipient list
                fail_silently=False,
            )
            logger.info(f'Email successfully sent to {email}')
            # Render the same form page with a success message
            return render(request, 'Portal:index', {'message': 'You have been added to the wait list!'})
        except Exception as e:
            logger.error(f'An error occurred while sending email: {e}')
            return render(request, 'Portal:index', {'message': f'An error occurred: {str(e)}'})

    # If not a POST request, render the form page normally
    return render(request, 'Portal:index')

# Create your views here.
def index(request):
    if not request.user.is_authenticated:
        return render(request, 'homepage.html')
    else:
        return HttpResponseRedirect(reverse('Portal:home'))

# Create your views here.
def services(request):
    if not request.user.is_authenticated:
        return render(request, 'Services.html')
    else:
        return render(request, 'Services.html')
    # Create your views here.
def get_started(request):
    if not request.user.is_authenticated:
        return render(request, 'docs.html')
    else:
        return render(request, 'docs.html')
# Create your views here.
def contactus(request):
        return render(request, 'Contactus.html')

@csrf_exempt
def check_username(request):
    data = json.loads(request.body.decode('utf-8'))
    username = data['username']
    try:
        user = User.objects.get(username=username)
        return HttpResponse(json.dumps(True), content_type='application/json')  # Username exists (taken)
    except User.DoesNotExist:
        return HttpResponse(json.dumps(False), content_type='application/json')  # Username doesn't exist (available)
    
@login_required
def accept_bid(request, bid_id):
    bid = get_object_or_404(ProjectBid, id=bid_id)
    project = bid.project
    
    # Check if user is project owner
    if request.user.customuser != project.leader:
        messages.error(request, "You can only accept bids for your own projects.")
        return redirect('Portal:project_detail', project_id=project.id)
    
    # Check if bid is already accepted
    if bid.status == 'accepted':
        messages.info(request, "This bid is already accepted.")
        return redirect('Portal:project_detail', project_id=project.id)
    
    # Reject all other bids for this project
    ProjectBid.objects.filter(project=project).update(status='rejected')
    
    # Accept this bid
    bid.status = 'accepted'
    bid.save()
    
    # Create or get conversation between client and freelancer
    from .models import Conversation, Message
    conversation, created = Conversation.objects.get_or_create(
        project=project,
        defaults={'is_archived': False}
    )
    
    # Add participants if conversation was created
    if created:
        conversation.participants.add(request.user, bid.freelancer.user)
        
        # Send a welcome message
        welcome_message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=f"Hello! I've accepted your bid for the project '{project.project_name}'. Let's discuss the project details and get started!",
            message_type='system'
        )
    
    # FIXED: Changed bid.applicant to bid.freelancer
    messages.success(request, f"Bid accepted! You can now proceed with payment to {bid.freelancer.user.get_full_name()}.")
    return redirect('Portal:project_detail', project_id=project.id)
 
@csrf_exempt
def check_email(request):
    data = json.loads(request.body.decode('utf-8'))
    email = data['email']
    if email.endswith('@iiits.in'):
        return HttpResponse(json.dumps(True), content_type='application/json')  # IIITS emails should login with iiits link
    try:
        User.objects.get(email=email)
        return HttpResponse(json.dumps(True), content_type='application/json')  # Email exists (taken)
    except User.DoesNotExist:
        return HttpResponse(json.dumps(False), content_type='application/json')  # Email doesn't exist (available)

@csrf_exempt
def open_close_project(request):
    data = json.loads(request.body.decode('utf-8'))
    tid = data["task_id"]
    current_state = data["current"]
    task = Task.objects.get(id=tid)
    task.isCompleted = not task.isCompleted
    task.save()
    return HttpResponse(str(task.isCompleted))

def send_simple_message(reciever,subject,text):
    print(">>",reciever)
    print(">>",subject)
    print(">>",text)
    fromaddr = "vurudi100@gmail.com"
    toaddr = reciever
    msg = MIMEMultipart() 

    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = subject
    body = text
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "SwiftTalentForge")
    text = msg.as_string()
    x=server.sendmail(fromaddr, toaddr, text)
    print(x,"sent mail")
    server.quit()

def send_signup_email(user_email, first_name, request):
    """Send welcome email to newly registered users with error handling and timeout."""
    try:
        # Define your platform name and support email
        platform_name = 'Swift Talent Forge'
        support_email = 'support@swiftgen.com'

        try:
            # Read email content from file
            with open(os.path.join('Portal/', 'welcome_email.txt'), 'r') as file:
                message_template = file.read()
        except FileNotFoundError:
            # Fallback message if template file is not found
            message_template = """
            Welcome to {platform_name}!
            
            Hi {first_name},
            
            Thank you for joining {platform_name}. Your account has been successfully created.
            
            Get started by visiting your dashboard: {dashboard_url}
            
            If you need assistance, contact us at {support_email}
            
            Best regards,
            The {platform_name} Team
            """

        # Create the dashboard link
        dashboard_url = request.build_absolute_uri(reverse('Portal:home'))

        # Personalize the email content
        message = message_template.format(
            first_name=first_name,
            platform_name=platform_name,
            support_email=support_email,
            dashboard_url=dashboard_url
        )

        # Define the email subject
        subject = f'Account Creation Success on {platform_name}'

        # Create the email message
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=[user_email]
        )

        try:
            # Attach an image
            image_path = os.path.join('static/assets/img/', 'DER.jpeg')
            with open(image_path, 'rb') as image:
                email.attach('your_image.png', image.read(), 'image/png')
        except FileNotFoundError:
            # Log warning if image not found but continue sending email
            print(f"Warning: Welcome email image not found at {image_path}")

        # Send the email with timeout
        email.send(fail_silently=False, timeout=5)
        return True

    except Exception as e:
        # Log the error but don't stop the signup process
        print(f"Failed to send welcome email to {user_email}: {str(e)}")
        return False

def signup_user(request):
    """Handle user registration with proper validation and error handling."""
    context = dict()
    skill_list = Skill.objects.all()
    language_list = CommunicationLanguage.objects.all()
    context['skill_list'] = skill_list
    context['language_list'] = language_list

    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = ['name', 'fname', 'lname', 'email', 'passwd1', 'phno', 'bio', 'batch', 'gender']
            for field in required_fields:
                if not request.POST.get(field):
                    raise ValueError(f"{field.replace('_', ' ').title()} is required")

            # Get form data
            username = request.POST['name']
            first_name = request.POST['fname']
            last_name = request.POST['lname']
            email = request.POST['email']
            password1 = request.POST['passwd1']
            phone_number = request.POST['phno']
            bio = request.POST['bio']
            batchYear = request.POST['batch']
            gender = request.POST['gender']

            # Validate image
            if 'image' not in request.FILES:
                raise ValueError("Profile image is required")
            image = request.FILES['image']

            # Validate skills and languages
            skills = request.POST.getlist('skills[]')
            languages = request.POST.getlist('languages[]')
            if not skills:
                raise ValueError("Please select at least one skill")
            if not languages:
                raise ValueError("Please select at least one language")

            # Check if username or email already exists
            if User.objects.filter(username=username).exists():
                raise ValueError("Username already exists")
            if User.objects.filter(email=email).exists():
                raise ValueError("Email already exists")

            # Create the User object with transaction
            with transaction.atomic():
                # Create User
                user = User.objects.create_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=password1
                )

                # Create CustomUser
                cuser = CustomUser(
                    user=user,
                    phone_number=phone_number,
                    image=image,
                    bio=bio,
                    batchYear=batchYear,
                    gender=gender
                )
                cuser.save()

                # Save user skills
                for uskill in skills:
                    skill = Skill.objects.get(skill_name=uskill)
                    proficiency = request.POST.get(skill.skill_name)
                    if not proficiency:
                        raise ValueError(f"Proficiency level required for {skill.skill_name}")
                    UsersSkill.objects.create(
                        skill=skill,
                        user=cuser,
                        level_of_proficiency=int(proficiency)
                    )

                # Save user languages
                for ulanguage in languages:
                    language = CommunicationLanguage.objects.get(language_name=ulanguage)
                    fluency = request.POST.get(language.language_name)
                    if not fluency:
                        raise ValueError(f"Fluency level required for {language.language_name}")
                    UsersCommunicationLanguage.objects.create(
                        language=language,
                        user=cuser,
                        level_of_fluency=int(fluency)
                    )

            # Log the user in
            login(request, user)

            # Try to send welcome email
            try:
                send_signup_email(email, first_name, request)
            except Exception as e:
                logger.error(f"Failed to send welcome email to {email}: {str(e)}")
                messages.warning(request, "Account created successfully, but welcome email could not be sent.")
            else:
                messages.success(request, f"Welcome {first_name}! Your account has been created successfully.")

            return HttpResponseRedirect(reverse("Portal:home"))

        except ValueError as e:
            messages.error(request, str(e))
            context['error_message'] = str(e)
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            messages.error(request, "An error occurred during signup. Please try again.")
            context['error_message'] = "An unexpected error occurred. Please try again."

        # If there was an error, return to signup page with context
        return render(request, 'signup.html', context)

    # GET request
    return render(request, 'signup.html', context)

def recommended_jobs(cuser):
    jobs_recommended = list()
    users_skill_obj_list = UsersSkill.objects.filter(user=cuser)
    skills_list = set([obj.skill for obj in users_skill_obj_list])
    users_languages_obj_list = UsersCommunicationLanguage.objects.filter(
        user=cuser)
    languages_list = set([obj.language for obj in users_languages_obj_list])
    jobs = applicable_jobs(cuser)
    if jobs:
        for job in jobs:
            taskskreq_obj_list = TaskSkillsRequired.objects.filter(task=job)
            job_req_skills = set([obj.skill for obj in taskskreq_obj_list])
            tasklgreq_obj_list = TaskLanguagesRequired.objects.filter(task=job)
            job_req_languages = set(
                [obj.language for obj in tasklgreq_obj_list])
            common_job_skill = skills_list.intersection(job_req_skills)
            common_job_language = languages_list.intersection(
                job_req_languages)
            if len(common_job_skill) > 0 and len(common_job_language) > 0:
                jobs_recommended.append(job)
    return jobs_recommended

def home(request):
    if not request.user.is_superuser and request.user.is_authenticated:
        context = dict()
        cuser = CustomUser.objects.get(user=request.user)
        jobs_recommended = recommended_jobs(cuser)
        posted_projects = Project.objects.filter(
            leader=cuser).order_by('-postedOn')
        if len(posted_projects) == 0:
            context['current_posted_project'] = None
            context['current_added_task'] = None
            context['percentCompleted'] = None
        else:
            current_posted_project = posted_projects[0]
            context['current_posted_project'] = current_posted_project
            total_tasks = float(
                len(Task.objects.filter(project=current_posted_project)))
            completed_tasks = float(len(Task.objects.filter(
                project=current_posted_project, isCompleted=True)))
            if total_tasks == 0 or completed_tasks == 0:
                percentCompleted = 0
            else:
                percentCompleted = int((completed_tasks / total_tasks) * 100)
                if percentCompleted != 100:
                    percentCompleted = int(round(percentCompleted / 10)) * 10
            current_posted_project_tasks = Task.objects.filter(
                project=current_posted_project).order_by('-addedOn')
            if len(current_posted_project_tasks) == 0:
                context['current_added_task'] = None
            else:
                current_added_task = current_posted_project_tasks[0]
                context['current_added_task'] = current_added_task
            context['percentCompleted'] = percentCompleted
        task_obj_list = Contributor.objects.filter(user=cuser)
        if len(task_obj_list) == 0:
            context['current_working_task'] = None
        else:
            working_task_list = [obj.task for obj in task_obj_list if obj.task.isCompleted is False]
            if working_task_list:
                current_working_task = sorted(working_task_list, key=lambda x: x.addedOn, reverse=True)[0]
                context['current_working_task'] = current_working_task
        context['jobs_recommended'] = jobs_recommended
        return render(request, 'dashboard.html', context)
    elif request.user.is_superuser:
        return HttpResponseRedirect(reverse('Portal:admin'))
    else:
        return HttpResponseRedirect(reverse('Portal:index'))

def auth_callback_token(request, token):
    payload = {
        'token': token,
        'secret': clientSecret
    }
    response = requests.post(url, payload)
    content = json.loads(response.content.decode('utf-8'))
    student = content['student'][0]
    email = student['Student_Email']
    try:
        user = User.objects.get(email=email)
        login(request, user)
        if request.COOKIES.get('post_project'):
            print(request.COOKIES.get('post_project'))
            return form_state(request, 2)
        return redirect('Portal:home')
    except User.DoesNotExist:
        context = dict()
        context['student'] = student
        skill_list = Skill.objects.all()
        language_list = CommunicationLanguage.objects.all()
        context['skill_list'] = skill_list
        context['language_list'] = language_list
    return render(request, 'signup.html', context)
    
logger = logging.getLogger(__name__)

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

def login_user(request):
    """Handle user login with proper validation and feedback."""
    context = {}
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                # Attempt to authenticate user
                logger.debug(f"Attempting to authenticate user: {username}")
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    # Successful login
                    logger.debug(f"Authentication successful for user: {username}")
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.first_name}!")
                    
                    # Check if there's a pending project post
                    if request.COOKIES.get('post_project'):
                        logger.debug("Redirecting to form state with id=2")
                        return form_state(request, id=2)
                    else:
                        logger.debug("Redirecting to home")
                        return HttpResponseRedirect(reverse('Portal:home'))
                else:
                    # Failed login
                    logger.warning(f"Authentication failed for user: {username}")
                    messages.error(request, 'Invalid username or password.')
                    context['error_message'] = 'Username or password is incorrect'
                    
                    if request.COOKIES.get('post_project'):
                        context['post_project'] = 'post_project'
            
            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Login error for user {username}: {str(e)}")
                messages.error(request, 'An error occurred during login. Please try again.')
                context['error_message'] = 'An unexpected error occurred'
        
        else:
            # Form validation failed
            logger.warning("Login form is invalid")
            messages.error(request, 'Please correct the form errors.')
            context['error_message'] = 'Invalid form submission'
    
    else:
        # GET request - show empty form
        form = LoginForm()

    # Add form to context and render
    context['form'] = form
    return render(request, 'login.html', context)

def logout_user(request):
    logout(request)
    return HttpResponseRedirect(reverse('Portal:index'))

def applicable_jobs(cuser):
    '''
    Use this function when using sqlclient database
    '''
    if not cuser:
        projects = Project.objects.all()
    else:
        projects = Project.objects.exclude(leader=cuser)

    jobs = set()
    if projects:
        for project in projects:
            if not project.isCompleted:
                tasks = Task.objects.filter(
                        project=project, isCompleted=False)
                for task in tasks:
                    if task.contributor_set.count() == 0:
                        jobs.add(task)
    if jobs:
        print(jobs)
        sorted(jobs, key=lambda x: x.addedOn, reverse=True)
    return jobs

@csrf_exempt
def jobs_update(request):
    data = json.loads(request.body.decode('utf-8'))
    skills = data['skills']
    languages = data['languages']
    credits = data['credits']
    context = dict()
    cuser = None
    if request.user.is_authenticated:
        cuser = CustomUser.objects.get(user=request.user)
    jobs = applicable_jobs(cuser)
    # else:
    #     jobs = Task.objects.filter(isCompleted=False).order_by('-addedOn')
    filtered_tasks = set()
    filtered_tasks_skills = set()
    filtered_tasks_languages = set()
    filtered_tasks_credits = set()
    skills_len = len(skills)
    languages_len = len(languages)
    if len(skills) == 0 and len(languages) == 0:
        if not credits == "Both":
            filtered_tasks = [job for job in jobs if job.credits == credits]
            jobs = filtered_tasks
    else:
        for task in jobs:
            if skills_len > 0:
                taskskreq = TaskSkillsRequired.objects.filter(task=task)
                skill_list = [Skill.objects.get(
                    id=obj.skill.id) for obj in taskskreq]
                skill_list = [obj.skill_name for obj in skill_list]
                flag_skills = sum([skill in skills for skill in skill_list])
                if flag_skills > 0:
                    filtered_tasks_skills.add(task)
            if languages_len > 0:
                tasklgreq = TaskLanguagesRequired.objects.filter(task=task)
                language_list = [CommunicationLanguage.objects.get(
                    id=obj.language.id) for obj in tasklgreq]
                language_list = [obj.language_name for obj in language_list]
                flag_languages = sum(
                    [language in languages for language in language_list])
                if flag_languages > 0:
                    filtered_tasks_languages.add(task)
            if task.credits == credits:
                filtered_tasks_credits.add(task)

        if credits == "Both":
            if skills_len > 0 and languages_len > 0:
                filtered_tasks = filtered_tasks_skills.intersection(
                    filtered_tasks_languages)
            elif skills_len > 0:
                filtered_tasks = filtered_tasks_skills
            else:
                filtered_tasks = filtered_tasks_languages
        else:
            if skills_len > 0 and languages_len > 0:
                filtered_tasks = filtered_tasks_skills.intersection(
                    filtered_tasks_languages, filtered_tasks_credits)
            elif skills_len > 0:
                filtered_tasks = filtered_tasks_skills.intersection(filtered_tasks_credits)
            else:
                filtered_tasks = filtered_tasks_languages.intersection(filtered_tasks_credits)
        jobs = filtered_tasks
    print(filtered_tasks_skills, filtered_tasks_languages, filtered_tasks_credits)
    context['jobs'] = jobs
    print(jobs)
    return render(request, 'jobs.html', context)

def browse_jobs(request):
    """Enhanced project browsing with Upwork-style features"""
    context = dict()
    cuser = None
    if request.user.is_authenticated:
        cuser = CustomUser.objects.get(user=request.user)
    
    # Get all active projects (excluding user's own projects)
    if cuser:
        projects = Project.objects.filter(isCompleted=False).exclude(leader=cuser).order_by('-postedOn')
    else:
        projects = Project.objects.filter(isCompleted=False).order_by('-postedOn')
    
    # Add additional context for each project
    for project in projects:
        # Check if ProjectSkillsRequired model exists, if not skip
        try:
            project.skills_required = ProjectSkillsRequired.objects.filter(project=project)
        except:
            project.skills_required = []
        project.time_posted = project.postedOn
        project.days_ago = (timezone.now() - project.postedOn).days
        
    context['projects'] = projects
    context['skill_list'] = Skill.objects.all()
    
    return render(request, 'browsejobs.html', context)

def form_state(request, id=1):
    """Unicode-safe form state handling with proper cookie encoding"""
    context = dict()
    if id == 1:
        # Get form data and clean it for safe storage
        project_name = safe_string_for_database(request.POST['name'])
        description = safe_string_for_database(request.POST['desc'])
        deadline = request.POST['deadline']
        
        context['post_project'] = 'post_project'
        response = render(request, 'login.html', context)
        
        # Set cookies with Unicode-safe encoding
        response.set_cookie('post_project', 'post_project')
        response.set_cookie('name', safe_cookie_value(project_name))
        response.set_cookie('desc', safe_cookie_value(description))
        response.set_cookie('deadline', safe_cookie_value(deadline))
        
        return response
    else:
        # Retrieve and decode cookie values safely
        context['name'] = get_cookie_value(request, 'name')
        context['desc'] = get_cookie_value(request, 'desc')
        context['deadline'] = get_cookie_value(request, 'deadline')
        context['post_project'] = 'post_project'
        
        response = render(request, 'postproject.html', context)
        
        # Clean up cookies
        response.delete_cookie('post_project')
        response.delete_cookie('name')
        response.delete_cookie('desc')
        response.delete_cookie('deadline')
        
        return response

def post_project(request):
    """Enhanced project posting with budget and requirements - Unicode safe"""
    if request.method == 'POST':
        if request.user.is_authenticated:
            try:
                # Get and clean form data
                project_name = safe_string_for_database(request.POST['name'])
                description = safe_string_for_database(request.POST['desc'])
                deadline = request.POST['deadline']
                
                project = Project()
                project.project_name = project_name
                project.description = description
                project.deadline = deadline
                
                # Add the new fields with defaults if not provided
                project.budget_min = request.POST.get('budget_min', 0)
                project.budget_max = request.POST.get('budget_max', 0)
                project.project_type = request.POST.get('project_type', 'Fixed')
                project.experience_level = request.POST.get('experience_level', 'Intermediate')
                project.project_duration = request.POST.get('project_duration', '1 to 3 months')
                project.leader = CustomUser.objects.get(user=request.user.id)
                project.postedOn = timezone.now()
                project.save()
                
                # Handle skills if provided - FIXED VERSION
                skills = request.POST.getlist('skills[]')  # Changed from 'skills_required'
                for skill_name in skills:
                    try:
                        skill = Skill.objects.get(skill_name=skill_name)  # Use skill_name instead of id
                        ProjectSkillsRequired.objects.create(project=project, skill=skill)
                    except Skill.DoesNotExist:
                        logger.warning(f"Skill not found: {skill_name}")
                        pass
                
                messages.success(request, f'Project "{project_name}" has been posted successfully!')
                return redirect('Portal:project_description', project.id)
                
            except Exception as e:
                messages.error(request, f'Error posting project: {str(e)}')
                logger.error(f"Project posting error: {str(e)}")
        else:
            return form_state(request)
    
    # For GET request, provide context for the form
    context = dict()
    context['skill_list'] = Skill.objects.all()  # Changed from 'available_skills'
    context['selected_skills'] = []
    return render(request, "postproject.html", context)

def browse_projects(request):
    """Enhanced project browsing with Upwork-style features"""
    context = dict()
    
    # Get all projects
    projects = Project.objects.all().order_by('-postedOn')
    
    # Add skills to each project
    for project in projects:
        project.skills_required = ProjectSkillsRequired.objects.filter(project=project)
    
    # Calculate statistics
    active_projects = projects.filter(isCompleted=False)
    total_budget = sum(project.budget_max for project in projects if project.budget_max)
    
    context['projects'] = projects
    context['active_projects'] = active_projects
    context['total_budget'] = total_budget
    
    # Add search and filter functionality
    search_query = request.GET.get('search', '')
    experience_level = request.GET.get('experience', '')
    project_type = request.GET.get('type', '')
    duration = request.GET.get('duration', '')
    
    if search_query:
        projects = projects.filter(
            Q(project_name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if experience_level:
        projects = projects.filter(experience_level=experience_level)
    
    if project_type:
        projects = projects.filter(project_type=project_type)
    
    if duration:
        projects = projects.filter(project_duration=duration)
    
    context['filtered_projects'] = projects
    context['search_query'] = search_query
    context['selected_experience'] = experience_level
    context['selected_type'] = project_type
    context['selected_duration'] = duration
    
    return render(request, 'browse_projects.html', context)

def project_detail(request, project_id):
    """Detailed project view with bidding functionality"""
    project = get_object_or_404(Project, id=project_id)
    context = dict()
    
    context['project'] = project
    context['skills_required'] = ProjectSkillsRequired.objects.filter(project=project)
    context['bids'] = ProjectBid.objects.filter(project=project).order_by('-submitted_on')
    context['bids_count'] = context['bids'].count()
    
    # Get conversation for this project if it exists
    context['conversation'] = None
    if request.user.is_authenticated:
        try:
            from .models import Conversation
            conversation = Conversation.objects.filter(
                project=project, 
                participants=request.user
            ).first()
            context['conversation'] = conversation
        except:
            pass
    
    if request.user.is_authenticated:
        cuser = CustomUser.objects.get(user=request.user)
        context['is_owner'] = (project.leader == cuser)
        context['has_bid'] = ProjectBid.objects.filter(project=project, freelancer=cuser).exists()
        
        if request.method == 'POST' and not context['is_owner'] and not context['has_bid']:
            # Handle bid submission
            bid_amount = request.POST.get('bid_amount')
            delivery_time = request.POST.get('delivery_time')
            cover_letter = request.POST.get('cover_letter')
            
            if bid_amount and delivery_time and cover_letter:
                ProjectBid.objects.create(
                    project=project,
                    freelancer=cuser,
                    bid_amount=bid_amount,
                    delivery_time=delivery_time,
                    cover_letter=cover_letter
                )
                # Update proposals count
                project.proposals_count += 1
                project.save()
                
                messages.success(request, 'Your proposal has been submitted successfully!')
                return redirect('Portal:project_detail', project_id=project_id)
    
    return render(request, 'project_detail.html', context)

def post_project_enhanced(request):
    """Enhanced project posting with budget and requirements"""
    if request.method == 'POST':
        if request.user.is_authenticated:
            project = Project()
            project.project_name = request.POST['name']
            project.description = request.POST['desc']
            project.deadline = request.POST['deadline']
            project.budget_min = request.POST.get('budget_min', 0)
            project.budget_max = request.POST.get('budget_max', 0)
            project.project_type = request.POST.get('project_type', 'Fixed')
            project.experience_level = request.POST.get('experience_level', 'Intermediate')
            project.project_duration = request.POST.get('project_duration', '1 to 3 months')
            project.leader = CustomUser.objects.get(user=request.user.id)
            project.postedOn = timezone.now()
            project.save()
            
            # Handle skills
            skills = request.POST.getlist('skills[]')
            for skill_name in skills:
                skill = Skill.objects.get(skill_name=skill_name)
                ProjectSkillsRequired.objects.create(project=project, skill=skill)
            
            return redirect('Portal:project_detail', project_id=project.id)
        else:
            return redirect('Portal:login')
    
    context = dict()
    context['skill_list'] = Skill.objects.all()
    return render(request, "post_project_enhanced.html", context)

def project_description(request, project_id):
    project = Project.objects.get(id=project_id)
    if not project.isCompleted:
        if project.deadline < datetime.now().date():
            project.isCompleted = True
            project.save()
    
    added_tasks = Task.objects.filter(project=project.id)
    context = dict()
    context['project'] = project
    context['added_tasks'] = added_tasks
    context['skills_required'] = ProjectSkillsRequired.objects.filter(project=project)
    
    # Add bidding context
    context['bids'] = ProjectBid.objects.filter(project=project).order_by('-submitted_on')
    context['bids_count'] = context['bids'].count()
    
    year = project.deadline.strftime("%Y")
    month = project.deadline.strftime("%m")
    date = project.deadline.strftime("%d")
    context['year'] = year
    context['month'] = month
    context['date'] = date
    
    if request.user.is_authenticated:
        cuser = CustomUser.objects.get(user=request.user)
        context['is_leader'] = (project.leader.user == request.user)
        context['is_owner'] = (project.leader == cuser)
        context['has_bid'] = ProjectBid.objects.filter(project=project, freelancer=cuser).exists()
    
    # Use the project_detail template instead of projectdescription.html
    return render(request, 'project_detail.html', context)

def add_task(request, project_id):
    context = {}
    if request.method == 'POST':
        if request.user.is_authenticated:
            task = Task()
            task.task_name = request.POST['name']
            task.task_description = request.POST['desc']
            task.credits = request.POST['credits']
            if(task.credits=="Other"):
                task.mention = request.POST['mention']
            elif(task.credits=="Paid"):
                task.amount = int(request.POST['amount'])
            task.deadline = request.POST['deadline']
            skills = request.POST.getlist('skills[]')
            languages = request.POST.getlist('languages[]')
            task.project = Project.objects.get(id=project_id)
            task.save()
            project = Project.objects.get(id=task.project.id)
            project.task_count += 1
            project.save()
            for rskill in skills:
                skill = Skill.objects.get(skill_name=rskill)
                task_skill_req = TaskSkillsRequired()
                task_skill_req.task = task
                task_skill_req.skill = skill
                task_skill_req.proficiency_level_required = int(
                    request.POST[skill.skill_name])
                task_skill_req.save()
            for rlanguage in languages:
                language = CommunicationLanguage.objects.get(
                    language_name=rlanguage)
                task_language_req = TaskLanguagesRequired()
                task_language_req.task = task
                task_language_req.language = language
                task_language_req.fluency_level_required = int(
                    request.POST[language.language_name])
                task_language_req.save()
            return redirect('Portal:task_description',project_id ,task.id)
        return render(request, 'login.html')
    project = Project.objects.get(id=project_id)
    year = project.deadline.strftime("%Y")
    month = project.deadline.strftime("%m")
    date = project.deadline.strftime("%d")
    context['year'] = year
    context['month'] = month
    context['date'] = date
    context['project_id'] = project_id
    skill_list = Skill.objects.all()
    language_list = CommunicationLanguage.objects.all()
    context['skill_list'] = skill_list
    context['language_list'] = language_list
    return render(request, "addtask.html", context)

def submit_task(request, task):
    submit_url = request.POST.get("work_link",None)
    if(submit_url!=None):
        if (not task.isCompleted):
            task.task_link = submit_url
            task.save()

def status_update(request, task):
    if request.POST["status_update"] == "open":
        task.isCompleted = False
    elif request.POST["status_update"] == "close":
        task.isCompleted = True
    else:
        print("some error in task_description")
    task.save()

def apply_for_task(request, task):
    applicant = Applicant()
    applicant.task = Task.objects.get(id=task.id)
    applicant.user = CustomUser.objects.get(user=request.user.id)
    applicant.save()

def submit_task_review(request, task):
    print("We will accept/reject the students work here")

def user_task_rating(request,task):
    task.rating=request.POST.get("rating",None)
    task.save()

def user_user_rating(request,task,context):
    try:
        uurating=UserRating.objects.get(task=task)
    except:
        uurating=UserRating()
    uurating.task=task
    uurating.fre=Contributor.objects.get(task=task).user
    uurating.emp=task.project.leader
    if(context["is_contributor"]):
        uurating.e_rating=request.POST.get("rating",None)
    elif(context["is_leader"]):
        uurating.f_rating=request.POST.get("rating",None)
    uurating.save()

def select_user(request, task, context):
    user_id = request.POST["user_id"]
    is_applicant = False
    print(user_id)
    for i in context['applicants']:
        if i.user.user.id == int(user_id):
            is_applicant = True
    if is_applicant:
        if task.contributor_set.count() == 0:
            contributor = Contributor()
            contributor.user = CustomUser.objects.get(user=int(user_id))
            contributor.task = Task.objects.get(id=task.id)
            contributor.save()
            send_simple_message(str(contributor.user.user.email),"Selection for the Task"+str(),"You have been selected for the task "+str(contributor.task.task_name)+" of project "+str(contributor.task.project.project_name)+"\n\n -"+str(contributor.task.project.leader.user.username)) 
            for i in context['applicants']:
                if i.user!=contributor.user:
                    send_simple_message(str(i.user.user.email),"Non-Selection for the Task"+str(),"You have not been selected for the task "+str(contributor.task.task_name)+" of project "+str(contributor.task.project.project_name)+"\n\n -"+str(contributor.task.project.leader.user.username))
        else:
            print("we already have a contributor")
    else:
        print("Not an applicant")

def applicants(request, task_id):
    task = Task.objects.get(id=task_id)
    if (not request.user.is_authenticated or (request.user != task.project.leader.user)):
        return redirect("Portal:task_description", task.project.id, task_id)
    context = dict()
    context['task'] = task
    context['is_leader'] = (task.project.leader.user == request.user)
    context['applicants'] = task.applicant_set.all().order_by("-time_of_application")
    context['has_contributor'] = (task.contributor_set.count() > 0)
    if (context['has_contributor']):
        context['contributor'] = task.contributor_set.get()
    if request.method == 'POST':
        if request.user.is_authenticated and request.POST[
                "work"] == "select" and request.user == task.project.leader.user:
            select_user(request, task, context)
        return redirect("Portal:applicants", task_id)
    return render(request, "applicants.html", context)

def task_description(request, project_id, task_id):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)

    # Check and update task completion status
    if not task.isCompleted and task.deadline < timezone.now().date():
        task.isCompleted = True
        task.save()

    context = {
        'year': task.deadline.strftime("%Y"),
        'month': task.deadline.strftime("%m"),
        'date': task.deadline.strftime("%d"),
        'task': task,
        'is_leader': task.project.leader.user == request.user,
        'applicants': task.applicant_set.all(),
        'is_contributor': False,
        'submit_link': task.task_link,
        'skills_required': task.taskskillsrequired_set.all(),
        'languages_required': task.tasklanguagesrequired_set.all(),
        'task_rating': task.rating,
        'has_applied': task.applicant_set.filter(user__user=request.user).exists()
    }

    # Get conversation for this project if it exists
    context['conversation'] = None
    if request.user.is_authenticated:
        try:
            from .models import Conversation
            conversation = Conversation.objects.filter(
                project=task.project, 
                participants=request.user
            ).first()
            context['conversation'] = conversation
        except:
            pass

    try:
        contributor = task.contributor_set.get()
        context['contributor'] = contributor
        context['is_contributor'] = contributor.user.user == request.user
    except Contributor.DoesNotExist:
        context['contributor'] = None

    if request.method == 'POST' and request.user.is_authenticated:
        work_type = request.POST.get("work")
        if work_type == "submit_task":
            submit_task(request, task)
        elif work_type == "status_update":
            status_update(request, task)
        elif work_type == "apply" and not context['has_applied']:
            apply_for_task(request, task)
        elif work_type == "user_task_rating":
            user_task_rating(request, task)
        elif work_type == "user_user_rating":
            user_user_rating(request, task, context)
        elif work_type == "start_working":
            start_end_working(request, task)
        return redirect("Portal:task_description", project_id, task_id)

    return render(request, 'taskdescription.html', context)

def start_end_working(request, task):
    pass

def admin(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    else:
        context = dict()
        if request.user.is_superuser:
            no_of_users = len(User.objects.filter(is_superuser=False))
            tasks = Task.objects.filter(isCompleted=False)
            context['no_of_users'] = no_of_users
            context['no_of_jobs'] = len(tasks)  # Fixed this line
            print(context['no_of_jobs'])
            return render(request, 'admindashboard.html', context)
        return HttpResponse('<center><h1>You are not admin.</h1></center>')

def user_profile(request, username):
    context = dict()
    user = User.objects.get(username=username)
    cuser = CustomUser.objects.get(user=user)
    context['cuser'] = cuser
    if request.user.is_authenticated:
        if request.method == "POST":
            bio = request.POST['bio']
            cuser.bio = bio
            if request.FILES.get('image', None) is not None:
                image = request.FILES['image']
                cuser.image = image
            cuser.save()
            skills = request.POST.getlist('skills[]')
            languages = request.POST.getlist('languages[]')
            UsersSkill.objects.filter(user=cuser).all().delete()
            UsersCommunicationLanguage.objects.filter(
                user=cuser).all().delete()
            for skill in skills:
                skillreq = Skill.objects.get(skill_name=skill)
                uskill = UsersSkill(skill=skillreq, user=cuser,
                                    level_of_proficiency=int(request.POST[skill]))
                uskill.save()
            for language in languages:
                languagereq = CommunicationLanguage.objects.get(
                    language_name=language)
                ulanguage = UsersCommunicationLanguage(language=languagereq, user=cuser,
                                                       level_of_fluency=int(request.POST[language]))
                ulanguage.save()
            return HttpResponseRedirect(reverse('Portal:profile', args=(username,)))
    skills = UsersSkill.objects.filter(user=cuser)
    languages = UsersCommunicationLanguage.objects.filter(user=cuser)
    context['uskills'] = [obj.skill.skill_name for obj in skills]
    context['ulanguages'] = [
        obj.language.language_name for obj in languages]
    skill_list = Skill.objects.all()
    language_list = CommunicationLanguage.objects.all()
    context['skill_list'] = skill_list
    context['language_list'] = language_list
    context['erating'], context['frating'] = give_rating(cuser)
    return render(request, 'profile.html', context)

def usetochatname(request, username):
    context = dict()
    user = User.objects.get(username=username)
    cuser = CustomUser.objects.get(user=user)
    user_name=username
    return user_name

def give_rating(cuser):
    etasks = cuser.rating_by.all()
    ftasks = cuser.rating_to.all()
    elist = [task.e_rating for task in etasks]
    flist = [task.f_rating for task in ftasks]
    erating = None 
    frating = None
    if len(elist)>0:
        erating = int(round(sum(elist)/len(elist)))
        erating = [[1] * erating, [1] * (5 - erating)]
    if len(flist)>0:
        frating = int(round(sum(flist)/len(flist)))
        frating = [[1] * frating, [1] * (5 - frating)]
    return erating, frating

def myprojects(request):
    if request.user.is_authenticated:
        context={}
        cuser=CustomUser.objects.get(user=request.user)
        posted_tasks = [j for i in cuser.project_set.all() for j in i.task_set.all()]
        contributor_tasks=[i.task for i in cuser.contributor_set.all()]
        context['current_projects']=[i for i in cuser.project_set.all() if i.task_set.count()==0]
        context['completed']=[i for i in posted_tasks if i.isCompleted==True]+[i for i in contributor_tasks if i.isCompleted==True]
        context['active']=[i for i in posted_tasks if i.isCompleted==False]+[i for i in contributor_tasks if i.isCompleted==False]
        return render(request, 'myprojects.html',context)
    return render(request, 'login.html')

def task_editfunction(request, project_id, task_id):
    if request.user.is_authenticated:
        task = Task.objects.get(id=task_id, project=project_id)
        project = Project.objects.get(id=project_id)
        context = {}
        context['task'] = task
        context['project'] = project
        if request.method == 'POST':
            task.task_name = request.POST['name']
            task.task_description = request.POST['description']
            task.credits = request.POST['credits']
            if task.credits == 'Paid':
                task.amount = int(request.POST['amount'])
            else:    
                task.mention = request.POST['mention']
            task.deadline = request.POST['deadline']
            task.save()
            return redirect("Portal:task_description", project_id, task_id)
        project = Project.objects.get(id=project_id)
        year = project.deadline.strftime("%Y")
        month = project.deadline.strftime("%m")
        date = project.deadline.strftime("%d")
        context['year'] = year
        context['month'] = month
        context['date'] = date
        return render(request,'edittask.html',context)
    return redirect("Portal:task_description", project_id, task_id)