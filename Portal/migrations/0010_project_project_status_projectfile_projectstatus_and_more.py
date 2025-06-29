# Generated by Django 5.1.3 on 2025-06-26 09:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Portal', '0009_payment_payment_method_payment_paypal_order_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='project_status',
            field=models.CharField(choices=[('posted', 'Posted'), ('bidding', 'Receiving Bids'), ('hired', 'Freelancer Hired'), ('in_progress', 'Work in Progress'), ('submitted', 'Work Submitted'), ('revision', 'Revision Requested'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='posted', max_length=20),
        ),
        migrations.CreateModel(
            name='ProjectFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='project_files/')),
                ('original_filename', models.CharField(max_length=255)),
                ('file_type', models.CharField(max_length=50)),
                ('file_size', models.BigIntegerField()),
                ('description', models.TextField(blank=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('is_requirement', models.BooleanField(default=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='Portal.project')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Portal.customuser')),
            ],
        ),
        migrations.CreateModel(
            name='ProjectStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('posted', 'Posted'), ('bidding', 'Receiving Bids'), ('hired', 'Freelancer Hired'), ('in_progress', 'Work in Progress'), ('submitted', 'Work Submitted'), ('revision', 'Revision Requested'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_updates', to='Portal.project')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Portal.customuser')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WorkSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('revision_requested', 'Revision Requested'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('client_feedback', models.TextField(blank=True)),
                ('revision_notes', models.TextField(blank=True)),
                ('version_number', models.IntegerField(default=1)),
                ('is_final', models.BooleanField(default=False)),
                ('freelancer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Portal.customuser')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='Portal.project')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SubmissionFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='submissions/')),
                ('original_filename', models.CharField(max_length=255)),
                ('file_type', models.CharField(max_length=50)),
                ('file_size', models.BigIntegerField()),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='Portal.worksubmission')),
            ],
        ),
        migrations.CreateModel(
            name='FreelancerAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_download_files', models.BooleanField(default=False)),
                ('can_submit_work', models.BooleanField(default=False)),
                ('can_communicate', models.BooleanField(default=False)),
                ('access_granted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Portal.projectbid')),
                ('freelancer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Portal.customuser')),
                ('granted_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_granted', to='Portal.customuser')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Portal.project')),
            ],
            options={
                'unique_together': {('project', 'freelancer')},
            },
        ),
    ]
