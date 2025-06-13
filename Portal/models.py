from django.apps import AppConfig
from django.db import models
from django.contrib.auth.models import User
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
        os.remove(self.image.path)
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
        return self.project_name  # Fixed: was project_name2

# ADD THE MISSING TASK MODEL
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

# NEW MODEL: Project Bids/Proposals
class ProjectBid(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bids')
    freelancer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time = models.IntegerField(help_text="Delivery time in days")
    cover_letter = models.TextField(max_length=1000)
    submitted_on = models.DateTimeField(auto_now_add=True)
    is_selected = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('project', 'freelancer')
    
    def __str__(self):
        return f"{self.freelancer.user.username} - {self.project.project_name}"

# NEW MODEL: Project Skills Required  
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
    emp = models.ForeignKey(CustomUser, related_name='rating_by', on_delete=models.CASCADE, null=True, blank=True)  # Added null=True, blank=True
    fre = models.ForeignKey(CustomUser, related_name='rating_to', on_delete=models.CASCADE, null=True, blank=True)  # Added null=True, blank=True
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